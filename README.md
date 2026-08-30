# Gofer Trace SMB

> **Show it once. It remembers. It asks before it acts.**

Gofer Trace SMB turns one screen recording into an editable Markdown procedure, then lets a TrueForge agent execute that procedure through a restricted Obsidian-style vault.

```text
CAPTURE                 ORCHESTRATE              REMEMBER                  ACT + AUDIT
Screen recording  →  TrueForge SDK + MCP  →  Markdown / Obsidian  →  policy gate + log
```

TrueForge is the agent layer: it owns the model loop, chat interface, sessions, tool calls, streaming, and human checkpoints. This repository supplies the Gofer agent definition and its governed MCP tools.

The central idea is **governance as memory**. The owner can change approval behavior by editing `demo-vault/Policies/spending-limits.md`. The agent can read that policy, but the MCP boundary prevents it from writing to `Policies/`.

## Primary changes in this version

### TrueForge is now the application layer

- The former Gradio application has been removed.
- The browser interface is a React/Vite application built with `@truefoundry/trueforge-ui`.
- `@truefoundry/trueforge-sdk` configures the `gofer-smb` agent and submits recorded-workflow turns to the TrueForge runtime.
- TrueForge owns agent sessions, model execution, MCP tool calls, streaming responses, and human approval checkpoints.

### Screen recording is built into the interface

- **Record workflow** first asks whether to capture an entire display, application window, or browser tab.
- The browser's protected sharing dialog always confirms the exact source; Gofer cannot bypass that permission prompt.
- Recording happens locally with `MediaRecorder`, displays elapsed time, and produces a WebM backup the user may save.
- Selecting **Extract workflow** stages the video under a random opaque ID and submits an orchestration turn through the TrueForge SDK.

### Workflow extraction is governed through MCP

- The UI cannot call a direct Python extraction shortcut; `/workflows/extract` has been removed.
- TrueForge invokes `extract_workflow_from_recording(upload_id)` through the configured Gofer MCP server.
- Video bytes remain in short-lived local staging rather than being copied into an LLM prompt or MCP JSON argument.
- The staged video is deleted after successful extraction, failed extraction, explicit cleanup, or expiry.
- The generated, editable Markdown procedure is written under `demo-vault/Workflows/`.

### The vault is now a company second brain

- The same local Markdown tree opens directly in Obsidian and is exposed to TrueForge through governed vault tools.
- It includes company context, daily notes, tasks, projects, meetings, decisions, news, workflows, audit logs, and templates.
- `Company/` and `Policies/` are human-owned; agent writes are limited to explicitly approved operational folders.
- Bright Data supports current company/news research, while Qodo provides advisory pull-request audits for code-changing agent requests.

### The delivery path is reproducible

- Windows-compatible TrueForge startup and configuration scripts are included.
- Offline fixtures provide deterministic workflow/pricing demonstrations without ffmpeg or external extraction calls.
- Python lifecycle tests cover vault boundaries, Qodo integration, upload validation, staging, one-time consumption, and raw-video cleanup.
- TypeScript checking and the production Vite build validate the embedded TrueForge interface.

## Obsidian vault

Open `demo-vault/` as a vault in Obsidian. Obsidian and the Gofer MCP connector then operate on the same local Markdown files—there is no database import or synchronization layer to keep in step.

The vault now serves as a company second brain with a dashboard, daily notes, tasks, projects, meetings, decisions, news briefs, workflows, and reusable templates. The connector can read every Markdown note. Its writes are deliberately governed:

- `vault_write` can maintain operational notes under `Daily/`, `Decisions/`, `Log/`, `Meetings/`, `News/`, `Projects/`, `Tasks/`, and `Workflows/`.
- `vault_append` can append to those operational notes and `changelog.md`.
- `Company/` and `Policies/` remain human-owned and read-only to the agent.

Complete `Company/profile.md` and `Company/news-watchlist.md` in Obsidian before running company news monitoring. These owner-maintained notes ground Bright Data searches in the correct company, products, executives, market, competitors, partners, and sources.

The committed Obsidian settings keep links portable Markdown. Per-user workspace state is ignored so opening the vault does not add window/layout churn to Git.

## Architecture

```text
Browser / React + @truefoundry/trueforge-ui
        │
        ├── chat and agent turns ────────────────→ TrueForge runtime :8790
        │                                                │
        │                                                ├── model loop
        │                                                ├── sessions + streaming
        │                                                └── MCP tool orchestration
        │                                                         │
        └── raw recording ─→ local staging :8001/recordings       │
                                  │                               │
                                  └── opaque upload ID ───────────┘
                                                                    ↓
                                             Gofer MCP service :8001/mcp
                                                  │       │       │
                                                  │       │       └── Qodo/GitHub
                                                  │       └────────── Bright Data + pricing
                                                  └────────────────── Obsidian vault
```

The binary staging route only accepts, reports, and clears validated WebM/MP4/QuickTime uploads. It does not perform extraction. Extraction begins only when the TrueForge agent calls the MCP tool with the corresponding upload ID.

### Component map

| Component | Responsibility |
| --- | --- |
| `src/ScreenRecorder.tsx` | Capture permission flow, local recording, staging, and TrueForge SDK turn submission |
| `src/main.tsx` | Embedded TrueForge UI and connection state |
| `scripts/configure-trueforge.mjs` | MCP registration and repeatable `gofer-smb` agent configuration |
| `trace/intake.py` | Opaque-ID staging, expiry, status, one-time consumption, and cleanup |
| `trace/upload.py` | Upload validation and safe temporary video processing |
| `vault/mcp_server.py` | Governed vault, pricing, Qodo, and recording-extraction MCP tools |
| `vault/writer.py` | Vault path confinement and human-owned folder enforcement |
| `demo-vault/` | Obsidian-compatible company knowledge base and audit trail |

## Prerequisites

- Python 3.11
- Node.js 22.14 or newer
- A model provider configured in TrueForge
- `ffmpeg` only for live video extraction; the committed workflow fixture does not need it

## Install

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm install
$env:GOFER_OFFLINE = "1"
python scripts/preflight.py
```

macOS or Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
npm install
GOFER_OFFLINE=1 python scripts/preflight.py
```

## Configure TrueForge once

1. Start the Gofer MCP service:

   ```bash
   python app.py
   ```

2. Start the local TrueForge runtime:

   ```bash
   npm run dev:trueforge
   ```

3. Open `http://localhost:8790`, then configure a model under **Settings → Models**.

4. Set the model name and register the Gofer connector/agent:

   ```powershell
   $env:TRUEFORGE_MODEL = "openai/gpt-5-4-mini"
   npm run configure:trueforge
   ```

   Replace the model name with the fully qualified model configured in TrueForge. The script uses the official `@truefoundry/trueforge-sdk`; it registers `http://127.0.0.1:8001/mcp` and creates or updates the `gofer-smb` agent with both the governed vault and the already-configured Bright Data connector.

## Daily second-brain flow

After completing the two notes under `Company/`, ask the agent:

```text
Run my daily company brief. Review today's tasks, research material company news, and propose my top three priorities. Ask before committing any suggested task.
```

The agent reads owner-maintained company context, searches through Bright Data, saves a sourced brief under `News/`, updates the daily operating notes after confirmation, and records the changes in the audit changelog.

## Qodo request audits

Qodo Merge audits code-changing agent requests at the pull-request boundary:

- `qodo_request_review` posts a Qodo `/review` command containing the exact TrueForge request. TrueForge requires human approval before this tool runs because it writes a GitHub comment.
- `qodo_audit_status` reads Qodo bot comments and reviews and returns their source links.
- `.pr_agent.toml` gives Qodo repository-level review criteria focused on policy boundaries, unintended side effects, credential exposure, scope drift, rollback behavior, and tests.

Set `GITHUB_TOKEN` or `GH_TOKEN` with permission to comment on pull requests, or authenticate the installed GitHub CLI with `gh auth login`. Install the Qodo GitHub App for the repository. Read-only status checks on public repositories can work without a token but are subject to GitHub's anonymous limits.

Then ask the agent:

```text
Audit this implementation against my request with Qodo: https://github.com/OWNER/REPO/pull/123
```

Qodo is an advisory code-review signal, not an authorization source. A human still decides whether findings are resolved and whether the change may merge.

## Run the Gofer interface

For development, keep the MCP and TrueForge processes above running, then start the SDK interface:

```bash
npm run dev:ui
```

Open `http://127.0.0.1:5173`.

### Record a workflow

Select **Record workflow** in the upper-right corner of the interface. Gofer first asks whether you want to record an entire screen, one application window, or one browser tab. After you choose, the browser's protected share dialog asks you to approve the exact source. One source can be recorded at a time. The button displays elapsed time while recording. Select **Stop** when the demonstration is complete, then **Extract workflow**. The raw recording is staged in a short-lived local intake area, and its opaque upload ID is submitted through the TrueForge SDK. TrueForge invokes the `extract_workflow_from_recording` MCP tool, the governed Markdown result is written under `demo-vault/Workflows/`, and the temporary raw upload is deleted. Video bytes are never inserted into an LLM prompt or tool argument. **Save backup** optionally downloads a timestamped WebM copy. Cancelling the browser's share picker records nothing.

You can also start all three processes together after initial configuration:

```bash
npm run dev
```

If local development dependency optimization is restricted by your environment, use the verified production path:

```bash
npm run build
npm run preview
```

## Demo flow

Ask the `gofer-smb` agent:

```text
Do the weekly reorder
```

The agent should:

1. Read the learned workflow, inventory, supplier record, and current policy through MCP.
2. Use offline pricing to calculate **40 units × $8.50 = $340**.
3. Quote `$200-$500 — notify owner, proceed after 1h` and pause at a TrueForge human checkpoint.
4. After approval, create a simulated log note and append the changelog. No order or payment is submitted.

To demonstrate live governance, change `under $200` to `under $500` in `demo-vault/Policies/spending-limits.md`, save it, and ask the agent to run the reorder again. Because the agent rereads policy on every run, the $340 simulation should now follow the auto-approval rule.

## MCP boundary

The streamable HTTP server exposes:

- `vault_search`, `vault_read`, and `vault_list` as read-only tools
- `pricing_lookup` as a read-only live/offline enrichment tool
- `extract_workflow_from_recording` as the only recording-to-workflow extraction entry point
- `qodo_audit_status` as a read-only Qodo feedback reader
- `qodo_request_review` as a human-approved GitHub comment action
- `vault_write`, restricted to agent-maintained operational folders
- `vault_append`, restricted to those folders and `changelog.md`

Absolute paths, traversal, and symlinks are rejected. `Company/` and `Policies/` are human-owned. Policy writes always return:

```text
Policies are owned by the human operator and cannot be modified by the agent.
```

## Test and build

```bash
pytest -q
python -m compileall -q agent trace vault app.py scripts/preflight.py
npm run typecheck
npm run build
```

The local TrueForge runtime stores its SQLite state in ignored `.trueforge-data/`. The Windows startup command includes a narrowly scoped ESM loader because TrueForge 0.1.4 passes raw Windows migration paths to Node.

## Live services and offline mode

- `OPENAI_API_KEY` enables GPT-4o workflow extraction. Extracted results are cached by video SHA-256.
- `BRIGHTDATA_API_KEY` and `BRIGHTDATA_DATASET_ID` enable live supplier enrichment.
- `GOFER_OFFLINE=1` uses the committed workflow and pricing fixtures.

Offline mode removes external extraction and pricing dependencies, but TrueForge still needs a configured language model to execute the agent loop.
