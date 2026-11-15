---
id: QA-002
type: guide
status: draft
tldr: How to save a dated, hashed source snapshot, check a quote against it, and re-verify snapshots. Needed for verified critical claims.
---
# Source snapshots (QA-002)
Why: a critical `verified` claim needs a snapshot (E-CLAIM, QA-001). The tool
is scripts/snapshot.py (standard library, tested).

## Commands (repo root)
- `python3 scripts/snapshot.py fetch <url>` saves one page under
  `knowledge/01-research/sources/` with a `.meta.json` sidecar, and prints
  `SNAPSHOT: <path>#sha256=<hash>` and `ACCESSED_AT: <date>`.
  Put those two values in the claim's `snapshot` and `accessed_at`.
- `snapshot.py quote "<ref>" "<text>"` proves the wording is in the saved page
  (ignores case, spacing, HTML tags, script text). Run it for every price,
  limit or number you cite.
- `snapshot.py verify "<ref>"` re-checks one file's hash.
- `snapshot.py claims` re-checks every snapshot in claims.jsonl. Run it
  before handing off and in the verifier session.

## Rules
- One page per call. No crawling, logins, paywall bypass, or CAPTCHA tricks.
- robots.txt is respected (exit 3). `--ignore-robots` needs a human decision.
- Raw HTML only. Pages drawn by JavaScript may not contain the price text; if
  `quote` fails, the claim is NOT verified from that snapshot. Log it as a
  limitation and ask for HUMAN_REQUIRED help (a manual dated screenshot).
- PDFs are saved and hashed, but quote matching is not supported: check by hand.
- Snapshots are L3: never load them by default (GOV-001). Check the license
  or terms before storing large pages; keep only what a claim needs.
- Copyright: paraphrase in claims and outcome docs. Quote only the short
  wording that matters (a price, a limit).
- The hash proves the file has not changed since capture. It does not prove
  the vendor's statement is true.

## Not covered
Screenshots, login-only pages, and JavaScript rendering (a headless browser
would need a dependency, so it needs owner approval).
