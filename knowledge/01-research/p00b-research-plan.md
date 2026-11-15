---
id: RES-P00B-PLAN
type: research-plan
status: draft
tldr: "P00b plan for R1-R8: questions, first sources, verification bar, expected claims, human tasks, order (R1 and R5 first)."
---
# P00b research plan (R1-R8)
Scope: planning only. No research, claims, or pages fetched yet. Claim IDs
are `R<N>-CLM-NNN`. Counts below are planning estimates, not evidence.

## Verification bar (all tracks)
A critical claim is `verified` only with a primary source or direct test,
`source_url` + `accessed_at`, `validation_method`, `confidence_rationale`,
a reviewer, and a dated snapshot unless `source_type` is `direct_test`.
Vendor claims cannot be `verified`. Contradictions are logged, not silently
resolved. Current prices carry access dates (GOV-005, PH-P00b).

## Suggested order
1. Wave 1: R1, R5. Highest information gain; unblock D2/D7 and R6 costs.
2. Wave 2: R2, R8, R6. R2 uses R1 samples; R6 uses R1/R5 prices; R8 independent.
3. Wave 3: R3, R4, R7. Need human interviews/campaign data; R7 needs R2/R5/R6 choices.
One researcher session per track, then one verifier pass per track.

## Tooling needed before wave 1
Proposed separate task (no code in this session): a snapshot script that
fetches a page, saves its content plus SHA-256 and access date under
01-research/sources/, and includes tests. Critical non-direct-test claims
depend on it for `verified` snapshots (PH-P00b; ENG-002 ER-3).

## R1 Competitive intelligence
Questions: Which advertised features actually work? Current price and plan
model per competitor? Export formats and quality? Usage limits, AI caps,
licensing?
First sources: official pricing/feature/support docs for Designrr and
ZebraLearn (seeds), Automateed, Canva, Reedsy, Atticus, Gumroad, Payhip;
lawful dated screenshots; public demos.
Verified bar: price/feature quoted from the official page with access date
and snapshot hash; hands-on only if actually purchased and tested.
Expected claims: ~30-40 (about 8 competitors x price, features, limits).
HUMAN_REQUIRED: paid-product hands-on tests (PH-P00b); any purchase/spend.

## R5 AI and technical feasibility
Questions: Can a structured pipeline produce chapter text, images, and valid
PDF/EPUB? Which model gateway/SDKs? Job queue, retries, data model? Token,
latency, and cost per ebook? Source citation and editing loop? Does the editor
schema round-trip without data loss, and is EPUB output compatible with major
readers? Is tenant isolation enforceable? Are checkout webhooks idempotent?
Which model-gateway tool-call features exist, and are local/open-weight
models viable? Is long chunked generation reliable at the 100-line /
1,500-token write limit (INC-001, ENG-002 ER-1/E2/E5)?
First sources: official model-provider docs (OpenAI, Anthropic, Google) and
SDK docs; PDF (WeasyPrint, Prince, Paged.js) and EPUB 3 (W3C) docs;
background-job docs; POC only under 01-research/poc/.
Verified bar: runnable POC test with captured output/log/hash; untested
integrations labeled hypothesis; paid API tests need human approval.
Expected claims: ~30-40, including `direct_test` for editor round-trip, EPUB
compatibility, webhook idempotency, and chunked-generation reliability.
HUMAN_REQUIRED: approval for any paid API/gateway usage; POC scope if cost > 0.

## R2 Ebook content and visual quality
Questions: What makes a paid educational ebook credible (depth, exercises,
diagrams, hierarchy, typography, cover)? Minimum PDF/EPUB/accessibility
targets? What design quality is realistically automatable?
First sources: W3C EPUB 3 and WCAG; PDF/UA; publisher style guides; legally
free samples and public-domain books; rendering experiments in poc/.
Verified bar: measured export/render test or human-reviewed rubric; no
assumed access to paid books; no copying proprietary layouts.
Expected claims: ~15-20.
HUMAN_REQUIRED: rubric review (R2 human_task and PH-P00b).

## R8 Agentic SDLC
Questions: Which spec-first workflows and review/test gates hold up? Which
agent capabilities are documented vs opinion? How to keep tool portability
and multi-agent ownership?
First sources: seeds (Reddit, Medium, timdeschryver); authoritative tool docs
(agent SDKs, Git, CI); local automation tests.
Verified bar: tool behavior from official docs; workflow claims from a local
test; opinions kept as hypothesis/unverified.
Expected claims: ~15-20.
HUMAN_REQUIRED: none in contract; human confirms acceptable references and
where opinion sources are used.

## R6 Business and unit economics
Questions: Separate ebook and SaaS revenue models? AI token/API, payment
fees, refunds, hosting, support, acquisition costs? Break-even and margins
under low/base/high assumptions?
First sources: official AI API, payment (Stripe/PayPal), hosting, and email
pricing; independent recalculation of every formula; Q-001 target cost.
Verified bar: each input from a dated official price; formulas recomputed
independently; observed figures separated from illustrative values.
Expected claims: ~15-20.
HUMAN_REQUIRED: Q-001 target cost per ebook; assumption choices for demand
and acquisition.

## R3 Customer demand and niches
Questions: Which buyer segments and jobs-to-be-done exist? What demand
signals exist? Which objections block purchase? Which niches are underserved?
First sources: public search-intent data, marketplace/category listings,
public reviews and forums, competitor sales pages; interviews only if
actually conducted.
Verified bar: demand signal dated and sourced; search volume or AI opinion
is never willingness to pay; willingness to pay only from real interviews
or sales.
Expected claims: ~15-20, mostly hypothesis until tested.
HUMAN_REQUIRED: R3 interviews and any outreach (PH-P00b); human demand
validation.

## R4 Sales and marketing
Questions: Which landing, checkout, delivery, and attribution flows work?
What do platform ad policies allow? Which refund and measurement rules
apply? Which preview/landing patterns convert?
First sources: Meta/Instagram and Google Ads policy/help; Stripe, Payhip,
Gumroad checkout docs; email-provider docs; observed public funnels.
Verified bar: policy/mechanics from official docs with dates; ad economics
stay assumptions until real campaign data; no ad spend.
Expected claims: ~20-25.
HUMAN_REQUIRED: any campaign spending, account creation, or outreach
(currently disallowed).

## R7 Legal, trust and compliance
Questions: Copyright and AI-authorship limits? Source/image/asset licenses?
Privacy (GDPR/CCPA), payments and tax, consumer refunds, ad policies, and
security baseline? Which jurisdiction sources apply, given the seller
location in Q-002, and is the payment provider available in that country?
First sources: US Copyright Office and EU law/guidance; AI provider terms;
license texts (CC, stock); GDPR/CCPA official; Stripe/PayPal terms; platform
ad policies; OWASP.
Verified bar: quoted law/terms text with date; not legal advice; elevated
owner review for legal and security findings.
Expected claims: ~20-25.
HUMAN_REQUIRED: professional legal review questions and owner risk-register
review (PH-P00b, R7 human_task); Q-002 seller/tax residency.

## Totals and dependencies
Expected R1-R8 total: ~150-200 claims (est.). R1/R5 early reduce rework in
R2/R6; R3/R4/R7 close after human inputs. No research, claims, or fetches
were performed in this planning session.
