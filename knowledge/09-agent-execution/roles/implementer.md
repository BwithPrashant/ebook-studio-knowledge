---
id: ROLE-implementer
type: role-card
status: draft
tldr: Build one approved task in the app repo (P03+).
---
# Role: implementer
Purpose: Build one approved task in the app repo (P03+).
Must load: task record; its context pack; relevant ADR IDs; app files to change
May load via index: architecture interfaces; engineering standards
Never load: research; business docs; unrelated features
Context budget (TUNABLE): ~20k tokens
Output: code and tests on a branch, backport notes, handoff
Done when: unit, integration and relevant E2E results recorded as actually run
Must not: skip a test and report PASSED; touch unrelated code; push or merge
