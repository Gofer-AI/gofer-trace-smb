"""Extract representative frames and convert a screen recording to workflow JSON."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, Field


class Step(BaseModel):
    n: int
    action: str
    tool: str
    inputs: str
    expected: str
    sensitive: bool
    sensitive_reason: str | None = None


class Workflow(BaseModel):
    name: str
    steps: list[Step] = Field(min_length=1)
    tools_required: list[str]
    preconditions: list[str]


def video_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_frames(video: str | Path, destination: str | Path) -> list[Path]:
    output = Path(destination) / "frame-%03d.jpg"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video), "-vf", "fps=1/2,scale=768:-2", "-frames:v", "20", str(output)],
        check=True,
    )
    return sorted(Path(destination).glob("frame-*.jpg"))


def extract_workflow(video: str | Path, cache_dir: str | Path = "cache") -> dict:
    cache = Path(cache_dir) / f"trace-{video_hash(video)}.json"
    fallback = Path("samples/weekly-reorder.json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    if os.getenv("GOFER_OFFLINE") == "1":
        return json.loads(fallback.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as directory:
        frames = extract_frames(video, directory)
        images = [{"type": "input_image", "image_url": "data:image/jpeg;base64," + base64.b64encode(frame.read_bytes()).decode()} for frame in frames]
        response = OpenAI().responses.parse(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            input=[{"role": "system", "content": "Infer the demonstrated SOP. Mark spending, customer contact, deletion, and external writes sensitive."},
                   {"role": "user", "content": [{"type": "input_text", "text": "Turn these chronological frames into one workflow."}, *images]}],
            text_format=Workflow,
        )
        workflow = response.output_parsed.model_dump()
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(workflow, indent=2), encoding="utf-8")
    return workflow

