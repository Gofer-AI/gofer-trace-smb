"""Short-lived local staging for recordings orchestrated by TrueForge."""
from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from trace.upload import MAX_RECORDING_BYTES, RecordingUploadError, process_recording, safe_recording_name

INTAKE_TTL_SECONDS = 24 * 60 * 60
INTAKE_ROOT = Path(
    os.getenv("GOFER_RECORDING_INTAKE", Path(tempfile.gettempdir()) / "gofer-recording-intake")
)


def _upload_id(value: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise RecordingUploadError("Invalid recording upload ID.") from exc
    if str(parsed) != value:
        raise RecordingUploadError("Invalid recording upload ID.")
    return value


def _paths(upload_id: str, root: Path) -> tuple[Path, Path]:
    safe_id = _upload_id(upload_id)
    return root / f"{safe_id}.video", root / f"{safe_id}.json"


def _write_status(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    temporary.replace(path)


def prune_expired_recordings(*, root: Path = INTAKE_ROOT) -> None:
    if not root.exists():
        return
    cutoff = time.time() - INTAKE_TTL_SECONDS
    for status_path in root.glob("*.json"):
        try:
            payload = json.loads(status_path.read_text(encoding="utf-8"))
            created_at = float(payload.get("created_at", 0))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            created_at = 0
        if created_at >= cutoff:
            continue
        video_path = status_path.with_suffix(".video")
        video_path.unlink(missing_ok=True)
        status_path.unlink(missing_ok=True)


def stage_recording(
    content: bytes,
    *,
    filename: str,
    content_type: str,
    root: Path = INTAKE_ROOT,
) -> dict[str, Any]:
    if not content:
        raise RecordingUploadError("The recording is empty.")
    if len(content) > MAX_RECORDING_BYTES:
        raise RecordingUploadError("The recording exceeds the 250 MB local upload limit.")

    safe_name = safe_recording_name(filename, content_type)
    root.mkdir(parents=True, exist_ok=True)
    prune_expired_recordings(root=root)
    upload_id = str(uuid.uuid4())
    video_path, status_path = _paths(upload_id, root)
    video_path.write_bytes(content)
    status = {
        "upload_id": upload_id,
        "status": "staged",
        "filename": safe_name,
        "content_type": content_type.partition(";")[0].strip().casefold(),
        "size": len(content),
        "created_at": time.time(),
        "raw_recording_retained": True,
    }
    _write_status(status_path, status)
    return status


def recording_status(upload_id: str, *, root: Path = INTAKE_ROOT) -> dict[str, Any]:
    _video_path, status_path = _paths(upload_id, root)
    if not status_path.is_file():
        raise RecordingUploadError("Recording upload not found or already cleared.")
    try:
        return json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecordingUploadError("Recording upload status is unavailable.") from exc


def clear_recording(upload_id: str, *, root: Path = INTAKE_ROOT) -> None:
    video_path, status_path = _paths(upload_id, root)
    video_path.unlink(missing_ok=True)
    status_path.unlink(missing_ok=True)


def extract_staged_recording(
    upload_id: str,
    *,
    vault_root: str | Path,
    root: Path = INTAKE_ROOT,
    processor: Callable[..., dict[str, Any]] = process_recording,
) -> dict[str, Any]:
    video_path, status_path = _paths(upload_id, root)
    status = recording_status(upload_id, root=root)
    if status.get("status") != "staged" or not video_path.is_file():
        raise RecordingUploadError("Recording upload is not available for extraction.")

    status["status"] = "processing"
    _write_status(status_path, status)
    try:
        result = processor(
            video_path.read_bytes(),
            filename=str(status["filename"]),
            content_type=str(status["content_type"]),
            vault_root=vault_root,
        )
    except Exception as exc:
        status.update(
            status="failed",
            error=str(exc),
            raw_recording_retained=False,
        )
        _write_status(status_path, status)
        raise
    finally:
        video_path.unlink(missing_ok=True)

    completed = {
        **status,
        **result,
        "upload_id": upload_id,
        "status": "created",
        "raw_recording_retained": False,
    }
    _write_status(status_path, completed)
    return completed
