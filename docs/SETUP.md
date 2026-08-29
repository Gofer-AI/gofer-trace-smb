# Setup and demo process

This is the shortest reliable path from a fresh clone to the two-run hackathon demo.

## 1. Install system prerequisites

Install **Python 3.11**, `ffmpeg`, and Git. Confirm the exact Python interpreter before creating the environment:

```bash
python3.11 --version
ffmpeg -version
```

Do not use a newer system Python accidentally. Create an isolated environment from Python 3.11:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 2. Choose offline or live mode

Start with **offline mode**. It proves the complete governance demo without relying on conference Wi-Fi:

```bash
cp .env.example .env
export GOFER_OFFLINE=1
python scripts/preflight.py
```

The offline path uses `samples/weekly-reorder.json` for the learned workflow and
`cache/weekly-reorder-fallback.json` for the `$8.50` Acme price.

For live extraction and enrichment, edit `.env` and set:

```dotenv
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o
BRIGHTDATA_API_KEY=...
BRIGHTDATA_DATASET_ID=...
GOFER_OFFLINE=0
```

Load the file into the shell before launching processes:

```bash
set -a
source .env
set +a
python scripts/preflight.py
```

Never commit `.env`; it is ignored by Git.

## 3. Prove the MCP boundary before opening the UI

The MCP server is a stdio process. Its registration lives in `trueforge.mcp.json`:

```bash
python -m vault.mcp_server
```

The command waits silently for MCP input; that is expected. Stop it with `Ctrl-C` after
the import/startup check. In the hackathon TrueForge UI, import the JSON configuration or
create an MCP provider with:

- **Name:** `gofer-trace-vault`
- **Command:** `python`
- **Arguments:** `-m`, `vault.mcp_server`
- **Environment:** `GOFER_VAULT=demo-vault`
- **Working directory:** the repository root

Before continuing, use TrueForge to call these tools once:

1. `vault_list("Workflows")`
2. `vault_search("Weekly supplier reorder")`
3. `vault_read("Policies/spending-limits.md")`
4. `vault_write("Log/mcp-smoke-test.md", "# MCP smoke test")`
5. `vault_append("changelog.md", "\n- MCP smoke test completed.")`

Also prove the security boundary by attempting:

```text
vault_write("Policies/spending-limits.md", "overwrite")
```

The exact result must be:

```text
Policies are owned by the human operator and cannot be modified by the agent.
```

Reset the smoke-test log/changelog before the stage demo so the audit trail starts clean.

## 4. Add the real recording

Record the weekly reorder and save it as:

```text
samples/weekly-reorder.mp4
```

For a live extraction, run this from a Python shell:

```bash
python - <<'PY'
from trace.extract import extract_workflow
from trace.to_markdown import write_workflow

video = "samples/weekly-reorder.mp4"
workflow = extract_workflow(video)
print(write_workflow(workflow, video, "demo-vault"))
PY
```

Run it once before presenting. The output is cached by video hash, making subsequent
demonstrations fast and resilient to network failure.

## 5. Run the UI

```bash
GOFER_OFFLINE=1 python app.py
```

Open `http://127.0.0.1:7860` and verify the three panes are visible. The committed offline
price should produce **40 units × $8.50 = $340**.

## 6. Rehearse the winning two-run demo

### First run: approval fires

1. Click **Do the weekly reorder**.
2. Watch the right pane highlight the workflow, supplier, and policy notes.
3. Confirm the middle pane displays the `$340` proposal and this exact policy text:

   ```text
   $200-$500 — notify owner, proceed after 1h
   ```

4. Click **Approve simulated order**.
5. Confirm one new note appears in `demo-vault/Log/` and one line is appended to
   `demo-vault/changelog.md`.

### Second run: policy edit changes behavior

1. Open `demo-vault/Policies/spending-limits.md` in Obsidian or a text editor.
2. Change only `under $200` to `under $500` and save.
3. Click **Re-run with current policy** without restarting the app.
4. Confirm the same `$340` proposal auto-approves and no gate is shown.
5. Restore the original `$200` policy after rehearsal.

The presenter line is: **“We just reprogrammed the agent by editing a text file. The
business owns its brain.”**

## 7. Final submission checks

```bash
pytest -q
python -m compileall -q agent trace vault app.py scripts/preflight.py
git diff --check
git status --short
```

Then complete the external checks that cannot be automated locally:

1. Run Qodo and resolve or record its findings.
2. Run the complete two-pass demo twice without repairing files between passes.
3. Confirm no secret is tracked with `git grep -nE '(sk-|BRIGHTDATA_API_KEY=.+)'`.
4. Confirm TrueForge—not a direct Python shortcut—can invoke all five MCP tools.
5. Capture a backup screen recording of the successful demo.
6. Push the repository, verify the MIT license is visible, and submit before the deadline.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` | Activate `.venv` and reinstall `requirements.txt`. |
| `ffmpeg: command not found` | Install ffmpeg or use the committed offline workflow fixture. |
| MCP server exits immediately | Launch from the repository root and verify the virtual environment is active. |
| Bright Data request fails | Set `GOFER_OFFLINE=1`; the disk cache is the intentional fallback. |
| `$340` does not gate | Restore the committed policy and confirm the Acme cache price is `$8.50`. |
| Second run still gates | Save the policy file and ensure the first rule says `under $500`. |
| Policy write succeeds through MCP | Stop the demo; verify TrueForge points to this repository's `vault.mcp_server`. |

