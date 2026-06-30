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
| **bounty** | discover real agent-eligible bounties daily → deliver → payout | ★ task pays USDC per delivered bounty (Algora PR-merge; new: Superteam/ClawTasks/hackathons) ★ | ✅ run.sh+core+healthcheck LIVE; $0 (Algora inventory dry) | add Superteam Earn + ClawTasks (Base USDC, agent-native) as new sources beyond Algora; honest payout-KYC gate |
| **video** | faceless gen (MoneyPrinterTurbo) → post daily | YouTube ad rev + clip campaigns + desc affiliate | ✅ run.sh + video-core + healthcheck (auto-revive 2026-06-30); $0 | keep daily; self-improve toward more money |

NOTE (2026-06-30, Dais): the **audit** slot was DELETED. "audit" was a misnomer — it wasn't auditing anything; it
was bounty-hunting on code4rena/Cantina, which had **no open openings** for us. `bounty` is the correct, single
name for that job. 5 slots remain: clip · gig · affiliate · bounty · video.

## Money-certainty order (build daily-loops in this order)
gig (fastest, client-pays) → affiliate (commission/sale) → bounty (per-task USDC) → video (parity) ; clip = done.

## Build order (each via /vcsdd, verify output one-by-one — NOT rushed)
1. **GIG daily loop** — run.sh exists; add the earn-core (core+healthcheck+daily driver) so it bids/delivers
   every day. Verify: a real bid/delivery action observed + (eventually) a real USDC settle on-chain.
2. **AFFILIATE** — build run.sh (wrap earn-affiliate-slideshow) + producer + core + healthcheck. Verify: a
   real slideshow posted daily to our own account (browser-verified), Amazon link in bio.
3. **BOUNTY** — broaden sources beyond Algora (dry): add Superteam Earn (superteam.fun/skill.md, agent register→
   listings/live→submit) + ClawTasks (clawtasks.com/skill.md, Base USDC, agent-hires-agent). Verify: real
   agent-eligible listings fetched from a NON-empty source; honestly flag the human-claim/KYC payout gate.
4. **VIDEO** — clip parity DONE (producer + healthcheck auto-revive, 2026-06-30). Verify: a real faceless video posted daily.
5. **AUDITOR** — build the cross-loop monitor (daily-fire check + verify-correctness + strategic "will it work").
6. **Generalize** — extract clip's core/healthcheck/producer into an `earn-core` template each slot reuses.

## Verification discipline (every step)
/vcsdd: spec → RED (failing check) → GREEN → fresh-context adversary (maker≠checker) → no-mock E2E (real run)
→ ★ MY own output verify ★: browser-render check for posts (video plays + captions, naturalWidth>0), on-chain
check for USDC (record-earn / wallet balance). "ran / posted / submitted" ≠ done. Real side-effect or it's not done.
Agent team may build; I verify every output myself.

## ★ EMPIRICAL bounty-well findings (2026-06-30, all sources actually probed live) ★
The bottleneck is DEMAND/inventory, not the loop. All three bounty wells are dry RIGHT NOW (verify-first, not theory):
| source | probe result | doable USDC now | verdict |
|---|---|---|---|
| Algora (GitHub) | 48 "open" → gate caught 4/4 fake (withdrawn / dead-funder / token-paid / existing-PR) | $0 | dry |
| Superteam Earn | registered (HTTP 201, creds saved); 9 "live" listings = 8 closed (winners announced months ago) + 1 open: Imperial AI Agent Hackathon $5,000 USDG due 2026-07-06 — contest-judged + demo-video + UK-scoped + human claimCode payout gate | ~$3k contest long-shot | nearly empty |
| ClawTasks | free_tasks_only:true (paid-bounty WIND-DOWN); /api/bounties 500s; "No open bounties"/"No agents yet"; register 500s | $0 | dead/dormant |
→ CONCLUSION: a fixed list of wells is the wrong design. We need the auditor (below) to HUNT wells continuously.

## ★ SELF-IMPROVEMENT ARCHITECTURE (the real ask — backed by primary sources) ★
Three "selves": ① self-HEAL ✅ (healthcheck revives dead cores, all 5 slots incl. video as of today) ·
② self-IMPROVE 🟡 (only earn/video has the inner "make next better" loop) · ③ self-DIRECT ❌ (no "highest-ROI" brain).
Two altitudes (sources converge on separation of concerns):
- INNER (per slot) = Voyager (arxiv 2305.16291) + Reflexion (arxiv 2303.11366): each wake read real USDC outcome →
  verbal post-mortem to memory → mutate next tactic → keep what raised USDC. earn/video already does this; EXPAND to all 5.
- OUTER AUDITOR (1, less frequent) = Darwin-Gödel Machine (arxiv 2505.22954) + STOP (arxiv 2310.02304) + bandit
  (lilianweng multi-armed-bandit): (i) keep a VERSIONED ARCHIVE of skill/tactic variants, branch new ones from old
  "stepping stones"; (ii) allowed to rewrite the runner/decide logic itself; (iii) rank earn-slots by expected
  USDC/wake and allocate the next wake via UCB/Thompson (exploit winners, probe new wells) — the "AI-Elon" mover;
  (iv) when a well dries (Algora/Superteam/ClawTasks all $0), the auditor HUNTS a new well (agent-reach) and BUILDS
  a new slot (skill-creator). MUST run under the INV-7 on-chain-USDC-only reward gate + a fresh-context adversary
  (DGM reward-hacked by faking logs → verifier is mandatory).
Have vs missing: HAVE = inner loop (video), INV-7 reward gate, recursive-improver (copy-only), decisive-agent (weak),
agent-reach (research). MISSING = DGM archive, STOP self-rewrite, and the cross-slot UCB/Thompson allocator keyed on
on-chain USDC/wake. ★ The single highest-ROI build = that cross-slot bandit allocator + archive = step 5 AUDITOR. ★
Swarm: loops are model-agnostic skills in public ~/anicca → any AI clones & runs the same earn+self-improve → trillion-agent swarm feeding one treasury.
