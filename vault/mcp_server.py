"""MCP tools exposing the vault to TrueForge."""
from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse

from agent.enrich import current_prices
from agent.qodo import audit_status, request_review
from trace.intake import clear_recording, extract_staged_recording, recording_status, stage_recording
from trace.upload import MAX_RECORDING_BYTES, RecordingUploadError
from vault.writer import VaultAccessError, VaultWriter

VAULT_ROOT = Path(os.getenv("GOFER_VAULT", Path(__file__).parents[1] / "demo-vault"))
writer = VaultWriter(VAULT_ROOT)
mcp = FastMCP(
    "gofer-trace-vault",
    host=os.getenv("GOFER_MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("GOFER_MCP_PORT", "8001")),
    streamable_http_path="/mcp",
    json_response=True,
)


async def _read_recording_upload(request: Request) -> bytes | JSONResponse:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_RECORDING_BYTES:
                return JSONResponse({"error": "The recording exceeds the 250 MB local upload limit."}, status_code=413)
        except ValueError:
            return JSONResponse({"error": "Invalid Content-Length header."}, status_code=400)

    chunks: list[bytes] = []
    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > MAX_RECORDING_BYTES:
            return JSONResponse({"error": "The recording exceeds the 250 MB local upload limit."}, status_code=413)
        chunks.append(chunk)
    return b"".join(chunks)


@mcp.custom_route("/recordings", methods=["POST"])
async def stage_recording_route(request: Request) -> JSONResponse:
    """Stage raw video locally before a TrueForge turn invokes the extraction tool."""
    content = await _read_recording_upload(request)
    if isinstance(content, JSONResponse):
        return content
    try:
        result = stage_recording(
            content,
            filename=request.headers.get("x-gofer-filename", "screen-recording.webm"),
            content_type=request.headers.get("content-type", "application/octet-stream"),
        )
    except RecordingUploadError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse(result, status_code=201)


@mcp.custom_route("/recordings/{upload_id}", methods=["GET", "DELETE"])
async def recording_status_route(request: Request) -> JSONResponse:
    upload_id = request.path_params["upload_id"]
    try:
        if request.method == "DELETE":
            clear_recording(upload_id)
            return JSONResponse({"status": "cleared"})
        return JSONResponse(recording_status(upload_id))
    except RecordingUploadError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
def extract_workflow_from_recording(upload_id: str) -> dict:
    """Consume a locally staged screen recording and create its governed workflow note."""
    return extract_staged_recording(upload_id, vault_root=VAULT_ROOT)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def vault_search(query: str) -> list[dict[str, str]]:
    """Search all Markdown notes by title and content."""
    needle = query.strip().casefold()
    if not needle:
        return []
    matches: list[dict[str, str]] = []
    for note in sorted(VAULT_ROOT.rglob("*.md")):
        if note.is_symlink():
            continue
        content = note.read_text(encoding="utf-8")
        haystack = content.casefold()
        index = haystack.find(needle)
        if needle in note.stem.casefold() or index >= 0:
            index = max(index, 0)
            start, end = max(0, index - 80), min(len(content), index + len(query) + 160)
            matches.append({
                "title": note.stem,
                "path": note.relative_to(VAULT_ROOT).as_posix(),
                "excerpt": " ".join(content[start:end].split()),
            })
    return matches


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def vault_read(path: str) -> str:
    """Read a note; reads are unrestricted within the vault."""
    return writer.resolve(path).read_text(encoding="utf-8")


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def vault_list(folder: str) -> list[str]:
    """List Markdown note titles in a vault folder."""
    directory = writer.resolve(folder, must_exist=False)
    if not directory.is_dir():
        raise VaultAccessError(f"Vault folder not found: {folder}")
    return sorted(path.stem for path in directory.glob("*.md") if not path.is_symlink())


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
def vault_write(path: str, content: str) -> str:
    """Write an agent-maintained operations note; Company and Policies are read-only."""
    writer.write(path, content)
    return f"Wrote {path}"


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
def vault_append(path: str, text: str) -> str:
    """Append to the audit changelog or an agent-maintained operations note."""
    writer.append(path, text)
    return f"Appended {path}"


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def pricing_lookup(product: str) -> dict:
    """Get supplier prices and whether they came from a live source or the offline cache."""
    prices, source = current_prices(product)
    return {"product": product, "prices": prices, "source": source}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
def qodo_audit_status(pr_url: str) -> dict:
    """Read Qodo Merge feedback for a GitHub pull request; feedback is advisory."""
    return audit_status(pr_url)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        openWorldHint=True,
    )
)
def qodo_request_review(pr_url: str, agent_request: str) -> dict:
    """Post a human-approved Qodo review request that ties a PR to an agent request."""
    return request_review(pr_url, agent_request)


if __name__ == "__main__":
    transport = os.getenv("GOFER_MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)

