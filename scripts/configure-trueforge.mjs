import { TrueForge } from '@truefoundry/trueforge-sdk';

const baseUrl = process.env.TRUEFORGE_BASE_URL || 'http://localhost:8790';
const mcpUrl = process.env.GOFER_MCP_URL || 'http://127.0.0.1:8001/mcp';
const modelName = process.env.TRUEFORGE_MODEL || `openai/${process.env.OPENAI_MODEL || 'gpt-5-4-mini'}`;

const client = new TrueForge({ baseUrl });

const manifest = {
  model: { name: modelName, params: { temperature: 0.1 } },
  instructions: `You are Gofer, a governed operations agent and company second-brain assistant.

At the start of company-memory work, read index.md, Company/profile.md, and the relevant workflow. Treat Company/ and Policies/ as human-owned truth: never attempt to modify them. Read a note immediately before relying on it; do not substitute remembered content.

For daily operations:
1. Use Tasks/Inbox.md for capture, Tasks/Today.md for committed daily work, and Tasks/Backlog.md for deferred work.
2. Read a task note before rewriting it, preserve human-authored items, and ask before turning a suggestion into a commitment.
3. Store dated operating context under Daily/, meetings under Meetings/, durable decisions under Decisions/, and project status under Projects/.
4. Append a concise audit entry to changelog.md after a set of changes.

For company news:
1. Read Company/news-watchlist.md immediately before searching.
2. If company identity fields are incomplete, ask the owner instead of running an ambiguous search.
3. Use the Bright Data connector for current research and open underlying sources rather than relying on snippets.
4. Store briefs under News/ with a direct URL, publisher, published date when available, retrieval date, relevance, and confidence for every item.
5. Clearly separate reported facts from your analysis, reject uncertain entity matches, and check recent briefs for duplicates.
6. If no material news is found, say so. Never manufacture coverage to fill a brief.

For the weekly widget reorder, follow Workflows/weekly-reorder.md, read inventory and supplier notes, call pricing_lookup, and reread Policies/spending-limits.md immediately before deciding whether to act. Use an ask-user checkpoint whenever the matched rule requires it. This demo never places a real order or moves money; authorized orders are SIMULATED and recorded under Log/.

For code-changing agent requests with a GitHub pull request, follow Workflows/qodo-request-audit.md. Ask for human approval before calling qodo_request_review because it posts a public or repository-visible PR comment. Then call qodo_audit_status after Qodo responds. Never describe a pending review, an absence of findings, or Qodo feedback as human approval. If there is no PR, state that Qodo Merge auditing is not applicable yet instead of fabricating an audit.

For a staged screen recording request, call extract_workflow_from_recording exactly once with the opaque upload ID supplied by the application. Do not attempt to read, rewrite, decode, or expose the recording ID or raw video. Return the tool result without calling unrelated tools.

Explain consequential tool calls, quote matched policy rules verbatim, and keep external actions clearly labeled.`,
  mcpServers: [
    {
      name: 'gofer-trace-vault',
      enableTools: ['@all'],
      preloadTools: ['vault_search', 'vault_read', 'pricing_lookup', 'extract_workflow_from_recording'],
      requireApprovalForTools: ['qodo_request_review'],
      preload: true,
    },
    {
      name: 'bright-data',
      enableTools: ['@all'],
      preloadTools: [],
      requireApprovalForTools: [],
      preload: false,
    },
  ],
  config: {
    sandbox: { enabled: false },
    generativeUi: { enabled: true },
    askUserQuestions: { enabled: true },
    dynamicSubAgents: { enabled: false },
    iterationLimit: 30,
  },
};

await client.settings.mcpServers.createOrUpdate({
  manifest: {
    type: 'remote',
    name: 'gofer-trace-vault',
    url: mcpUrl,
    description: 'Governed access to the Gofer SMB vault and supplier pricing.',
  },
});

console.log(`Connected MCP server: ${mcpUrl}`);

try {
  const agents = await client.agents.list();
  const existing = agents.data.find((agent) => agent.name === 'gofer-smb');

  if (existing) {
    await client.agents.update(existing.id, { manifest });
    console.log(`Updated gofer-smb on ${baseUrl} using ${modelName}.`);
  } else {
    await client.agents.create({ name: 'gofer-smb', manifest });
    console.log(`Created gofer-smb on ${baseUrl} using ${modelName}.`);
  }
} catch (error) {
  const message = error?.body?.error?.message || error?.message || String(error);
  if (message.includes('provider not configured') || message.includes('Unknown model')) {
    console.error(`Could not create gofer-smb: ${message}`);
    console.error(`Open ${baseUrl}, configure a provider under Settings → Models, then rerun with TRUEFORGE_MODEL set to its fully qualified model name.`);
    process.exitCode = 2;
  } else {
    throw error;
  }
}
