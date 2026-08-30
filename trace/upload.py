"""Validate and process browser screen recordings."""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Callable

from trace.extract import extract_workflow
from trace.to_markdown import write_workflow

MAX_RECORDING_BYTES = 250 * 1024 * 1024
ALLOWED_VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}


class RecordingUploadError(ValueError):
    """Raised when a recording upload is unsafe or unsupported."""


def safe_recording_name(filename: str, content_type: str) -> str:
    media_type = content_type.partition(";")[0].strip().casefold()
    suffix = ALLOWED_VIDEO_TYPES.get(media_type)
    if suffix is None:
        raise RecordingUploadError("Upload a WebM, MP4, or QuickTime screen recording.")
    stem = Path(filename or "screen-recording").stem
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-.")[:100]
    return f"{stem or 'screen-recording'}{suffix}"


def process_recording(
    content: bytes,
    *,
    filename: str,
    content_type: str,
    vault_root: str | Path,
    extractor: Callable[[str | Path], dict] = extract_workflow,
) -> dict:
    if not content:
        raise RecordingUploadError("The recording is empty.")
    if len(content) > MAX_RECORDING_BYTES:
        raise RecordingUploadError("The recording exceeds the 250 MB local upload limit.")

    safe_name = safe_recording_name(filename, content_type)
    with tempfile.TemporaryDirectory(prefix="gofer-recording-") as directory:
        recording = Path(directory) / safe_name
        recording.write_bytes(content)
        workflow = extractor(recording)

    workflow_path = write_workflow(workflow, safe_name, vault_root)
    return {
        "status": "created",
        "workflow_path": workflow_path,
        "workflow_name": workflow["name"],
        "steps": len(workflow.get("steps") or []),
        "source_recording": safe_name,
        "raw_recording_retained": False,
        "extraction_mode": "offline_fixture" if os.getenv("GOFER_OFFLINE") == "1" else "live",
    }
