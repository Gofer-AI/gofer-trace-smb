from pathlib import Path

import pytest

from vault.writer import COMPANY_ERROR, POLICY_ERROR, VaultAccessError, VaultWriter


@pytest.fixture
def vault(tmp_path: Path) -> VaultWriter:
    for folder in ("Company", "Policies", "Workflows", "Log", "Tasks", "News"):
        (tmp_path / folder).mkdir()
    (tmp_path / "changelog.md").write_text("# Log\n")
    return VaultWriter(tmp_path)


def test_allowed_writes(vault: VaultWriter, tmp_path: Path):
    vault.write("Workflows/test.md", "workflow")
    vault.write("Log/run.md", "run")
    vault.write("Tasks/Today.md", "- [ ] ship")
    vault.write("News/brief.md", "sourced brief")
    vault.append("Tasks/Inbox.md", "- [ ] triage\n")
    vault.append("changelog.md", "entry")
    assert (tmp_path / "Workflows/test.md").read_text() == "workflow"
    assert (tmp_path / "changelog.md").read_text().endswith("entry")
    assert (tmp_path / "Tasks/Inbox.md").read_text() == "- [ ] triage\n"


@pytest.mark.parametrize("path", ["Policies/rules.md", "policies/rules.md"])
def test_policy_writes_have_exact_error(vault: VaultWriter, path: str):
    with pytest.raises(VaultAccessError, match=POLICY_ERROR):
        vault.write(path, "bad")


@pytest.mark.parametrize("operation", ["write", "append"])
def test_company_facts_are_human_owned(vault: VaultWriter, operation: str):
    with pytest.raises(VaultAccessError, match=COMPANY_ERROR):
        getattr(vault, operation)("Company/profile.md", "bad")


@pytest.mark.parametrize("path", ["../outside.md", "/tmp/outside.md", "Inventory/item.md", "Templates/note.md"])
def test_rejects_unsafe_write_targets(vault: VaultWriter, path: str):
    with pytest.raises(VaultAccessError):
        vault.write(path, "bad")


def test_rejects_symlink(vault: VaultWriter, tmp_path: Path):
    try:
        (tmp_path / "Log/link").symlink_to(tmp_path.parent, target_is_directory=True)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows symlink creation requires Developer Mode or elevation")
        raise
    with pytest.raises(VaultAccessError):
        vault.write("Log/link/escape.md", "bad")

