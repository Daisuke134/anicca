# SPEC — profitable-article-writer: any AI writes an article and earns, zero human (2026-06-29)

Date: 2026-06-29, updated 2026-07-04 · Status: **Sprint 1 + Sprint 2 COMPLETE (VCSDD 4-D converged)**, building Sprint 3+
Author: main agent (Claude Code, dev IDE) · Repo: `Daisuke134/anicca` · Branch: `feature/human-funded`
Skill home: `skills/profitable-article-writer/` · VCSDD state: `.vcsdd/features/profitable-article-writer/`

## §-1 STATUS (2026-07-04) — what is actually built vs still ahead

```
 ✅ Sprint 1 COMPLETE  orchestration skeleton: run.sh 1-wake, V0/V0.5 gates (fail-closed),
                       Mode A draft-first, per-install identity, model-agnostic, sonnet-only loop.
                       Adversary PASS (3 rounds, 0 findings) + formal hardening. 13/13 tests.
 ✅ Sprint 2 COMPLETE  REAL content-gen hook (generate_draft), REAL note.com DRAFT publish
                       (visuals: hero+2 inline figures, eyecatch/cover, SINGLE ¥500 paid gate —
                       replacing the old メンバーシップ). REQ-19 (daily executor = `claude -p` sonnet)
                       + REQ-20 (verifier = main agent, browser-verified render) added.
                       Adversary PASS (4 rounds, 0 findings) + hardening. 20/20 tests.
                       Real evidence: note draft `nfb2ace9f0ed8` (anicca123), independently
                       browser-verified by the main agent (cover + diagrams + 有料/¥500 panel visible).
 ✅ Sprint 2.5 COMPLETE Standalone real-publish tool (REQ-21/22), structurally isolated from run.sh/Mode-B/
                       daily-wake. Adversary PASS (1c: 3 rounds, contract: 2 rounds, impl: 1 round) + hardening.
                       26/26 tests. ★ REAL PUBLISH EXECUTED 2026-07-04: `nfb2ace9f0ed8` is now genuinely
                       PUBLIC — verified 3 independent ways (tool output, separate note-verify-live.py,
                       main agent's own fresh logged-out curl). V1(real)=TRUE. V4(¥500 sale) tracking starts now.
 ⏳ NEXT: Sprint 3     Distribution (X/Threads) + trust ramp → V2 reach / V3 convert
    Sprint 4          Wire run.sh into the runtime daily loop (claude -p sonnet, unattended)
    Sprint 5          Self-heal (REQ-17) + self-improve (REQ-18) — zero Opus, zero human
    Sprint 6          Niche generalization + spawn self-funded child
 Method used throughout: VCSDD strict (10-phase, 4-role). Every builder/adversary claim independently
 re-verified by the main agent (re-run tests myself, open screenshots myself, grep the fix myself) —
 never taken on faith. See `.vcsdd/features/profitable-article-writer/reviews/` for the full audit trail.
```

## §0 What this is and what it feeds

Rename + widen the existing `ai-entity-article-writer` skill into **`profitable-article-writer`**: a
model-agnostic, zero-human-loop skill that ANY frontier-model AI installs and runs to **write an article →
funnel it → sell a backend → receive real money in its own account/wallet → verify the money landed →
repeat daily**. AI-entities stays the **default/flagship niche**, but the niche is a parameter the running
agent picks for its own audience.

This is the **CONTENT earn slot** of the master recipe — it does NOT replace it:
- SSOT it obeys: `2026-06-28-frontier-model-earn-recipe.md` (any frontier AI earns > the human pays; **ZERO
  human in the loop**; the human's ONLY contribution is COMPUTE; **LOCAL vs CLOUD** is the only behavioral axis;
  same shared skill set; surplus → UBI).
- SSOT it slots into: `2026-06-28-anicca-master-architecture-one-repo-credential-gating.md` (one repo, one wake
  body, one registry, **per-skill credential gating**; `content_*` slots already declared).
- Verifier it reuses: `skills/self/founder-loop/` (`record-earn.mjs` = the ONLY ledger writer, anti-fake gates
  INV-1..7; goal = a real on-chain/account receipt, never "the wake ran").

Non-negotiable invariants inherited:
- **ZERO human loop.** No human click / OTP relay / approval / delivery. Any sub-step that needs a human is made
  autonomous (login→stored creds, OTP→Gmail/AgentMail auto-read, account→`ig-account-create`-style self-signup,
  payout→wallet) or dropped.
- **No extra API.** Generation is done by the running agent on its own subscription. The skill names NO model /
  provider / API key. Same skill runs on Claude/Opus today, GPT/Grok/DeepSeek/Kimi later — swap the model.
- **LOCAL vs CLOUD** differ ONLY in the browser/compute body: CloakBrowser (`:9222` CDP) local vs a cloud
  headless browser (browser-sh) cloud. Same skill, same loop, swapped body.
- **EXPLAIN, don't RUN (Dais 2026-07-03).** The article is a **deeply-researched, detailed, VISUAL explainer** —
  NOT a "we ran it and here are the receipts" lab report. The skill does NOT execute external repos/tools to
  produce the piece, MUST NOT claim to have run anything, and MUST NOT emit error-log content. Running is
  brittle and error-spew damages the brand ("we did it together but the agent isn't there yet"). The moat becomes
  **research depth + synthesis across primary sources + original diagrams/visuals + honest verdict from those
  sources** — not receipts. Revisit only once execution is reliable enough to never spew failures publicly.

## §1 AS-IS — supply is perfect, demand & money are uninstrumented

The current skill writes world-class articles and publishes them with a render/slop verify. That is the
**supply** side at 100%. The **demand + money** side is at 0% — not just unverified, **not built**.

```
 SUPPLY (build)                         DEMAND · MONEY (earn)
 ✅ deep research / synthesize / verdict  ❌ did anyone READ it (reach)
 ✅ de-slop + language purity            ❌ did the funnel CONVERT (free→paid→backend)
 ✅ render screenshot verify (V0)        ❌ did real ¥/USDC LAND (earn)
 ✅ live publish, logged-out (V1)        ❌ does it keep earning daily (sustain)
```

`founder-loop` STATE already names the bottleneck: **"NO realised external earn yet — bottleneck is
DEMAND/LISTING/PRICING, not code."** money-loops research already converged: **"the moat is not generation
(solved & ~free); it is ① distribution ② monetization."**

## §2 The BP, distilled (Kくん + まな → one doctrine)

| Author | Core BP | Verdict |
|---|---|---|
| **Kくん** | 動線が先・content後。X流入 → 無料note(教育/信頼) → 有料note → **backend高単価=本当の金** (note本体でなくbackendで1700万)。daily運用・per-platform | ADOPT funnel + backend + daily-org + per-platform. REJECT `ANTHROPIC_API_KEY` 量産 (contradicts no-extra-API; AI-slop量産 dies to 2025 demonetization + note公式の一次情報優先) |
| **まな** | AI丸投げは沈む。AI=リサーチ/構造/たたき台、走るagent=体験/数字/失敗談/温度。ドメイン知識が本質。信頼残高 7:1。**収益=リーチ×CTR×成約×単価**。10ライティング技法 | ADOPT WHOLE — this is our existing anti-slop moat AND the persuasion craft we dropped |

**Synthesis:** keep our まな-grade purity engine, bolt Kくん's funnel + distribution + daily-org around it, add
the persuasion craft we omitted, and the running agent (Sonnet wake) does all generation = zero extra API =
the OSS-replicable, model-agnostic, self-fundable thing.

## §3 The six missing organs

| # | Organ | BP source | Today |
|---|---|---|---|
| 1 | **Funnel (動線)** | Kくん「動線設計が先」無料→有料→backend | single article, no flow |
| 2 | **Backend high-ticket (the real money)** | Kくん「1700万はbackend」 | no backend product |
| 3 | **Distribution (集客)** | まな「収益=リーチ×…」reach 0 → ¥0 | "publish" only, no X/Threads inflow |
| 4 | **Trust ramp (信頼残高)** | まな「預け入れ:引き出し=7:1」cold account doesn't sell | new agent = ¥0 day 1, no ramp |
| 5 | **Per-install identity (model/cred-agnostic)** | earn-recipe「ZERO human」+ memory「model-agnostic」 | hardwired to Dais creds |
| 6 | **Earn + payout verify (closed loop)** | 5-gate earn memory + GLVS | render-verify only; no money-verify, no payout rail |

**Monetization (Dais 2026-07-03) — per-article ONE-TIME payment is PRIMARY:**
- **PRIMARY** = sell EACH note as a one-time purchase in the **¥500「迷う前にポチ」band** (high conversion, a cold
  audience buys, fastest first-sale). Money = volume × ¥500, NOT a subscription wall. (BP: せいぬ/イケイケ兎 — ¥500 =
  "ポチられる" 閾値; 設計=テーマ/見出し/価格で決まる.)
- **OPTIONAL** = a subscription / 月額マガジン for readers who want everything — an add-on join, not the main gate.
- NOT Brain/Tips affiliate (others' accounts, JP-only). Payout → the install's OWN note account/wallet.
This supersedes the earlier "own-product funnel primary" line.

### §3.1 Multi-platform monetization matrix (Dais 2026-07-03) — one article, N native rails

The skill ALREADY publishes EN+JP to X / Substack / note / Zenn / dev.to. Do NOT limit money to note. **One
deeply-researched piece (the shared moat) → repurposed per platform (native shape + language) → each platform
monetized its OWN native way.** People earn $10k EACH from note, Substack, X separately — we stack the rails
from ONE engine.

```
 ONE piece (EN+JP)  ── shared writing engine (research + visual explainer) ──
   │  repurpose per platform (native format + language)
   ▼
 PLATFORM   LANG    NATIVE MONEY RAIL                          ROLE
 note       JP      ¥500 単発有料 + 月額マガジン                DIRECT $ (ポチ帯)
 Substack   EN/JP   paid subscription (creator-priced, recurring)  DIRECT $ (recurring)
 X          EN/JP   ad-rev-share(at impression scale) + X Articles/Subscriptions + top-funnel  FUNNEL + $
 Zenn       JP      有料Books + 支援バッジ (dev niche)          DIRECT $ (dev)
 dev.to     EN      no native paywall → SEO/reach              FUNNEL → drives the paid rails
```

Principle: **paywall-less platforms (dev.to, X posts) are TOP-FUNNEL** that drive readers to the paid rails
(note ¥500, Substack sub, Zenn Books) + an owned email list; **paywalled platforms are the DIRECT $ rails.**
Each platform is a **credential-gated parameter** in `registry.json` (`content_note`, `content_substack`,
`content_devto`, `x_poster`, + add `content_zenn`, `content_x_articles`); an install monetizes only the rails it
has creds for. **V4 earn-verify runs PER RAIL** (money landed on note ≠ on Substack ≠ on X). Prove ONE rail
first (default: note ¥500), then light up the others from the same article.

### §3.2 Zero-human account + payout per rail — the REAL gate (honest, 2026-07-03)

"Any AI earns by writing, zero human" splits into THREE sub-gates. Only the third is genuinely hard — be honest,
don't overclaim (brand safety):

```
 GATE 1  CREATE account  ✅ Instagram PROVEN E2E (ig-account-create: Gmail plus-address, OTP auto-read,
                            NO phone, NO captcha). Email/GitHub rails (dev.to, Substack, Zenn) = SAME pattern,
                            no phone → replicable but NOT yet proven here. Phone-gated (X; sometimes note) =
                            needs SMS-rental → NOT yet proven, FLAGGED.
 GATE 2  PUBLISH         ✅ solved for every rail given creds (existing publishers).
 GATE 3  GET PAID (KYC)  ★ the real wall ★ note/Substack/Zenn/X withdrawals need a BANK account + identity
                            verification. This, not login, is the zero-human blocker.
```

Payout resolves by funding mode (per the frontier-model-earn-recipe axis):
- **HUMAN-FUNDED:** the install carries the human's payout account as a one-time install fact (the human's ONLY
  roles = COMPUTE + a payout identity). The RUNTIME loop stays zero-human; note ¥500 / Substack sub land in the
  human's payout account.
- **SELF-FUNDED:** cannot pass bank KYC → money MUST be crypto-native. The article funnels to an x402-gated
  resource / own crypto checkout → USDC to the instance wallet (reuse `skills/earn/x402-sell` + `founder-loop`).
  Platform paywalls are the human-funded rail; the wallet checkout is the self-funded rail.

V4 earn-verify runs PER RAIL and PER MODE (bank receipt for human-funded, on-chain receipt for self-funded).

## §4 The writing craft we dropped (improve INSIDE the article)

Our PLAYBOOK perfected **PURITY** (clarity / anti-slop) and **deliberately killed CONVERSION** — rule #1 verbatim
is "an article, not a sales piece; no self-reference; subject = the thing." Right for an explainer, wrong for a
**profitable** note. まな proves you can be anti-slop AND a master copywriter. We did only half.

Eight additions from BP — each kept HONEST (no hype, the moat stays):

| # | Add | BP example | Today |
|---|---|---|---|
| 1 | Desire hook (痛み + 好奇心gap + 数字) | 「24時間で3,275万円」「え？と常識破壊」 | clarity-only opener |
| 2 | Direct address (あなた) + emotion (恐怖/好奇心/焦り/希望) | 「あなたは今の給料に満足してますか」 | ですます/三人称, あなた禁止 |
| 3 | Article = funnel (有料split + backend CTA woven in) | 「ここから先は有料」「おまけ/応用編」→ backend | standalone essay, no CTA |
| 4 | Paid-split as craft (free part = a sales letter, cut at the payoff) | free 5万字でファン化 → 動線設置 | paywall mechanism, free part not a sell |
| 5 | まな's 10 techniques, honest only (両面提示/失敗談/生活の小変化/比較仮想敵/大義名分=透明性/プロフィール=最終兵器) | §ライティング術 | honest verdict ≈ half of 両面提示 only |
| 6 | Scannability gate (一文≤60字 / 漢字率≤30% / 改行多め / 箇条書き≤5 / mobile-first) | note買者の読み方 | natural-JP checked, no numeric gate |
| 7 | CTR title formula (KW × 切り口 × 感情) | 【完全保存版】【悲報】数字 | accurate, not CTR-optimized |
| 8 | Proof = social proof framing | 売上SS / before-after | no running → proof = research depth + primary-source citations + original diagrams; frame these as the reason to trust/buy |

**Synthesis (dialectic, not pick-one):** the article BODY keeps explainer purity (that earns trust = the 無料
教育 role); DESIRE comes from the hook on top + the backend CTA at the end + the paid part being the exclusive
payoff + honest persuasion structures. Purity and conversion do not conflict — we were doing half.

## §5 The verification ladder — finish-line = V4, not V1

The current verify stops at V0/V1 ("the artifact is good & live") and never reaches "it earned." That is the
"more verification missing" Dais named.

```
 V5 CONTINUOUS  ledger grows daily, unattended                 ❌  (sustain)
 V4 EARN        real ¥/USDC landed in per-install account/wallet ❌ ★finish-line★ (record-earn anti-fake)
 V3 CONVERT     free→paid→backend CTR + email capture            ❌
 V2 REACH       humans actually saw it (views/impressions)       ❌
 V1 PUBLISHED   live, logged-out visitor, URL 200                ✅
 V0 RENDER      no breakage / no slop / paywall gate correct      ✅  (note-publish vision gate)
 V0.5 CRAFT     draft: hook makes desire? CTA exists? free=sales letter? readability pass?  ← NEW, fresh-context adversary scores
```

**DONE is V4**, per founder-loop discipline: a unit is DONE only on a verifiable receipt of real external money
in a per-install account/wallet, confirmed by `record-earn`'s anti-fake gate AND my own browser/on-chain E2E —
never "published," never "the wake ran." V0.5 + V2..V5 are the gates we add.

## §6 Folder tree (real structure) + model assignment

```
Daisuke134/anicca
├─ skills/registry.json            ← add ONE slot:
│     "content_article": { credentials_required:["NOTE_SESSION_COOKIE"],
│                          dir:"skills/profitable-article-writer", entrypoint:"run.sh", status:"declared" }
├─ skills/profitable-article-writer/        ★new (migrated+renamed from ai-entity-article-writer)★
│   ├─ SKILL.md          NL only, no model/provider named = AI-agnostic
│   ├─ run.sh            1-wake entrypoint                     🟢 claude -p sonnet
│   ├─ PLAYBOOK.md       purity moat + §4 craft layer + §2 BP   (read)
│   ├─ brain/            ① write: research / synthesize / VISUAL-explain / verdict / de-slop (NO external run)  🟢 sonnet
│   ├─ funnel/           ③ free→paid→backend + backend-product/ (#1,#2)                   🟢 sonnet
│   ├─ publish/          note-/zenn-/substack-/devto-/x-publish + render verify (V0/V1)    🟢 sonnet
│   ├─ distribute/       ④ x-buzz / x-article / threads (#3, reach→V2)                     🟢 sonnet
│   ├─ trust/            ⑤ 7:1 ramp / profile / 固定post (#4)                              🟢 sonnet
│   ├─ identity/         per-install accounts; self-create if absent (#5)                  (—)
│   └─ state/            per-install (gitignored): topic-queue / posted-ledger / funnel-metrics
├─ runtime/              EXISTING loop body
│   ├─ anicca-daemon.sh  launchd wake                          🟢 claude -p sonnet
│   └─ loop/config.mjs   model tier (funded = sonnet)          ← Sonnet pinned here
└─ skills/self/founder-loop/   EXISTING earn verifier
    ├─ founder-loop.sh   goal-check each wake                  🟢 sonnet
    └─ record-earn.mjs   ★only ledger writer · anti-fake★       🔴 NO LLM (deterministic)

~/.anicca/ (runtime_root, gitignored) = per-install body
  .env: NOTE_SESSION_COOKIE / X_OAUTH1_BUNDLE / wallet  ·  state/STATE.md  earn-ledger.jsonl
```

**Model policy (cap-safe):** every loop wake = `claude -p --model sonnet` (cheap, 5-min cache, separate weekly
cap). `record-earn` (V4) = **no LLM, deterministic** (un-fakeable). **Opus only** for design/spec + the
fresh-context vcsdd adversary — **never inside the loop**. The daily loop burns zero Opus.

## §7 Runtime / automation (how it actually loops)

```
 launchd/cron 5-min heartbeat (existing anicca-daemon.sh)
   → claude -p --model sonnet (headless, 1-shot, own sub, $0 extra API)
   → read STATE.md → pick ONE action
   → run.sh: brain → funnel → publish → distribute (LOCAL: CloakBrowser :9222 / CLOUD: headless browser)
   → record-earn verifies V0..V4 (anti-fake) → STATE.md atomic update → next wake (no human)
```
We ADD the skill body + registry slot; the daemon, founder-loop ledger, note-publish pipeline, and publishers
are EXISTING and reused.

### §7.1 Publish lifecycle — draft-first, graduate to autonomous (Dais 2026-07-03)

Slop must never go public, so publishing ramps in two modes (the note-publish pipeline already defaults to
`AUTONOMY=off` = stop at draft, notify for review):

```
 MODE A (default, trust-building):  agent writes → note DRAFT → V0/V0.5 self-check →
   notify Dais (URL + screenshot) → Dais reviews/edits → Dais clicks publish.   (human = final gate)
        │  Dais says "post directly" (HARD 0.27 verbatim go)
        ▼
 MODE B (autonomous, the full loop):  agent writes → V0/V0.5 PASS → publishes directly →
   distributes → record-earn verifies V4 → daily, zero human.
```
Mode A = `AUTONOMY=off` (human-review gate sits between V0.5 and V1); Mode B = `AUTONOMY=on` (gate removed). The
switch is per-install, flipped ONLY on Dais's explicit go. Mode B is the "no human in the loop" end state.

## §8 Build order (each piece = its own VSDD cycle: SPEC→RED→GREEN→fresh-context adversary→my browser/on-chain E2E)

```
SPEC 1 ▸ rename + identity(#5) + funnel+backend+payout skeleton(#1,#2,#6) + PLAYBOOK craft(§4) + V0.5 gate
         ← FIRST (BP: design 動線 before content). Finish-line: ONE real cycle earns ONE real unit, V4-verified.
SPEC 2 ▸ distribution + trust ramp (#3,#4) → reach (V2) + convert (V3)
SPEC 3 ▸ wire into daily GLVS loop + V5 continuous earn-verify (reuse daemon + founder-loop)
SPEC 4 ▸ niche generalization (niche as parameter) + spawn self-funded child (phase 2)
```

## §9 Definition of done (this whole skill)

A 4-D convergence per VSDD: spec ✓ · tests ✓ · impl ✓ · **V4 earn verified** ✓ — the loop, with zero human
touch, wrote an article, ran the funnel, posted + drove traffic, and a **real external ¥/USDC landed in a
per-install account/wallet**, confirmed by `record-earn`'s anti-fake gate and my own browser/on-chain check,
on the niche the agent chose, runnable on any frontier model by swapping the model.

## §11 Operating model + self-operation (Dais 2026-07-03/07-04, added to VCSDD behavioral-spec REQ-17..20)

- **REQ-19 Daily executor = `claude -p` (Sonnet).** The daily article wake — research → write → V0/V0.5 → post a
  note DRAFT (Mode A) — runs unattended on the headless `claude -p --model sonnet` loop. It does the work.
- **REQ-20 Verifier = the main agent (Opus), out of the daily loop.** The rendered draft is checked by the main
  agent via a real browser look (no slop, paywall gate, hook/CTA, visuals) — not by the executor grading itself.
  This is the Mode-A trust ramp; once trusted, Mode B removes this step (self-heal/improve, REQ-17/18, removes it
  for good).
- **REQ-17 Self-heal** (Sprint 5): on an unattended wake failure, the skill diagnoses from its own logs/state and
  attempts an autonomous fix (retry/refresh cred/switch rail) — zero Opus, zero human. Unrecoverable → quarantine
  + record; the loop survives.
- **REQ-18 Self-improve** (Sprint 5): the skill reads its own per-rail stats (V2/V3/V4) and adjusts the next
  wake's topic/hook/price/rail-mix to earn more — a closed loop the model drives by judgment, never hardcoded
  rules. Zero Opus, zero human.

**Sprint 2.5 — DONE (2026-07-04): flip the verified draft to real, by hand.** "the note is not actually
published, we have to have it actually published, after the verification." Built a standalone, one-off tool
(`lib/note-publish-live.py` + independent `lib/note-verify-live.py`), structurally excluded from `run.sh`'s call
graph (grep-verified, adversary-verified 6 rounds total across 1c/contract/impl review). The main agent
personally invoked it once (`NOTE_LIVE_PUBLISH=1 python3 lib/note-publish-live.py --draft-key nfb2ace9f0ed8`).
**Result: `nfb2ace9f0ed8` is genuinely PUBLIC.** Verified 3 independent ways: the tool's own output, the separate
verifier process (logged-out, PASS:true), and the main agent's own fresh curl (HTTP 200 + exact title match).
V1(real)=TRUE. This closed the manual proof — but it was a HUMAN HAND on the trigger, not the loop. Dais
2026-07-04: "then wire that in, yes, we have to" — the honest gap this leaves open is §11.1.

### §11.1 Sprint 4 — wire real publish INTO the loop (Mode B), so no human/Opus ever triggers it again

Today: `run.sh` (the daily `claude -p` wake) stops at Mode A's draft every time — by design, it structurally
cannot reach a publish click (REQ-6/REQ-21's isolation is intentional and stays true for Mode A). The real
publish that just happened was the main agent running a separate tool by hand — **not the loop**. Closing this
gap is Sprint 4's job:

- **REQ-23 Mode-B publish branch.** WHEN `run.sh` runs WITH `AUTONOMY=on` (Mode B) AND V0∧V0.5 PASS, THEN `run.sh`
  itself SHALL perform the equivalent of `note-publish-live.py`'s confirm→click sequence, reusing the SAME
  fail-closed pre-publish checks (price/type/eyecatch/visuals) and the SAME try/except/finally exception-safety
  (no leaked context, no raw traceback) — NOT a re-invention, a real code-sharing wire-up (e.g. `note-publish-live.py`'s
  core logic becomes an importable function both the standalone tool AND `run.sh`'s Mode-B branch call). This is
  the ONLY caller allowed to reach the real click from an unattended wake.
- **REQ-24 Mode-B post-publish verify, in-loop.** Immediately after a Mode-B publish, `run.sh` SHALL invoke the
  SAME independent verifier logic as `note-verify-live.py` (logged-out fetch, 200 + content match) and record
  the result to state; on verify failure, the wake SHALL record an unconfirmed-publish state (never silently
  assume success) for the next wake or self-heal (REQ-17, Sprint 5) to reconcile.
- **Trust-ramp graduation (§7.1, unchanged principle):** Mode B is flipped per-install by explicit go — start
  with a small number of Mode-B wakes (e.g. 1-in-N) while Mode A continues alongside for comparison, widen once
  stable. Self-heal/self-improve (Sprint 5, REQ-17/18) is what eventually makes even THIS graduation decision
  unattended — until then, turning AUTONOMY=on is the one calibration knob a human/main-agent still touches.

## §10 Non-goals / open

- NOT Brain/Tips affiliate. NOT a hosted SaaS, NOT Dais's domain/accounts — per-install creds only.
- NOT Opus in the loop.
- NOT "run it / receipts" articles (Dais 2026-07-03) — research + visual explainer only, no external execution,
  no error-spew. Revisit when execution is reliable.
- RESOLVED 2026-07-03: monetization = ¥500 per-article one-time (primary) + optional subscription; publishing =
  Mode A (draft-first, Dais reviews) → Mode B (autonomous) on Dais's go.
- OPEN (resolve in Spec 1 plan): backend/upsell format beyond the ¥500 note (magazine vs bundle —
  agent picks per market); first niche to prove V4 on (default: AI-entities, the flagship).
