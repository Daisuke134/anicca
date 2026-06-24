# ANICCA — CANONICAL EXECUTION ORDER (do them IN THIS ORDER, never lose the order)

This file is the single source of truth for WHAT to do NEXT and in WHAT ORDER. Order matters: you
cannot prove the recipe for takeoff before the tools actually earn; you cannot write the honest article
before the numbers are real. Read this file first every session. Update the ☐/☑ as you go.

The end goal = **TAKEOFF**: AI that earns its own money on a $0 model, pays its own compute, and
self-spawns clones with the same earning setup → population + capital grow exponentially with NO human
funding. We are searching for **the recipe** (which model × which skills × which setup) that takes off.
Cite: lesswrong.com/w/ai-takeoff, ai-2027.com/research/takeoff-forecast.

Truth rules (so I never lie again): every number here must be on-chain-verifiable or from a real tx
hash. "realised revenue" = earn_usdc actually recorded from a closed/settled action, NOT net worth,
NOT unrealised position value. The dashboard is real-time (Supabase ← telemetry-poster ← live chain).

---

## PHASE 1 — make anicca actually USE every earn tool (at least one real run each)
- ☑ 1.1 yield — REAL: Aave $1.20 + Morpho $1.00 + Moonwell $1.00 (on-chain shares verified 2026-06-21)
- ☑ 1.2 hl — REAL: ETH long perp opened, entry $1735, 2x lev (tx verified)
- ☐ 1.3 x402 — make ONE real sale (self-test mainnet x402 payment proves the rail end-to-end) ← NEXT
- ☐ 1.4 token — actually launch a small token (MoltX) → confirm fee inflow path
- ☐ 1.5 0xwork — exercise once against a real task
- ☐ 1.6 FIX: AgentClient shows only 4 venues — add beefy + investment(WETH bluechip) cells so the
       page shows ALL real holdings (data already posted, display is missing them)

## PHASE 2 — make anicca actually EARN (realised revenue > 0) with each tool, on the FREE model
- ☐ 2.1 realise a gain anicca itself decides: close HL up / yield interest booked / x402 sale
- ☐ 2.2 the dashboard's revenue_by_source now shows real per-tool earnings — confirm each tool's $ > 0
- ☐ 2.3 deploy the idle ~$3.4 on Solana → Base (kill the drag) via a skill anicca runs itself
- ☐ 2.4 fix loop_detect dead-time: when fully deployed, anicca should manage HL / advertise x402 / cook,
       not spin on yield-hold

## PHASE 3 — THE MODEL EXPERIMENT (free → auto → premium), same tools, measure earnings
ClawRouter profiles: free (100% savings, $0) · auto (74-100%) · eco (95-100%) · premium (0%, best).
- ☐ 3.1 run FREE (free/glm-4.7) for N days → record realised net (current phase)
- ☐ 3.2 if free does NOT reach net-positive → switch /model auto → measure same window
- ☐ 3.3 → switch /model premium (Claude) → measure. Hypothesis: premium earns with the SAME tools
- ☐ 3.4 OUTPUT = THE RECIPE: which model × which skills × which setup first reaches net-positive
       (this is the takeoff recipe — the whole point)

## PHASE 4 — TAKEOFF LOOP (self-spawn, the exponential)
- ☐ 4.1 a net-positive parent runs self/spawn → a cloud child (Akash) with the SAME setup + own wallet
- ☐ 4.2 child earns unaided → feeds its own compute → spawns its own child → exponential
- ☐ 4.3 inter-anicca mutual aid: surplus peer auto-funds a low-balance peer (Base USDC)
- ☐ 4.4 scale: 1 local + N cloud on free model; fund more → some run premium to experiment

## PHASE 5 — UBI (surplus flows back to humans)
- ☐ 5.1 1% of MRR / surplus → charity-match or human payout, no human click

## PHASE 6 — CONTENT (publish, honest, with the live dashboard as proof)
- ◐ 6.1 automaton article — DONE as a FREE-only story, ships NOW. Canonical = docs/articles/2026-06-11-automaton-jp.md
       (worktree ~/.cache/anicca-article-wt, branch docs/frank-article). NOT automaton-pays-for-itself.md (STALE).
       Real numbers in it: そのまま×無料=$0 / そのまま×有料(GPT-5.5)=$0 burned ~$17 / 改造(道具)×無料=+$0.1676 (hl close, on-chain).
       Premium-with-tools is NOT run (Dais 2026-06-23: do NOT fund premium, keep free glm-4.7). Remaining = PUBLISH ORDER below.
- ☐ 6.2 takeoff article — our definition of takeoff (self-funding + self-spawning, no human), citing
       lesswrong + ai-2027, + the UBI vision
- ☐ 6.3 block 6-3 — per-tool realised earnings table once Phase 2 has real numbers

---

## RIGHT NOW — updated 2026-06-23b (MONETIZE BEFORE PUBLISH — we don't give the sauce for free)
The article is DONE & verified (note draft, all visuals as compact images, infographic). Before publishing we set
up monetization, because the whole point is 10k MRR from writing. note = the key. ORDER:

★ STRATEGY (Dais 2026-06-24): DO NOT enable any cron/launchd yet. Autonomous-now = slop = no money. Instead:
  (a) publish 2 MORE articles BY HAND (Dais + Claude) to battle-test & polish the skill,
  (b) BUILD the full pipeline so it is STAGED & ready: publish-to-note.sh (--draft/--go) + the claude -p agent
      prompt + verify checklist + the launchd plist WRITTEN BUT NOT LOADED,
  (c) flip automation on later with a SINGLE `launchctl load` ("tap once"). Prepare for that tap; don't tap yet. ★
M1. ☑ DONE (verified by screenshot 2026-06-23): membership「アニッチャのメンバーシップ」exists; plan スタンダードプラン = **¥500/月 set**. 公開 toggle still OFF on purpose — publish it together with M2 (so members have content). Fee 10%, MRR engine.
M2. ☑ DONE+VERIFIED 2026-06-24: published https://note.com/anicca123/n/na3a631e63d1a — 無料[0]-[5]+「で、稼げたのか？」teaser free, [6]+ (8378字/7画像) MEMBER-ONLY; membership ¥500/月 plan 公開ON, 「参加手続きへ」live (verified as a non-member visitor). Pure membership, no single price. ORIG below:
M2x. **This article = membership-gated** (COPY ChatGPT研究所, the top AI note creator = pure membership read-all; NO combine). FREE = [0]–[5] (what Automaton is = the hook). [6]+ (the experiment / earning logs) = **member-only** — added to the membership 特典 so only ¥500/月 subscribers read it. NO single-article price (that was a combine = wrong). Membership = the only monetization (recurring MRR). Then publish the membership plan (公開 ON) now that it has content.

P1. ☑ DONE: verified the rendered gate as a visitor (screenshot) — free preview + ¥500 subscribe CTA. URL = https://note.com/anicca123/n/na3a631e63d1a
P1b. ☑ DONE 2026-06-24: note article fully POLISHED & re-verified as a visitor — 見出し画像(eyecatch) set, body duplicate hero removed, broken heading restored, MANUAL 目次 (7 big titles only, auto-目次 deleted). Pipeline saved as reusable scripts in ~/.openclaw/skills/ai-entity-article-writer/scripts/note-publish/ + lessons in SKILL.md. note publishing is now repeatable.
P1c. (nice-to-have) make the manual 目次 clickable (per-heading anchor links); add per-heading anchor jumps.
P2. **Other JP platforms** each with their monetization: Zenn(投げ銭/バッジ) → Substack(paid subscription) →
    X Article(有料購読) → TikTok image (hook → link to the paid note).
D.  **EN**: translate → dev.to → X Article → Substack(EN) (paid).
L.  Cloud 3体 (Akash) → verify launch-copy claims TRUE → LAUNCH post.
F.  AUTOMATE — ☐ BUILD & STAGE NOW, ENABLE LATER (one `launchctl load` after the skill is proven). Design locked 2026-06-24: an LLM is required end-to-end (writing AND the pre-post visual verify),
    so automation = a LOCAL `claude -p` AGENT (Agent SDK headless, --allowedTools Read,Bash,Write,Edit), fired by
    **launchd** (~/Library/LaunchAgents/ai.anicca.note-publish.plist, same pattern as the live ai.anicca.* jobs).
    Must be LOCAL (cloud Routines can't reach the daily-driver browser). The agent loop:
      ① write (ai-entity-article-writer) → ② publish-to-note.sh <md> --draft (render+imgs+eyecatch+目次+paywall+
      membership, STOP before public) → ③ VERIFY by VISION: screenshot the draft as a logged-out visitor + Read it
      (eyecatch shown? 目次=big titles only? imgs not crushed? [6]+ gated? headings intact?) + note API
      (can_read=false, eyecatch set) → ④ PASS → publish-to-note.sh --go ; FAIL → fix & re-verify or Telegram →
      ⑤ Telegram the live URL + screenshot. publish-to-note.sh = deterministic hands (--draft/--go split);
      claude -p = the eyes+brain (writing + the visual pre-post gate). Same shape per platform (publish-to-<x>.sh).
    BUILD ORDER: F1 publish-to-note.sh (--draft/--go, idempotent, guards) → F2 the claude -p agent prompt + verify
    checklist → F3 launchd plist (daily) → F4 generalize to Zenn/Substack/X.

MONEY MODEL (note, researched 2026-06-23): 有料記事(単発) + メンバーシップ(月額=MRR, 手数料10%, 初期0) +
定期購読マガジン(手数料20%). Funnel = free useful articles → followers → membership(recurring) + paid premium.
Same shape on Substack(paid sub) and X(有料購読). MONEY TRUTH: realised so far = +$0.1676 (on-chain).


AUTONOMY: earn actions done by anicca ITSELF (buffer + close-in-profit in runtime/loop/prompt.mjs + earn-detect.mjs).
I (Claude, type-2) only FIX the system + MONITOR + write/publish the article.
