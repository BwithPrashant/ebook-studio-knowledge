---
id: QA-001
type: policy
status: draft
tldr: Research evidence rules, and which kbcheck error enforces each.
---
# Research QA policy
Claims live in registry/claims.jsonl (schema: schemas/claim.schema.json).
| Rule | Enforced by |
|---|---|
| Verified claim has method, rationale, access date, URL (or direct test) | E-CLAIM |
| A vendor_claim source can never be "verified" | E-CLAIM |
| Critical verified claim has reviewer and snapshot | E-CLAIM |
| Disputed claim lists contradictions | E-CLAIM |
| Track COMPLETE needs validated outcome doc, verified claims, done human tasks | E-WS-COMPLETE |
| Deliverable at validated needs evidence; no unverified critical claim cited | E-DELIV, E-GATE |
| Deliverable maturity equals doc status | E-DELIV |
| Validated doc cannot depend on a lower-status doc | E-DEP-RANK |
| Phase READY_FOR_REVIEW/APPROVED needs gate pass, contract, human file | E-PHASE-*, E-APPROVAL |
Not machine-checkable (still required): a second model repeating the first
is not verification; current prices carry dates; contradictions are logged
not silently resolved; financial formulas independently recalculated;
legal/security findings get elevated owner review.
Known gap: kbcheck does not fetch URLs. Source reachability and quote
matching need a network-enabled script (planned for P00b).
