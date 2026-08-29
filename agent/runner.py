"""The one demo path: remember, enrich, govern, simulate, and record."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

from agent.enrich import current_prices
from agent.policy import decide
from vault.mcp_server import vault_append, vault_read, vault_search, vault_write

EventSink = Callable[[str, str, str], None]


def _frontmatter(note: str) -> dict:
    if not note.startswith("---"):
        return {}
    result = {}
    for line in note.split("---", 2)[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


@dataclass
class RunResult:
    status: str
    proposal: dict
    decision: dict
    run_id: str
    events: list[tuple[str, str, str]] = field(default_factory=list)


def run_weekly_reorder(approve: bool = False, sink: EventSink | None = None) -> RunResult:
    events: list[tuple[str, str, str]] = []
    def emit(kind: str, message: str, path: str = "") -> None:
        events.append((kind, message, path))
        if sink:
            sink(kind, message, path)

    emit("read", "Reading vault catalog", "index.md"); vault_read("index.md")
    found = vault_search("Weekly supplier reorder")
    workflow_path = found[0]["path"] if found else "Workflows/weekly-reorder.md"
    emit("read", "Consulting learned workflow", workflow_path); vault_read(workflow_path)
    emit("read", "Checking Acme supplier record", "Suppliers/acme.md")
    supplier = _frontmatter(vault_read("Suppliers/acme.md"))
    emit("read", "Loading live owner policy", "Policies/spending-limits.md")
    vault_read("Policies/spending-limits.md")
    prices, provenance = current_prices("widgets")
    # Inventory need fixes quantity; enrichment selects the affordable supplier and price.
    quantity = 40
    chosen = min((name, price) for name, price in prices.items() if name != "borealis")
    proposal = {"supplier": chosen[0].title(), "quantity": quantity, "unit_price": chosen[1], "amount": round(quantity * chosen[1], 2), "pricing_source": provenance}
    emit("tool", f"Pricing ({provenance}) produced {quantity} × ${chosen[1]:.2f} = ${proposal['amount']:.2f}")
    policy = Path(__file__).parents[1] / "demo-vault/Policies/spending-limits.md"
    decision = decide(proposal, policy, supplier.get("status") == "disputed")
    needs_gate = decision["decision"] != "auto_approve"
    if needs_gate and not approve:
        emit("gate", f"Approval required for ${proposal['amount']:.2f}\nPolicy: “{decision['matched_rule']}”")
        return RunResult("awaiting_approval", proposal, decision, "pending", events)
    run_id = uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    emit("sandbox", "Simulated purchase order created — no money moved")
    log_path = f"Log/{now.date().isoformat()}-reorder-{run_id}.md"
    log = f"# Weekly reorder — {run_id}\n\n**SIMULATED — NO MONEY MOVED**\n\n- Supplier: {proposal['supplier']}\n- Quantity: {quantity}\n- Unit price: ${chosen[1]:.2f}\n- Total: ${proposal['amount']:.2f}\n- Pricing: {provenance}\n- Decision: {decision['decision']}\n- Matched policy: {decision['matched_rule']}\n"
    vault_write(log_path, log)
    vault_append("changelog.md", f"\n- {now.isoformat()} — Simulated {quantity}-widget reorder for ${proposal['amount']:.2f}; see [[{log_path[:-3]}]].")
    emit("write", "Run logged and changelog appended", log_path)
    return RunResult("completed", proposal, decision, run_id, events)
