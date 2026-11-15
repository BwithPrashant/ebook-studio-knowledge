# Knowledge bootstrap proposal, part 2 (registries, schemas, validators)

STATUS: PROPOSAL. Overlay it on a new branch of ebook-studio-knowledge
(same flow as part 1). Python 3 standard library only; no installs.

## Contents
- scripts/kbcheck.py         validate | gate | status | tokens
- scripts/tests/             52 unit tests (all pass; includes negative tests)
- schemas/                   workstream, deliverable, phase, claim
- knowledge/registry/        R1-R10, D1-D18, phases, claims (empty), state
- knowledge/ docs            registry guide, QA policy, task contract,
                             product scope seed, seed sources, updated indexes
- app-repo/AGENTS.md         copy to the ROOT of ebook-studio-app (not the knowledge repo)

## Apply
    cd ebook-studio-knowledge && git switch -c chore/p00a-registries
    unzip part2 zip to /tmp, then:
    cp -R /tmp/knowledge-bootstrap-part2/knowledge/. ./knowledge/
    cp -R /tmp/knowledge-bootstrap-part2/schemas ./schemas
    cp -R /tmp/knowledge-bootstrap-part2/scripts ./scripts
    python3 scripts/kbcheck.py validate        # expect: OK: 0 finding(s)
    python3 -m unittest discover -s scripts/tests
    python3 scripts/kbcheck.py gate P00a       # expect: PASS
Then commit, push, PR. Separately, put app-repo/AGENTS.md in the app repo.

## Files this OVERWRITES (review the diff)
knowledge/INDEX.md, PROJECT_CONTEXT.md (frontmatter added, wrapped URL
fixed, seed URLs moved to 01-research/seed-sources.md), STATUS.md (now
generated), 00-governance/{INDEX,document-conventions}.md,
01-research/INDEX.md, 02-product/INDEX.md, 04-engineering/INDEX.md,
06-quality/INDEX.md, 09-agent-execution/INDEX.md,
09-agent-execution/phases/REGISTRY.md (now a pointer to phases.json),
09-agent-execution/templates/claim.yaml (superseded by claim schema).

## Corrections to part 1
- Conventions said 8 required frontmatter fields; my own role cards and
  contracts only had 4. Now required: id, type, status, tldr; the rest optional.
- Registry data is JSON, not YAML (no YAML parser in the standard library).
- The phase list lives only in registry/phases.json (REGISTRY.md was a duplicate).

## Interpretations to confirm
- Deliverables the handbook marks "[P00]" are required at "validated";
  those marked "P00 draft" (D4, D5, D6, D7, D10) at "draft". See
  deliverables.json "required_maturity".
- COMPLETE for a research track needs: validated outcome doc, at least one
  verified claim (R1-R8), human tasks done, no blockers. Human tasks I set:
  R2 rubric review, R7 owner review of legal risks, R9 spot-check of critical claims.

## Known limits
- Token counts are chars/4 estimates. Re-measure with your Qwen tokenizer.
- kbcheck does not fetch URLs; reachability and quote-matching of sources
  need a network-enabled script (candidate P00b task).
- It checks structure and consistency, not whether research is correct.
  The human gate and R9 verification still carry that.
- After merging: set P00a to READY_FOR_REVIEW in phases.json only once
  `gate P00a` passes; you then write approvals/P00a.md to approve.
