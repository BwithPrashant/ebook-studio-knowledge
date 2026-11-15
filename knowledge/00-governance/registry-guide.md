---
id: GOV-005
type: guide
status: draft
tldr: Where machine-readable state lives, who edits it, and the kbcheck commands.
---
# Registry guide
Source of truth (JSON, validated against schemas/):
- registry/workstreams.json  R1-R10: status, outcome doc, human tasks, blockers
- registry/deliverables.json D1-D18: path, maturity, evidence claim IDs
- registry/phases.json       phase status, gate, contract path
- registry/claims.jsonl      one claim per line (schema: schemas/claim.schema.json)
- registry/state.json        last validation record, next action
STATUS.md is generated from these. Never edit it by hand.
## Who edits what
- researcher: appends claims (verification "unverified" or "vendor_claim"
  unless directly tested); updates own R status and outcome doc.
- verifier: sets verification, reviewer, snapshot on claims. Never the
  claim's author.
- librarian: indexes, deliverable maturity, STATUS, validator runs.
- human: approvals/<PHASE>.md and phase status APPROVED only.
## Commands (repo root, Python 3, no dependencies)
- python3 scripts/kbcheck.py validate        all structural and evidence checks
- python3 scripts/kbcheck.py gate P00a       objective gate for a phase
- python3 scripts/kbcheck.py status --write  regenerate STATUS.md
- python3 scripts/kbcheck.py tokens          estimated context cost per role
- python3 -m unittest discover -s scripts/tests
Order before a commit: validate --record, then status --write.
## Approval file format (approvals/P00a.md)
decision: APPROVED
approver: <name>
date: YYYY-MM-DD
