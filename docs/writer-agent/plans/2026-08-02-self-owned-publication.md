# Self-Owned Writer Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Subagents are disabled for this work. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a reader buy one Writer article or subscribe to the Writer archive on `aniccaai.com/blog`, unlock it without creating a site account, and feed exact Stripe receipts back into the canonical Writer Money Ledger.

**Architecture:** Public pages contain metadata and a useful preview only; paid bodies remain in Netlify function bundled private files. Stripe-hosted Checkout handles one-time payments and recurring Billing. A signed bearer entitlement binds a Checkout Session to an article or archive scope, and a local read-only Stripe collector turns verified Checkout, Subscription, Balance Transaction, refund, and payout objects into canonical Writer receipts. The existing Anicca Letter subscription prices become archive entitlement; this is article monetization, not automatic generation of a separate product.

**Tech Stack:** Next.js 14, React 18, Netlify Functions, Node test runner, Stripe Checkout/Billing API, HMAC-SHA256 entitlement tokens, Python Writer Money Ledger, launchd.

## Global Constraints

- Canonical requirements remain in `docs/writer-agent/WRITER-AGENT-SSOT.md`; this file is an execution plan, not a second SSOT.
- One-time Japanese Writer articles use JPY 500. English uses a separately provisioned Stripe Price recorded in the live receipt; currencies are never converted inside accounting.
- Recurring archive access reuses `STRIPE_LETTER_JP_PRICE` and `STRIPE_LETTER_EN_PRICE`; no unrelated generated product is introduced.
- Use Stripe-hosted Checkout Sessions and Billing, never Charges, raw card handling, or a manual renewal loop.
- Webhooks must verify the Stripe signature before any state transition. Secrets remain in Netlify/local secret stores and never enter source, logs, URLs, or Telegram.
- A successful redirect is not payment proof. Unlock requires a retrieved Checkout Session with matching metadata and paid/active status.
- No site login, Google account, Gmail account, note account, or Substack account is required by the reader. The entitlement is a signed bearer credential; Stripe may still collect legally/payment-required customer details.
- Test/dry-run/internal payments never count as revenue. A payment, fee, refund, subscription, and payout remain distinct receipt types.
- Every public article carries immutable `run_id`, `artifact_id`, `slug`, source hash, preview hash, and paid-body hash.

---

### Task 1: Private article contract and public preview

**Files:**
- Create: `apps/landing/netlify/functions/_lib/writer-article-contract.js`
- Create: `apps/landing/netlify/functions/_lib/__tests__/writer-article-contract.test.js`
- Create: `apps/landing/private/writer-articles/.gitkeep`
- Modify: `apps/landing/netlify.toml`
- Modify: `apps/landing/app/blog/[slug]/page.tsx`

**Interfaces:**
- Consumes: JSON `{slug,run_id,artifact_id,lang,title,source_sha256,preview_markdown,preview_sha256,paid_markdown,paid_sha256,access_model}`.
- Produces: `validateWriterArticle(value)`, `publicPreview(value)`, and private files bundled only into `writer-content`.

- [x] Write a failing Node test that rejects a changed hash, missing lineage, unsupported language, a preview duplicated inside the paid body, and an access model outside `one_time|archive|both`; assert a valid fixture returns metadata without `paid_markdown`.
- [x] Run `node --test apps/landing/netlify/functions/_lib/__tests__/writer-article-contract.test.js`; require the missing-module failure.
- [x] Implement exact SHA-256 validation and `publicPreview`, configure Netlify `included_files = ["private/writer-articles/**"]` only for `writer-content`, and make the blog route render only `preview_markdown` for a paid article.
- [x] Re-run the Node test and `npm --prefix apps/landing run build`; require both to pass and inspect generated HTML to prove the paid body is absent.
- [x] Commit only Task 1 files.

Task 1 receipt: product commit `c5782d72d` is pushed to both product remotes. The focused contract suite passes 3/3 and the existing Netlify suite passes 284/284. A production Next build passed; a temporary paid sentinel appeared in neither the generated article HTML, RSC payload, nor static chunks, while the public preview appeared in HTML and RSC. The temporary fixture was removed before commit. Netlify's per-function configuration scopes private article files to `writer-content`, not every function.

### Task 2: Checkout Sessions with exact Writer lineage

**Files:**
- Create: `apps/landing/netlify/functions/_lib/writer-checkout.js`
- Create: `apps/landing/netlify/functions/_lib/__tests__/writer-checkout.test.js`
- Modify: `apps/landing/netlify/functions/checkout.js`

**Interfaces:**
- Consumes: `{product:"writer_article"|"writer_archive",slug,artifact_id,run_id,lang,client_reference_id}` plus the validated private registry.
- Produces: URL-encoded Checkout Session parameters with exact metadata and a Stripe-hosted URL response.

- [x] Write failing tests proving unknown slugs, mismatched artifact/run IDs, missing anonymous client reference, and caller-supplied price IDs are rejected; assert one-time mode uses `STRIPE_WRITER_*_PRICE`, archive mode uses existing Letter prices, and all five lineage fields reach Checkout/Subscription metadata.
- [x] Run the focused Node test and require failure.
- [x] Implement an allowlisted registry lookup, `mode=payment` for one article, `mode=subscription` for archive, `client_reference_id`, `{CHECKOUT_SESSION_ID}` success URL, and no raw payment data.
- [x] Re-run focused tests and existing Netlify function tests.
- [x] Commit only Task 2 files.

Task 2 receipt: product commit `0a34eb014` is pushed to both product remotes. Eight focused tests prove server-selected Writer/Letter Prices, exact slug/run/artifact/lang/client-reference metadata on Checkout plus PaymentIntent or Subscription, fixed-origin return URLs, rejection before Stripe for unknown/mismatched/caller-priced requests, and unchanged legacy ebook mapping. The complete Netlify suite passes 292/292 and the production Next build passes. Writer calls pin Stripe API `2026-04-22.dahlia`; no raw card field or caller price reaches Stripe.

### Task 3: Accountless entitlement and paid-body delivery

**Files:**
- Create: `apps/landing/netlify/functions/_lib/writer-entitlement.js`
- Create: `apps/landing/netlify/functions/_lib/__tests__/writer-entitlement.test.js`
- Create: `apps/landing/netlify/functions/writer-content.js`
- Create: `apps/landing/components/blog/WriterUnlock.tsx`
- Modify: `apps/landing/app/blog/[slug]/page.tsx`

**Interfaces:**
- Consumes: retrieved Stripe Checkout Session/Subscription objects and `WRITER_ACCESS_SECRET`.
- Produces: `issueEntitlement`, `verifyEntitlement`, an HttpOnly/Secure/SameSite=Lax cookie, and paid markdown only for the bound slug or archive scope.

- [x] Write failing tests for tampering, expiry, wrong slug, unpaid Checkout, canceled/past-due Subscription, test-mode objects in live mode, and replay on another article; assert paid one-time and active/trialing archive paths pass.
- [x] Run the focused test and require failure.
- [x] Implement constant-time HMAC verification, a one-hour token, live Stripe retrieval on first success and recurring access, and generic public errors that disclose no Stripe IDs.
- [x] Add `WriterUnlock`: persistent random anonymous client reference, buy/subscribe buttons, success-session exchange, natural-language loading/error/access states, and paid-body rendering after entitlement.
- [x] Run focused tests, TypeScript build, and browser screenshots at 390px and 1440px; verify the paid body never appears before entitlement.
- [x] Commit only Task 3 files.

Task 3 receipt: product commit `d3ff8f967` is pushed to both product remotes. Constant-time signed one-hour access tokens are separate from long-lived HttpOnly purchase receipts, so a one-time buyer can return after the short token expires without paying again; archive access re-reads the Stripe Subscription and rejects canceled/past-due/test-mode objects. Twelve focused entitlement/content tests cover tampering, expiry, wrong-slug replay, unpaid Checkout, lineage mismatch, live/test separation, persistent one-time restore, and active/trialing archive access. The complete Netlify suite passes 304/304 and the production Next build passes. Temporary production-build sentinels were absent from generated HTML, RSC, route artifacts, and static chunks. The locked reader UI was visually inspected at 1440px and 390px; the fixture and screenshots were not committed.

### Task 4: Webhook safety and non-email Writer fulfillment

**Files:**
- Create: `apps/landing/netlify/functions/_lib/__tests__/writer-webhook.test.js`
- Modify: `apps/landing/netlify/functions/webhook.js`

**Interfaces:**
- Consumes: signed Stripe `checkout.session.completed`, `customer.subscription.*`, `invoice.paid`, `charge.refunded`, and payout events.
- Produces: idempotent `ok writer` acknowledgement; it never sends the ebook PDF or Letter email for Writer products.

- [x] Write failing tests proving bad signatures fail, Writer checkout does not execute ebook/Letter fulfillment, duplicate event IDs have one logical outcome, and unrelated existing products keep their behavior.
- [x] Run the focused test and require failure.
- [x] Route `writer_article` and `writer_archive` immediately after signature verification, retaining Stripe as the source of truth and leaving accounting to the read-only collector.
- [x] Run all Netlify function tests.
- [x] Commit only Task 4 files.

Task 4 receipt: product commit `282277aaf` is pushed to both product remotes. Stripe signatures now use constant-time comparison, accept rotated multiple `v1` values, and reject timestamps outside 300 seconds. Writer Checkout/Subscription/Invoice/refund/payout events return `ok writer` immediately after signature and JSON verification, with no ebook delivery, Letter email, or legacy store write. Duplicate Writer event IDs repeat the same zero-side-effect acknowledgement. Five focused tests include a real legacy ebook fulfillment regression; the complete Netlify suite passes 309/309 and a fresh production build reached a new final `BUILD_ID`.

### Task 5: Writer self-owned publication adapter

**Files:**
- Create: `skills/article-writer/scripts/self_owned_article.py`
- Create: `tests/art/test_article_self_owned_publication.py`
- Modify: `skills/article-writer/config/revenue-surfaces.json`
- Modify: `skills/article-writer/scripts/publication_resume.py`
- Modify: `skills/article-writer/scripts/article-resume-pending.sh`
- Modify: `apps/landing/app/blog/[slug]/page.tsx`
- Modify: `apps/landing/netlify/functions/_lib/writer-article-contract.js`
- Modify: `apps/landing/netlify/functions/_lib/__tests__/writer-article-contract.test.js`

**Interfaces:**
- Consumes: frozen run article, useful preview boundary, immutable hashes, stable slug, and the landing private-article target.
- Produces: a stable `self-owned/<lang>` publication intent and a public readback receipt bound to the same run/artifact; repeated execution never creates a second slug.

- [x] Write failing fixtures for deterministic slugging, preview/paid separation, exact hashes, existing same-hash skip, conflicting same-slug refusal, cross-repo dirty-state refusal, public preview readback, crash-window ledger repair, and non-blocking worker integration.
- [x] Run focused tests and require failure.
- [x] Implement staging through an isolated exact-target git transaction; never modify or stage unrelated landing changes. Commit/push content, then retry only the deploy readback while other loop work continues.
- [x] Keep the already-declared self-owned destination revenue-capable and integrate pending/resume without expanding or blocking exact8.
- [x] Run focused and full Writer tests plus the complete Netlify suite and production build.
- [x] Commit only Task 5 files.

Task 5 receipt: runtime commit `3725ee8` is pushed to the Writer runtime remote and product commit `cdd805380` is pushed to both product remotes. The adapter creates deterministic JA/EN preview+paid contracts from the immutable same-run drafts, persists `self-owned/<lang>` intent before git delivery, refuses unrelated landing dirt, commits only exact private article JSON targets, reuses the same slug/hash after a crash, and repairs a missing append-only ledger row from durable live state without duplicating it. Self-owned receipts are strict same-run adjunct rows and do not change the exact8 set. The resume worker starts the configured self-owned adapter under its own lock in the background, so landing dirt and deploy propagation cannot delay another platform. Production HTML exposes a script-safe `writer-public-contract` containing the exact public projection and preview hashes; the paid body remains private. Verification: 12 focused adapter tests, 606/606 Writer tests, 310/310 Netlify tests, shell/Python validation, and a production build. A temporary paid sentinel appeared zero times in generated HTML, RSC, and static assets while the public manifest and preview appeared on the fixture page; the fixture and generated snapshot were removed. Task 7 still owns live branch/remote provisioning, deployment, public readback, and real payment E2E.

### Task 6: Stripe receipts into the Money Ledger

**Files:**
- Create: `skills/article-writer/scripts/writer_stripe_sync.py`
- Create: `skills/article-writer/scripts/install-writer-stripe-sync-worker.sh`
- Create: `tests/art/test_article_writer_stripe_sync.py`
- Modify: `skills/article-writer/scripts/money_sync.py`
- Modify: `skills/article-writer/scripts/writer_report.py`

**Interfaces:**
- Consumes: read-only Stripe Checkout Sessions, Subscriptions, Invoices, Balance Transactions, refunds, and payouts whose metadata identifies the Writer.
- Produces: append-only external receipts and canonical direct-writing money/subscription/fee/refund/payout rows.

- [ ] Write failing fixtures proving metadata joins one artifact, session completion alone is not received money, active non-test subscriptions create MRR, invoice payment creates received recurring revenue, balance transaction creates the exact fee/net, refund reduces net, payout is not new revenue, and cursor replay is idempotent.
- [ ] Run focused tests and require failure.
- [ ] Implement a least-privilege read-only connector, durable cursor/outbox, exact Stripe object IDs and hashes, separate live/test handling, and five-minute `RunAtLoad` launchd installation.
- [ ] Add self-owned article/archive stream lines and receipt links to the shared Web/Telegram report.
- [ ] Run focused and full Writer suites.
- [ ] Commit only Task 6 files.

### Task 7: Live provisioning, deploy, and zero-revenue truth check

**Files:**
- Modify: `docs/writer-agent/WRITER-AGENT-SSOT.md`
- Runtime receipts only: Writer state and deployment/readback artifacts.

**Interfaces:**
- Consumes: tested Tasks 1-6 and existing Stripe/Netlify ownership.
- Produces: public preview URL, live Checkout URL, live entitlement denial before payment, installed receipt worker, and truthful zero revenue until an external buyer pays.

- [ ] Create live-mode reusable one-time Writer Prices (JPY 500 and the approved English amount) and set Netlify environment references without printing secrets; reuse Letter Prices for archive access.
- [ ] Deploy the landing branch and verify public preview, checkout metadata, cancel return, robots/canonical behavior, and mobile/desktop screenshots. Do not buy from the owner account to manufacture revenue.
- [ ] Install/kick the Stripe receipt worker immediately and prove repeated kicks produce no duplicate receipt.
- [ ] Run a real external-customer purchase only when it occurs organically; verify Checkout, entitlement, article body, money event, fee/net, payout state, Web UI, and Telegram all share the exact receipt lineage.
- [ ] Mark #13 DONE only after both a real one-time unlock and a real recurring renewal receipt; before then keep it PARTIAL with exact live evidence and remaining external events.

## Self-review

- Spec coverage: paid article, recurring archive, accountless reader UX, Writer publication, payment/subscription/fee/refund/payout accounting, reports, live deploy, and no-account OSS boundary are each assigned. General OSS packaging remains #21 and Cloudflare parity remains #22 in the SSOT.
- Placeholder scan: no `TBD`, generic error-handling step, or unstated interface remains.
- Type consistency: `slug/run_id/artifact_id/lang/client_reference_id` is the shared lineage across content, Checkout metadata, entitlement, publication receipt, and money receipt.
