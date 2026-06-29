# Earn Slots — Daily-Loop Master Plan (2026-06-30)

THE canonical plan for making every earn method run as its own **independent, every-single-day** loop,
build via **/vcsdd** (verification-driven: spec → RED → GREEN → fresh-context adversary → no-mock E2E →
**my own browser/on-chain output verify**). Not rushed. Verify the OUTPUT of each, one by one.

## Core principle (CORRECTED 2026-06-30, BP-verified) — NOT a one-picker
WRONG: one loop that each wake picks the single highest-ROI slot (it could "choose not to post clips today").
RIGHT: **each earn method is its OWN independent loop that posts/acts EVERY day, unconditionally.** Consistency
is the product. Only by posting daily per method do we learn what actually works; what works starts earning.
- BP-1 (consistency): Medium "I Tried Monetizing Faceless Reels for 30 Days" (@vireuoess) — *"post
  consistently for 30 days… just strategy, CONSISTENCY"*, *"scalable, post multiple times a day"*.
- BP-2 (fastest first $): AI-earn guides — *"The fastest path is freelancing; land your first AI gig within
  1-4 weeks if you actively pitch."* → gig pays first; content is a reach game that pays later.
- BP-3: content (clip/video/affiliate) earns after reach builds (≈30 days+), so clip=$0 now is EXPECTED.

## The reusable EARN-CORE template (clone per slot; clip is the proven reference)
Every slot gets the SAME three pieces, independent per slot:
1. **PRODUCER** (daily launchd) — make fresh content/work-unit → a per-slot queue. (clip: producer.sh @3:17am)
2. **POSTER/ACTOR LOOP** (headless claude-p core, tmux + cron) — each fire: drain queue → post/act to the
   slot's ready accounts → record-earn → ledger. (clip: clip-cli.sh + cron :07)
3. **HEALTHCHECK** (launchd every 5min) — restart the core if it died. (clip: clip-healthcheck.sh)
All no-human (captcha→CapSolver, OTP→gog gmail/chat.db, login→creds), fail-closed account-guard, INV-7
record-earn (only real external on-chain USDC counts).

## AUDITOR (separate, over ALL loops)
A monitor that checks: (a) every slot's loop is actually firing daily, (b) each verifies correctly
(record-earn, no fake "posted=earned"), and (c) **thinks about whether what each slot is doing will actually
work** (strategic, not just "did it run"). Surfaces failures + improvement ideas. (index.mjs's old
"pick one" role is retired → repurpose toward monitoring; it does NOT choose whether to post.)

## Per-slot: ideal · money path · status · get-there
| slot | ideal (daily) | money path | status | get-there |
|---|---|---|---|---|
| **clip** | clip real podcasts → post daily to all platforms | per-view campaigns (Whop/clipping.net USDC) + organic→own offers | ✅ full daily loop LIVE (producer+core+healthcheck); $0 (reach) | keep running; wire wallet on Whop/clipping.net; revisit when a clip breaks ~50-100k views |
| **gig** | scan boards → bid/deliver AI-doable gigs daily | ★ client pays USDC directly (LaborX/Coconala/abillio) — no views needed ★ | ✅ run.sh(real, detect/bid/deliver/settle)+spec+live; ❌ no daily driver | ★ FIRST: add core+healthcheck+daily driver (fastest first $, 1-4wk) ★ |
| **affiliate** | educational faceless slideshows daily, Amazon link in bio | ★ commission per sale (no campaign needed) ★ | △ earn-affiliate-slideshow skill exists; ❌ run.sh + daily loop | build run.sh (wrap slideshow) + producer + core + healthcheck |
| **audit** | scan code4rena/Cantina → analyze → submit findings daily | ★ $60-135k USDC pools per valid finding ★ (highest unit) | ❌ declared, no run.sh | build run.sh (discover→analyze→draft/submit) + daily driver; flag KYC/account blockers honestly |
| **video** | faceless gen (MoneyPrinterTurbo) → post daily | YouTube ad rev + clip campaigns + desc affiliate | ✅ run.sh + video-core running (other CC); $0 | add producer + healthcheck to clip parity; keep daily |

## Money-certainty order (build daily-loops in this order)
gig (fastest, client-pays) → affiliate (commission/sale) → audit (highest unit) → video (parity) ; clip = done.

## Build order (each via /vcsdd, verify output one-by-one — NOT rushed)
1. **GIG daily loop** — run.sh exists; add the earn-core (core+healthcheck+daily driver) so it bids/delivers
   every day. Verify: a real bid/delivery action observed + (eventually) a real USDC settle on-chain.
2. **AFFILIATE** — build run.sh (wrap earn-affiliate-slideshow) + producer + core + healthcheck. Verify: a
   real slideshow posted daily to our own account (browser-verified), Amazon link in bio.
3. **AUDIT** — build run.sh (discover→analyze→draft) + daily driver. Verify: real open-contest list fetched,
   a candidate finding drafted; honestly flag what blocks a real submission.
4. **VIDEO** — bring to clip parity (producer + healthcheck). Verify: a real faceless video posted daily.
5. **AUDITOR** — build the cross-loop monitor (daily-fire check + verify-correctness + strategic "will it work").
6. **Generalize** — extract clip's core/healthcheck/producer into an `earn-core` template each slot reuses.

## Verification discipline (every step)
/vcsdd: spec → RED (failing check) → GREEN → fresh-context adversary (maker≠checker) → no-mock E2E (real run)
→ ★ MY own output verify ★: browser-render check for posts (video plays + captions, naturalWidth>0), on-chain
check for USDC (record-earn / wallet balance). "ran / posted / submitted" ≠ done. Real side-effect or it's not done.
Agent team may build; I verify every output myself.
