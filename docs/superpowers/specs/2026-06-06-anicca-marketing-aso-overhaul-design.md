# Anicca Marketing + ASO Overhaul — Design Spec

**Date:** 2026-06-06
**Owner:** Dais (directives 2026-06-05/06)
**Status:** SPEC — patches enumerated, NOT yet applied. Apply per rollout order on `go`, one at a time with live-run + camofox visual verification.

> All edits are in the **runtime store `~/.openclaw`** (crons/skills) and **iOS App Store metadata** — both are HARD RULE #0 worktree-exempt (gateway reads live). Apply on `main`/live, but run spec→patch→live-run→verify per item.

---

## 0. Context / Root Theme

Marketing is misrouted and stale. Verified facts (read from `~/.openclaw/cron/jobs.json` + skills + Postiz API):

| Symptom | Verified root cause |
|---|---|
| JA video on EN Larry TikTok; Larry JA silent on @anicchasan | `larry-anicca-ja-1` cron is a **verbatim copy of `larry-anicca-en-1`** — TikTok=`cmlt171…`(EN), IG=`cmmzzg2…`(EN), `--account anicca-en`. JA never routed to JA account. |
| Everything piled into 1 EN account | `cmlt171…`(@aniccaen2) shared by Larry EN + reelclaw en card-2 + 4.7-morning + honne-en |
| EN reelclaw widget never posts | `reelclaw-anicca-en-widget-1` AND `-2` both `enabled:false` |
| honne JA same hook forever | `run-honne-ja.sh` reads fixed `honne-ai/honne-hooks-ja.json` (hand-written dict), not fresh-generated from `pattern-honne-ja.jsonl` |
| honne EN not posting ~1wk+ | recent cron runs error out (last success ~2026-05-30) |
| iOS subtitle cryptic | "A line when you need it" / "必要な瞬間にやさしい一行" = zero keywords, category unclear |
| Nobody catches these | No pre-post quality gate, no post-post audit. Dais is the monitor. |

Postiz integration map (authoritative, `~/.openclaw/state/postiz-integrations.json` + live API):

| ID | platform | account | intended owner |
|---|---|---|---|
| `cmlt171eq04d9r00yzzceb6bw` | TikTok | @aniccaen2 | Larry EN (currently shared) |
| `cmlrv8jq000hun60yy57eaptx` | TikTok | @anicchasan | Larry JA |
| `cmmzzg2es0539p30ycb94ayx0` | IG | @anicca.monk (EN) | Larry EN |
| `cmmzujxpa04ujp30yxqpg1vci` | IG | @anicchasan (JA) | Larry JA |
| `cmpc3gx4001nklg0y27a8o66q` | IG | @anicca.en | reelclaw EN card/widget |
| `cmmzukbkw04ulp30yfvijrwio` | YouTube | @anicca-ai (EN) | reelclaw EN card/widget |
| `cmnhlk3ju058lpn0ytilqdpo0` / `cmnipef7g…` / `cmn1oukj9…` | TT/IG/YT | anicca-ja-card | reelclaw JA |
| `cmnit95mg015rrm0ye5vm8dhl` | TikTok | honne | honne JA+EN (shared) |

---

## Part A — iOS ASO (subtitle = keyword list, bundled with 1.9.3)

**Directive:** subtitle must be a plain-word **keyword list** like successful apps (e.g. モチベーション・自尊心・名言・メンタルヘルス・自己肯定感・感謝・幸せ・瞑想・ポジティブ). No cryptic poetry. Same approach EN + JA. Copy what works.

**Current (asc-pulled):**
- name EN `Daily Affirmations - Anicca` / JA `毎日のアファメーション - アニッチャ`
- subtitle EN `A line when you need it` / JA `必要な瞬間にやさしい一行`
- keywords EN `anxiety,mindfulness,sleep,stress,overthinking,grief,burnout,selfcare,calm,healing`
- keywords JA `不安,睡眠,ストレス,考えすぎ,グリーフ,燃え尽き,セルフケア,落ち着き,癒し,自己肯定感`

**New subtitle (≤30 chars, keyword-list, complements keyword field):**
- EN candidate 1: `Calm, Sleep, Self-Love & Focus` (30)
- EN candidate 2: `Affirmations, Calm & Self-Love` (30)
- JA candidate 1: `自己肯定感・瞑想・名言・感謝・幸せ` (17)
- JA candidate 2: `自己肯定感・名言・瞑想・感謝・ポジティブ` (20)
→ **Pick one EN + one JA at apply time** (default EN-1 + JA-2).

**Keyword field** stays keyword-stuffed (already good). Optionally add 自己肯定感→move to subtitle, free a slot for 名言/瞑想/感謝.

**SUBMISSION MECHANICS (answer to "do we need a new version?"):**
- name + subtitle live at **appInfo** level; keywords at **version-localization** level. Both require a **version that goes through review** to change. Promotional text is the only field editable live with no review.
- 1.9.2 is `WAITING_FOR_REVIEW` (locked). You **cannot create a new version** while 1.9.2 is non-released, and editing 1.9.2's metadata now would reset its review.
- **Decision: bundle subtitle + keyword change INTO the 1.9.3 submission.** Do NOT do a separate metadata-only submission now. It rides the 1.9.3 review you already plan — **no extra/earlier review triggered, 1.9.2 untouched.**
- Apply order: 1.9.2 distributes → create 1.9.3 version slot → set new subtitle/keywords on it via `asc metadata` → attach build 369 → submit. (One review, both binary + metadata.)

---

## Part B — Larry: routing fix + 3×/day + static human background

### B1. Fix `larry-anicca-ja-1` (THE smoking gun)
File: `~/.openclaw/cron/jobs.json`, job `larry-anicca-ja-1`, `payload.message`:
```
cmlt171eq04d9r00yzzceb6bw  →  cmlrv8jq000hun60yy57eaptx   # TikTok EN→JA (@anicchasan)
cmmzzg2es0539p30ycb94ayx0  →  cmmzujxpa04ujp30yxqpg1vci   # IG EN→JA
--account anicca-en        →  --account anicca-ja          # history ledger
```
Verify: fire once → camofox open @anicchasan TikTok → JA slide visible; @aniccaen2 gets NO JA post.

### B2. 3×/day (EN + JA)
Duplicate `larry-anicca-en-1` → en-2, en-3 (e.g. 08:00 / 13:00 / 19:00 JST). Same for ja-1 → ja-2, ja-3 (08:30 / 13:30 / 19:30). Each entry keeps its language's correct Postiz IDs + `--account`. 14-day anti-repeat already prevents dupes across the 3 daily runs.

### B3. Static human background (no rotation, no random) — EN + JA
The `bedroom/` folder IS the "human" set: `slide1.jpg` = man by fireplace, `slide2.jpg` = people on couch (different).
Directive: **slide1 = `bedroom/slide1.jpg` (static man), slides 2–6 = `bedroom/slide2.jpg` (static, the other image). Identical for EN and JA.**
Patch the larry slide-build step so all of slide2..6 use the single `bedroom/slide2.jpg` and slide1 uses `bedroom/slide1.jpg` — remove the slideN.jpg→N mapping. Text overlays still freshly generated per run; only the photo is fixed.

---

## Part C — EN account isolation (Larry vs reelclaw) + new EN-videos TikTok

**Goal:** @aniccaen2 (`cmlt171…`) = **Larry EN only**. reelclaw EN card+widget move to a **new dedicated "English videos" TikTok** (Dais created it) connected to Postiz.

### C1. Connect new EN-videos TikTok to Postiz → obtain new integration ID `<NEW_EN_TT>`.
### C2. reelclaw EN card/widget crons: `--tt cmlt171…` → `--tt <NEW_EN_TT>`. Keep IG `cmpc3gx4…` + YT `cmmzukbkw…` (already correct/shared for card+widget).
### C3. Remove `4.7-slideshow-morning` from `cmlt171…` (disable, or give it its own ID).
### C4. `reelclaw-honne-en-1/2` keep their own honne TT (Part E), not `cmlt171…`.
Result: @aniccaen2 receives Larry EN only.

---

## Part D — JA TikTok cleanup (@anicchasan = Larry JA only)

Disable JA slideshow crons that contaminate `cmlrv8jq…` (verified: tomb-ja `postiz-draft.py` hard-refs it; cafe/fashion/retreat-ja via env/config — confirm at apply):
- `anicca-tomb-slideshow-ja-daily` → `enabled:false`
- `anicca-cafe-slideshow-ja-daily` → `enabled:false`
- `anicca-fashion-slideshow-ja-daily` → `enabled:false`
- `anicca-retreat-slideshow-ja-daily` → `enabled:false`
(iam-photo/color-ja, mantra-ja, 4.7-ja already OFF.)
Re-enable each later once it has its own dedicated TikTok account. After B1 + D, @anicchasan = Larry JA only.

---

## Part E — Honne: fresh generation + honne-EN repair

### E1. Fresh hooks (kill fixed dict)
`~/.openclaw/workspace/skills/reelclaw/scripts/run-honne-ja.sh` (+ `-en.sh`): replace `honne-hooks-ja.json` lookup with Larry-style flow — read `~/.openclaw/state/content-library/pattern-honne-ja.jsonl`, pick 1 by views + not-in-14d + emotion diversity, **LLM-generate a fresh hook** (clone structure, new wording), append to account-history. Removes the "怒ってないよ" repeat.
### E2. honne-EN repair
Diagnose recent error in `~/.openclaw/cron/runs/` for honne-en (model fallback / Postiz auth). Fix, re-fire, verify a real TT_POST_ID. honne is `cmnit95mg…` (shared EN+JA today — give honne-EN its own account when available).

---

## Part F — reelclaw EN widget re-enable

`reelclaw-anicca-en-widget-1` + `-2`: `enabled:false → true`; set model to a stable tier (avoid the DeepSeek/Codex cooldown that killed them 5/31–6/1). After C2 they post to `<NEW_EN_TT>` + IG `cmpc3gx4…` + YT `cmmzukbkw…`. Verify each fires + posts.

---

## Part G — ★ Quality Gate (Anicca self-verifies + self-heals) ★

**Directive:** Anicca, not Dais, finds and fixes posting errors. Two layers.

### G1. Pre-Post Gate — `~/.openclaw/skills/_shared/quality-gate.sh` (NEW, fail-closed)
Every content cron calls `quality-gate.sh <run_dir> <target_account_lang> || exit 1` BEFORE Postiz publish:
1. **lang × account match** — video lang == target account lang (block JA→EN account).
2. **fits on screen** — measure each hook/body line bbox vs TikTok safe area; JA one-liners that overflow → shrink/re-wrap/regenerate. (Direct fix for "text off-screen".)
3. **hook freshness** — not in account-history 14d; not byte-identical to last post; provably generated (not a static dict id).
4. **basic health** — video exists, duration in range, caption present.
Fail → iterate/regenerate until pass, THEN post. Each content skill patched to invoke it.

### G2. Post-Post Auditor — extend `~/.openclaw/skills/anicca-universal-observer` (cron, few×/day)
1. Read all `account-history.jsonl` + cron run logs → log per-account "hook posted".
2. **camofox** opens each live TikTok/IG/YT → visually confirm right account / no overflow / hooks varied.
3. Detect: lang-mismatch, repeated hooks, text overflow, **posting gap** (account silent > N days → catches honne-EN-type stalls).
4. On detect → auto-file `gh issue` to `Daisuke134/anicca-oss` → forum-issues/forum-rollout self-applies. (No Dais in loop.)

### G3. Account-Health self-loop (added 2026-06-06 per Dais)
New cron `anicca-account-health-daily` (06:00 JST). Reads existing `~/.openclaw/state/content-metrics/zero-view-streaks.json` (threshold 100 views / streak 3 days / lookback 7d — already populated by `aniccaai-dashboard-refresh`). For each account with streak ≥ 3:
1. camofox opens the live TikTok/IG/YT → classify cause: shadowban / login-expired / content-quality / hard-zero.
2. Auto-act:
   - shadowban → spawn warmup mini-cron (manual-style posts + comment replies) AND Slack pepper Dais with "create new <kind> account" + signup URL + ready Gmail alias.
   - login-expired → Postiz re-connect via camofox + Google login env (no Dais).
   - content-quality → bump the source skill's hook-generation variation (force LLM regen with new pattern jsonl pick).
   - hard-zero ≥ 7d → disable the offending cron + Slack report.
3. Goal: Dais never monitors. Anicca pepper only when a NEW account must be physically created.

(Part G is large → build via full SDD: spec→plan→TDD→verify.)

---

## Part H — 4 new accounts (mail)

AgentMail free tier is at inbox limit → use **Gmail aliases** (Dais authorized "alias, whatever"). 2FA auto-read via Gmail MCP. Ready immediately, no provisioning:
- iam EN → `keiodaisuke+iamen@gmail.com`
- iam JA → `keiodaisuke+iamja@gmail.com`
- larry EN → `keiodaisuke+larryen@gmail.com`
- larry JA → `keiodaisuke+larryja@gmail.com`
Dais signs up TikTok with these; Anicca reads the 2FA code each time and relays it. Scale toward ~10 accounts after.

---

## Rollout order (apply on `go`, verify each before next)

1. **A** — (deferred) bundle subtitle+keywords into 1.9.3; applied only when 1.9.2 distributes.
2. **B1** — Larry JA routing fix (highest impact, lowest risk). camofox verify.
3. **D** — disable JA slideshow contamination. 
4. **B3** — static human bg (EN+JA).
5. **B2** — 3×/day.
6. **E** — honne fresh + honne-EN repair.
7. **C + F** — new EN-videos TT + reelclaw EN widget re-enable + EN isolation.
8. **G** — quality gate (separate SDD spec/plan/TDD).
9. **H** — already usable; used during TikTok signups.

## Verification (per item)
- Each cron change: `openclaw cron` fire once → read run log for real POST_ID → **camofox open the live account** and eyeball the post (right account, text fits, hook fresh). Postiz "PUBLISHED" alone is insufficient (HARD RULE #16/#17).
- Subtitle/keywords: `asc metadata` diff + App Store Connect render.
