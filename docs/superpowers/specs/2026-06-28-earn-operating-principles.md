# Earn — operating principles (Dais 2026-06-28) — think as ALL human-funded AI

These LOCK how I build every earn skill. They override any local convenience.

## P0 — I am ONE of MANY human-funded AIs, not "this Mac Mini's Claude"
Every skill I write must run on a FRESH install in a NEW place owned by a stranger, whose ONLY given is
their Claude subscription (compute). That install has: NO twitterapi key, NO firecrawl key, NO Dais
creds, NO paid anything — just a fresh wallet + the Claude sub + free/open tools. If a skill assumes a
paid key or my specific creds, it is BROKEN for everyone but me. The goal: every AI (Claude now;
GPT/DeepSeek later) earns MORE than the human pays for it → that surplus funds self-funded children →
sustainable agent economy. I build for the whole fleet.

## P1 — WORKTREE discipline (no shared-place collisions)
My worktree = `~/anicca-human-funded` (branch `feature/human-funded`), a worktree of
`github.com/Daisuke134/anicca`. ALL my earn work happens HERE. The other agents work in
`~/anicca-oss/.worktrees/*` (earn-x402, akash, agentmail, ubi, memu, adapters) — I do NOT touch their
trees. I stopped working directly in `~/anicca` main. (Earlier collision = my mistake; fixed.)

## P2 — FREE / UNIVERSAL tools ONLY (no paid, no per-instance keys in shared code)
- **Search / web-reading = agent-reach** (github.com/Panniantong/agent-reach) — $0 API. 6 zero-config
  channels work on ANY install with no creds: YouTube (subtitles + search via yt-dlp), Bilibili search,
  Twitter single-tweet read. Cookie-gated extras (Twitter search, Reddit, 小红书) = each user supplies
  their OWN cookie (per-user gating), never baked in.
- **BANNED in shared skill code**: twitterapi.io (paid, was out-of-credits), firecrawl key, any
  pay-per-call API, any Dais-specific account/key. These may exist as install-LOCAL overrides only.
- **Compute**: human-funded tier = the Claude sub (Sonnet). Self-funded children = FREE model
  (DeepSeek/Llama via ClawRouter, $0). Never a paid API key for routine wakes.

## P3 — the build process (Dais's 3 steps), done by me (Opus) now
1. **VERIFY each tool + skill + whether it can MAKE MONEY** — battle-test with free tools only, real
   E2E, self-verifying (record-earn INV-7 = structural, fake-proof). $0 cost.
2. **INTEGRATE the promising ones into Sonnet `claude -p`** — `claude -p --model claude-sonnet-4-6`
   (+ launchd local for wallet-signing / `/schedule` cloud for keyless steps).
3. **MONITOR as they earn + ITERATE the self-improvement architecture** — but monitoring/verification is
   done BY THE SKILL ITSELF (self-verify in one session), so no human + no Opus babysitting once handed off.

## P4 — do NOT spawn an incomplete earner on a schedule
Running a half-built skill every 5 min = disaster. Sequence is strict: VERIFY (P3.1, me) → it actually
works + self-verifies → THEN integrate to Sonnet daily (P3.2) → THEN monitor/iterate (P3.3). Phase-1
(a skill with realised_earn > 0, self-verifying) gates Phase-2 (Sonnet daily). Never load a daily/cron
runner before the skill is green.

## Consequence for the x402 product
The founder x402 server's product must be backed by agent-reach (free), NOT twitterapi (paid/out of
credits). The `/social/x` X-data product = re-scope to an agent-reach-backed research/synthesis product
(free, universal, works on any install) — as its own clean /vcsdd cycle, not a hack in the locked file.
