from pathlib import Path

import pytest

from vault.writer import POLICY_ERROR, VaultAccessError, VaultWriter


@pytest.fixture
def vault(tmp_path: Path) -> VaultWriter:
    for folder in ("Policies", "Workflows", "Log"):
        (tmp_path / folder).mkdir()
    (tmp_path / "changelog.md").write_text("# Log\n")
    return VaultWriter(tmp_path)


def test_allowed_writes(vault: VaultWriter, tmp_path: Path):
    vault.write("Workflows/test.md", "workflow")
    vault.write("Log/run.md", "run")
    vault.append("changelog.md", "entry")
    assert (tmp_path / "Workflows/test.md").read_text() == "workflow"
    assert (tmp_path / "changelog.md").read_text().endswith("entry")


@pytest.mark.parametrize("path", ["Policies/rules.md", "policies/rules.md"])
def test_policy_writes_have_exact_error(vault: VaultWriter, path: str):
    with pytest.raises(VaultAccessError, match=POLICY_ERROR):
        vault.write(path, "bad")


@pytest.mark.parametrize("path", ["../outside.md", "/tmp/outside.md", "Inventory/item.md"])
def test_rejects_unsafe_write_targets(vault: VaultWriter, path: str):
    with pytest.raises(VaultAccessError):
        vault.write(path, "bad")


def test_rejects_symlink(vault: VaultWriter, tmp_path: Path):
    (tmp_path / "Log/link").symlink_to(tmp_path.parent, target_is_directory=True)
    with pytest.raises(VaultAccessError):
        vault.write("Log/link/escape.md", "bad")

