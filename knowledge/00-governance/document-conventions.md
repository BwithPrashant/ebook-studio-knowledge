---
id: GOV-001
type: convention
status: draft
tldr: Every doc has frontmatter, a short TLDR, stable IDs, and a size cap. Enforced by kbcheck.
---
# Document conventions (context-minimization rules)
## Frontmatter
Required: id, type, status (placeholder|draft|validated|approved), tldr
(single line, max 300 chars). Optional: phase, owner, depends_on [IDs],
updated. Exempt: INDEX.md, STATUS.md, and files under templates/,
approvals/, runs/, sources/, poc/.
## Rules
1. One concern per file. Cap: 150 lines or ~2,000 tokens (TUNABLE).
   Above the cap: split; the parent becomes a short summary + links.
2. Stable IDs: R3, D7, REQ-012, ADR-004, R1-CLM-001, FEAT-012.
   Cite by ID; never copy another doc's text (DRY).
3. Raw captured sources live under 01-research/sources/ (layer L3) and are
   NEVER loaded by default.
4. Every doc is linked from exactly one INDEX.md.
5. A file's existence never implies completion: only `status` counts, and
   a validated/approved doc may not depend on a lower-status doc.
## Context layers
L0 always: AGENTS.md, STATUS.md, role card, phase contract.
L1 by manifest: the role's must-load list.
L2 by index: domain docs chosen via TLDR and "load when".
L3 never by default: raw sources, long evidence.
## Index entry
`- [id](path) | status | ~tokens | roles | load when ...`
Check everything with: python3 scripts/kbcheck.py validate
