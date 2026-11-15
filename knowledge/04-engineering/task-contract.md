---
id: ENG-001
type: contract
status: draft
tldr: Mandatory 10-step SDLC and cross-repo task record for every app change. Not active until P03 is approved.
---
# Task contract (ENG-001)
Applies to P03+ only. No app work before P00-P02 are approved.

## Steps
1. Load the task spec and relevant indexes; inspect app source, tests, Git state.
2. Confirm approved acceptance criteria, affected contracts, dependencies.
3. Plan the minimal change, migration impact, tests, rollback.
4. Implement on a scoped branch; preserve unrelated changes.
5. Run unit tests and static checks.
6. Run integration tests and affected E2E journeys.
7. Review correctness, security, maintainability, regressions; fix blockers.
8. Backport knowledge, decisions, test evidence, task status.
9. Run final CI/quality gates; record actual outcomes.
10. Authorized local commits with the task ID in each repo; prepare PRs.

## Rules
- Bug fix: reproduce first; add a failing regression test when feasible.
- Refactor: keep observable behavior; start with safety tests.
- A skipped test is labeled SKIPPED with a reason, never PASSED.
- No force push, protected-branch merge, production deploy, spend or public
  publishing without human authorization.
- Cross-repo changes are not atomic: sync_status stays pending until both
  sides are reviewed and merged.

## Task record (store under 05-delivery/tasks/)
```
task_id: FEAT-012
knowledge_spec: knowledge/02-product/features/FEAT-012.md
knowledge_revision: <sha>
app_base_revision: <sha>
status: approved | in_progress | validation | review | done
branch: feat/FEAT-012
checks: {unit: pending, integration: pending, e2e: pending, review: pending}
app_commit: null
knowledge_commit: null
sync_status: pending
```
