---
id: ENG-002
type: policy
status: draft
tldr: Rules for large or multi-step agent work - bounded writes, verify after every write, checkpoints, recovery, evidence-based completion. Model-independent.
---
# Execution reliability (ENG-002)
Origin: INC-001 (a 1,000-line write silently failed). Root cause there is
UNKNOWN, so these rules are precautions, not a fix for one model. Doc size
cap is GOV-001; approvals are GOV-002. IDs are ER-n (not R-n: R1-R10 are
research tracks).

## Rules
- ER-1 Bounded generation. One tool call writes one unit. Default limit:
  100 lines or ~1,500 tokens per write or append (TUNABLE until INC-001
  experiments E1-E4 measure the real limit). Larger artifacts become several
  files or several verified chunks, never one big write. Never ask a model for
  an exact-count dump in one go.
- ER-2 Generate, write, verify, then continue. Write through a tool call,
  run the check in ER-3, and only then start the next unit.
- ER-3 Never trust a completion message. Verify the file on disk:
  `python3 scripts/artifact_check.py <file> [--min-lines N] [--contains TEXT]
  [--numbered N]`. Record the command and its real output.
- ER-4 Checkpoints. Keep `runs/<RUN-ID>-checkpoint.md` (template:
  templates/checkpoint.md). Mark a unit VERIFIED only after ER-3 passes.
- ER-5 Recovery. On restart or interruption: read the checkpoint, check
  existing files with artifact_check, resume at the first unit that is not
  VERIFIED. Never regenerate or overwrite a VERIFIED unit. Appends are not
  idempotent: put `<!-- unit:Uxx -->` at the start of each appended chunk and
  check for it before appending again. Max 2 retries per unit; then mark it
  FAILED, add a question to open-questions.md, and stop.
- ER-6 Tool lifecycle. A tool call printed as ordinary text is NOT executed.
  Count a write only once the runtime returned a tool result AND the file
  passes ER-3.
- ER-7 Completion needs evidence. Say COMPLETED only if: required files
  exist, ER-3 checks pass, acceptance criteria are met, evidence is in the
  handoff, and any needed human approval (GOV-002) exists.

## Tool lifecycle states
INTENDED > GENERATED > ACCEPTED > DISPATCHED > EXECUTED > PERSISTED > VERIFIED
| State | Who can show it |
|---|---|
| INTENDED, GENERATED | model output |
| ACCEPTED (parsed as a real tool call), DISPATCHED, EXECUTED | runtime logs only |
| PERSISTED | filesystem (file exists, size > 0) |
| VERIFIED | artifact_check PASS recorded in checkpoint/handoff |
An agent can attest only to PERSISTED and VERIFIED. It must not claim
ACCEPTED/DISPATCHED/EXECUTED without runtime log evidence.

## Responsibility boundaries
| Component | Owns |
|---|---|
| Orchestrator | task split, assignment, dependencies, checkpoints, recovery |
| Execution runtime | tool calls, filesystem writes, execution logs |
| Verification | file checks, tests, acceptance criteria |
No orchestrator exists yet. Until one is approved, the human, AGENTS.md,
the checkpoint file and artifact_check.py play those roles. Keep all three
independent of the model provider.

## Enforcement today vs proposed
- Today: AGENTS.md rule, handoff template evidence line, checkpoint
  template, scripts/artifact_check.py (tested).
- Proposed, needs owner approval: kbcheck checks that handoffs in runs/ have
  an evidence line and no VERIFIED unit without a result; a benchmark script
  for INC-001 experiments; an orchestrator.
