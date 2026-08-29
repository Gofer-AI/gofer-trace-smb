"""Three-pane Gradio demo for Gofer Trace SMB."""
from __future__ import annotations

import html
import os
from pathlib import Path

import gradio as gr

from agent.runner import run_weekly_reorder

ROOT = Path(__file__).parent
VAULT = ROOT / "demo-vault"
os.environ.setdefault("GOFER_OFFLINE", "1")

STEPS = ["Read inventory", "Check threshold", "Read supplier", "Enrich prices", "Govern action", "Record run"]


def timeline(active: int = -1) -> str:
    return "".join(f'<div class="step {"active" if i == active else ""}"><b>{i + 1:02}</b><span>{html.escape(step)}</span></div>' for i, step in enumerate(STEPS))


def tree(selected: str = "") -> str:
    rows = []
    for note in sorted(VAULT.rglob("*.md")):
        relative = note.relative_to(VAULT).as_posix()
        rows.append(f'<div class="file {"selected" if relative == selected else ""}">◇ {html.escape(relative)}</div>')
    return "".join(rows)


def render_events(events: list[tuple[str, str, str]]) -> str:
    return "".join(f'<div class="event {kind}"><span>{html.escape(kind.upper())}</span>{html.escape(message).replace(chr(10), "<br>")}</div>' for kind, message, _ in events)


def start():
    result = run_weekly_reorder(False)
    selected = result.events[-2][2] if result.events else ""
    note = (VAULT / selected).read_text(encoding="utf-8") if selected else ""
    return timeline(4), render_events(result.events), tree(selected), note, gr.update(visible=result.status == "awaiting_approval"), result.status


def approve():
    result = run_weekly_reorder(True)
    selected = result.events[-1][2]
    note = (VAULT / selected).read_text(encoding="utf-8")
    return timeline(5), render_events(result.events), tree(selected), note, gr.update(visible=False), result.status


def open_note(path: str):
    clean = path.strip().replace("\\", "/")
    candidate = (VAULT / clean).resolve()
    if VAULT.resolve() not in candidate.parents or not candidate.is_file():
        return "Choose a valid vault note."
    return candidate.read_text(encoding="utf-8")


CSS = """
body,.gradio-container{background:#09100f!important;color:#e8f0ec}.gradio-container{max-width:1500px!important}
.hero{padding:20px 4px}.hero h1{font-size:34px;margin:0;color:#f4f7f5}.hero p{color:#86a096;font-size:16px}
.pane{border:1px solid #263b34!important;border-radius:14px!important;background:#101a17!important;padding:16px!important;min-height:590px}
.step{display:flex;gap:14px;padding:17px;margin:8px 0;border-left:3px solid #2d443c;background:#14211d;border-radius:4px}.step b{color:#6f8f83}.step span{font-weight:600}.step.active{border-color:#5ee0a1;background:#19352a;box-shadow:0 0 18px #35b77a22}.step.active b{color:#5ee0a1}
.event{padding:13px;margin:9px 0;background:#14211d;border-radius:8px;border:1px solid #263b34}.event span{font-size:10px;letter-spacing:1px;color:#72b99b;display:block}.event.gate{background:#352818;border-color:#e5a84b;color:#ffe4b5}.event.gate span{color:#ffc568}.event.write{border-color:#5ee0a1}
.file{font-family:monospace;padding:7px 10px;color:#9fb5ad}.file.selected{background:#214b39;color:#75ecae;border-radius:5px}.note textarea{font-family:ui-monospace,monospace!important;background:#0b1411!important}
.status{font-size:12px;color:#5ee0a1}.primary{background:#45d58e!important;color:#07110d!important;border:0!important;font-weight:700!important}
"""

with gr.Blocks(css=CSS, title="Gofer Trace SMB") as demo:
    gr.HTML('<div class="hero"><h1>Gofer Trace <span style="color:#5ee0a1">SMB</span></h1><p>Show it once. It remembers. It asks before it acts.</p></div>')
    with gr.Row(equal_height=True):
        with gr.Column(elem_classes="pane"):
            gr.Markdown("### WATCH → WORKFLOW")
            timeline_html = gr.HTML(timeline())
            run = gr.Button("▶ Do the weekly reorder", variant="primary", elem_classes="primary")
            rerun = gr.Button("↻ Re-run with current policy")
        with gr.Column(elem_classes="pane"):
            gr.Markdown("### AGENT ACTIVITY")
            activity = gr.HTML('<div class="event"><span>READY</span>Waiting for a workflow…</div>')
            approve_button = gr.Button("Approve simulated order", visible=False, variant="primary")
            status = gr.Textbox(label="Run status", value="ready", interactive=False, elem_classes="status")
        with gr.Column(elem_classes="pane"):
            gr.Markdown("### LIVE VAULT MEMORY")
            file_tree = gr.HTML(tree())
            path = gr.Textbox(label="Open note", value="Policies/spending-limits.md")
            note = gr.Code(value=(VAULT / "Policies/spending-limits.md").read_text(), language="markdown", label="Note being consulted", elem_classes="note")
            open_button = gr.Button("Open vault note")
    outputs = [timeline_html, activity, file_tree, note, approve_button, status]
    run.click(start, outputs=outputs); rerun.click(start, outputs=outputs); approve_button.click(approve, outputs=outputs)
    open_button.click(open_note, inputs=path, outputs=note)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
