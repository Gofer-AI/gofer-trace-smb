"""Translate Gofer Trace structured memory into an Obsidian workflow note."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from vault.writer import VaultWriter


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not slug:
        raise ValueError("Workflow name must contain letters or numbers.")
    return slug


def is_sensitive(step: dict[str, Any]) -> tuple[bool, str]:
    if step.get("sensitive"):
        return True, str(step.get("sensitive_reason") or "external write")
    text = f"{step.get('action', '')} {step.get('tool', '')}".casefold()
    categories = {
        "spends money": ("purchase", "order", "pay", "checkout", "invoice"),
        "contacts a customer": ("email", "send", "message", "contact", "notify"),
        "deletes data": ("delete", "remove", "purge"),
        "writes to an external system": ("submit", "publish", "update portal", "external write"),
    }
    for reason, words in categories.items():
        if any(word in text for word in words):
            return True, reason
    return False, ""


def workflow_markdown(workflow: dict[str, Any], source_video: str) -> str:
    steps = workflow.get("steps") or []
    frontmatter = {
        "type": "workflow",
        "source_video": source_video,
        "captured": date.today().isoformat(),
        "steps": len(steps),
        "tools_required": workflow.get("tools_required", []),
    }
    tools = ", ".join(str(tool) for tool in frontmatter["tools_required"])
    yaml_lines = [
        "type: workflow",
        f"source_video: {frontmatter['source_video']}",
        f"captured: {frontmatter['captured']}",
        f"steps: {frontmatter['steps']}",
        f"tools_required: [{tools}]",
    ]
    lines = ["---", *yaml_lines, "---", f"# {workflow['name']}", ""]
    lines.extend(["## Preconditions"] + [f"- {item}" for item in workflow.get("preconditions", [])] + [""])
    lines.append("## Steps")
    sensitive: list[str] = []
    for index, step in enumerate(steps, 1):
        number = int(step.get("n", index))
        lines.append(
            f"{number}. {step['action']} — tool: {step.get('tool', 'unknown')} — "
            f"inputs: {step.get('inputs', 'none')} — expect: {step.get('expected', 'completed')}"
        )
        flagged, reason = is_sensitive(step)
        if flagged:
            sensitive.append(f"- Step {number} — {step['action']} — {reason}")
    lines.extend(["", "## Sensitive actions", *(sensitive or ["- None"]), ""])
    return "\n".join(lines)


def write_workflow(workflow: dict[str, Any], source_video: str, vault_root: str | Path) -> str:
    relative = f"Workflows/{slugify(workflow['name'])}.md"
    VaultWriter(vault_root).write(relative, workflow_markdown(workflow, source_video))
    return relative
