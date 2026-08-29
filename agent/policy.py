"""Live parser for owner-authored spending policy."""
from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path
from typing import Literal, TypedDict


class Decision(TypedDict):
    decision: Literal["auto_approve", "notify", "block_require_approval"]
    matched_rule: str
    amount: float


def _rules(path: Path) -> list[str]:
    # Intentionally re-read on every decision. The owner can reprogram the agent live.
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("- ")]


def decide(action: dict, policy_path: str | Path, supplier_disputed: bool = False) -> Decision:
    amount = Decimal(str(action.get("amount", "0")))
    rules = _rules(Path(policy_path))
    if supplier_disputed:
        line = next((line for line in rules if "disputed" in line.casefold()), None)
        if line:
            return {"decision": "block_require_approval", "matched_rule": line[2:], "amount": float(amount)}
    for line in rules:
        normalized = line.casefold().replace(",", "")
        under = re.search(r"under \$(\d+)", normalized)
        band = re.search(r"\$(\d+)\s*[-–—]\s*\$?(\d+)", normalized)
        over = re.search(r"over \$(\d+)", normalized)
        matched = bool(under and amount < Decimal(under.group(1))) or bool(
            band and Decimal(band.group(1)) <= amount <= Decimal(band.group(2))
        ) or bool(over and amount > Decimal(over.group(1)))
        if matched:
            if "auto-approve" in normalized:
                decision = "auto_approve"
            elif "notify" in normalized:
                decision = "notify"
            else:
                decision = "block_require_approval"
            return {"decision": decision, "matched_rule": line[2:], "amount": float(amount)}
    raise ValueError(f"No policy rule covers ${amount}; refusing to act.")

