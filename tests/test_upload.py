from pathlib import Path

import pytest
from starlette.testclient import TestClient

import trace.upload as upload
from trace.intake import (
    clear_recording,
    extract_staged_recording,
    recording_status,
    stage_recording,
)
from trace.upload import RecordingUploadError, process_recording, safe_recording_name
from vault import mcp_server


def workflow_fixture(_path: str | Path) -> dict:
    return {
        "name": "Recorded task",
        "steps": [
            {
                "n": 1,
                "action": "Open dashboard",
                "tool": "browser",
                "inputs": "dashboard",
                "expected": "dashboard visible",
                "sensitive": False,
            }
        ],
        "tools_required": ["browser"],
        "preconditions": ["Signed in"],
    }


def test_safe_recording_name_normalizes_untrusted_filename():
    assert safe_recording_name("../Quarterly demo?.WEBM", "video/webm;codecs=vp9") == "Quarterly-demo.webm"


def test_rejects_unsupported_media_type():
    with pytest.raises(RecordingUploadError, match="WebM, MP4, or QuickTime"):
        safe_recording_name("demo.avi", "video/x-msvideo")


def test_process_recording_writes_workflow_and_removes_temporary_video(tmp_path: Path):
    (tmp_path / "Workflows").mkdir()
    seen_path: Path | None = None

    def extractor(path: str | Path) -> dict:
        nonlocal seen_path
        seen_path = Path(path)
        assert seen_path.read_bytes() == b"webm-data"
        return workflow_fixture(path)

    result = process_recording(
        b"webm-data",
        filename="demo.webm",
        content_type="video/webm",
        vault_root=tmp_path,
        extractor=extractor,
    )
    assert result["workflow_path"] == "Workflows/recorded-task.md"
    assert result["raw_recording_retained"] is False
    assert result["extraction_mode"] in {"offline_fixture", "live"}
    assert (tmp_path / result["workflow_path"]).is_file()
    assert seen_path is not None and not seen_path.exists()


def test_rejects_empty_and_oversized_recordings(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(upload, "MAX_RECORDING_BYTES", 4)
    for content in (b"", b"12345"):
        with pytest.raises(RecordingUploadError):
            process_recording(
                content,
                filename="demo.webm",
                content_type="video/webm",
                vault_root=tmp_path,
                extractor=workflow_fixture,
            )


def test_http_route_only_stages_recording_for_trueforge(monkeypatch):
    monkeypatch.setattr(
        mcp_server,
        "stage_recording",
        lambda *_args, **_kwargs: {
            "upload_id": "2d7b2c8f-8993-4dd7-954d-7bd9ad792af0",
            "status": "staged",
        },
    )
    with TestClient(mcp_server.mcp.streamable_http_app()) as client:
        stage_response = client.post(
            "/recordings",
            content=b"webm-data",
            headers={"Content-Type": "video/webm", "X-Gofer-Filename": "demo.webm"},
        )
    assert stage_response.status_code == 201
    assert stage_response.json()["status"] == "staged"


def test_trueforge_intake_stages_then_consumes_recording(tmp_path: Path):
    intake_root = tmp_path / "intake"
    vault_root = tmp_path / "vault"
    (vault_root / "Workflows").mkdir(parents=True)
    staged = stage_recording(
        b"webm-data",
        filename="demo.webm",
        content_type="video/webm",
        root=intake_root,
    )
    upload_id = staged["upload_id"]
    assert recording_status(upload_id, root=intake_root)["status"] == "staged"
    assert (intake_root / f"{upload_id}.video").read_bytes() == b"webm-data"

    def processor(content: bytes, **_kwargs) -> dict:
        assert content == b"webm-data"
        return {
            "workflow_path": "Workflows/recorded-task.md",
            "workflow_name": "Recorded task",
            "steps": 1,
            "extraction_mode": "offline_fixture",
            "raw_recording_retained": False,
        }

    result = extract_staged_recording(
        upload_id,
        vault_root=vault_root,
        root=intake_root,
        processor=processor,
    )
    assert result["status"] == "created"
    assert result["workflow_path"] == "Workflows/recorded-task.md"
    assert not (intake_root / f"{upload_id}.video").exists()
    assert recording_status(upload_id, root=intake_root)["raw_recording_retained"] is False

    with pytest.raises(RecordingUploadError, match="not available"):
        extract_staged_recording(
            upload_id,
            vault_root=vault_root,
            root=intake_root,
            processor=processor,
        )


def test_trueforge_intake_deletes_video_when_processing_fails(tmp_path: Path):
    intake_root = tmp_path / "intake"
    staged = stage_recording(
        b"webm-data",
        filename="demo.webm",
        content_type="video/webm",
        root=intake_root,
    )

    def failing_processor(*_args, **_kwargs):
        raise RuntimeError("extractor unavailable")

    with pytest.raises(RuntimeError, match="extractor unavailable"):
        extract_staged_recording(
            staged["upload_id"],
            vault_root=tmp_path,
            root=intake_root,
            processor=failing_processor,
        )
    status = recording_status(staged["upload_id"], root=intake_root)
    assert status["status"] == "failed"
    assert status["raw_recording_retained"] is False
    assert not (intake_root / f"{staged['upload_id']}.video").exists()


def test_trueforge_intake_clear_removes_raw_video_and_status(tmp_path: Path):
    staged = stage_recording(
        b"webm-data",
        filename="demo.webm",
        content_type="video/webm",
        root=tmp_path,
    )
    clear_recording(staged["upload_id"], root=tmp_path)
    assert not list(tmp_path.iterdir())
