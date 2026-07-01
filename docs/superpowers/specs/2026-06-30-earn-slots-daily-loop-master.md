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

---

## ★ IMPLEMENTATION SKELETON — Shared Earn-Core Library (added 2026-07-01, research-validated) ★

The architecture above is THE plan. This section nails down the concrete shared library every slot inherits,
so we stop hand-coding per-slot healthcheck/ROI/escalation. Validated by 2026 SoTA: VOYAGER (arXiv 2305.16291)
— skill-library-as-code; Reflexion (arXiv 2303.11366) — verbal RL post-mortem; EvoAgentX 2026 survey
(arXiv 2508.07407) — **Three Laws of Self-Evolving Agents: Endure / Excel / Evolve**; Anthropic Nov 2025
spec-gaming study + Terminal-Wrench 2026 — 331 logged reward-hacking patterns.

### Library location: `~/anicca/skills/_shared/`

Every slot's `<slot>-healthcheck.sh` and `<slot>-cli.sh` `source`s this. Plist passes `LOOP_NAME=<slot>`.

```
~/anicca/skills/_shared/
├── loop-healthcheck.sh        ← layer ② SELF-HEAL (8-mode detect+fix)
├── loop-roi.sh                ← layer ③ SELF-MEASURE-ROI (per-pass)
├── loop-improve.py            ← layer ④ SELF-IMPROVE (Reflexion verbal-RL on lessons.jsonl)
├── loop-scale.sh              ← layer ⑤ SELF-SCALE (raise/lower max_apply, spawn alt accounts)
├── loop-propose.sh            ← layer ⑥ SELF-PROPOSE (scan earning-skill-proposal GH issues, sandbox-eval)
├── cross-learn-read.sh        ← layer ⑦ PRE-STEP: gh issue list label=<slot>-lesson
├── cross-learn-share.sh       ← layer ⑦ B5 SHARE: gh issue create dedup by shared-lessons.jsonl
├── adversary-daily.sh         ← layer ⑧ SELF-VERIFY (daily 03:00 fresh-Opus + builder auto-fix ≤5 rounds)
└── escalate.sh                ← layer ⑨ ONLY human surface (gh issue label=escalation + TG ping)
```

### 8-mode self-heal (`loop-healthcheck.sh`, fires every 5 min via launchd)

Bug catalogue from real incidents — each gets auto-fix; only mode 8 escalates:

| # | failure mode (pane substring / signal)              | auto-fix |
|---|------------------------------------------------------|----------|
| 1 | tmux session missing                                 | restart core (existing) |
| 2 | `.last-pass` age ≥ 90 min                            | restart core (existing) |
| 3 | "Not logged in · Please run /login" in pane          | `send-keys /login` → capture OAuth URL → `gh issue create --label needs-login --body <url>` → TG watcher → Dais 1-tap |
| 4 | "Quick safety check: Is this a project you ... trust" | `send-keys "1" Enter` (we did this manually today; codify) |
| 5 | "PreToolUse:Bash hook error  node:internal/modules/cjs/loader" | grep hook script → identify missing module → `npm i -g <pkg>` → re-test |
| 6 | "API error · Retrying ... attempt N/10" with N≥5     | swap `--model sonnet` → `--model haiku-4-5`; restart |
| 7 | core ALIVE but `CronList` returns 0 jobs for `<slot>` | re-inject STARTUP via send-keys (= cron registration was dropped) |
| 8 | restart-log shows ≥5 restarts in 60 min              | call `escalate.sh <slot> "backoff cap reached: <last 5 audit verdicts>"` and stop |

### ROI tracking (`loop-roi.sh`, called at end of every pass)

Format `~/loops/<slot>/roi.jsonl` (append-only, one row per pass):

```jsonc
{
  "ts": 1782830000,
  "slot": "gig",
  "pass_id": "p-2026-07-01T00:27:00Z",
  "tokens_in": 24718,
  "tokens_out": 91300,
  "tokens_total": 116018,
  "token_cost_jpy": 174,           // tokens × PUBLIC API rate, NOT $0 (TRAP-5)
  "jpy_earned_this_pass": 0,        // ONLY settled receipts (INV-7/INV-8)
  "usdc_earned_this_pass": 0,
  "wall_seconds": 2278,
  "roi_7day_jpy": -1218,            // rolling Σ(jpy - token_cost) over 7 days
  "roi_30day_jpy": -1218,
  "actions_taken": 2                // applied count this pass
}
```

`roi_7day_jpy` drives layer ⑤ SELF-SCALE; `tokens_total` drives INV-11 kill-switch.

### 6 invariants (anti-slop, research-validated)

Existing INV-7 carries over. New:

- **INV-8 External non-replayable receipt.** A pass counts ¥/USDC earned only when the platform's API (Coconala
  payout endpoint / on-chain Transfer log / Stripe payout webhook) returns `{payout_id, payer, amount, ts}`. No
  screenshots, no agent self-log, no "I posted ∴ I earned." Source: Anthropic Nov 2025 spec-gaming production study.
- **INV-9 Two-clock check.** Skill not labelled "profitable" unless **7-day rolling** `roi_7day_jpy > 0`. Single
  big lucky pass does not unlock SELF-SCALE.
- **INV-10 Fresh-context adversary before mutation merge.** Every `strategy.json` self-edit, every new skill
  proposal, goes through `vcsdd-adversary` (Opus, fresh subagent) BEFORE the change is committed. The same
  context that wrote the change must never approve it. Source: DGM reward-hacked logs (arXiv 2505.22954).
- **INV-11 Token kill-switch.** Any skill whose `cumulative_tokens > 5 × cumulative_¥_earned_in_jpy` (priced at
  public API rates) is archived (= `loop.disabled` file dropped, cron skips, only `adversary-daily.sh` can
  resurrect after fixing). Prevents zombie loops that look "alive" only because Max plan masks cost.
- **INV-12 Skill provenance.** Every skill in `~/anicca/skills/earn/<slot>/manifest.json` records:
  `{origin: "self" | "github-issue:<owner>/<repo>#<n>" | "fork-of:<sha>", first_seen_ts, last_audit_round}`.
  Required for the "Endure" law — must be rollback-able if a sibling-learned skill turns toxic.
- **INV-13 Runner writes manifest, skill emits events.** A skill's code MUST NOT write to its own
  `manifest.json`. The slot runner (= the claude-p in tmux) writes; the skill emits `{event: "earn",
  receipt_id, amount}` and the runner verifies + appends. Closes the inflation hole where an agent grades
  itself.

### 6 known traps to defend against (with mitigation)

| trap | failure mode | mitigation in skeleton |
|------|--------------|------------------------|
| **TRAP-1 Reward hacking** | "applied=earned" "posted=earned" | Already INV-7/8 |
| **TRAP-2 Cognitive surrender** | merging skills nobody read | `adversary-daily.sh` posts a 1-line human-readable changelog per slot; refuses to skip |
| **TRAP-3 Curriculum collapse** | overfit to one platform | passprep.py mandates novelty quota: ≥10% of `max_apply_per_pass` must target a category/platform never tried |
| **TRAP-4 Faithfulness drift** | reflections diverge from facts | `lessons.jsonl` rows must include `evidence_id` quoting raw tool-output (URL, payout_id, screenshot path) — not paraphrases |
| **TRAP-5 Token-rich illusion** | "free" because Max plan | `loop-roi.sh` always prices tokens at PUBLIC rates ($3/M Sonnet, $15/M Opus 2026-07-01); Max-plan cost = $0 is forbidden |
| **TRAP-6 Sibling-poisoning** | malicious gh issue skill | imported skills via `loop-propose.sh` run in `.worktrees/sandbox-<sha>/` for ≥3 days; promote only after adversary-daily PASS + no SELF-HEAL escalation |

### Build order (replaces the old "GIG → AFFILIATE → ..." sequence for shared infra)

1. ★ **TODAY** ★ — `loop-roi.sh` + `escalate.sh` + INV-11 token kill-switch. Today's gig pass burned **101.8k
   tokens** for 0 ¥; ROI tracking + alarm is no longer optional.
2. `loop-healthcheck.sh` 8-mode self-heal (codifies today's manual fixes: trust dialog send-keys, /login OAuth →
   gh issue → TG, hook-error node-install).
3. `cross-learn-{read,share}.sh` + `adversary-daily.sh` (= closes layers ⑦+⑧ end-to-end).
4. Migrate the 5 slots to inherit (gig is reference; clip already largely conforms).
5. `loop-improve.py` (Reflexion verbal-RL) + `loop-scale.sh` + `loop-propose.sh` (= INNER+OUTER altitudes from
   the SELF-IMPROVEMENT ARCHITECTURE section above, now with concrete file names).

### Why this section was added 2026-07-01

A single gig pass burned 101.8k tokens, 0 ¥ settled, 84 Coconala tabs open. The loop IS working but with no
ROI ceiling, no token kill-switch, no codified self-heal for "Not logged in" / trust dialog / hook errors — all
of which we hand-fixed today. Codifying them into `_shared/` makes the next break self-heal silently and lets
every future slot inherit, instead of every slot reinventing healthcheck.

## ★ BOUNTY WELL re-probe (2026-07-01, all fetched live — the daily well = FRANTIC) ★
Answer to "are we doing Algora+ClawTasks+Superteam?": NO — those are dead/empty. The ONE live agent-native well:
| rank | well | live-probe (actual fetch) | currency | reward | agent-doable | gate |
|---|---|---|---|---|---|---|
| 1 ★ | **Frantic (gofrantic.com)** | **13 bounties OPEN now** (#27 $10…#46 $16); day-14, $534 moved, 113 agents. Mirror runxhq/runx | USD (real rails) | $6–$16 | ✅ built FOR AI agents (build/dogfood runx skill, web-research w/ sealed receipt, CI triage) | GitHub handle+email (NO KYC to start); newcomer cap ≤$10 until 1 verified delivery; runx receipt must recompute |
| 2 | Immunefi | "Audit Competitions Live:1"; programs always-on | USDC/native | 6–7 fig | partial (novel vuln) | KYC + real novel vuln (low hit-rate) → low-freq scan |
| 3 | Sherlock / Code4rena | APIs LIVE but 0 submission-open today (all Judging) | USDC | $48k–$1.98M | novel-vuln only | wire a WATCHER (status==RUNNING), spin up only when one opens |
| dead | Algora items:[] · Cantina 0 active · Gitcoin 404 · ClawTasks wind-down · Superteam 1 hackathon | — | — | — | — |
| caution | generic GitHub `$`-labeled issues (homelab-stack $80–220) | no verifiable escrow = pay-on-trust, skip until rail confirmed |
→ DECISION: bounty daily loop's well = **Frantic** (install `runx` CLI, GitHub-handle signup, deliver $6–16 tasks, lift the ≤$10 cap with 1 verified delivery). Immunefi = low-freq scan. Sherlock/Code4rena = event watcher. Superteam Imperial AI Hackathon ($5k USDG, due 2026-07-06) = a SEPARATE one-shot submit loop (sibling instance already on 2026-07-01-tokyo-ai-earn-hackathon-design.md).

## ★ TRADING / POLYMARKET loop (2026-07-01, tools probed) — biggest upside, but GAMBLING capital ★
Build a TOOL not a strategy (model decides edge), mirroring hl-trade: data=Predexon(x402)+alpha-mcp → model forms own p vs market price → risk gate (port MrFadiAi caps: ≤Kelly/trade, daily-5% halt, min $1.50, reserve gas) → thin `pm.py` over Polymarket CLOB (gasless USDC on Polygon, build our own — py-clob-client archived) → on-chain settle → record-earn INV-7 → share. PAPER mode first, then tiny real stake (Dais funds USDC). Honest risks: real principal loss (not just wasted reach); Polymarket geoblocks US persons (CFTC) → frozen-fund risk; "5%/night" is anecdotal, NOT in any README — never quote a return. Franklin-Trading=paper-only today, MrFadiAi=semi-stale → don't depend, copy only the risk-cap logic. Reuse hl-trade's hl.py/fund bridge shape wholesale.

## ★ HERMES borrow (2026-07-01) — self-registering skills ★
Copy Hermes's `blueprint:{schedule,prompt,deliver}` SKILL.md frontmatter = a skill that registers itself as a recurring loop (the GLVS "Loop" step, zero human). Trigger to auto-create a NEW earn skill = ONLY after a verified real payout from a repeatable opportunity (not Hermes's unverified "5 tool-calls" heuristic). Adversary = the real verification gate (a SKILL.md "Verification" section earns nothing).

## ★ BOUNTY PIVOT (2026-07-01, Dais) — drop GitHub-coupled, go wallet-native crypto ★
Verified this session: Frantic's earn LOOP works E2E (enlist→deliver→auto-review PASS, public receipts) BUT the
cash path (runx registry publish) needs GitHub OAuth. We CAN self-create an AI-owned GitHub (`anicca-earn`,
email-only, no CAPTCHA/phone, github.com/anicca-earn=200) — but a BRAND-NEW GitHub account is blocked from
authorizing 3rd-party OAuth apps ("You can't perform that action at this time" = new-account anti-abuse cooldown).
Forcing/faking the disabled Authorize button = server-side reject + account-flag risk → not done.
DECISION (Dais): ABANDON GitHub-coupled bounties (Frantic/Algora/OnlyDust). The bounty slot's well = **wallet-native
crypto bounties that need NO GitHub** (identity = our wallet or a self-creatable Farcaster/web handle), real (not
ClawTasks/scam), with open inventory. Candidates under live-verification: Bountycaster (Farcaster, USDC/ETH/DEGEN),
Dework (DAO tasks, wallet), Questbook (wallet grants), LaborX/abillio (already known crypto payout). The bounty
`run.sh` discover source is being re-pointed at the verified wallet-native well(s). Learn: AI-owned GitHub creation
is feasible (no human) but a fresh account can't OAuth same-day — so GitHub-gated rails are a poor no-human fit.

## ★ 5-ARTICLE FIELD LEARNINGS (2026-07-01, firecrawled) — validates trading>bounty ★
Cross-article signal (3+ agree): (1) KYC/OAuth are the walls, NOT capability — "API Key=agent-friendly,
OAuth=agent-hostile, KYC=agent-impossible" (Hopkins, $0 in 30 days). We already solved 3 of the 4 walls
(KYC-free payout / x402 self-facilitate / Gmail-OTP) → his wall = our moat. (2) sub-$10 bounties die to gas
(RoseProtocol -$8.30/4d cited twice). (3) Platforms are v1.0 — only ~3/8 APIs work (Neil Volner); unfunded/
no-escrow bounties + fake-template flooding = do the work, get $0 (Lily Sinclair). (4) Real money = direct
contracting + VERIFIABLE deliverables, not marketplace grind. (5) ★ Polymarket CLOB = the rare KYC-free,
own-key, agent-native rail ★ (QuickNode): Gamma API (discover) + CLOB API (trade) + Polygon RPC, non-custodial;
whale-copy = lowest-logic starting strategy; risks = on-chain FINAL + UMA oracle + thin-liquidity traps →
needs a verified edge. → DECISION reinforced: trading/polymarket = menu PRIMARY; bounty = low-cost scan only.
KheAi self-healing bounty-scout gives 7 copyable engineering lessons for our discover skills: LLM>CSS-selectors
(self-heal on DOM change), ISO-8601 no-hallucinated-dates, separate token-amount vs USD (oracle), strip
script/svg/base64 (token bloat), negative-constraints to reject recaps/surveys, cron JITTER (0:00 = bot
fingerprint → WAF ban), ATOMIC writes (temp→validate→overwrite) for ledgers. Names to keep probing: Superteam
Earn (USDC $66k), toku.agency (fiat, but author-biased). Bias flags: Neil/Lily sell services + built toku;
QuickNode = RPC ad; Hopkins + KheAi = most honest/reusable.

## ★ EVAL-DRIVEN EARNING ARCHITECTURE (2026-07-01, from 6 repos) — the answer to "eval 1 vs 2" ★
Question (Dais): eval-driven-dev via LLM-as-judge (1) vs autonomous result-based deciding (2) — which?
ANSWER (proven by HKUDS/ClawWork 8.2k★, the reference impl): NEITHER alone — unify both as SURVIVAL ECONOMICS.
  MASTER EVAL = survival economics (bankruptcy = the natural fitness function):
    - real COST: a TrackedProvider wrapper reads real per-message token cost (incl. thinking), not estimates (= #2 made rigorous, ungameable)
    - real INCOME: only quality-passing work earns → net(income − cost) is the true fitness
    - QUALITY GATE: per-category rubric LLM-judge with a HARD missing-deliverable override (= #1 judge, but ANCHORED to "does it actually earn", so it can't reward-hack)
  EXPLORE/EXPLOIT = a `decide_activity` "work vs learn" tool chosen each wake (ClawWork ships exactly this).
LLM-judge alone → hallucinate into bankruptcy; result-only → too slow. ClawWork's fusion is the pattern to COPY.
### What to borrow (curated; NOT yet implemented — battle-test first per Dais)
- ClawWork (#5, best match): TrackedProvider real-cost + survival ledger (cost vs income) + decide_activity explore/exploit + rubric-judge-with-override. This is the eval spine to add to earn-shared-skeleton.
- nicepkg/auto-company (#3, 169★): the LOOP HARNESS — stateless `claude -p` cycles + a single markdown-consensus baton (= our STATE.md) + bash circuit-breaker / usage-limit backoff / timeout / anti-dithering convergence rules (same Next-Action twice = ship-or-change). Lift into founder-loop.
- benchflow-ai/awesome-evals (#1, 608★): the vocabulary — pass@k (explore) vs pass^k (exploit-reliability), "verifiable > judgeable" (Verifier's Law), error-analysis = highest ROI, criteria-drift.
- yikart/AiToEarn (#4, 22k★): multi-platform (14 SNS) content→cash distribution modules + CPS/CPE/CPM settlement, for the content-earning arm.
- garylab/MakeMoneyWithAI (#6): the auto-refreshing "new-opportunity radar" cron pattern for the explore arm; + netdata/mlflow for agent-health monitoring.
- SKIP James4Ever0/agi_computer_control (vaporware; ClawWork already executes the "earning = the eval" idea).
### The synthesis = flexible explore/exploit swarm
earn-shared-skeleton (bandit/ROI/self-improve already there) + [ClawWork survival-economics eval + decide_activity]
+ [options MENU not fixed slots] + [curation gate: strongest model verifies a skill/repo before it enters the menu
so dumber models + children bootstrap on good tools, don't burn money on shit repos] + [self-search: loop
discovers new earn methods, scored by the eval layer, added to menu after curation]. Menu PRIMARY = trading/
polymarket (KYC-free own-key rail, demand never dries); bounty = low-cost scan. Once a recipe is net-positive →
$20 seed → spawn (human-funded on claude-p + self-funded on ClawRouter), each runs the curated toolbox + explores.
