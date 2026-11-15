---
id: GOV-002
type: policy
status: draft
tldr: Agents act freely inside a branch; humans approve phases, spend, deploys.
---
# Autonomy and approvals
## Statuses
NOT_STARTED, IN_PROGRESS, VALIDATION, READY_FOR_REVIEW, APPROVED,
plus BLOCKED and CHANGES_REQUESTED (proposed additions).
READY_FOR_REVIEW needs all objective gates green. APPROVED needs a human
file `approvals/<PHASE>.md` containing `decision: APPROVED`, name, date.
CHANGES_REQUESTED returns the phase to IN_PROGRESS with listed fixes.
## Pre-authorized (no prompt needed)
Edit files in the repo's allowed paths on a feature branch; local commits to
that branch with task ID; read-only web research; run local scripts/tests.
## Requires human
Phase approval; ADRs on stack/data model/security; installing dependencies;
any paid action or paid-account use; push, merge to protected branch;
deploy; publishing; ad spend; legal/compliance conclusions.
## Gate packet
One page (templates/gate-packet.md): produced items, check results, open
risks, decisions needed, recommendation. Agents prepare it; the human only
decides.
## Human-required tasks
Work an agent cannot do (interviews, hands-on tests needing paid accounts,
rubric review) is labeled HUMAN_REQUIRED in the contract, never faked.
