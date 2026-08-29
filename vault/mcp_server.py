"""MCP tools exposing the vault to TrueForge."""
from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from vault.writer import VaultAccessError, VaultWriter

VAULT_ROOT = Path(os.getenv("GOFER_VAULT", Path(__file__).parents[1] / "demo-vault"))
writer = VaultWriter(VAULT_ROOT)
mcp = FastMCP("gofer-trace-vault")


@mcp.tool()
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


@mcp.tool()
def vault_read(path: str) -> str:
    """Read a note; reads are unrestricted within the vault."""
    return writer.resolve(path).read_text(encoding="utf-8")


@mcp.tool()
def vault_list(folder: str) -> list[str]:
    """List Markdown note titles in a vault folder."""
    directory = writer.resolve(folder, must_exist=False)
    if not directory.is_dir():
        raise VaultAccessError(f"Vault folder not found: {folder}")
    return sorted(path.stem for path in directory.glob("*.md") if not path.is_symlink())


@mcp.tool()
def vault_write(path: str, content: str) -> str:
    """Write only Workflows/ or Log/ notes."""
    writer.write(path, content)
    return f"Wrote {path}"


@mcp.tool()
def vault_append(path: str, text: str) -> str:
    """Append only to changelog.md."""
    writer.append(path, text)
    return f"Appended {path}"


if __name__ == "__main__":
    mcp.run(transport="stdio")

