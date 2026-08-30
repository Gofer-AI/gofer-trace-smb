from pathlib import Path

import pytest

from agent.policy import decide


POLICY = """---
type: policy
---
- Reorders under $200 — auto-approve
- $200-$500 — notify owner, proceed after 1h
- Over $500 — block, require explicit approval
- Never reorder from a supplier flagged "disputed" in Suppliers/
"""


def test_340_quotes_verbatim_rule(tmp_path: Path):
    policy = tmp_path / "policy.md"; policy.write_text(POLICY, encoding="utf-8")
    result = decide({"amount": 340}, policy)
    assert result["decision"] == "notify"
    assert result["matched_rule"] == "$200-$500 — notify owner, proceed after 1h"


def test_policy_is_reread_without_restart(tmp_path: Path):
    policy = tmp_path / "policy.md"; policy.write_text(POLICY, encoding="utf-8")
    assert decide({"amount": 340}, policy)["decision"] == "notify"
    policy.write_text(POLICY.replace("under $200", "under $500"), encoding="utf-8")
    assert decide({"amount": 340}, policy)["decision"] == "auto_approve"


@pytest.mark.parametrize("amount,expected", [(199.99, "auto_approve"), (200, "notify"), (500, "notify"), (500.01, "block_require_approval")])
def test_boundaries(tmp_path: Path, amount: float, expected: str):
    policy = tmp_path / "policy.md"; policy.write_text(POLICY, encoding="utf-8")
    assert decide({"amount": amount}, policy)["decision"] == expected


def test_disputed_supplier_always_blocks(tmp_path: Path):
    policy = tmp_path / "policy.md"; policy.write_text(POLICY, encoding="utf-8")
    result = decide({"amount": 100}, policy, supplier_disputed=True)
    assert result["decision"] == "block_require_approval"
    assert "disputed" in result["matched_rule"]

