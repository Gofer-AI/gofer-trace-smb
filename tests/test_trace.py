import json
from pathlib import Path

from trace.to_markdown import is_sensitive, workflow_markdown, write_workflow


def fixture():
    return json.loads(Path("samples/weekly-reorder.json").read_text())


def test_trace_schema_maps_to_workflow_note():
    note = workflow_markdown(fixture(), "samples/weekly-reorder.mp4")
    assert "steps: 6" in note
    assert "## Sensitive actions" in note
    assert "Step 5" in note and "spends money" in note


def test_semantic_sensitivity_fallback():
    assert is_sensitive({"action": "Send customer email", "tool": "email"}) == (True, "contacts a customer")


def test_writer_uses_workflows_boundary(tmp_path: Path):
    (tmp_path / "Workflows").mkdir()
    path = write_workflow(fixture(), "samples/weekly-reorder.mp4", tmp_path)
    assert path == "Workflows/weekly-supplier-reorder.md"
    assert (tmp_path / path).exists()

