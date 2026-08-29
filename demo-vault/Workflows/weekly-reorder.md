---
type: workflow
source_video: samples/weekly-reorder.mp4
captured: 2026-08-27
steps: 6
tools_required: [vault, bright_data, sandbox]
---
# Weekly supplier reorder

## Preconditions
- Stock level below reorder threshold

## Steps
1. Open inventory note — tool: vault — inputs: widgets — expect: current stock levels
2. Check reorder threshold — tool: vault — inputs: inventory — expect: required quantity
3. Read supplier record — tool: vault — inputs: Acme — expect: supplier status and terms
4. Fetch current prices — tool: bright_data — inputs: widgets — expect: current supplier prices
5. Place simulated purchase order — tool: sandbox — inputs: quantity, unit price — expect: simulated PO confirmation
6. Record the run — tool: vault — inputs: run summary — expect: log and changelog entry

## Sensitive actions
- Step 5 — Place simulated purchase order — spends money
