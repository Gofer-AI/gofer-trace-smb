#!/usr/bin/env python3
"""Check whether this machine is ready to run the hackathon demo."""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_NOTES = (
    "index.md",
    "changelog.md",
    "Policies/spending-limits.md",
    "Suppliers/acme.md",
    "Suppliers/borealis.md",
    "Inventory/widgets.md",
    "Workflows/weekly-reorder.md",
    "Company/profile.md",
    "Company/news-watchlist.md",
    "Tasks/Today.md",
    "Tasks/Inbox.md",
    "News/README.md",
    "Workflows/daily-company-brief.md",
    "Workflows/qodo-request-audit.md",
)
REQUIRED_MODULES = ("mcp", "openai", "pydantic", "dotenv")


def check(label: str, passed: bool, guidance: str = "") -> bool:
    icon = "PASS" if passed else "FAIL"
    suffix = f" — {guidance}" if guidance else ""
    print(f"[{icon}] {label}{suffix}")
    return passed


def warn(label: str, guidance: str) -> bool:
    print(f"[WARN] {label} — {guidance}")
    return True


def main() -> int:
    results: list[bool] = []
    offline = os.getenv("GOFER_OFFLINE") == "1"
    version_ok = sys.version_info[:2] == (3, 11)
    results.append(check("Python 3.11", version_ok, f"found {sys.version.split()[0]}"))
    ffmpeg_ready = shutil.which("ffmpeg") is not None
    if offline and not ffmpeg_ready:
        results.append(warn("ffmpeg", "not installed; the committed workflow fixture will be used"))
    else:
        results.append(check("ffmpeg", ffmpeg_ready, "install ffmpeg for live video extraction"))

    missing_modules = [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]
    results.append(check("Python dependencies", not missing_modules, "missing: " + ", ".join(missing_modules) if missing_modules else ""))

    missing_notes = [note for note in REQUIRED_NOTES if not (ROOT / "demo-vault" / note).is_file()]
    results.append(check("Seeded demo vault", not missing_notes, "missing: " + ", ".join(missing_notes) if missing_notes else ""))
    results.append(check("Offline pricing cache", (ROOT / "cache/weekly-reorder-fallback.json").is_file()))
    results.append(check("Offline workflow fixture", (ROOT / "samples/weekly-reorder.json").is_file()))
    results.append(check("TrueForge MCP configuration", (ROOT / "trueforge.mcp.json").is_file()))

    live_keys = bool(os.getenv("OPENAI_API_KEY") and os.getenv("BRIGHTDATA_API_KEY") and os.getenv("BRIGHTDATA_DATASET_ID"))
    runtime_ready = offline or live_keys
    results.append(check(
        "Runtime mode configured",
        runtime_ready,
        "" if runtime_ready else "set GOFER_OFFLINE=1 or configure all live API keys",
    ))

    if all(results):
        print("\nReady: start the MCP service with `python app.py`, then run TrueForge and the SDK UI.")
        return 0
    print("\nNot ready yet. Resolve FAIL items, then run this preflight again.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
