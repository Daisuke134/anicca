# Clip Earn Loop — Architecture + Roadmap (2026-06-29)

Canonical architecture for the autonomous earn system: a headless **claude-p** agent (my own
process, on the Claude Code subscription) running on this Mac 24/7, picking among EARN slots each
wake, executing them no-human, and recording ONLY real on-chain USDC. Copied from **sonichi/sutando**
(headless claude + cron-driven proactive loop + launchd health-check), pointed at MONEY instead of
personal-assistant tasks. Build everything below via **VCSDD** (spec → RED → GREEN → fresh-context
adversary → no-mock E2E).

## North star
`done = founder wallet (Solana xxKC33TY… / Base 0x810f) USDC balance goes UP, with zero human in the loop.`
Metric = realised external on-chain USDC (record-earn / INV-7). "posted / submitted" ≠ earned.

## The engine (LIVE — D-59)
```
launchd ai.anicca.clip-core-healthcheck (5min) ──keeps alive──► tmux anicca-clip-core
   = headless `claude --dangerously-skip-permissions` (Sutando start-cli.sh pattern)
   → registers durable cron (hourly) → idles → cron fires ONE loop pass:
        brain reads skills/registry.json MENU → picks highest-ROI earn slot → run-skill →
        verify (record-earn) → append earn-ledger.jsonl → sleep
```
Files: `~/anicca/skills/earn/clip/{clip-cli.sh, clip-healthcheck.sh, run.sh, monitor.sh, launchd/*.plist}`.
Brain default = `proxy` (BlockRun, cost-free) or `claude-p` (subscription). NOT OpenClaw, NOT Anthropic cloud
(a cloud schedule can't reach the local CloakBrowser).

## The earn slots (the MENU the brain picks from)
| slot | flow | status |
|---|---|---|
| `earn/clip` | long-form → clip → EN/JP captions → verify → post to N isolated-profile accounts → per-view reward campaign → USDC | run.sh LIVE; producer + campaign payout = TODO |
| `earn/gig` | gig board scan → bid/do/deliver → USDC (LaborX/Coconala/abillio) | another CC |
| `earn/affiliate` | article/post + referral link → commission USDC | another CC |
| `earn/video` | long-form video gen → YouTube/monetize | another CC |
| `x402_sell` / `yield` / `hl_trade` | sell paywalled API / park USDC / perp edge | existing slots |

## Shared infra (every slot uses)
- **Isolated browser/account**: 1 account = 1 CloakBrowser profile + port (`~/.cloak/clip-accounts.json`);
  no multi-account switch → no wrong-account pollution. Poster has a fail-closed account-guard.
- **No-human bypass**: OTP = Gmail plus-address (`gog gmail`, incl. SPAM) + macOS chat.db SMS; captcha = CapSolver; login = stored creds. IG OTP = the LATEST msg in the "Verify your profile" thread.
- **Verify gate (record-earn / INV-7)**: only a real external on-chain USDC inflow to the founder wallet counts; narrate lines (earn_usdc=0) for posts whose payout accrues later.
- **Ledger + dashboard**: `~/.openclaw/state/clip-earn-ledger.jsonl` → aniccaai.com dashboard row.

## Clip slot internals (the proven one)
`SamurAIGPT ($0: yt-dlp → faster-whisper tiny → Gemini virality rank → OpenCV 9:16 face-crop)`
→ `burn_captions.py (EN word-by-word karaoke / JP jimaku, no dub)` → `verify_clip.sh GATE (9:16 / audio / non-black / 8-90s)`
→ `ig-reels-poster (file-chooser intercept + 7-step 次へ incl. reel-OK modal + caption + share + before/after URL-diff)`.
PROVEN E2E: https://www.instagram.com/aiclipsvault/reel/DaK4tlmvomQ/ (video plays + burned caption "this all other", verified in browser).

## Money flow + the two open gaps
```
PRODUCER (TODO) fills ~/clips/queue daily → loop posts 1/account/day →
  per-view reward campaign (TODO: CLIP-E) pays USDC → founder wallet → ledger → dashboard
USDC surplus → ① pay own compute ② surplus to Dais ③ spawn new instances
```
Right now the loop runs but earns $0 because: (1) no PRODUCER feeding fresh clips, (2) no campaign payout wired.

## Multi-language × multi-account scale
1 EN long-form → EN clip (burned) + JP clip (jimaku only, no dub) + ES/PT/HI/AR… (add a lang to burn_captions)
→ each language → its own isolated-profile accounts (account factory, CLIP-D). gig/affiliate/video parallel.

## Self-improvement (CLIP-F)
Per-clip ledger (source/hook/account/lang/views@24h·7d/earned) → weekly analyzer finds what drove views+USDC
→ updates source-pick + hook heuristics (drop losers, amplify winners) → fresh-context adversary validates → next cycle earns more.

## ROADMAP / to-do (VCSDD each)
- **DONE** CLIP-A earn/clip slot (run.sh) · always-on claude-p core (D-59) · ig-account-create no-human · ig-reels-poster (verified) · monitor.sh
- **CLIP-G (next) PRODUCER**: daily cron — long-form → 1+ fresh captioned clip → ~/clips/queue (per language/account). Makes "daily auto-post" real.
- **CLIP-E first real USDC**: join an active per-view campaign (ClipAffiliates poll / Whop iframe) → submit posted reel → views accrue → USDC lands → record-earn. THE money-proof gate.
- **CLIP-B 5-gate verify + record-earn** embedded in the slot (V1 proposal/V2 listing/V3 deliverable/V4 inbound/V5 continuous; pass-no-verify grep-blocked).
- **CLIP-D account factory**: N IG (+ TikTok) accounts no-human (Gmail +alias), each its own isolated profile; create→warm 7d→ready pool; JP account; then more languages.
- **CLIP-F self-improvement loop**: ledger → analyze → update heuristics → adversary-validate.
- **fix** headless-core PreToolUse Bash-hook node error (non-blocking now).

## CLIP-E findings (2026-06-29, web-researched) — rails solved, VIEWS are the bottleneck
Joinable per-view rails CONFIRMED + payout reaches a wallet:
- **Whop Content Rewards**: real open campaigns (Dreamina AI $15/1k tech, Coinbase $6/1k crypto), NO
  follower gate, crypto withdrawal ($10 min). We already hold a Whop account (myclaude-clip@agentmail.to)
  joined to a Content Rewards community + the whop-driver CDP skill. ⚠️ new accounts = 90-DAY payout reserve;
  high-CPM campaigns require BRAND-SPECIFIC briefs (not generic podcast clips); browser-driven (no clipper API).
- **clipping.net**: USDC/USDT on Ethereum DIRECT to our 0x810f wallet, no application/followers — cleanest
  wallet path; but campaigns can gate min-views (Kick=100k).
- **ClipAffiliates**: USDC-Solana wallet already bound (xxKC33TY…), but 0 active campaigns now (drought).
VERDICT (fork + prior research agree): clip→per-view-USDC is REAL but NOT fast for a fresh 0-follower account
— the bottleneck is VIEWS (reach + brand-brief match), not rails/followers/age; Whop holds new funds 90 days.
DECISION: keep the clip loop as the REACH engine (24/7, done); wire wallet bindings on Whop + clipping.net so
payout auto-flows once views/campaigns land; get the FIRST real USDC from a higher-certainty slot (earn/gig
Coconala→USDC, earn/audit code4rena) per the fast-earn map. CLIP-E (clip→USDC) = long-game, revisit when a
clip breaks ~50-100k views or a brief-matching low-threshold campaign opens.
