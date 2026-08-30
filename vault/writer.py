"""Filesystem boundary for the human-owned Obsidian vault."""
from __future__ import annotations

from pathlib import Path, PurePosixPath

POLICY_ERROR = "Policies are owned by the human operator and cannot be modified by the agent."
COMPANY_ERROR = "Company facts are owned by the human operator and cannot be modified by the agent."
WRITABLE_ROOTS = {
    "Daily",
    "Decisions",
    "Log",
    "Meetings",
    "News",
    "Projects",
    "Tasks",
    "Workflows",
}


class VaultAccessError(ValueError):
    """Raised when a requested vault operation violates the boundary."""


class VaultWriter:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def resolve(self, relative: str, *, must_exist: bool = True) -> Path:
        raw = str(relative).replace("\\", "/")
        posix = PurePosixPath(raw)
        if not raw or posix.is_absolute() or ".." in posix.parts:
            raise VaultAccessError("Vault paths must be safe relative paths.")
        candidate = self.root.joinpath(*posix.parts)
        # Existing parents may not be symlinks. This also catches a symlink leaf.
        cursor = self.root
        for part in posix.parts:
            cursor = cursor / part
            if cursor.exists() and cursor.is_symlink():
                raise VaultAccessError("Symlinks are not allowed in vault paths.")
        resolved = candidate.resolve(strict=False)
        if resolved != self.root and self.root not in resolved.parents:
            raise VaultAccessError("Path escapes the vault root.")
        if must_exist and not resolved.is_file():
            raise VaultAccessError(f"Vault note not found: {raw}")
        return resolved

    @staticmethod
    def _is_policy(path: str) -> bool:
        return bool(PurePosixPath(path.replace("\\", "/")).parts) and PurePosixPath(
            path.replace("\\", "/")
        ).parts[0].casefold() == "policies"

    def write(self, relative: str, content: str) -> None:
        if self._is_policy(relative):
            raise VaultAccessError(POLICY_ERROR)
        parts = PurePosixPath(relative.replace("\\", "/")).parts
        if parts and parts[0].casefold() == "company":
            raise VaultAccessError(COMPANY_ERROR)
        if not parts or parts[0] not in WRITABLE_ROOTS or not relative.endswith(".md"):
            allowed = ", ".join(f"{root}/" for root in sorted(WRITABLE_ROOTS))
            raise VaultAccessError(f"vault_write is restricted to Markdown notes under: {allowed}")
        path = self.resolve(relative, must_exist=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def append(self, relative: str, text: str) -> None:
        if self._is_policy(relative):
            raise VaultAccessError(POLICY_ERROR)
        normalized = relative.replace("\\", "/")
        parts = PurePosixPath(normalized).parts
        if parts and parts[0].casefold() == "company":
            raise VaultAccessError(COMPANY_ERROR)
        allowed = normalized == "changelog.md" or (
            bool(parts) and parts[0] in WRITABLE_ROOTS and normalized.endswith(".md")
        )
        if not allowed:
            raise VaultAccessError("vault_append is restricted to changelog.md and agent-maintained Markdown notes.")
        path = self.resolve(normalized, must_exist=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text)

