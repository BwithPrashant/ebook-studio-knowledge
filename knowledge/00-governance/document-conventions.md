---
id: GOV-001
type: convention
status: draft
tldr: Every doc has frontmatter, a 3-line TLDR, stable IDs, and a size cap.
---
# Document conventions (context-minimization rules)
## Required frontmatter
id, type, status (placeholder|draft|validated|approved), phase, owner,
depends_on [IDs], tldr (max 3 lines), updated (YYYY-MM-DD).
## Rules
1. One concern per file. Soft cap 150 lines or ~2,000 tokens (TUNABLE).
   Above the cap: split; the parent becomes a short summary + links.
2. Stable IDs: R3, D7, REQ-012, ADR-004, R1-CLM-001, FEAT-012,
   RUN-P00b-003. Cite by ID; never copy another doc's text (DRY).
3. Raw captured sources live under 01-research/sources/ and are NEVER
   loaded by default (layer L3).
4. Every doc must appear in exactly one INDEX.md.
5. Existence of a file never implies completion: only `status` counts.
## Context layers
- L0 always: AGENTS.md, STATUS.md, role card (~1.5k tokens, TUNABLE)
- L1 by manifest: phase contract + the role's must-load list
- L2 by index: domain docs, chosen using TLDR + "load when"
- L3 never by default: raw sources, long evidence
## Index entry fields
id | status | ~tokens | roles allowed | load when (one line).
Validator (part 2) fails on: unindexed doc, dead link, missing frontmatter,
oversize doc, merge-conflict markers, placeholder cited as evidence.
