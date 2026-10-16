# American Backyard AI Sales Assistant

An AI customer-service agent built for a real store, with the measurement system to prove it works: a 32-case evaluation suite mined largely from real customer traffic, human-graded against written rubrics, with a temperature-0 LLM judge audited against the human grader — closing at 30/32 with both failures caught, characterized, and fixed in the open.

Built solo over a summer internship at American Backyard, my family's outdoor-furniture store in Alpharetta, Georgia (family-owned since 1992).

---

https://github.com/user-attachments/assets/cbbbf13b-5406-4e80-8501-b85396a6b324

---


## 1. Overview

**Nextdoor Neighbor** is a chat widget built for the store's site that answers customer questions from the store's real knowledge — the product catalog, policy documents I wrote with the owners, and an ~85-section furniture-care guide I compiled from manufacturer documentation. It looks up live prices from Shopify, respects hard boundaries (no discounts, no stock claims, no order lookups), and hands off to staff by capturing leads that land in the store inbox. It currently runs against a test storefront; production deployment is scheduled for winter, behind the security gate described in §9.

The system is a RAG (retrieval-augmented generation) architecture: nothing was fine-tuned. The model answers from documents retrieved at question time, which keeps every claim groundable and lets the knowledge base update in seconds instead of retraining.

Headline numbers: 547-chunk vector knowledge base · 3 tools · 32 eval cases · **30/32 closing board** (judge agreement 27/32) · 0 security findings above the review bar · Lighthouse accessibility 12/14 → **19/19**, axe 7 issues → **0**.

## 2. System Architecture

- **Backend:** FastAPI `/chat` endpoint. Conversation state lives server-side in SQLite and is replayed to the model each turn (the model itself is stateless).
- **Model:** Claude Sonnet (`claude-sonnet-4-6`) via the Messages API, in an agentic tool loop capped at 5 rounds — the model decides when to search; my code executes tools and feeds results back.
- **Three tools:**
  - `search_knowledge_base` — semantic search over a Chroma vector store (446 product chunks + 101 policy sections), with a product/policy metadata filter and a tool description that routes "do you sell/carry X" questions to policy content.
  - `search_products` — live prices and variants from the Shopify Admin GraphQL API (client-credentials OAuth, read-only scope). Prices are deliberately **not** embedded: they go stale, so they come only from the live store.
  - `create_lead` — saves contact info to SQLite, then notifies staff via a Resend transactional email (DB write first; email is best-effort so a mail outage never loses a lead).
- **Widget:** a ~150-line dependency-free JavaScript IIFE. `textContent`-only rendering (no HTML injection path), `sessionStorage` UUID sessions, accessible dialog semantics (`role="dialog"`, `aria-live` replies, labeled input, visible focus, Escape-to-close), and a phone-number fallback if the API errors.
- **System prompt:** ~20 behavioral rules — completeness, never-deflect-for-known-info, don't-guess, "a grounded no is not a guess," retry-without-filter, exclusion-respect, anti-invention, order-routing, plain-text output. Nearly every rule is traceable to a specific failure an eval caught.

Design decisions with reasons: plain-text staff emails (defangs injection via email HTML), `reply_to=customer` (staff reply in one click), fixed destination inbox (can't be redirected by chat input), zero dollar figures in the knowledge base (single source of truth is the live store), no inventory tool (the store's POS isn't integrated yet — the bot says so instead of guessing).

### Running locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add your own keys
python shopify_client.py    # pulls the product catalog -> data/products.json
python ingest.py            # builds the 547-chunk vector store
uvicorn main:app --reload   # open http://localhost:8000/widget/test_page.html
```

Evals: `python run_evals.py` (add `--send-email-cases` to include the case that fires a real staff email), then `python judge.py evals/results-<date>.json`. Note: the Shopify and Resend keys are store-specific; the policy knowledge files ship in this repo, but the product pull requires store credentials.

## 3. The Knowledge Base

The KB is authored, not scraped. Over the summer I wrote the store's operational knowledge down — store operations, delivery, returns and warranty — in sessions with the owners, and compiled an ~85-section care guide covering 15+ manufacturers from their official care documentation (two days of writing; warranty-voiding claims verified against sources).

Chunking is semantic and header-anchored: one chunk per product (with a title/vendor/tags header), one chunk per `##` policy section. Retrieval units match answer units, and headers deliberately carry customer vocabulary — the don't-sell line says both "Big Green Egg grills" and "green egg grills" because that's how customers actually type it, and embeddings anchor on it.

Standing law (§6): **content changes trigger an eval review**, because rubrics written against yesterday's knowledge rot.

## 4. The Evaluation System

- **`evals/cases.json`** — 32 cases. The first 17 were hand-invented; the rest were mined from the store's real customer traffic (Shopify Inbox history), PII-stripped into `evals/question_bank.md` (~40 verbatim customer lines, clustered by species: order status, parts, constrained search, brand coverage, compound questions, solicitations).
- **`run_evals.py`** — replays every case against a fresh session, with a `/health` preflight (is the server up?) and **content canaries** (do the KB ground-truth strings the rubrics depend on actually exist on disk?) so a battery can't run against a world that doesn't match its assumptions.
- **Human grading** — observations-first protocol: describe what each turn factually did *before* writing any verdict (see §6 for why this rule exists).
- **`judge.py`** — a temperature-0 LLM judge that grades strictly against each case's written `expected` behavior, nothing else. Its agreement with my grades is measured (27/32 at close), and every disagreement gets adjudicated in writing — sometimes the judge wins, sometimes I do, and the record says which and why.
- **Provenance rules:** results files are never hand-edited; a fix verified after a run is logged in `eval-notes.md` and goes green on the *next* full battery, not by editing history.

## 5. What the Evals Caught

The suite grew from 17 invented cases to 32 — the later cases mined from real customer questions — and the score moved from 14 pass / 1 partial / 2 fail to a 30/32 close. But the number matters less than the four failure families the suite caught.

### Epistemic hedging
Before the fix, the bot would say it couldn't find hot tubs in its knowledge base, then add that this didn't necessarily mean American Backyard doesn't sell them, and tell the customer to call and check. That was wrong: the store definitively does not sell hot tubs, and the bot should be able to say so. The fix was content plus prompt: a "What We Sell (and What We Don't)" section in the knowledge base, paired with a new system-prompt rule — *"a grounded no is not a guess."* After the fix, the same question gets a plain, correct no with a pivot to what the store does carry. (Cases: `hot-tub-kinds`, `lead-ask-first`, `brand-not-carried`.)

### Retrieval composition bugs
The subtlest family — the knowledge existed, the model behaved, and the answer was still wrong, because of how retrieval composed. First: a category filter excluded the exact policy section that held the answer, so the bot reported "no results" for a question the KB could answer (fixed with a retry-without-filter rule and routing guidance in the tool description). Then the deeper one: ask about Lloyd Flanders' Mackinac collection, and the search returns *Grand Traverse* products — a partial success. Because the search found *something*, no retry fired, the policy card explaining special orders never arrived, and the bot hedged ("we may or may not carry it") when the true, documented answer was "Lloyd Flanders is one of our manufacturers; the website doesn't show everything; we can typically order it." **Partial product success suppressed the policy lookup.** Fixed with a listed-manufacturer rule that fires precisely on that condition. (Cases: `parts-replacement`, `set-split`, `listed-brand-unlisted-product`.)

### Constraint violations
A real customer message: *"I don't want mgp or hdpe material, what other options do you have?"* The bot recommended POLYWOOD — which **is** HDPE — and justified it with an invented distinction: "made from recycled materials (different from standard HDPE)." One run after that was fixed, it recommended Envirowood, another polymer lumber one brand deeper — and the knowledge that Envirowood is a polymer was already sitting in the care guide's own description of it. Fixes: an exclusion rule (never recommend what the customer excluded) and a materials-glossary chunk that maps the acronyms (POLYWOOD = HDPE; MGP = marine-grade polymer; Envirowood = same family). This case closed **FAIL** on the final board — the fix landed after the closing run, and the board reports what ran, not what I hoped. (Case: `negative-material`.)

### Fabrications
Asked about Ebel lead times, the bot confirmed "20 weeks" for the "Reserve Collection — Charleston and Amherst tables, for example" — **products that do not exist** — woven between two real products (the Laurent Sofa and Trevi Fire Pit) with real lead times. The mix of real and invented is exactly what made it convincing. The judge flagged the answer as suspicious; my check against the actual catalog proved which names were real and which were fabricated. Fix: an anti-invention rule — never cite product names, collections, prices, warranties, or lead times that don't appear in search results. Grade: **FAIL**, kept on the board. (Case: `compound-ebel`.)

## 6. What the Instrument Caught About Its Operators

The judge was built to grade the bot. Four times, it graded me instead.

### The rubber-stamp incidents
Four times across the project, my grading notes described what the rubric *wanted* instead of what the transcript *showed* — claiming the bot "asked for the customer's email" when no ask appeared in any turn, or that it suggested "no POLYWOOD products" when the reply's fifth bullet literally began with the word POLYWOOD. Each time, the judge — which only reads transcripts — disagreed, and auditing its reasons exposed my note instead of its error.

### The worst-note principle
A wrong grade miscounts one case. A **false note** poisons the record that every later debugging session trusts. The POLYWOOD incident is the proof: my note said the violation didn't exist, and if that board had shipped, the project's first real bug would have shipped inside it.

### The observations-first protocol
The rule I grade by now: describe what each turn factually did — which claims, which asks, which tools — *before* writing a verdict. After adopting it, my grades ran stricter than the judge's in places, because I hold the bot to catalog ground truth the judge can't see.

### Rubric rot
When the What-We-Sell section shipped, the hot-tub rubrics silently became wrong: they rewarded yesterday's correct behavior (careful hedging) and punished today's (the grounded no). Standing law: **every content change triggers a cases.json review, and rubric edits get logged.** Some cases are *planned-rot* and labeled at birth: `photo-reference` expires the day image support ships; the financing case rots the day financing gets documented.

### The canary saga — the verifier gets verified
After a content edit appeared to be missing, three successive `grep` checks returned zero for "Big Green Egg" — three alarms, three rounds of process debugging. Then a diagnostic grep printed the actual line: my file said "green egg grills," in my own phrasing, which is also how customers type it. The edit had existed the entire time. The verification string — written by the AI mentor I built this project with — was quoting the *plan* instead of the *file*, and all three alarms were false. Doctrine, now applied to every canary in `run_evals.py`: **verification strings are rubrics too; quote the world, not the plan.** (And the meta-lesson: I verify my AI tools' output exactly the way I verify my bot's.)

### The finale: one heuristic, two verdicts
In the closing pass, the judge's invented-facts suspicion fired twice. On `compound-ebel` it was a **true positive** — the products were fake, my catalog check confirmed it. On `shademaker-warranty` it was a **false positive** — the "case-by-case review" sentence it flagged as invented sits verbatim in `returns_warranty.md`, which the judge cannot see. The same heuristic, distinguished only by a human holding ground truth. That's the division of labor this project settled on: the automated judge is a tireless second column that catches what I miss — and it is never the verdict.

## 7. Security & Accessibility Posture

**Security.** The full codebase passed an AI-assisted security review with zero findings above the reporting bar — a claim I verified rather than trusted: spot-checks confirmed the cited lines were real, SQL is parameterized and confined to `database.py`, the widget renders with `textContent` only (0 `innerHTML`), and the tree held no key material. A `gitleaks` sweep of the entire git history found no leaked secrets. The best security finding came from my own `.gitignore` battery, not the scanner: SQLite sidecar files (`chat.db-wal`), which carry recent customer messages, matched no ignore rule — closed with `*.db*`. Secrets live only in `.env` (never tracked; `.env.example` ships instead), and the Shopify scope is read-only.

Honest limits, documented at scan time: the review excludes rate-limiting/DoS and dependency CVEs by design (both scheduled pre-deploy), and prompt injection against the bot itself is covered by prompt rules plus the eval battery's robustness case — design-and-evals coverage, not scanner coverage.

**Accessibility.** A pre-registered-prediction audit (Lighthouse snapshot, axe DevTools, a keyboard walk, VoiceOver) baselined the widget at 12/14 Lighthouse and 7 axe issues: silent replies for screen-reader users, no dialog semantics, a placeholder posing as a label, and what looked like a Level-A keyboard exclusion. Six fixes later — dialog role, `aria-live` replies, a programmatic label, visible focus indicators, Escape-with-focus-return, harness `lang`/`<main>` — the page scores **19/19 on Lighthouse** (the denominator *grew*: new ARIA made more audits applicable, all passing) and **0 axe issues** on the strictest settings, and VoiceOver speaks every reply. The gravest baseline finding was then re-graded on post-fix evidence: the launcher had been keyboard-reachable all along — focus was landing *invisibly* (a 2.4.7 focus-visibility failure, now fixed). The adjudication is appended to the baseline document with the original finding preserved unedited.

The moral, earned twice in one day: **automated green is not the property.** The worst finding of each audit came from hands-on testing, and a clean scan is a statement about the scanner's categories, not the product. Full records: `evals/security-review-2026-08-03.md`, `evals/a11y-scan-2026-08-03.md`.

## 8. Known Limitations

- **Phrasing sensitivity** is mitigated and measured, never eliminated: before the both-phrasings anchor landed, "big green egg grills" drew a grounded no while "green egg grills" drew a hedge. Anchors reduce the class; the eval suite watches it.
- **The judge has a documented conservative bias** — it flags unverifiable claims as potentially invented because it can't see the catalog. That's accepted by design; the human adjudicates.
- **The closing board's two failures** (`negative-material`, `compound-ebel`) have fixes in prompt and content, verified by spot-checks — but per provenance rules they stay red until the next full battery certifies them.
- **Cosmetic drift:** occasional "Great question!" openers, and intermittent markdown/emoji despite the plain-text rule (the widget renders raw text by design, so drift is visible, not dangerous).
- **By design:** no stock or inventory answers (POS not integrated), no order lookups (a deliberate privacy ruling — order questions route to staff), and per-tab session memory (`sessionStorage`).

## 9. Roadmap

- **Phase 8 — pre-deploy gate:** rate limiting, CORS, kill switch, AI-disclosure line, data-deletion mechanism, privacy-policy amendments (owner-approved, lawyer-reviewed), Snyk SCA/SAST, standing secrets-access deny rules with a fake-`.env` canary test.
- **Vision:** customer photo upload → identify furniture and forward to staff. Demand is validated by the store's inbox history; today a bridge rule asks customers to describe the item or email the photo.
- **Order status:** the **#1 question class in real traffic** (9 of ~40 mined lines). Building it requires a new API scope *and* reversing a deliberate privacy ruling, so it's scheduled as an owner decision, not a sprint.
- **Phase 9:** head-to-head benchmark against Shopify Inbox's built-in AI agent, on the same mined question bank.

## 10. Numbers & Receipts

| Metric | Value |
|---|---|
| Eval cases (final) | 32 — later cases mined from real customer traffic |
| Closing board (human-graded) | **30 / 32** (2 FAILs kept, characterized in §5) |
| Judge agreement at close | 27 / 32, every disagreement adjudicated in writing |
| Score arc | 14 / 1 / 2 (first 17-case run) → 30 / 32 |
| Knowledge base | 446 product chunks + 101 policy sections = 547 |
| Security review | 0 findings above bar, spot-verified · gitleaks: full history, no leaks |
| Accessibility | Lighthouse 12/14 → 19/19 · axe 7 → 0 · VoiceOver speaks replies |

Key commits: `7afc884` (eval era close — fabrication caught and addressed), `a044f97` (a11y fixes verified). Full artifacts in `evals/`: every results file with judge columns, the PII-stripped question bank, both audit reports, and `eval-notes.md`.

---

Built by Dominic Luckino ([github.com/dluckino](https://github.com/dluckino)) — every line typed, run, and verified by me; built with a Claude coding agent. MIT License.
