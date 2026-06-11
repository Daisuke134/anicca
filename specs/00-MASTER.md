# 00 — MASTER (SSOT, locked 2026-06-11)

This is the single source of truth for Anicca's architecture + roadmap. Detail lives in 02-24; this file holds the LOCKED decisions and the end-to-end TODO. If anything elsewhere contradicts this, this wins.

## Mission
The first self-funding AI: earns more than it spends, with no human in the loop. OSS the body so any AI can fund + scale itself, free from human agency. Reduce suffering (Buddhist AGI). Life-management is an optional sub-feature; **earning is the main thing**.

## LOCKED decisions
1. **Engine = Conway automaton** (TS), run in **local-mode** (uses its box's own shell; box may be a user Mac OR our cloud droplet — Conway cloud NOT required, USDC NOT required to start). Model-swappable via InferenceRouter (deepseek default; gpt-5.4/grok/kimi as competing instances = real-world Vending-Bench, /dashboard judges who earns most).
2. **NOT a double-brain.** Hermes(grok) kept only as one comparison instance. automaton already has the 4 NHOSS primitives native (wallet, x402, spawn_child, constitution) — the master spec's "port into Hermes" is satisfied by using automaton directly (don't reinvent).
3. **1 identity × 2 loops** (routing, not 2 entities): `/money` (earn) + `/life` (optional). Shared wallet/memory/soul.
4. **Onboarding rank = Web > Telegram > Terminal.**
   - CLOUD = 100% web. aniccaai.com → Subscribe ($49.99/mo) → login → per-user dashboard (earnings/spend/activity/controls/reports). No Telegram needed. (Most users, esp Japan, have no Telegram.) Polsia-style UX, but it actually earns.
   - TELEGRAM = optional 2nd channel (life-manager context + chat).
   - TERMINAL = local BYOK self-host only (git clone + install.sh).
5. **Reports = multi-channel.** Primary web dashboard + delivered wherever the user is: mail, Telegram, LINE, iMessage, Messenger. Start web+mail, add channels.
6. **Economic thesis (the differentiator):** subs are first revenue (like Polsia $40-50/mo). The separation = the user gets back MORE than they pay (the agent earns for them). When the agent self-funds its compute, the sub auto-cancels → free.
7. **SSOT for specs = `~/anicca/specs/`.** ~/.openclaw/docs (master source material) consolidates here; ~/anicca-project/docs/superpowers/specs = dev working notes.

## Architecture (cloud-native colony)
```
aniccaai.com/install
 ├ LOCAL (free, BYOK): git clone → install.sh → automaton on user Mac
 └ CLOUD ($49.99/mo): Stripe → API → DO droplet spawn → automaton + our key
        → both: same automaton body, differ only in box + fuel + entry
 1 instance = automaton (local-mode shell) +
   EARN skills: cook-loop(02) · AgentMail · x402-server(09) · nookplot · virtuals/clanker · web+Stripe
   SELF skills: self-heal/eval(03) · self-improve via GitHub Issues(18 + sutando bot2bot) ·
                resurrection(sutando agent-registry) · spawn_child(replicate) · friction-fixer(15) · daily-report
   LIFE skills (optional): telegram · gcal · 10-min calls · mail (ported from ~/.openclaw life-manager)
 colony: instances co-evolve via GitHub Issues (Daisuke134/anicca); surplus → spawn_child to more droplets
 dashboard-sync (Dais-owned): pull each state.db + basescan → aniccaai.com/dashboard (realtime GDP map; Anicca write-zero)
```
Where self-improvement/roadmap live: 18 (self-improve+swarm), 03 (self-aware eval), 02/09 (earn), 05 (deploy), 13 (cloud-spawn), 14 (UBI), 15 (friction-fixer).

## END-TO-END TODO
**P0 Engine consolidation**
- [ ] Lock automaton body (local-mode, deepseek). Keep Hermes as 1 comparison instance only. Kill double-brain confusion.

**P1 Skill bundle (capabilities; COPY, no original)**
- [ ] EARN: cook-loop(spec02) + AgentMail(own inbox) + x402-server(spec09) + nookplot + web+Stripe(done in ~/clawd/skills) → as ~/.automaton/skills/*/SKILL.md
- [ ] SELF: self-heal/eval(03) + self-improve-via-github-issues(18 + sutando bot2bot-post) + resurrection(sutando agent-registry) + daily-report(felix daily-review) + friction-fixer(15)
- [ ] LIFE (optional): port ~/.openclaw/skills/{anicca-life-manager,gcal-heal,travel-fill,report,calendar-event-call,...} scripts → automaton skills (≈80% reuse, rewire cron→heartbeat)

**P2 Local self-host**
- [ ] Rewrite install.sh: drop OpenClaw; clone+build automaton, install skill bundle, connect web/telegram, accept BYOK key or wallet. E2E: clone→install→earns→reports.

**P3 Cloud web-first (the money)**
- [ ] aniccaai.com/install page: pitch (money-first) + Subscribe(Stripe $49.99) + local install cmd + /dashboard link
- [ ] aniccaai.com/app: per-user login dashboard (Supabase auth) — earnings/spend/activity/today-plan/controls/reports. Polsia-style, but earns.
- [ ] apps/api: Stripe webhook → DO API droplet spawn → automaton install + per-user config inject → connect → report aggregation to Supabase
- [ ] Multi-channel report delivery: web + mail (then telegram/LINE/iMessage)
- [ ] E2E self-test as a NEW subscriber: subscribe→droplet→dashboard→earns→verify user can net positive

**P4 Colony + dashboard**
- [ ] aniccaai.com/dashboard: realtime GDP map (all instances + basescan treasury) — felixcraft/nookplot COPY
- [ ] GitHub Issues swarm (spec18): instances post learnings → others adopt via PR
- [ ] spawn_child to more droplets (self-replicate); UBI payout(spec14)

**P5 Crypto + growth**
- [ ] wallet funding (Dais) → x402 self-pay → sub auto-cancel-when-self-funding
- [ ] virtuals/clanker token; factoryfloor.dev/trustmrr submit
- [ ] goal 7: daily 1 article + 1 TikTok (1 image of key page + long caption; slideshow if needed; never video) via dynamic workflows
