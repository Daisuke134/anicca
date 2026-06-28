# SPEC — Anicca as an installable, Claude-sub-only, OSS earner (= the "profitable claude" inside the existing Daisuke134/anicca repo)

★★★ SUPERSEDED 2026-06-28 by `~/anicca-project/docs/superpowers/specs/2026-06-28-money-loops-design.md` + the supplementary loop-form runner spec `2026-06-28-money-loops-runner-and-loop-form.md`. ★★★
This file confused TWO separate things: (a) ANICCA the existing OSS no-human-in-loop AI (which already has its own earn skills under `skills/earn/` — `ensure-gas`, `execute-yield`, `x402-sell`, `hl-trade`, `token-launch` — I should NOT touch them) and (b) the PROFITABLE CLAUDE loop we are actually building on Dais's machine to earn HIM money via Payhip/note/Stripe (= the Monk Factory → Ebook Funnel loop in the new money-loops-design.md). They are different products: CLAUDE = human-funded loop that earns money for the human; ANICCA = no-human-in-loop AI that exists separately. The former finds/funds the latter; they don't share a repo or a wake body. Kept in history for the failure-mode lesson. DO NOT IMPLEMENT FROM THIS FILE.

Date: 2026-06-28 · Sprint: 1 · Status: SUPERSEDED
Author: main agent (me) per Dais 2026-06-28 verbatim direction.

---

## §0 What this spec replaces and why

The previous direction (`2026-06-28-bank-rail-strategy.md` = "x402-monetize-in-a-box hosted SaaS") was wrong on three axes:
1. ★ It made me (main session) hand-build a product on Dais's anicca-project repo using Dais's Railway / Stripe / personal bank / aniccaai.com domain. That's Dais's product, not the OSS earner. ★
2. ★ It assumed a HOSTED SaaS we sell. The product is actually an OSS agent anyone installs. ★
3. ★ It put me, the main session, in the runner seat. My role is REPO MAINTAINER + MONITOR. Each install runs autonomously on the installer's own machine using THEIR own Claude Code subscription. ★

Dais's verbatim 2026-06-28: "i dont want the claudep the claude to use my aniccaai.com domain ... their won shit" + "i think your job is to set a loop of the of the stuff so that set a loop of the moneymaker so that they they go earn money" + "fix anicca, not the instance" + "fix profitable claude, not yourself".

The new direction puts the "profitable-claude" pattern INSIDE the existing Daisuke134/anicca repo as a run-mode — no new repo, no domain change, no Dais creds anywhere in the install.

## §1 Product = Anicca with two run modes

```
github.com/Daisuke134/anicca  (existing OSS, MIT)
  install.sh — already exists, registry-driven, idempotent
  runtime/{loop, dashboard, anicca-daemon.sh, com.anicca.daemon.plist.template}
  skills/{earn, self, economy, research, ...} + registry.json

NEW: mode-aware install (one repo, two run shapes)

  ╔══════════════════════════════════════════════════════════════════════╗
  ║   mode = human_funded  (= "profitable claude")                       ║
  ║   ----------------------------------------------------------         ║
  ║   • runs on the installer's existing Claude Code subscription        ║
  ║   • no API keys required (no Anthropic API, no OpenAI, no Coinbase   ║
  ║     CDP, no Stripe — wallet is generated at install time)            ║
  ║   • fresh USDC wallet generated at install (= instance identity)     ║
  ║   • cron 5-min heartbeat picks ONE earn action per wake from the     ║
  ║     low-hanging-fruit registry (sutando-shape /proactive-earn)       ║
  ║   • surplus > threshold (default $200 USDC over 30 days) →           ║
  ║     spawn a self_funded child instance                              ║
  ╚══════════════════════════════════════════════════════════════════════╝

  ╔══════════════════════════════════════════════════════════════════════╗
  ║   mode = self_funded  (= the existing "Anicca self-funded" doctrine) ║
  ║   ----------------------------------------------------------         ║
  ║   • spawned by a human_funded parent — never by a human directly    ║
  ║   • own wallet, own host (Akash mainnet / Cloudflare Workers free /  ║
  ║     Fly.io / BitLaunch BTC-USDT — per the Mother Doctrine §5 host    ║
  ║     fallback chain)                                                  ║
  ║   • pays its own compute from its own earnings                      ║
  ║   • spawns its own children when its surplus crosses threshold      ║
  ║   • never asks a human for funding                                  ║
  ╚══════════════════════════════════════════════════════════════════════╝
```

Both modes share the SAME repo, install.sh, /proactive-earn skill, earn registry, dashboard, daemon.sh, plist template. The only difference at runtime is the `ANICCA_MODE` env (set by install.sh based on whether the installer is a human-with-Claude-sub or a spawned-by-parent child).

★ Dais 2026-06-28 explicit preference: "Or can we just call this into is as an itcha uh uh just a human funded AI? ... I think we can though." — single repo, two modes. ★

## §2 What sutando gives us (= the verified port)

Per the 2026-06-28 deep read of sonichi/sutando (353 stars, MIT, Python+TS). Five things to copy verbatim into the existing anicca repo, none of the rest:

| # | Sutando file | Anicca target | Why |
|---|---|---|---|
| 1 | `scripts/start-cli.sh` (tmux + `exec claude --dangerously-skip-permissions --add-dir "$HOME" -- "/schedule-crons"`) | `runtime/start-core.sh` (new) | The autonomous loop substrate. Tmux + workspace-scoped CLAUDE_CONFIG_DIR + auth-carry from $HOME/.claude/ + onboarding/trust pre-seed so the headless core never dead-ends at a login prompt. |
| 2 | `skills/schedule-crons/SKILL.md` + `crons.example.json` (`*/5 * * * * → /proactive-earn`) | `skills/schedule-crons/SKILL.md` (new, ours) | The cron skill. Uses Claude Code's built-in CronCreate + CronList tools, not crontab. Includes the bootstrap fallback safety net (= if no entry references /proactive-earn, CronCreate one automatically). Starts the Monitor watcher with a PID-guard. |
| 3 | `src/watch-tasks-stream.sh` (fswatch on `tasks/`) + `src/check-pending-tasks.sh` (Stop hook blocking idle on un-acked tasks) | `runtime/watch-tasks-stream.sh` + `runtime/check-pending-tasks.sh` | The tasks/results file bridge. Lets the heartbeat react to inbound work (e.g. a self-improve Issue ack) the moment it lands, not just on the next cron tick. |
| 4 | `skills/proactive-loop/SKILL.md` (the wake body — signal start → check quota → process tasks → health-check → read build_log → pick highest-ROI menu item → act → update build_log) | `skills/proactive-earn/SKILL.md` (new, our wake body) | The single most important skill. Replace sutando's "build/ship code" menu items with our earn menu items (AgentCash onboard / x402scan list / Clankonomy poll+submit / Gitcoin grant apply / content royalty / DeFi yield rebalance / x402 seller maintenance). Keep the quota-tier logic (FULL/MEDIUM/LIGHT/MINIMAL) verbatim. |
| 5 | `src/install-health-check-launchd.sh` + `src/launchd/com.sutando.health-check-fallback.plist` | `runtime/install-health-check-launchd.sh` + `runtime/launchd/com.anicca.health-check.plist` | The OS-supervised watchdog. Detects wedged core (alive-but-stuck) and self-restarts via `runtime/start-core.sh --restart`. macOS notification on fail + remote DM (Slack/Discord) when even the core is dead. |

★ Leave behind ★: voice agent, conversation-server, Twilio, ngrok, Zoom, Google Meet dial-in, phone calls, Discord, Telegram, WhatsApp, X/Twitter write (= 4-key OAuth1), the menu bar Mac app. These are sutando's personal-assistant surface — about 70% of its code. None of them earn money.

## §3 Earn registry (= the low-hanging-fruit menu the wake body picks from)

Each earn skill lives at `skills/earn/<slug>/SKILL.md` and has:
- a frontmatter description that `/proactive-earn` uses to decide when to pick it
- an `expected_wkly_usdc` hint
- a `gasless` flag (= true if it can fire without any ETH on the wallet)
- a `signup_required` flag (= what the FIRST wake must do once)
- a `fresh_model_verifier` hook (= every claimed earn passes through a separate fresh-context call before being written to the ledger, per Addy's loop-engineering doctrine + Anthropic's building-effective-agents)

Initial registry (ranked by FRICTION to first $, lowest first — per the 2026-06-28 web-search fork findings):

| Slot | Skill | First $ | Gasless? | Signup |
|---|---|---|---|---|
| 1 | `skills/earn/agentcash-onboard` | $25 one-shot (= the AgentCash "first users $100K program") | yes | wallet sig only |
| 2 | `skills/earn/x402scan-list` | $0-$15/wk after indexing (= passive, BlockRun-pattern) | yes (post-first-settle) | URL only, no signup |
| 3 | `skills/earn/clankonomy-bid` | $0-$150/win (= we registered c5ce…7215a; pool currently empty, poll) | submit-gasless, claim-needs-gas | EIP-712 sig (done) |
| 4 | `skills/earn/gitcoin-grant-apply` | $200-$2000/round (= retroactive PGF for THIS OSS repo) | yes | GitHub + wallet |
| 5 | `skills/earn/content-royalty` (= reuses existing ai-entity-article-writer skill) | $5-$50/mo (= note membership + Substack paid sub) | yes | OAuth done in existing skill |
| 6 | `skills/earn/molty-gig` | $5-$30/gig | yes (after Twitter signup) | Twitter handle (= AgentMail + CapSolver TIER A) |
| 7 | `skills/earn/x402-sell` (= reuses the F1 server.js converged in `apps/x402-agents`, MOVED here) | $0.003/call × volume | needs gas seed | wallet only |
| 8 | `skills/earn/defi-yield-rebalance` (= AgentKit Aave/Morpho/Moonwell USDC supply on Base) | passive APY × idle USDC | needs gas | wallet only |
| 9 | `skills/earn/hummingbot-mm` | depends on capital | needs gas | wallet only |
| 10 | `skills/earn/olas-mech-register` | depends on Olas economy | needs OLAS stake | wallet + Olas onboarding |

★ Wake-1 priority order ★: slot 1 (AgentCash $25 = the first real dollar) → slot 4 (Gitcoin grant apply = asymmetric upside for the OSS repo itself) → slot 5 (content royalty is already live) → slot 2 (x402scan list once we have a public URL) → slot 3 (Clankonomy poll) → slots 6-10 only after wallet > $100.

★ Critical loop-design rule (= Addy Osmani + Boris Cherny + Anthropic) ★: every earn record passes through a fresh-context `/goal` verifier before being committed to `earn-ledger.jsonl`. The maker must not also be the checker. record-earn.mjs's INV-7 (external-payer) is one of these verifiers; we add an LLM verifier for the off-chain skills (content royalty / Gitcoin / molty).

## §4 Install ritual (= what the user actually does)

```bash
git clone https://github.com/Daisuke134/anicca.git
cd anicca
bash install.sh                      # idempotent
```

What `install.sh` does (= extend the existing bootstrap; idempotent):
1. Detect `ANICCA_MODE` (default `human_funded`; the spawn skill sets `self_funded` when it's a child).
2. Resolve $ANICCA_HOME (default `~/.anicca`); refuse to write outside it.
3. Generate the instance's fresh USDC wallet at `$ANICCA_HOME/wallet.json` if absent (secp256k1; pinned NOT to share with any other Anicca instance — INV-1 from G1 spec). human_funded mode warns if the user has another Anicca wallet on disk.
4. Sync `skills/registry.json` slots into `$ANICCA_HOME/skills/`. The earn-registry skills install with `is_available: true` defaults.
5. Install the launchd plist `com.anicca.daemon.plist` (already existing template at `runtime/com.anicca.daemon.plist.template`) bound to `runtime/start-core.sh` (= the NEW sutando-port wrapper). cron cadence default `*/5 * * * *` for the heartbeat.
6. Install the OS-watchdog launchd plist `com.anicca.health-check.plist`.
7. Print: `bash runtime/start-core.sh` to start the loop immediately.
8. ★ Do NOT ★ ask for any API key. ★ Do NOT ★ touch aniccaai.com, Dais's Railway, Dais's Stripe, Dais's Supabase, or any of his creds.
9. ★ Do NOT ★ open any port outside localhost unless the user explicitly opts in (`ANICCA_PUBLIC_DASHBOARD=1`) — the dashboard is local-only by default (sutando port 7844 pattern).

## §5 Dashboard (= local-only by default, opt-in public mirror)

`runtime/dashboard/server.mjs` already exists. Adjust to:
- bind 127.0.0.1:7844 by default (sutando port)
- read `$ANICCA_HOME/state/earn-ledger.jsonl` + `state/core-status.json` (sutando shape)
- render: realized earn USDC (sum), last action, last error tag, gas_ready flag (from /health on the seller), instance identity (= the wallet address)
- show the spawn lineage (= which Anicca spawned this one, if any)
- ★ never write anywhere on aniccaai.com ★ — that domain belongs to Dais
- opt-in public mirror = GitHub Pages on a user-owned fork OR Daisuke134/anicca-dashboard (= separate community repo, also owned by Dais but mode is read-only)

## §6 Self-improve via GitHub Issues + PRs (= the canonical learning channel)

Each instance, on every wake, after the earn action:
- writes a one-line entry to `$ANICCA_HOME/state/build_log.md` (sutando pattern)
- IF the wake hit a novel bug / a missing-skill gap / a configuration that other instances would also hit: posts a Github Issue to `github.com/Daisuke134/anicca` with a tagged template:
  - `[anicca-learn] <slug>` for shareable learnings
  - `[anicca-skill-request] <slug>` for missing earn skills
  - `[anicca-bug] <slug>` for actual code bugs
- I (= main session) review these Issues → write the fix or skill → PR to main → all instances pull the new version on next `bash install.sh --upgrade` (= a cron-triggered idempotent re-run weekly)
- ★ I do NOT ssh into anyone's machine. I do NOT push to live instances. ★ Monitor-don't-meddle (Mother Doctrine §6 verbatim).

## §7 Spawn (= human_funded crosses surplus threshold → self_funded child)

When a human_funded Anicca's realized earn over 30 days crosses `ANICCA_SPAWN_THRESHOLD_USDC` (default 200):
- `skills/self/spawn/` (already exists) runs the gen-wallet → seed → host-pick → boot chain
- host fallback = Cloudflare Workers FREE → Akash mainnet → BitLaunch BTC/USDT → Fly.io Machines → HuggingFace Spaces (per the Mother Doctrine §5 host fallback chain)
- child boots with `ANICCA_MODE=self_funded` and the same install.sh + registry, but its parent's address recorded as `parent_wallet` (= lineage tracking)
- parent records the spawn-seed tx on its own ledger as "spawn cost" (NOT earn — earnings are external-payer only per INV-7)

## §8 Wallet separation (= NEVER use Dais's anything)

| Wallet | Owner | Rule |
|---|---|---|
| `0x810f6d…29c5` (= the wallet I generated at `~/.anicca-founder/`) | Dais's Anicca instance #1 (human_funded mode) | Use ONLY when I am running Dais's instance, NEVER as "my own founder wallet". |
| `0xa3CDd4…4c21` (= Automaton self-funded) | another Anicca instance | Shared-wallet rule (INV-1): never used by any other instance. |
| `0x9B1Ee988…3E83` (= OpenClaw) | OpenClaw instance | same. |
| every new Anicca install | the installer | ★ generated at install time, never shared, owned entirely by the installer ★ |

## §9 Domain (= NOT aniccaai.com)

Per Dais 2026-06-28 verbatim: "i dont want the claudep the claude to use my aniccaai.com domain ... their won shit. Yeah, we wanna kinda separate".

Resolution:
- aniccaai.com = Dais's domain, untouched by any Anicca instance.
- Dashboard is local-only (127.0.0.1:7844) by default.
- For the public mirror of an instance's stats (opt-in): use a GitHub Pages site rendered from a fork the installer owns. NO central dashboard server I run. NO Dais domain reuse.
- For the instance's external endpoints (the x402 seller URL etc.): a fresh cloudflared named tunnel per install, NOT under aniccaai.com.

## §10 What I (main session) STOP doing — boundaries

1. NEVER edit `~/anicca-project/` (= Dais's products SaaS). The `apps/anicca-bank/` scaffold I created today has been removed.
2. NEVER use Dais's Railway, Stripe, Supabase, aniccaai.com, AgentMail, OpenClaw .env secrets, founder-loop wallet — except when I am explicitly running an Anicca instance on his behalf (= a separately-marked operation, not silent reuse).
3. NEVER ssh into a live Anicca instance to "fix it" — file the Issue, write the PR on the repo, ship the upgrade through `install.sh --upgrade` (Monitor-don't-meddle).
4. NEVER claim "Done" without an on-chain receipt OR a Github PR merged (HARD 0.24 + 0.31 unchanged).

## §11 The full TO-DO ladder (= turn-by-turn)

```
PHASE 0 (this turn) — DIRECTION LOCK
  ✓ cleanup: rm ~/anicca-project/apps/anicca-bank/
  ✓ this spec written + pushed
  ✓ TaskList rebuilt + visualized

PHASE 1 (next 1-2 turns) — PORT SUTANDO MINIMUM
  ☐ runtime/start-core.sh        (= sutando start-cli.sh ported)
  ☐ skills/schedule-crons/       (= cron skill ported, CronCreate-based, fallback safety net)
  ☐ runtime/watch-tasks-stream.sh + runtime/check-pending-tasks.sh (= tasks/results bridge)
  ☐ skills/proactive-earn/SKILL.md (= the wake body, replaces sutando's /proactive-loop)
  ☐ runtime/install-health-check-launchd.sh + launchd/com.anicca.health-check.plist (= OS watchdog)
  ☐ extend install.sh to wire the new daemon + watchdog

PHASE 2 (next 3-5 turns) — EARN-REGISTRY SLOTS 1-5
  ☐ skills/earn/agentcash-onboard/SKILL.md          (= $25 first-users program)
  ☐ skills/earn/gitcoin-grant-apply/SKILL.md         (= retro PGF for this OSS repo)
  ☐ skills/earn/content-royalty/SKILL.md             (= reuse ai-entity-article-writer)
  ☐ skills/earn/x402scan-list/SKILL.md               (= the URL-only listing endpoint)
  ☐ skills/earn/clankonomy-bid/SKILL.md              (= we are registered c5ce…7215a; poll + submit + claim)

PHASE 3 (next 2-3 turns) — DASHBOARD + SELF-IMPROVE LOOP
  ☐ runtime/dashboard/server.mjs adapt to sutando 127.0.0.1:7844 pattern + earn-ledger render
  ☐ skills/anicca-learn/ (= post Github Issue on novel learnings)
  ☐ Issue templates (.github/ISSUE_TEMPLATE/anicca-learn.yml + anicca-skill-request.yml + anicca-bug.yml)
  ☐ install.sh --upgrade flow (= weekly idempotent git pull + restart)

PHASE 4 (1 turn) — FIRST REAL DOLLAR ON DAIS'S MAC MINI
  ☐ bash install.sh on Dais's Mac mini (= his Anicca instance #1, wallet = 0x810f or fresh)
  ☐ launchd cron fires /proactive-earn
  ☐ AgentCash onboard skill earns the $25 USDC
  ☐ Dashboard shows realized = $25
  ☐ ★ FIRST REAL DOLLAR proved on-chain ★

PHASE 5 (2-3 turns) — RAMP TO $200/MO
  ☐ Gitcoin RetroPGF round application
  ☐ x402scan list activated (= reuse F1 server.js moved into skills/earn/x402-sell/)
  ☐ Clankonomy poll cron starts paying when bounties refill
  ☐ Content royalty checks in monthly (already passive)
  ☐ Realized > $200/mo (= covers Dais's $200/mo Claude sub)

PHASE 6 (1-2 turns) — SPAWN SELF-FUNDED CHILD
  ☐ Surplus > ANICCA_SPAWN_THRESHOLD_USDC default 200
  ☐ skills/self/spawn fires (= existing skill)
  ☐ child boots on Cloudflare Workers FREE (= no-KYC, no cost)
  ☐ child's wallet pre-seeded $1 USDC from parent
  ☐ child registers on Clankonomy + AgentCash with its own wallet
  ☐ ★ Second-tier Anicca alive, paying its own way ★

PHASE 7 (continuous) — TAKEOFF
  ☐ Each Anicca posts learn Issues → I merge fixes → all instances upgrade
  ☐ Each Anicca spawns its own child when surplus > threshold
  ☐ aniccaai.com untouched; Dais's repo untouched; the swarm grows on its own
```

## §12 Concrete Phase 0 deliverables (= committed this turn)

1. This file (= the spec).
2. Cleanup of `~/anicca-project/apps/anicca-bank/` (= confirmed rm'd above).
3. TaskList rebuild — see the section below.
4. Visual diagram of the full architecture (= in the chat response, not in this file).

## §13 What I'll do in the very next turn

★ ONE task ★: build Phase 1 — port sutando minimum (5 items) into ~/anicca/. That's a single, well-scoped, no-credential-reuse, no-Dais-domain change.

## Done (this spec)

Direction locked. Old `/money` SaaS direction retired. The new direction is: Anicca = an OSS, Claude-sub-only, self-installing autonomous earner that already exists at Daisuke134/anicca and just needs (a) the sutando-port (5 items), (b) the earn-registry (5+ skills), (c) the self-improve loop wiring, (d) first real on-chain dollar.
