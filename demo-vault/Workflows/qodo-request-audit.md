---
type: workflow
owner: engineering
tools_required: [vault, qodo_merge, github]
applies_to: code_changes_with_pull_request
---
# Qodo request audit

## Purpose

Use Qodo Merge as an independent code-review signal for a TrueForge agent request and its resulting GitHub pull request.

## Steps

1. Confirm the exact agent request and the GitHub pull-request URL.
2. Confirm the PR is intended to implement that request. Do not audit unrelated repositories or PRs.
3. Explain that requesting review posts a PR comment, then obtain human approval through the TrueForge checkpoint.
4. Call `qodo_request_review` with the exact request and PR URL.
5. Treat the result as `requested`, never as cleared. Wait for Qodo Merge to respond.
6. Call `qodo_audit_status` and present Qodo's findings with links.
7. Resolve material findings, update tests, and request another Qodo review when the diff changes materially.
8. Require normal human approval before merge or any consequential downstream action.

## Decision states

- `not_applicable`: no code change or no PR exists
- `configuration_required`: Qodo GitHub App or GitHub authentication is missing
- `requested`: review comment was posted but Qodo has not responded
- `reviewed`: Qodo feedback is available; a human must assess it
- `blocked`: material findings remain unresolved
- `human_approved`: only a human can set this state

## Guardrails

- Qodo Merge reviews code diffs; it is not a general-purpose runtime policy engine.
- Never post a GitHub comment without the TrueForge approval checkpoint.
- Never put credentials, customer data, private vault content, or unrelated prompts into the review request.
- Never infer approval from silence or from a review with no reported findings.
