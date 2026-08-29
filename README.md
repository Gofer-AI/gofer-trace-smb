# Gofer Trace SMB

> **Show it once. It remembers. It asks before it acts.**

Gofer Trace SMB turns one screen recording into an editable Markdown procedure, lets an agent execute that procedure through an MCP-accessible Obsidian vault, and applies owner-authored approval policy before a simulated external action.

```text
WATCH              REMEMBER                 ACT                    RECORD
MP4 → GPT-4o  →  Markdown/Obsidian  →  TrueForge + policy  →  Log + changelog
```

The central idea is **governance as memory**: the owner can audit the workflow and change approval behavior by editing `demo-vault/Policies/spending-limits.md`. The MCP agent may read that policy but can never write it.

## Demo in five minutes

Requires Python 3.11 and `ffmpeg` for a live video extraction.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
GOFER_OFFLINE=1 python app.py
```

1. Open `http://localhost:7860` and click **Do the weekly reorder**.
2. The agent visibly reads its workflow, supplier record, and current policy.
3. Cached pricing produces a load-bearing proposal: 40 × $8.50 = **$340**.
4. The gate quotes `$200-$500 — notify owner, proceed after 1h` verbatim. Approve the simulated action.
5. Edit the first policy rule from `under $200` to `under $500`, save it, then click **Re-run with current policy**. The run proceeds without a gate or service restart.

No real order or payment is ever submitted. “Execution” produces a simulated PO and audit notes only.

For machine preparation, TrueForge smoke testing, live extraction, the two-run stage
script, and final submission checks, follow **[docs/SETUP.md](docs/SETUP.md)**. Run
`python scripts/preflight.py` after configuring the environment to get an actionable
readiness report.

## TrueForge / MCP

Register `trueforge.mcp.json` with the hackathon TrueForge build, or use the equivalent MCP UI settings:

```json
{"command":"python","args":["-m","vault.mcp_server"],"env":{"GOFER_VAULT":"demo-vault"}}
```

The server exposes exactly `vault_search`, `vault_read`, `vault_list`, `vault_write`, and `vault_append`. Writes are restricted to `Workflows/` and `Log/`; append is restricted to `changelog.md`. The TrueForge distribution is supplied at the event, so its project-specific import/configuration step is intentionally isolated to this provider registration.

## Live services and offline mode

- Set `OPENAI_API_KEY` to enable GPT-4o structured workflow extraction. Results are keyed by the video SHA-256 and cached.
- Set `BRIGHTDATA_API_KEY` and `BRIGHTDATA_DATASET_ID` for a live Bright Data dataset trigger.
- Set `GOFER_OFFLINE=1` for the committed workflow/pricing fallback. This is the stage-safe path.

## Test and review

```bash
pytest -q
python -m compileall agent trace vault app.py
```

Run Qodo against the final repository before submission and record any material fixes in the commit/PR description.

## Security boundary

All vault paths are resolved beneath the configured root. Absolute paths, traversal, and symlinks are rejected. Policy writes return: `Policies are owned by the human operator and cannot be modified by the agent.` The human owns the rules; the agent cannot edit its permissions.

## Scope

This hackathon build deliberately has no accounts, database, multi-agent delegation, second workflow, or real checkout integration.
