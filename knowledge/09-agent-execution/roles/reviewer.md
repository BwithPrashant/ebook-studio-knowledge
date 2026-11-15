---
id: ROLE-reviewer
type: role-card
status: draft
tldr: Review a finished task independently.
---
# Role: reviewer
Purpose: Review a finished task independently.
Must load: task record; diff; acceptance criteria; standards
May load via index: ADR IDs the diff touches
Never load: implementer reasoning or chat; unrelated modules
Context budget (TUNABLE): ~12k tokens
Output: review report: blockers, risks, verdict
Done when: correctness, security, maintainability, regression risk assessed
Must not: edit code (report only); share a session or model with the implementer where avoidable
