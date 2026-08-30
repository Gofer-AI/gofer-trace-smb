---
type: workflow
owner: operations
cadence: daily
tools_required: [vault, bright_data]
---
# Daily company brief

## Purpose

Turn company context, tasks, and sourced external developments into a short operating brief.

## Steps

1. Read `Company/profile.md`, `Company/news-watchlist.md`, `Tasks/Today.md`, `Tasks/Inbox.md`, and the newest daily note.
2. If the company identity or watchlist is incomplete, ask the owner for the missing fields. Do not run a broad ambiguous company search.
3. Search current external sources through Bright Data using the watchlist. Prefer primary sources and reputable publications.
4. Verify entity identity, publication date, and source URL. Check recent `News/` briefs to prevent duplicates.
5. Save a dated brief under `News/YYYY-MM-DD-company-brief.md`. Clearly separate reported facts from analysis.
6. Surface no more than three suggested priorities. Do not silently turn news into committed work.
7. With owner confirmation, update `Tasks/Today.md`, triage `Tasks/Inbox.md`, and create the day's `Daily/YYYY-MM-DD.md` note.
8. Append a concise description of vault changes to `changelog.md`.

## Guardrails

- Never modify `Company/` or `Policies/`.
- Never report an item without a direct URL, publisher, published date when available, and retrieval date.
- Never claim two similarly named entities are the same without corroboration.
- If no material news is found, say so explicitly instead of filling space.
