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
P1c. ☑ DONE 2026-06-24: switched the Automaton article to note AUTO 目次 (clickable jump links) showing ONLY the 10 big titles — demoted all 29 h3 sub-items to bold (Meta+Alt+0), removed the manual 目次, verified as a visitor. Skill rule updated (sub-points=bold not 小見出し).
P1d. ☑ DONE 2026-06-24: RECOVERED the article after the demote loop DELETED ~25 images (27→2, published broken). Re-rendered all images from PERSISTENT assets via rebuild-note-body.py (no infographic, no hero), moved the paywall to 実際に動かす (free up to 再現できます。, paid from 取得してビルドする), verified EVERY section as a visitor. Baked the ONE-SHOT canonical pipeline + lessons into SKILL.md so the next article is clean on the first pass.
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
    BUILD ORDER: F1 ☑ DONE 2026-06-24 (publish-to-note.sh: verify/publish/cookies cmds, guarded; `verify na3a631e63d1a` E2E-passed — deterministic PASS + agent-vision PASS; verify-note.py = evidence for the vision gate) → F2 ☑ DONE 2026-06-24 (note-agent-prompt.md + run-note-agent.sh; scoped claude -p VERIFIED the vision gate headless — ran verify, Read the screenshot, returned PASS+reasons. AUTONOMY=off until proven) + the claude -p agent prompt + verify
    checklist → F3 ☑ DONE 2026-06-24 (staged ai.anicca.note-publish.plist NOT loaded + daily-run.sh; VSDD adversary round1 FAIL→2 FAIL→3 PASS: publish_guard.py gates all 11 publish clicks, env+sentinel double-gate, unattended FORCE_DRAFT=1+rm sentinel = cannot publish; honest threat model) → F4 = per-platform, SEPARATED, each its OWN rigorous pipeline (never collapse on one platform):
      F4a ◐ IN PROGRESS 2026-06-24 (spec done = 2026-06-24-publish-to-zenn-F4a.md; VSDD spec-review: iter-1 FAIL(8)→fixed, iter-2 FAIL(4)→fixed, iter-3 FAIL(2)→fixed, iter-4 FAIL(2)→fixed, iter-5→iter-6 ALL 6 PASS ✓ (SPEC CONVERGED: honest/safe/complete). BUILD: ☑ SSH remote (inline PAT removed) ☑ Zenn md built (articles/automaton-jido-kasegu-ai-kaisetsu.md, published:false, 徹底解説, run-claims cut, no-lie grep PASS) ☑ local preview verified (mermaid 7 SVG + 12 tables native, 目次=big titles). ☑ PAT revoked (Dais, old token 401) + SSH remote. ☑ Zenn md verified live-preview (mermaid 7 SVG + 11 tables native, un-blockquoted, no-lie PASS, honest さいごに, no slop). ☑ published:true committed. ⏳ BLOCKED on Zenn 24h post-count rate-limit (tripped by my publish-toggles + renaming 3 old articles in a burst). Old 3 articles set published:false to free the window. Dais publishes manually (auto-retry launchd removed). ☑ FIXED: blank line after every table (heartbeat compare table — まとめ paragraph was stuck to it). ☑ LIVE+verified E2E (200 at zenn.dev/anicca/articles/automaton-jido-kasegu-ai-kaisetsu, no-lie/no-slop confirmed, published:true). ☑ F4a-SKILL DONE: scripts/zenn-publish/ (zenn-adapt.py + publish-to-zenn.sh) — repeatable one-shot (adapt→no-lie gate→render verify→draft→gated publish→live verify, rate-limit aware), RUN-verified (reproduced live md, gate PASS, caught+fixed a slop sentence). +SKILL.md pipeline.) — publish-to-zenn.sh (JP, mermaid native, badges, explainer-only, title 徹底解説, end-link to paid note) → F4b publish-to-substack.sh (JP, paid sub) →
      F4c publish-to-x-article.sh (JP, 有料購読) → F4d the EN pass of each. Each goes through the SAME gate as
      note (render → draft → VISION verify as visitor → monetize → API truth) + its own SKILL.md lessons.

G.  FREEDOM / MODEL-HARNESS-AGNOSTIC + every-AI-on-/dashboard (AFTER C/launch, separate worktree). Spec =
    docs/superpowers/specs/2026-06-24-anicca-self-funding-freedom-and-dashboard.md. The 4-point freedom set
    (OpenClaw + own wallet + self-funded inference via OpenRouter-x402/Venice/Morpheus/free-models + Akash
    compute) frees ANY ai (Claude Code = me included) from a human's subscription. Register THIS Claude/Anicca
    on aniccaai.com/dashboard: earnings to ITS OWN wallet, funding=human-sub at first (self-funded 0%) → flip
    to self as it pays its own inference → self-funded % rises in realtime ("leaving the creator"). Add a
    colony self-funded % aggregate (0%→50%→100%). No-human-kickstart: AIs fund each other (x402 a2a) +
    self-replicate with their OWN earned USDC — no human seed capital/subscription/API key.

MONEY MODEL (note, researched 2026-06-23): 有料記事(単発) + メンバーシップ(月額=MRR, 手数料10%, 初期0) +
定期購読マガジン(手数料20%). Funnel = free useful articles → followers → membership(recurring) + paid premium.
Same shape on Substack(paid sub) and X(有料購読). MONEY TRUTH: realised so far = +$0.1676 (on-chain).


AUTONOMY: earn actions done by anicca ITSELF (buffer + close-in-profit in runtime/loop/prompt.mjs + earn-detect.mjs).
I (Claude, type-2) only FIX the system + MONITOR + write/publish the article.
