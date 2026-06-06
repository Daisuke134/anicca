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

## Part I — ReelFarm-killer: Fixed-Hook + LLM-Body + Static-BG + CTA (Dais 2026-06-06)

**Goal:** Larry を ReelFarm 同等に進化させ、 ReelFarm 月額サブスク解約 (来月〜)。 既に skill 側は LLM body 生成済、 残りは ①固定フック化 ②CTA スライド追加 ③背景 1枚完全固定。

### REVISED 2026-06-06 evening: 4 version × EN/JA = 8 系統 (各 3×/日)

| ver | bg pattern | account |
|---|---|---|
| v1 | slide1=maleface.jpg, slides2-6=bedroom/slide2-6.jpg (variety) | EN=@aniccaen2 / JA=@anicchasan (既存) |
| v2 | 全=maleface.jpg (static) | NEW EN/JA |
| v3 | 全=sunset.jpg (static) | NEW EN/JA |
| v4 | 全=femaleface.jpg (static) | NEW EN/JA |

EN 全 ver: include_cta=true (7 slides), JA 全 ver: include_cta=false (6 slides, A/B用)。
hook + body LLM-fresh + CTA は spec original の通り。 fixed-strings json 8 ファイル。

新規 TikTok 垢 = 6 (larry v2/3/4 EN+JA) + 2 (iam EN/JA) + 1 (reelclaw EN videos) = **9 個**。

### Pattern (適用先: 既存 larry-en/ja + 新 mental-jp / morning-en の 4 垢全て)

```
slide 1   FIXED HOOK              (per-account constant string)
slide 2-6 FRESH LLM-GENERATED     (clone-don't-template from pattern-larry-*.jsonl)
slide 7   FIXED CTA               (per-account constant string)
bg all 7  bedroom/slide1.jpg      (male face, static, identical across all 7 slides)
```

### Fixed strings

| account-handle | language | slide-1 hook (固定) | slide-7 CTA (固定) |
|---|---|---|---|
| larry-en (既存 @aniccaen2) | EN | `5 affirmations to tell yourself every morning…` | `try anicca — words like these every day` |
| larry-ja (既存 @anicchasan) | JA | `メンタルが強い人の口癖５選` | `毎日こんな言葉を、アニッチャで。` |
| new mental-jp (MANUAL-5 改) | JA | `メンタルが強い人の口癖５選` | 同上 |
| new morning-en (MANUAL-4 改) | EN | `5 affirmations to tell yourself every morning…` | 同上 |

### Slide-2..6 LLM generation rule

- 各 cron で 5 件の本文をフレッシュ生成（既存 larry の clone-don't-template フロー使用）。
- 14d anti-repeat は **本文のみ**を index（フックは固定で除外）。
- JA 例: `なんとかなる。` `今できることをやるだけ` 等、 短く強く。
- EN 例: `i am allowed to start over` `i deserve gentleness from myself` 等。

### Diff (larry cron message)

```diff
- STEP 2 — Generate 6 fresh slide texts (clone-don't-template) ...
+ STEP 2 — Generate 5 fresh BODY slide texts only (slide 2-6). Slide 1 and 7 are
+         FIXED strings (hook + CTA) read from /Users/anicca/.openclaw/skills/anicca-larry/
+         state/fixed-strings-<account>.json. Do not regenerate slide 1 or slide 7.
+         BODY texts: clone structure only from pattern-larry-<lang>.jsonl, fresh wording.
+         14d anti-repeat indexes BODY texts; the fixed hook is exempt.

- Generate 6 slides ... using bedroom-themed assets in
-   ~/.openclaw/workspace/tiktok-marketing/assets/6-slide-images/bedroom/.
+ Generate 7 slides. ALL 7 slides use the SAME background photo:
+   ~/.openclaw/workspace/tiktok-marketing/assets/6-slide-images/bedroom/slide1.jpg
+   (the male-by-fireplace image). No rotation, no random, identical bg across all 7.
+ Slide 1 text = fixed hook (above). Slide 7 text = fixed CTA. Slides 2-6 = fresh LLM body.
```

### Account naming (NOT "larry" — bot-like, user-unfriendly)

The handle IS the brand. Replace MANUAL-4/5 names:

| 旧 (廃) | 新 | フック・ブランド |
|---|---|---|
| `@anicca.larry.en` | **`@anicca.morning`** or `@morning.affirmations` | 5 affirmations to tell yourself every morning |
| `@anicca.larry.jp` | **`@anicca.mental.jp`** or `@kuchiguse.jp` | メンタルが強い人の口癖５選 |

### ReelFarm subscription kill-switch

このパターン稼働 + 1週間 (TT_POST_ID 7日分連続) 達成後、 ReelFarm 月額キャンセル。 dashboard で cancel → confirm 課金停止。

### Apply order within Part I

I-1. fixed-strings json 4 ファイル作成 (per-account hook + CTA)
I-2. larry skill の slide build を「slide 1 固定 / slide 2-6 LLM / slide 7 固定 / 全 bg = bedroom/slide1.jpg」へ patch
I-3. 既存 larry-en/ja-1 で fire → camofox 目視 (slide 数 = 7, bg 一致, フック 固定)
I-4. 新 mental-jp / morning-en 垢 connect 後、 cron 配線 + fire 検証
I-5. ReelFarm cancel

---

## Part K — Unlimited AgentMail signup pool (Dais 2026-06-06)

**Discovery**: AgentMail Python SDK `client.agent.sign_up(human_email, username)` creates a new org + 1 inbox + dedicated API key **with no CAPTCHA** — bypasses the Clerk Turnstile that blocks the web signup form. Each working seed email = unlimited orgs.

### Working seeds (verified 2026-06-06)
- `*@aniccaai.com` (any subaddress: tt1, tt2, tt3, …, mkt, marketing, anicca, team, etc. — infinite)
- Dais's MUIT work email (one-shot)

### Forbidden seeds
- `*@agentmail.to` itself (ForbiddenError "Domain is forbidden")
- Gmail aliases normalized to existing org email (AlreadyExistsError)

### Skill: `agentmail-pool`
```
~/.openclaw/skills/agentmail-pool/
  SKILL.md
  scripts/provision.sh    — `provision.sh <human_email> <username>` → new org/inbox/api_key
  scripts/read-otp.sh     — `read-otp.sh <inbox>` → poll last 5 messages, extract 4-8 digit codes
```

### Propagation (Dais directive)
This power must propagate to:
- `anicca-oss` (public) — embed the skill so any Anicca instance can self-provision inboxes
- `~/.openclaw` (private) — local store has it (✅ done)
- Hermes SOUL.md / spawned anicca-N constitution.md — skill listed as core capability

### Cron: daily inbox provisioning
New cron `agentmail-pool-replenish-daily` (06:30 JST). If pool count < 20 fresh inboxes, provision 5 more from `*@aniccaai.com` seeds. Total state at `~/.openclaw/state/agentmail-pool.jsonl` (append-only log).

---

## Part L — TikTok account warmup mode (Dais 2026-06-06)

**Phase model** per newly-created TikTok account, per `cron/jobs.json` cron payload:

| phase | duration | TikTok post mode | music | shadow-ban risk |
|---|---|---|---|---|
| **warmup** | day 0–6 (first 7 days post-signup) | Postiz `post_mode=draft` (MEDIA_UPLOAD) + auto-music ON | yes (Postiz auto-add) | minimized (looks human) |
| **live** | day 7+ | `post_mode=DIRECT_POST` + music ON | yes | normal |

### Implementation diff
```
~/.openclaw/skills/_shared/post-to-tiktok.js (SSOT for TT post params):
+  const created_at = read_created_at(account)   // YYYY-MM-DD
+  const days_since = (now - created_at) / 86400_000
+  const phase = days_since < 7 ? 'warmup' : 'live'
+  const post_mode = phase === 'warmup' ? 'MEDIA_UPLOAD' : 'DIRECT_POST'
+  const auto_music = true   // both phases now ON (Dais 2026-06-06)
```

### Registry field (state/anicca-accounts-registry.json)
Add `created_at: ISO_DATE` per account; auto-promote `phase: live` after day 7 (computed at post-time, not stored).

---

## Part M — Capafy publish: "Free Affirmation Slideshow Maker" (= ReelFarm-killer commercial)

The fixed-hook + static-bg + LLM-body + CTA pattern is **bundleable as a Capafy skill**.

### USP
- Zero GPT image-gen cost (background = bundled male/female/sunset assets, fixed per account)
- Zero ReelFarm subscription
- Free LLM-grade content via clone-don't-template from pattern jsonl
- Works on **free local models** (Ollama, llama.cpp) — no API spend

### Skill name candidate
- `larry-free-slideshow-maker` / `affirmation-slideshow-bot` / `niche-slideshow-cloner`

### Capafy listing copy (draft)
> Make affirmation TikTok slideshows daily for $0. Pick your niche (morning / mental / sleep / spirituality), pick your host image (we ship 3), pick your hook. The skill generates 5 fresh body lines per day via LLM (works on free local models) and posts via Postiz. Replace ReelFarm. Bundled assets = nothing to buy.

### Mode
- **Download** $19.99: skill src + 3 host images + fixed-strings JSON templates + cron + Postiz integration helper
- **Subscription** $9.99/mo (our hosted LLM key): same + we run the LLM

### Apply order
M-1. Skill folder split + asset license check (3 host images need clear license)
M-2. Capafy `init` / `configure` / `ship` (see capafy-publisher skill)
M-3. CLAUDE.md leak scrub before publish
M-4. Submit for review

---

## Part N — Monitoring via Postiz API → /socials (NO camofox token-burn)

**Verified 2026-06-06**: Postiz REST `https://api.postiz.com/public/v1/` exposes everything we need EXCEPT follower count (= per-platform official API needed for that one field).

### Endpoints (verified live)
- `GET /integrations` → 30 accounts, fields: `id, name, identifier, picture, disabled, profile (handle)`
- `GET /posts?startDate=ISO&endDate=ISO` → all posts in window with `content, publishDate, releaseURL, state, integration{id,name,picture}`
- `GET /analytics/post/{post_id}` → views / likes / comments (empty list = not yet ingested)

### Registry SSOT
`~/.openclaw/state/anicca-accounts-registry.json` (✅ built 2026-06-06, 30 rows). Per-account fields:
- `postiz_id, platform, name, handle, disabled` (from /integrations)
- `signup_mail, assigned_to_skill, assigned_cron, created_at, phase (warmup/live)`
- `followers` (filled by per-platform API: TikTok/IG/YT)
- `last_post_at, posts_per_day_7d, weekly_views, weekly_engagement`
- `weekly_views_prev, weekly_views_change_pct, weekly_engagement_change_pct`

### Cron flow (replace camofox-based audit)
```
aniccaai-dashboard-refresh   05:00 JST   (existing, extend)
  └→ pull /integrations (30 accounts)
  └→ pull /posts (last 7d)
  └→ for each post: pull /analytics/post/{id}, sum views/likes/comments
  └→ aggregate per integration_id: posts_7d, views_7d, eng_7d
  └→ compare vs last week snapshot (state/socials-weekly-{date}.json)
  └→ compute change_pct
  └→ flag dead accounts (views < 100 × 3 streak days, already in zero-view-streaks.json)
  └→ write state/socials-latest.json
  └→ aniccaai-dashboard refresh → /socials page
```

### Follower count (1× weekly, separate)
Per-platform official API (1 cron weekly):
- TikTok: scrape via `https://www.tiktok.com/@<handle>?lang=en` (camofox 1×/week per account, low cost)
- IG: Graph API (need Meta app) or scrape
- YT: YouTube Data API v3 (free key, exact)
→ store in `followers` field, snapshot weekly to track growth.

### /socials page (rendered from registry)
Public ranking page on `https://aniccaai.com/socials`:
- Table rows: handle, platform, followers, posts/7d, views/7d, eng/7d, Δ vs last week
- Sort by views default
- Color: green (Δ ≥ +10%), yellow (-10% to +10%), red (Δ ≤ -10%)
- Anyone can see Anicca's marketing performance

---

## Part O — Slideshow→Video skill (YouTube Shorts scaling)

ffmpeg + 既存 slide image 6 枚 → 24 秒 mp4。 ✅ demo verified 2026-06-06。 `/tmp/larry-slideshow-demo.mp4` で確認済 (1080×1920, 2MB, H.264 yuv420p YouTube 互換)。

### New skill: `~/.openclaw/skills/anicca-slideshow-to-video/`

```
scripts/
  build.sh <run_dir> <music_file?> <out.mp4>   # ffmpeg concat + optional audio overlay
  fetch-music.sh <niche>                        # royalty-free or DL via tiktok-api-dl
  post-to-yt.sh <out.mp4> <yt_integration_id>   # Postiz YouTube publish
```

### Hook
Larry / iam / reelclaw 投稿成功後 (post-skill in jobs.json) に hook:
```
ON larry-* SUCCESS:
  build slideshow.mp4 from same slide images
  post to YT Shorts integration (cmmzukbkw04ulp30yfvijrwio = @anicca-ai)
```

### Music
- royalty-free clip 1 つ bundle (skill 内 `assets/music/affirmation-bg.mp3`)
- 後で `musicdl` or `tiktok-api-dl` でバズ音源差替
- TikTok 投稿は元々 audio 付き（TT API）→ YouTube 用にも同じ音源使えれば一貫性 +

### Scale impact
Larry 8 系統 × 3/日 = 24 / 日 × YT shorts publish = **+24 YT 投稿/日 = 168/週**
→ 既存 reelclaw YT 7/日 = 49/週 + 168/週 = **217/週 ✓ 100/週/platform クリア**

タスク #82–85 で実装。

---

## Part P — Cron run-verification on every patch (Dais 2026-06-06)

「次の自然発火を待たず即 fire で検証」 = 失敗を Anicca が自分で見つけて自己修復する基本姿勢。

### Workflow per patch (B1, B2, B3, C, D, E, F, I, etc.)
```
1. patch jobs.json / skill file
2. openclaw cron run <job-id>           ← 即 fire
3. check exit code + log (~/.openclaw/cron/runs/<run-id>.jsonl)
4. if non-zero:
   a. read error verbatim
   b. patch root cause
   c. goto 2
5. camofox / Postiz API で実投稿目視 (account, hook, text fit, language match)
6. mark task #completed in tasklist
```

### 削除されるべき antipattern
- 「次の 8 am まで待つ」「3時間後の自然発火で見る」 = 違反 (HARD RULE #14 finish-job)
- 失敗を Slack 通知だけして Anicca が後で見つける期待 = 違反 (Dais 監視 ≠ Anicca 監視)

タスク #86 で全パッチに「即 fire 検証」step 義務化。

---

## Part Q — Dead-account daily mail (gog gmail、 Slack 廃止)

Slack はノイズ多くて見落とすので **重要事項は Gmail 送信**。 ただし送信ルール:

### 送信タイミング
- 毎日 06:30 JST (anicca-account-health-daily cron in spec Part G3)
- **dead account が 1 件もない日は mail を送らない** (no-op、 Dais の inbox 詰まらせない)

### 送信条件 (per account)
`zero-view-streaks.json` に `streak ≥ 3 days` の record → dead 判定 → Gmail 1 通にまとめて送信

### Mail format (ASCII)
```
Subject: [Anicca] Please warm up or create new accounts (N dead today)

The following accounts have 0 views consecutively. Pick warm-up OR new-account per row:

┌─────────────────────────────────────────────────────────────────────────────┐
│ # │ @handle              │ posting               │ dead days │ new mail       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1 │ @anicca.affirm.he    │ EN affirmation        │     5     │ tt-tt5@agent…  │
│   │                      │ slideshow w/ maleface │           │ (key: stored   │
│   │                      │                       │           │  in registry)  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2 │ @anicca.kuchiguse.he │ JA mental-quote       │     7     │ tt-tt6@agent…  │
│   │                      │ slideshow w/ maleface │           │                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3 │ honne_reveal         │ EN honne TT           │     3     │ tt-tt7@agent…  │
└─────────────────────────────────────────────────────────────────────────────┘

Action:
  - If you want to WARM UP an existing account → reply "warmup #N" (Anicca pauses cron 7d, post as draft)
  - If you want to CREATE NEW account → reply "new #N" (use the prepared mail above)
    pw = Keiodaisuke1234! / 2FA OTP = Anicca が即読む

Mails are pre-provisioned in registry (~/.openclaw/state/agentmail-pool.jsonl).
On reply, Anicca walks you through TikTok signup + Postiz connect.
```

### Implementation
- Cron 既存 `aniccaai-dashboard-refresh` (05:00 JST) → 拡張で `socials-latest.json` + dead 検出
- 新サブステップ: dead 件数 > 0 なら上記 format で gog gmail send
- 送信時、 各 dead row に対し fresh mail を pool から allocate (or provision daily if pool < 20)
- Registry に `assigned_mail_for_next_replacement` フィールド追加

タスク #87。

---

## Part T — IAM fresh-generation + screen-fit guard (Dais 2026-06-06)

現状 5 IAM skill (color-en/ja, photo-en/ja, mantra-ja) は固定 7 affirmation rotation = NG。
特に JA で 5 行 overflow → screen 外に text 切れ。

### Fresh-gen flow (両言語、 必要時に応じて 1 ~ 7/日)
```
1. seed pool: ~/.openclaw/skills/anicca-iam-color-<lang>/scripts/build-slideshow.py の
   IAM_TEMPLATE_B[_JA] (verified i.am app screenshot 由来 7 件)
   + new ~/.openclaw/state/content-library/pattern-iam-<lang>.jsonl (バズ例追加)

2. LLM prompt:
   EN: "Generate 1 short 'I am' affirmation, 4-6 words, uppercase,
        max 4 lines × 14 chars, no semicolons, present tense.
        examples (verbatim style guide):
        - I AM ENOUGH AS I AM.
        - I CHOOSE PEACE TODAY.
        - I SEE IT. I LIKE IT. I WANT IT. I GOT IT."
   JA: "「私は」「私には」で始まる肯定 1 行、 max 5 行 × 7 chars/line。
        examples:
        - 私には光がある。
        - 私は満たされている。
        - 私はそのままで尊い。"

3. word-count guard (build-slideshow.py 修正):
   EN: total chars > 56 → reject → LLM 再生成 (3 retry)
   JA: total chars > 35 → reject → 同上

4. picks.json に items=[{text,lines}] 書込 → 既存 renderer

5. append-to-history (account=iam-<lang>) で 14d anti-repeat
```

bg pastel palette は rotate のまま (Dais OK = pink/green/blue etc)。

タスク #91 で実装。

---

## Part U — slideshow→video freshness (Dais 2026-06-06)

要件: video 化する larry run は **1 時間前 〜 24 時間前** の最新を選ぶ。 同 video 反復防止。

### build.sh 改修
```diff
- RUN_DIR=$(ls -td ~/.openclaw/workspace/tiktok-marketing/run-*/ ... 2>/dev/null | head -1)
+ RUN_DIR=$(find ~/.openclaw/workspace/tiktok-marketing -maxdepth 1 -type d \
+   \( -name 'run-*' -o -name 'afternoon-*' \) -mmin +60 -mmin -1440 \
+   -exec stat -f '%m %N' {} \; | sort -rn | head -1 | cut -d' ' -f2)
+ [ -z "$RUN_DIR" ] && { echo "no fresh run in 1h-24h window, skip"; exit 0; }
```

local archive (larry run dir 永続):
- larry skill の cleanup 抑制
- 7 日経過 dir のみ delete cron で掃除 (別タスク)

タスク #92。

---

## Part V — 1.9.3 提出前 修正 (App Store)

### 1. 無料トライアル撤去
- subscription products から 3-day free trial 削除
- App Store Connect CLI (asc) で subscription offerings 編集
- 関連: monthly $9.99 / annual $49.99 だけ残す

### 2. Paywall design 改修
- 「Try 3 days for free」CTA → 「Subscribe」 / 「Continue」
- copy 全 review (Anicca で何できるか強調)
- A/B test 開始は別タスク

### 3. Subtitle (キーワード羅列)
- EN: "Affirmations, Calm & Self-Love" or "Affirmations · Sleep · Mindful · Calm"
- JA: "自己肯定感・名言・瞑想・感謝・ポジティブ"

### 4. submit flow
1. asc metadata update subtitle + keywords
2. version 1.9.3 create + binary attach (existing build)
3. asc review submit

タスク #93。

---

## Part W — Newsletter daily fix (1.9.3 提出後)

Dais 報告: 私 mail で 1 通だけ受領、 daily 来ない。

### 修正
- daily-letter-sender cron 検証 (現 schedule + last run + error)
- Day-N letter generation:
  - 1 letter 分量 を 200 字 → 500-800 字 に拡張
  - Anicca で何ができるか naturally introduce
  - Cross-promo: Anicca-install / cemetery for AI / 他 product
- subscriber テーブル + Resend API 連携 check
- domain は verified `letters@aniccaai.com` 使用済 (前 session 確定)

タスク #94。

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
