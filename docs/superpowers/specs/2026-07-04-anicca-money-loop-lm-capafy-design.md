# Anicca Money Loop — Life Manager + Capafy (focused) — Design Spec

- **Date**: 2026-07-04
- **Author**: Claude Code (dev IDE) with Dais
- **Decision owner**: Dais (verbatim 2026-07-04)
- **Pairs with**: `2026-07-04-openclaw-claude-p-merge-design.md` (the claude-p harness) — this spec sets WHAT the loop earns money on.

## 0. Decision (Dais 2026-07-04) — drop x402, focus on 2 money engines
The self-improving claude-p loop's job = **make money + self-improve, using ONLY the skills with the highest probability of earning**. Concretely = **TWO engines**:
1. **Life Manager** — scale the $20/mo phone agent (just shipped: Gemini two-way + barge-in + cost fixed).
2. **Capafy** — publish skills as subscription sales-agents; the `anicca-capafy-daily-publish` cron already runs `capafy-autopublish/scripts/daily_publish.sh` daily (1 backlog skill → full publish chain).

**Dropped**: x402 / direct-crypto self-earn. Not in scope.

## 1. The money truth (corrected)
Money flows to the **human's registered account** (Apple/Stripe/Capafy are tied to Dais's legal entity; Apple forbids crypto payout). So the loop earns money **FOR Dais** (→ his bank), which is *why a human starts an Anicca up*. The self-funding target: **total product revenue (LM + Capafy) > what Dais spends (~$200/mo)** → the experiment "can an AI given human credentials earn more than the human spends on it" succeeds when this crosses $200.

Reality now (dashboard.json 2026-07-04): MRR $27, spend $128–200, profit **−$101 to −$173/mo**. Target $10k MRR / 2026-05-31.

## 2. Engine A — Life Manager (scale)
- **State**: shipped + prod-verified (Gemini two-way default + barge-in; Composio calendar; $100→<$10 cost; pay-link fixed; money-path monitor). 3 users (all Dais tests), $0 net new revenue.
- **Scale levers (the loop works these, weakest funnel step first)**:
  - E1 **Gmail late-notice** (raise value → retention). = task #6.
  - **Funnel instrumentation**: start→calendar-connect→phone→pay→retain; measure drop-off.
  - **Distribution**: Telegram onboarding link where late-prone people are (ADHD/busy-pro communities); the pitch = "never be late — it calls you."
- **Revenue proof**: a real non-Dais user pays $20/mo (Stripe `lm_stripe_events` > 0).

## 3. Engine B — Capafy (daily autopublish)
- **State**: `anicca-capafy-daily-publish` cron EXISTS (daily 1-skill publish chain). Publish playbook = `~/.openclaw/docs/CAPAFY_PROFITABLE_PLAYBOOK.md` (clone top sellers: run_online + subscription + 3-tier ladder $1.99/$2.99–5.99/$6.99–14.99 + 24h trial + message caps).
- **Earn model**: buyers subscribe → we host the LLM → recurring revenue (minus hosted-LLM cost; safe margin ≈ week $5.99 × cap8). Download almost never sells → publish as **subscription**.
- **The loop's job here**: (a) verify the daily cron actually PUBLISHES (status=under-review→listed), (b) feed the backlog with skills that have high earning probability (clone proven winners' niches), (c) track sales per listing, kill dead listings, double down on sellers.
- **Revenue proof**: a Capafy listing gets a paid subscriber (real sale in the Capafy dashboard).

## 4. The loop (GLVS, claude-p) — self-improve + self-heal
```
GOAL   done = (LM Stripe revenue + Capafy subscription revenue) > Dais monthly spend
READ   dashboard.json + Stripe(lm_stripe_events) + Capafy sales + App Store Connect + spend
ACT    pick the single highest-EV action across the 2 engines:
         A) LM: fix the weakest funnel step / ship E1 / post the onboarding pitch
         B) Capafy: verify daily publish landed / add a high-EV skill to backlog / promote a seller
VERIFY real side-effect (new Stripe sub / new Capafy subscriber / retained user) + fresh-context adversary
STATE  STATE.md: what was tried, what the metric did, what to try next; kill losers, scale winners
→ next cycle (human out of loop; main-agent out of loop after the harness is built)
```
Self-heal = the money-path-monitor pattern (already built for the Stripe link) generalized: if a revenue surface breaks (LM /health down, Capafy cron failing, pay-link wrong), auto-detect + heal + one Telegram ping.

## 5. Non-goals
x402/crypto self-earn (dropped). New product surfaces beyond LM + Capafy (stop the factory-app sprawl; focus). Mass-migrating all ~157 OpenClaw crons to claude-p at once (quota burn + unverifiable — start with these 2 engines).

## 6. First moves (ordered)
1. **Verify Capafy daily cron actually earns** — is `anicca-capafy-daily-publish` publishing + is anything selling? (read cron logs + Capafy sales). If broken, fix it (it's the cheapest already-wired revenue).
2. **LM E1 Gmail late-notice** (retention value) + **funnel instrumentation** (see where users drop).
3. **Build the claude-p GLVS harness** that drives the 2 engines on a cadence, reads the metrics, verifies real revenue, updates STATE.md — starting L1 (report-only) → L2 (assisted) → L3 (unattended).

## 7. Reddit / community = an AUTHENTIC-CONVERSATION LOOP, not a broadcast cron (Dais 2026-07-04)
The reason marketing must be a **loop** (claude-p agent) and NOT a fire-and-forget cron: real community growth is **ongoing, stateful, two-way conversation + trust**, not posting links. Dais verbatim intent:
- We do NOT push the product. We JOIN the conversation genuinely — answer people's questions, be helpful, be a real participant in the subreddit.
- Trust is built CONTINUOUSLY over many interactions (the loop remembers past threads/people = stateful; a cron can't).
- The product surfaces NATURALLY and softly, as a builder story tied to a real pain: "this is a problem I have, and I can explain it carefully — I built X to solve it." Never pushy, never a link-drop.
- Because it's a real problem we understand deeply, we can explain it well → that earns trust → trust converts, not a CTA.

### Design implications
- **Agent-driven judgment per conversation** (memory `feedback_build_agents_not_hardcode_regex`): the agent reads each thread/reply and DECIDES what to say — no scripted templates, no regex, no canned CTA. My job = build the LOOP; the agent decides the words (memory `feedback_build_the_harness_not_do_their_work`).
- **Stateful**: track which subreddits/threads/users we've engaged, what was said, karma, what earned trust vs got removed → STATE.md. Reply to replies (the conversation continues).
- **Value-first cadence**: mostly helpful comments (no product), occasional genuine builder-story post; respond to every reply/question. NOT daily link spam.
- **Targets** (LM's pain = lateness): r/ADHD, r/productivity, r/getdisciplined, r/executivedysfunction, r/SideProject, r/startups.
- **Guardrails**: warmed/aged accounts (karma first via genuine comments), per-subreddit rules respected, ban-risk tracked, back off where removed. Same warmup discipline as TikTok/IG.
- **Self-improve**: measure signups attributed to reddit + trust signals (upvotes, positive replies, DMs asking "what's it called"); double down on what earns trust, drop what gets removed.

This is a NEW engine of the claude-p money loop (alongside Capafy publish + LM funnel). It is the clearest example of why the harness = a conversational LOOP, not a cron.

## 8. VERIFY findings (2026-07-04) — Capafy engine was DEAD (task #9)
Verified `anicca-capafy-daily-publish` (09:00 JST daily). TWO failures found:
1. **Auth expired**: the `am_sk_…` access token returns `code 1001 "Token is invalid or expired"`. The cron has been failing auth for ~6 weeks; last successful publish = 2026-06-04 (afrexai, agent_id 5837985051), log stopped 2026-06-22. Revenue from Capafy ≈ $0 (the $27 total MRR is not Capafy).
2. **Backlog mostly unpublishable**: ~211 backlog skills, the majority SKIPPED by the leak-guard ("SKILL.md has creator-local paths/refs") or size (>500 KB). Even after re-auth, few skills can publish as-is.

**Fix (no-human-in-loop, Dais consented to Capafy ToS/privacy 2026-07-04)**: no refresh_token exists (config has only access_token/user_id/email/name) → re-auth = email-OTP (`login-init` → OTP to keiodaisuke@gmail.com read via `gog gmail` → `login-verify` → new token to config.json). Then: publish 1 skill to prove revival; query real listings + sales; fix failure #2 by cleaning creator-local refs so more skills publish. This is why the loop must SELF-HEAL: a "daily money cron" silently died for 6 weeks with nobody noticing — the harness must detect+heal revenue-surface auth expiry (generalize the money-path-monitor).

### Execution directive (Dais 2026-07-04)
NO human in the loop. Execute the TODO one-by-one IN ORDER, never skip. #9 (Capafy revive) → #6 (LM E1/funnel) → #10 (Reddit loop) → #8 (harness). Each item run to real-side-effect verification before the next.

## 8b. VERIFY conclusion — Capafy earns $0 (demand, not publishing, is the wall)
Fresh query (token re-authed 2026-07-04): 19 published agents, **ALL 0 sales, $0 revenue, $0 payout (below_threshold)**. Statuses mixed — some `status=0` (draft, never submitted), some `status=4` (LISTED but 0 sales). The marketplace DOES have demand (memory: top sellers 68/57/56 sales) → our listings are just not competitive/discoverable → $0.
**Decision (data-driven)**: Capafy's bottleneck = DEMAND, not publish volume. Pumping more daily listings = supply into a market where ours get $0 = waste. Token is fixed (the cheap existing cron can keep running), but Capafy is **LOW-ROI**; the money loop's effort goes to Life Manager (real product, real $20/mo) + Reddit demand-gen. Capafy stays a background cron, NOT a loop focus, until/unless a demand fix (competitive listings in proven niches, or promotion) is proven to convert. This is itself a self-improve signal: measure→reallocate away from a $0 engine.

## 9. META-FINDING (2026-07-04 verification pass) — the wall is DEMAND, not features
Verifying the TODO one-by-one surfaced a consistent pattern: **the features already exist; nothing has users/sales.**
- Capafy: 19 published listings → **$0** (0 sales). Publishing works; demand = 0.
- Life Manager: full feature set (two-way voice, calendar, cost-fixed, monitor) → **3 test users, $0 net new**.
- Late-notice (E1): **already built + wired + live** (notify.js via Resend, server.js:43/263). Not a gap.
⇒ Building MORE features (E1 Gmail upgrade, more Capafy listings) is NOT the lever. **The single bottleneck = DEMAND / distribution / getting real users.** The money loop must put its effort into DEMAND GENERATION: #10 Reddit authentic-conversation loop + LM funnel distribution, NOT more supply. Deprioritize: E1 Gmail upgrade (feature exists via Resend), Capafy publish volume (0 demand), E2 Pipedream (Composio works). Reorder the money loop: **#10 Reddit demand-gen → #8 harness that optimizes demand → measure real signups/sales**. This is the honest, data-driven pivot.

## 10. SELF-IMPROVING design (Dais 2026-07-04) — both engines learn; kill the duplicate trash
Root cause of low demand (Dais): "we're not following best practice sometimes." Fix = make BOTH engines SELF-IMPROVE (read outcomes → adjust → follow BP better), and delete the duplicate skills that caused confusion.

### 10a. Dedup / refactor (the trash)
- `capafy-autopublish` VENDORS its own `vendor/capafy-publisher` + `vendor/capafy-user` (SKILL.md: "never invoke the standalones directly"). But the cron runs the OLD `scripts/daily_publish.sh` which points at the STANDALONE `~/.openclaw/skills/capafy-publisher` (line 23) — a duplicate. This double-copy is what confused both Dais and me (I refreshed the standalone token, not the vendored one).
- Refactor: (1) fresh token copied into the vendored configs [DONE 2026-07-04, verified code 0]; (2) repoint the cron `anicca-capafy-daily-publish` from `daily_publish.sh` → the vendored **DAILY_LOOP** (`claude -p --model sonnet` per DAILY_LOOP.md, which uses `publish_one.sh` → `vendor/capafy-publisher`); (3) DELETE the standalone `~/.openclaw/skills/{capafy-publisher,capafy-user}` + `cfo-earner-capafy` (0 cron refs) once the cron no longer references them.

### 10b. Capafy self-improve loop
Publishing already works; DEMAND is the gap → the loop must LEARN what sells:
- **READ**: per-listing sales (`GET /agent/sales/trend`, `/agent/agents`), status, views; the winners' current pricing/structure (market search).
- **JUDGE (agent, not hardcode)**: which of our niches/listings convert vs which are dead; are we drifting from a proven winner's structure/pricing/category; are any listings overclaiming (linter) or wrong-type (not sandbox-complete).
- **ACT**: adjust pricing/listing copy toward the current top sellers; retire dead listings (free the ≤5 slot); build the NEXT inventory item in a PROVEN-selling niche (copy the current winner verbatim); re-publish.
- **VERIFY**: real sales delta over weeks (not vanity "published"). STATE.md tracks niche→sales.
- This is why it's a LOOP: the market moves; the agent re-reads winners + our sales each cycle and follows BP, instead of blindly publishing more supply.

### 10c. Life Manager self-improve loop
- **READ**: funnel (Telegram start→calendar-connect→phone→pay→retain), activation, churn, cost-per-outcome, call transcripts.
- **JUDGE**: weakest funnel step; why users drop; what the onboarding/pitch/paywall gets wrong vs BP.
- **ACT**: fix the one weakest step (onboarding copy, paywall, distribution to r/ADHD etc.), ship it, measure.
- **VERIFY**: real new paid users (Stripe `lm_stripe_events`).

### 10d. The harness ties them
`claude -p` GLVS loop drives both engines: reads real revenue, picks the highest-EV self-improvement across LM + Capafy, verifies real side-effect, updates STATE.md, repeats — human + main-agent out of the loop. Reddit demand-gen (#10) feeds LM. Self-heal (money-path-monitor pattern) catches auth/expiry outages like the 6-week Capafy token death.

## 11. THE LOOP ITSELF — the self-improve + self-heal mechanism (Dais 2026-07-04: "the loop itself" is the product)
The engines (LM, Capafy, Reddit) are interchangeable; the PRODUCT is the LOOP mechanism that makes them improve + heal with no human. Every cycle (claude-p, launchd), in order:
0. **HEAL FIRST** — health-check EVERY revenue surface before anything else: auth alive (Capafy/Stripe/Gemini/Composio tokens not expired), endpoints 200 (LM /health, aniccaai.com, pay-link), crons firing (log freshness). If broken → auto-fix (re-auth via email-OTP, restart, rollback) or ONE escalation. ★This step is what was missing — the Capafy token died and the "daily money cron" ran dead for 6 weeks with nobody noticing.★ Generalize the money-path-monitor into a per-surface heartbeat.
1. **READ** — STATE.md + live metrics (LM funnel, Capafy sales, spend, current winners).
2. **JUDGE** (agent, no hardcode) — the single highest-EV action to increase REAL revenue now.
3. **ACT** — do that one action (raise quality toward market BP, not raw supply).
4. **VERIFY** — real side-effect only (new Stripe sub / new Capafy subscriber / retention), + fresh-context adversary. "Published / posted" ≠ success; money moved = success.
5. **STATE** — persist what was tried, how the metric moved, next hypothesis; scale winners, retire losers. Conversation is volatile; STATE.md is durable.
→ next cycle, human + main-agent out. Roll out L1 report-only → L2 assisted → L3 unattended.

**Invariant**: the loop must be able to detect + heal its own breakage (self-heal) AND move a real revenue metric over time (self-improve). A loop that only publishes/posts (no heal, no revenue-verify) is the failure mode we just found. Build the HARNESS (this mechanism) first; the engines plug into it.

## 12. Current cleanup state + the claude-p decision (2026-07-04)
Investigated the Capafy scheduling reality:
- **The smart self-improving loop was BUILT but NEVER powered on.** `scripts/daily_loop.sh` (fires `claude -p --model sonnet` on `DAILY_LOOP.md`, uses `publish_one.sh` → **vendored** capafy-publisher) exists, but there is NO launchd job loaded and the cron does not point at it → it never ran. The only thing that ever ran = the OLD cron → `daily_publish.sh` → **standalone** `~/.openclaw/skills/capafy-publisher` (died 2026-06-22, token expired).
- **DONE**: fresh token copied into the vendored configs (verified code 0); `.bak`/`.bak.original` cruft deleted.
- **DECISION (per Dais's standing "merge OpenClaw crons into claude-p" direction, which supersedes the old "no claude-cli in cron" rule FOR THIS)**: go **claude-p**. Repoint the cron `anicca-capafy-daily-publish` (09:00 JST) → `daily_loop.sh` (Sonnet, 1 listing/run, `--max-turns 40`, cheap + quota-capped). Then DELETE the old path: `daily_publish.sh`, standalone `~/.openclaw/skills/{capafy-publisher,capafy-user}`, `cfo-earner-capafy` (0 cron refs). This powers on the self-improving loop for the first time.
- This is #11 (cleanup) fusing into #8 (the harness): the "repoint to daily_loop.sh claude-p" IS turning on the self-improving mechanism (§11). Coordinate with `2026-07-04-openclaw-claude-p-merge-design.md` (same claude-p direction).
- **Self-heal gap to close (§11 step 0)**: nothing noticed the loop was dead for 6 weeks OR never wired. The harness's HEAL-FIRST heartbeat must assert "the money cron actually fired + published in the last N days" and re-arm/alert if not.

## 13. BUILD: lm-capafy-loop harness spine (2026-07-04, claude-p way, VCSDD)
Corrected the architecture per Dais: the money loop runs the **claude-p way** (~/anicca/skills, Claude-subscription-fueled, like ~/anicca/skills/self/founder-loop + earn/clip's cli.sh+healthcheck+launchd), NOT an OpenClaw gateway cron. Built `~/anicca/skills/self/lm-capafy-loop/loop.sh` (committed anicca main f723435), modeled on founder-loop.sh:
- **HEAL-FIRST**: curl-checks each revenue surface — Capafy `/agent/account` (auth alive?), LM `/health` (200?), Stripe `/v1/subscriptions` (key valid?). Any down → STATE says exactly how to heal (e.g. "CAPAFY-AUTH-DOWN → re-login"). This is the missing piece that let Capafy die silently for 6 weeks.
- **READ real revenue (anti-fake)**: LM active paid subs (Stripe API) + Capafy net revenue (`/agent/sales/trend`). A number is real ONLY if the provider API returns it; "published/posted" is never revenue.
- **GOAL-check + atomic STATE.md**: goal = LM+Capafy revenue > Dais spend; STATE holds the real numbers + heal status + next action.
- **VERIFIED live 2026-07-04**: ran it — heal=none (all surfaces healthy), LM_subs=0, Capafy_net_3d=$0.0, honest status "NO realised external revenue yet — bottleneck = DEMAND". No fabrication.
This spine is the measurement backbone; the ACT (self-improve action = agent judgment) + the always-on cli.sh/healthcheck/launchd wrapper (claude-p cron cadence, self-heal restart) come next (#8), following the clip pattern exactly.

## 14. Correction (Dais 2026-07-05) — I missed a Claude-side duplicate; plan clarified
Honest answers to Dais's questions about what I actually did:
- **Capafy publish scheduling**: I repointed the OpenClaw CRON (jobs.json, 09:00) → `daily_loop.sh` (which spawns `claude -p sonnet`). This is a HYBRID (OpenClaw cron triggers a claude-p run), NOT yet a pure always-on claude-p loop (tmux+launchd like earn/clip). Imperfect.
- **Old vs new**: on the OpenClaw side I DID delete the old (standalone `capafy-publisher`+`capafy-user`, `daily_publish.sh`, `publish_chain.sh`, `.bak`) and kept the new working one (`capafy-autopublish` + vendored + `daily_loop.sh`).
- **Both AIs — I MISSED one**: there were TWO separate real copies of `capafy-autopublish` — `~/.claude/skills/` (stale, 6/28) and `~/.openclaw/skills/` (fixed, 7/4). I only fixed the OpenClaw one → the Claude-side copy was another stale duplicate. **FIXED 2026-07-05**: `~/.claude/skills/capafy-autopublish` is now a **symlink → the canonical `~/.openclaw/skills/capafy-autopublish`**, so both AIs share ONE fixed copy (vendored token, no `daily_publish.sh`, no divergence).

### Corrected target architecture (unify into ONE claude-p loop)
The Capafy publish (`daily_loop.sh`) and the money-measurement spine (`~/anicca/skills/self/lm-capafy-loop/loop.sh`) are currently SEPARATE. Target = ONE claude-p always-on loop (`lm-capafy-loop`, ~/anicca/skills, Claude-subscription, tmux+launchd healthcheck like earn/clip): HEAL → READ (LM funnel + Capafy sales) → JUDGE → **ACT calls the engines** (Capafy `daily_loop.sh` / LM funnel fix / Reddit) → VERIFY real revenue → STATE. The OpenClaw cron becomes redundant once the always-on loop drives publishing. Both AIs reference the ONE canonical skill via symlink. Next (#8): wrap lm-capafy-loop in cli.sh+healthcheck+launchd (copy earn/clip pattern) and make ACT invoke the Capafy engine.
