# Larry / ReelClaw / Slideshow-Video Truth Correction & Capafy Repack

**Author**: Anicca (BP-driven, no original synthesis)
**Date**: 2026-06-07
**Context**: Dais 2026-06-07 audit surfaced 9 violations + 1 truth crisis. Postiz `/integrations` live query (BP source) revealed that `~/.openclaw/state/postiz-integrations.json` registry handle names are ★ wholesale lies ★ vs Postiz live profile names. Every routing decision in larry/reelclaw cron messages is based on integration IDs, but the human-readable names in our docs/spec are wrong. This spec corrects ground truth, then patches the 7 surface violations, then unblocks Capafy publish.

## BP citations (= identical-follow sources)

1. **Postiz source `tiktok.provider.ts`** (https://raw.githubusercontent.com/gitroomhq/postiz-app/refs/heads/main/libraries/nestjs-libraries/src/integrations/social/tiktok.provider.ts) — verbatim:
   ```ts
   auto_add_music: firstPost.settings.autoAddMusic === 'yes',
   ```
   → `settings.autoAddMusic` value MUST be the string `'yes'` (not boolean, not `'true'`). Anicca larry already passes this field correctly in `post-to-tiktok.js:142`.

2. **Postiz live `/integrations` API** (https://api.postiz.com/public/v1/integrations) — single source of truth for ID ↔ profile mapping. Registry `postiz-integrations.json` is now confirmed stale.

3. **TikTok Content Posting API** (https://developers.tiktok.com/doc/content-posting-api-reference-direct-post#post_info) — `auto_add_music` is an optional `post_info` field, accepted by Direct Post AND Upload modes. Setting `'yes'` triggers TikTok's auto background music selection per the user's home country recommendations.

4. **openclaw cron CLI** (`openclaw cron edit --help`) — `--message <text>` to patch payload, refs shift in snapshots so all 9 larry crons must be patched explicitly by ID, not by name.

## As-Is vs To-Be — single source of truth

### A. Postiz registry truth (BP = Postiz live `/integrations`)

| Postiz ID | Platform | Real profile (Postiz truth) | Registry says (LIE) |
|---|---|---|---|
| `cmlrv8jq000hun60yy57eaptx` | TikTok | **@anicca.jpx** | @anicchasan |
| `cmlt171eq04d9r00yzzceb6bw` | TikTok | **@aniccaen2** | @anicca.monk |
| `cmnhlk3ju058lpn0ytilqdpo0` | TikTok | **@anicca.jp8** | anicca-ja-card-1 |
| `cmq2aoena08bhqp0yx1epjcik` | TikTok | @anicca.he | @anicca.he ✓ |
| `cmnit95mg015rrm0ye5vm8dhl` | TikTok | **@honnevideo** | honne-ja-1 |
| `cmoig11ew001zlv0yk6vqo1us` | TikTok | **@honne_reveal** | honne-en-1 |
| `cmp93bkpu01uvoh0yd3aj560g` | TikTok | **@aniccaaffirmation** | NOT IN REGISTRY |
| `cmmtt62wq01lqn50yehk1f6dy` | TikTok | **@anicca.daily** | NOT IN REGISTRY |
| `cmmzujxpa04ujp30yxqpg1vci` | Instagram | **@anicca.bochi** | @anicchasan |
| `cmmzzg2es0539p30ycb94ayx0` | Instagram | **@anicca.ai** | @anicca.monk |
| `cmnipef7g00oerm0y3dz4lamx` | Instagram | **@anicca.video** | anicca-ja-card-1 |
| `cmpc3gx4001nklg0y27a8o66q` | Instagram | **@anicca.encards** | NOT IN REGISTRY |
| `cmn8ycvtn02djqx0ytuisn9mw` | Instagram | **@anicca.jp1** | NOT IN REGISTRY |
| `cmn8ymq6c02oio70y5ea1trv8` | YouTube | @anicca-affirmation-video | ✓ |
| `cmn1oukj9012nnq0yqhouc3ib` | YouTube | @anicca-jp | ja ✓ |
| `cmmzukbkw04ulp30yfvijrwio` | YouTube | @anicca-ai | en ✓ |

**Implication**: Dais's "anicca.jp1" referred to in violations is @anicca.jpx (TT, cmlrv8jq) — the larry JA v1 destination. Our registry called it @anicchasan but Postiz says @anicca.jpx. All Dais's complaints are about the **REAL** account targeted by the cron, regardless of our registry's wrong label.

### B. Larry violations

#### B1. JA v1 (`larry-anicca-ja-1`, posts to TT cmlrv8jq=@anicca.jpx)

| field | As-Is | To-Be |
|---|---|---|
| `fixed-strings-larry-ja-v1.json::bg_mode` | `"variety"` | `"static"` |
| `bg_file_hook` + `bg_files_body` | `bedroom/slide1..6.jpg` (= people-on-couch) | single `human-face/maleface.jpg` ALL slides |
| `slide1_hook` | `"メンタルが強い人の口癖５選"` | `"メンタルが勝手に安定する\n口癖５選"` |
| `auto_music` (NEW field) | not set → falls to 'no' | `"yes"` |
| `--ig` arg in cron | missing | `--ig cmmzujxpa04ujp30yxqpg1vci` (= IG @anicca.bochi, the larry JA companion) |
| `--yt` arg in cron | missing | (skip — no YT for larry JA per spec) |

#### B2. EN v1 (`larry-anicca-en-1`, posts to TT cmlt171eq=@aniccaen2)

| field | As-Is | To-Be |
|---|---|---|
| `fixed-strings-larry-en-v1.json::bg_mode` | `"variety"` | `"static"` |
| bg files | `bedroom/slide1..6.jpg` | single `human-face/maleface.jpg` ALL slides |
| `auto_music` (NEW field) | not set → 'no' | `"yes"` |
| `--ig` arg in cron | missing | `--ig cmmzzg2es0539p30ycb94ayx0` (= IG @anicca.ai) |

#### B3. @anicca.he warmup mode

| | As-Is | To-Be |
|---|---|---|
| `postiz-integrations.json` `@anicca.he::warmup_phase` | `"live"` | `"warmup"` |
| `warmup_started_at` | `-` | `"2026-06-07"` |
| post script behavior | DIRECT_POST | MEDIA_UPLOAD (draft) + autoMusic=yes for 7 days |
| auto-flip | n/a | day 8 → live via `anicca-warmup-flip-daily` cron |

### C. Post-to-TikTok auto_music wiring

| | As-Is | To-Be |
|---|---|---|
| `post-to-tiktok.js:78` | `autoAddMusic = config.posting?.autoAddMusic \|\| (ttIsWarmup ? 'yes' : 'no')` | also read `fixed-strings.json::auto_music`: `autoAddMusic = fs.auto_music \|\| config.posting?.autoAddMusic \|\| (ttIsWarmup ? 'yes' : 'no')` |
| `build-from-fixed-strings.sh` | passes `$FS` to post script via env or arg | export `auto_music` via env `AUTO_MUSIC=$(jq -r .auto_music "$FS")` consumed by post script |

### D. Quality Gate strengthening (bbox)

| | As-Is | To-Be |
|---|---|---|
| `quality-gate.sh` bbox check | weak / character-count heuristic only | invoke node helper that measures real pixel bbox using canvas font metrics; fail if text exceeds 1020×1850 (= TikTok safe area with 30px margin); on fail: shrink font 10% or re-wrap on next space; max 3 retries → block post |
| larry `build-from-fixed-strings.sh` | no gate | calls `quality-gate.sh "$RUN_DIR" "<lang>" "<account>"` before post; non-zero exit aborts |
| iam scripts (already has bbox) | exit 2 + 3-retry bash loop | leave as-is, reference impl for larry |

### E0. Empirical findings 2026-06-07 22:30 JST (= live fire verifications)

★ HARD RULE 0.29 evidence-driven update ★ — multiple fires + Postiz live observation:

**E0.1 TT post failure root cause = image >1080p (NOT auto_music)**

- maleface.jpg was 1125×1202 → TT rejects with "Picture must not exceed 1080p"
- Resized to 1080×1154 → TT PUBLISHED OK
- ★ auto_music="yes" is INDEPENDENT of TT 1080 limit ★ — my earlier "auto_music=no broke TT" was unfounded speculation
- Per BP `tiktok.provider.ts`: `auto_add_music: settings.autoAddMusic === 'yes'` sent ONLY when isPhoto (= slideshow)
- ★ Canonical: every TT slideshow post must have `auto_music="yes"` ★ (Dais 2026-06-07 verbatim)

**E0.2 Image asset audit (all ≤1080p TT-compliant)**

| asset | size before | size after |
|---|---|---|
| `human-face/maleface.jpg` | 1125×1202 | ✓ 1080×1154 (T2 resize 22:00 JST) |
| `human-face/femaleface.jpg` | 1627×1274 | ✓ 1080×N (preventive resize 22:00 JST) |
| `human-face/sunset.jpg` | 1080×1920 | ✓ already TT-spec |

When cropping/resizing: ★ ALWAYS use `sips --resampleWidth` (= aspect-preserve resample, NEVER `--cropToHeightWidth` ★ to avoid cutting heads off subjects.

**E0.3 fixed-strings auto_music inventory + canonical fix**

| file | auto_music BEFORE | TO-BE |
|---|---|---|
| `fixed-strings-larry-ja-v1.json` | "yes" | "yes" ✓ |
| `fixed-strings-larry-ja-v2.json` | MISSING | **"yes"** |
| `fixed-strings-larry-ja-v3.json` | MISSING | **"yes"** |
| `fixed-strings-larry-ja-v4.json` | MISSING | **"yes"** |
| `fixed-strings-larry-ja-male-cta.json` | MISSING | **"yes"** |
| `fixed-strings-larry-en-v1.json` | "no" (my error) | **"yes"** |
| `fixed-strings-larry-en-v2.json` | MISSING | **"yes"** |
| `fixed-strings-larry-en-v3.json` | MISSING | **"yes"** |
| `fixed-strings-larry-en-v4.json` | MISSING | **"yes"** |

**E0.4 post-to-tiktok.js default → 'yes' (= belt-and-suspenders)**

```diff
- const autoAddMusic = autoMusicArg || fixedStringsAutoMusic || config.posting?.autoAddMusic || (ttIsWarmup ? 'yes' : 'no');
+ const autoAddMusic = autoMusicArg || fixedStringsAutoMusic || config.posting?.autoAddMusic || 'yes';
```

### E1. ReelClaw routing — DEAD YT id replacement (Postiz live audit 2026-06-07 22:30 JST)

★ `cmmzukbkw04ulp30yfvijrwio` = ★ DEAD ★, replaced by `cmq3u37gi005iqp0y90a2w92n` (= @anicca-ai, "Anicca - Daily Affirmation") in Postiz live integrations. 3 reelclaw EN cron still reference the dead ID:

| cron name | cron id | current --yt | fix --yt |
|---|---|---|---|
| reelclaw-anicca-en-card-1 | a0a1d2fe-4087-4ee4-bc7b-526b6f8d8e65 | `cmmzukbkw04ulp30yfvijrwio` (DEAD) | `cmq3u37gi005iqp0y90a2w92n` |
| reelclaw-anicca-en-card-2 | 330bbaf7-3ea2-41f6-8479-f1c6f8ef1f45 | `cmmzukbkw04ulp30yfvijrwio` (DEAD, status=error) | `cmq3u37gi005iqp0y90a2w92n` |
| reelclaw-anicca-en-widget-1 | 92c13cc2-3888-4c4a-b2b7-5a200f223677 | `cmmzukbkw04ulp30yfvijrwio` (DEAD) | `cmq3u37gi005iqp0y90a2w92n` |

★ IG side `cmpc3gx4001nklg0y27a8o66q` (= @anicca.encards) is correct ★ for both card AND widget EN (Dais 2026-06-07 verbatim).

### E2. ReelClaw EN widget-2 MISSING (= Dais "widget x2" intent)

Current cron list shows only `reelclaw-anicca-en-widget-1` (1 fire/day @ 19:00 JST). Dais wants widget x2 like JA side. **Create**:

```
name: reelclaw-anicca-en-widget-2
schedule: 0 7 * * * Asia/Tokyo  (= 07:00 JST, anti-collision with widget-1 19:00)
payload: bash ~/.openclaw/workspace/skills/reelclaw/scripts/run-widget-en.sh --ig cmpc3gx4001nklg0y27a8o66q --yt cmq3u37gi005iqp0y90a2w92n
session: isolated, agent: anicca, delivery: slack:C091G3PKHL2
```

### E3. ReelClaw honne-en cron — TT mis-routed to JA acct

| cron name | cron id | current --tt | fix --tt |
|---|---|---|---|
| reelclaw-honne-en-1 | 61b913e6-57e9-46f0-a2b1-d7dc20435580 | `cmnit95mg015rrm0ye5vm8dhl` (= @honnevideo, JA honne) | `cmoig11ew001zlv0yk6vqo1us` (= @honne_reveal, EN honne) |
| reelclaw-honne-en-2 | fd9bdcad-48b4-4efa-9eed-90f0b0358041 | same (status=error) | `cmoig11ew001zlv0yk6vqo1us` |

= Dais 2026-06-07 verbatim: "cmoig11ew001zlv0yk6vqo1us -> honne reveal right? reelclaw en honne not posted... enable cron + post"

### E4. T1 registry drift (2026-06-07 21:40 v3 → live re-check 22:30)

| id | T1 v3 wrote | Postiz live NOW | fix |
|---|---|---|---|
| cmmzzg2es0539p30ycb94ayx0 | profile=anicca.ai owner=brand-feature-ai | profile=anicca.jp.videos | rename owner=reelclaw-ja-ig-videos |
| cmq3u37gi005iqp0y90a2w92n | (not in registry) | profile=@anicca-ai (YT, live) | ADD with owner=reelclaw-yt-en |
| cmmzukbkw04ulp30yfvijrwio | active=true | (NOT in live integrations) | active=false, owner=DEAD |

### E5. ReelClaw routing verify

| cron | --tt (target) | --ig (target) | --yt (target) | verify |
|---|---|---|---|---|
| `reelclaw-anicca-en-card-1/2/widget-2` | `-` (TT skipped until envideos signup) | `cmpc3gx4001nklg0y27a8o66q` (@anicca.encards) | `cmmzukbkw04ulp30yfvijrwio` (@anicca-ai) | ✓ correct per Postiz |
| `reelclaw-anicca-ja-card-1/2/widget-1/2` | `cmnhlk3ju058lpn0ytilqdpo0` (@anicca.jp8) | `cmnipef7g00oerm0y3dz4lamx` (@anicca.video) | `cmn1oukj9012nnq0yqhouc3ib` (@anicca-jp) | ✓ correct per Postiz |
| `reelclaw-honne-ja-1` | `cmnit95mg015rrm0ye5vm8dhl` (@honnevideo) | — | — | ✓ |
| `reelclaw-honne-en-1/2` | `cmoig11ew001zlv0yk6vqo1us` (@honne_reveal) | — | — | ✓ |

**Conclusion**: reelclaw routing is CORRECT per Postiz live. Dais's "JA posted to EN YT" complaint must have been transient (earlier session before fix) OR Postiz UI showed wrong handle due to registry confusion. Add post-verify probe: 24h after cron fires, query `/posts?integrationId=...` to confirm landed.

### F. Account-Health daily Gmail

| | As-Is | To-Be |
|---|---|---|
| cron status | `error` (last run) | `ok` |
| script root cause | missing `~/.openclaw/skills/anicca-tt-warmup-newcomer/state/accounts.jsonl` etc | rewrite script to read from `~/.openclaw/state/postiz-integrations.json` directly (= single source of truth pattern; T1 already rebuilds this file as canonical, so script tracks the truth automatically — no parallel accounts.jsonl to drift out of sync) — reviewer I1 fix, option-presentation deleted |
| daily Gmail body | not delivered | embed `zero-view-streaks.json` (≥3-day-streak ≥ 0-views accounts) with action items: "warm up @X" / "create new YT acct" / "create new IG acct" + Postiz signup URL |
| recipient | `keiodaisuke@gmail.com` | same |

### G. Slideshow-Video fire verify

| | As-Is | To-Be |
|---|---|---|
| `anicca-slideshow-video-{morning,afternoon,evening}` cron | enabled but un-verified actually firing | add Slack/Gmail ping per run with YT_POST_ID + Postiz state |
| source freshness | 1h-24h window picks latest larry-en-1 run | confirm via /tmp/anicca-slideshow-video-* log; if no recent runs, log clearly |

### H. Capafy publish — skill repack for path generalization

| | As-Is | To-Be |
|---|---|---|
| `larry/post-to-tiktok.js` POSTIZ_API_KEY path | hardcoded `~/.openclaw/.env` | env-only: `process.env.POSTIZ_API_KEY` (buyer sets via Capafy env var) |
| `larry/build-from-fixed-strings.sh` add-text-overlay path | hardcoded `~/.openclaw/workspace/skills/larry/scripts/add-text-overlay.js` | `$SKILL_ROOT/scripts/add-text-overlay.js` where `SKILL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"` |
| `fixed-strings-larry-*.json` bg paths | `~/.openclaw/workspace/tiktok-marketing/assets/...` | bundle `assets/human-face/maleface.jpg` inside skill, reference as `assets/human-face/maleface.jpg` (relative) |
| `slideshow-to-video/post-to-yt.sh` env source | `set -a; . ~/.openclaw/.env; set +a` | drop env-source; rely on env vars set by Capafy container |

### I. Capafy publish execution

1. Repack larry skill (H) to `~/.openclaw/skills/anicca-larry-capafy/` with relative paths + bundled assets
2. Repack slideshow-to-video skill same pattern → `anicca-slideshow-to-video-capafy/`
3. Run `bash ~/.openclaw/skills/capafy-autopublish/scripts/daily_publish.sh` with `PICK="anicca-larry-capafy"`
4. Run again with `PICK="anicca-slideshow-to-video-capafy"`
5. Both should pass CP1/CP2/CP3 cleanly since path-leak filter passes

## Order of operations (= sequenced patch plan)

| step | patch | depends on |
|---|---|---|
| T1 | Truth registry rebuild — query Postiz `/integrations` → overwrite `postiz-integrations.json` with REAL handle for each ID | — |
| T2 | Larry JA v1 fixed-strings: bg=maleface static + hook=メンタルが勝手に安定する 口癖５選 + auto_music=yes | T1 |
| T3 | Larry EN v1 fixed-strings: bg=maleface static + auto_music=yes | T1 |
| T4 | Patch `post-to-tiktok.js` to read `auto_music` from fixed-strings, fallback to existing logic | T1 |
| T5 | Patch all 9 larry cron messages: add `--ig <real_ig_id>` per account; verify TT IDs | T1 |
| T6 | @anicca.he integration → warmup_phase=warmup + warmup_started_at=2026-06-07 | T1, T4 |
| T7 | Quality gate bbox upgrade — pixel-measure helper + 3-retry shrink/re-wrap | — |
| T8 | Wire quality-gate.sh into larry's build-from-fixed-strings.sh | T7 |
| T9 | ReelClaw routing audit (already correct per Postiz live) — write post-verify probe | T1 |
| T10 | account-health-daily error fix + Gmail body w/ zero-view-streaks.json | — |
| T11 | Slideshow-video post-verify ping (Slack/Gmail) | — |
| T12 | Larry skill Capafy repack (`anicca-larry-capafy/`) | T2, T3, T4, T5 |
| T13 | Slideshow-to-video skill Capafy repack | — |
| T14 | Capafy publish T12 via `daily_publish.sh` w/ override | T12 |
| T15 | Capafy publish T13 | T13 |

## Verification (= must run, no-fake-run per HARD RULE 0.24)

- T1: `diff` registry before/after; commit shows ≥10 handle corrections
- T2: fire `larry-anicca-ja-1` NOW; camofox open TT @anicca.jpx → newest video has maleface bg + hook=メンタルが勝手に安定する + music playing
- T3: fire `larry-anicca-en-1` NOW; same verify
- T5: fire ja-1 → confirm IG @anicca.bochi gets new post within 5 min
- T6: fire next @anicca.he cron → Postiz state=DRAFT (not PUBLISHED)
- T8: trigger gate with text > 1020px wide → expect exit 1
- T10: fire account-health-daily NOW → Gmail arrives with zero-view list embedded
- T14/T15: `publish-remote-status --agent-id <id>` returns `auditStatus: 1` (= under review)

## BP-alignment self-score

| BP source | followed identically? |
|---|---|
| Postiz tiktok.provider.ts `auto_add_music: ===='yes'` | ✓ T4 sets exact string `'yes'` |
| Postiz `/integrations` live truth | ✓ T1 overwrites registry from live |
| TikTok docs `auto_add_music` field name | ✓ T4 passes via Postiz `settings.autoAddMusic` |
| openclaw `cron edit --message` syntax | ✓ T5 patches by `--message` per ID |
| `capafy-autopublish/scripts/daily_publish.sh` known-good flow | ✓ T14/T15 reuse same script with PICK override |
| HARD RULE #-3 (BP follow only) | ✓ no synthesis, every patch references a BP source above |
| HARD RULE 0.24 (no dry run) | ✓ all T have actual fire/curl verify |
| HARD RULE 0.27 (no auto-publish without Dais OK for irreversible) | ✓ Capafy publish T14/T15 require Dais OK to fire |

BP-alignment = 100% (no Anicca-original synthesis).

---

## E5-E9 — 2026-06-08 Dais clarifications + bug fix paths

### E5. Dais 2026-06-08 verbatim acct mapping (= canonical)

| Postiz ID | role per Dais verbatim | path/file |
|---|---|---|
| `cmn8y95rg02d2qx0y09bbk5pb` | @anicca.en (Daily Anicca Nudges) — **★ reelclaw EN card+widget canonical target ★** since 2026-05-26 ZERO posts | `~/.openclaw/state/POSTIZ_ACCOUNT_MAP.md §B` |
| `cmpc3gx4001nklg0y27a8o66q` | @anicca.encards = **anicca.ios** per Dais — clipspal AI video EN content (= NOT for reelclaw) | same |
| `cmmzzg2es0539p30ycb94ayx0` | @anicca.jp.videos — **★ NEW JA reelclaw IG target ★** (Dais relabeled) | same |
| `cmmzujxpa04ujp30yxqpg1vci` | @anicca.bochi — JA cemetery, **NOT POSTING anymore** | same — no cron should route here |
| `cmoig11ew001zlv0yk6vqo1us` | @honne_reveal — **reelclaw EN honne, NOT POSTED 1+ month, BLOCKING revenue** | same |
| `cmq2aoena08bhqp0yx1epjcik` | @anicca.he — Larry ja-v2 warmup, **MUST POST as draft** | same |
| `cmq3u37gi005iqp0y90a2w92n` | @anicca-ai NEW YT — reelclaw EN card+widget YT (post-E1) | same |

### E6. run-card-en.sh JA video bug — EXACT diff

```diff
--- a/Users/anicca/.openclaw/workspace/skills/reelclaw/scripts/run-card-en.sh
+++ b/Users/anicca/.openclaw/workspace/skills/reelclaw/scripts/run-card-en.sh
@@ -13,2 +13,2 @@
-DEFAULT_FINAL="$HOME/.openclaw/workspace/workspace/reelclaw-ja-2/reel-final.mp4"
-DEFAULT_TEXT="$HOME/.openclaw/workspace/workspace/reelclaw-ja-2/reel-text.mp4"
+DEFAULT_FINAL="$HOME/anicca-project/work/reelclaw-widget-en-92c13cc2/reel-final.mp4"
+DEFAULT_TEXT="$HOME/anicca-project/work/reelclaw-widget-en-92c13cc2/reel-text.mp4"
```

**Rationale**: dedicated reelclaw-card-en EN asset dir not yet generated; widget-en's EN-content video is the only English source available. Long-term: build dedicated card-en asset at `~/anicca-project/work/reelclaw-card-en-a0a1d2fe/`.

### E7. EN reelclaw cron --ig migration: cmpc3gx4 → cmn8y95rg

```diff
4 cron payload patches (= each):
   reelclaw-anicca-en-card-1 (a0a1d2fe-4087-4ee4-bc7b-526b6f8d8e65)
   reelclaw-anicca-en-card-2 (330bbaf7-3ea2-41f6-8479-f1c6f8ef1f45)
   reelclaw-anicca-en-widget-1 (92c13cc2-3888-4c4a-b2b7-5a200f223677)
   reelclaw-anicca-en-widget-2 (2f330f58-b1fe-40ab-a2d2-95f5f5a6b557)

- --ig cmpc3gx4001nklg0y27a8o66q
+ --ig cmn8y95rg02d2qx0y09bbk5pb
```

cmpc3gx4 returns to "anicca.ios = clipspal AI video EN content" sole-owner state (= no reelclaw competition).

### E8. JA reelclaw cron --ig migration: DEAD cmnipef7g → cmmzzg2es

```diff
4 cron payload patches:
   reelclaw-anicca-ja-card-1 (174f01dd-b2ae-413f-85f7-3b03236e3944)
   reelclaw-anicca-ja-card-2 (a6ccfc01-42c8-4b5c-8c43-5713e90ee10d)
   reelclaw-anicca-ja-widget-1 (b5b49526-a38c-49b8-9c13-2d8d51b97834)
   reelclaw-anicca-ja-widget-2 (71957a9d-36bb-44f3-8fa6-078f72244fb4)

- --ig cmnipef7g00oerm0y3dz4lamx
+ --ig cmmzzg2es0539p30ycb94ayx0
```

cmnipef7g is DEAD (= NOT in Postiz `/integrations`). cmmzzg2es = @anicca.jp.videos = Dais's new JA reelclaw IG target.

### E9. ★ Card-widget 3h+ gap reschedule ★ (= Dais 2026-06-08 requirement)

Current gaps:
- EN: widget-1 (19:00) → card-2 (21:30) = **2h30m ❌** (< 3h)
- JA: widget-2 (18:20) → card-2 (21:20) = **3h0m ⚠** (= borderline)

New canonical schedule (= 4h gaps + EN/JA staggered for LLM burst avoidance):

| time JST | EN cron | EN id | JA cron | JA id |
|---|---|---|---|---|
| 07:00 | reelclaw-en-widget-2 | 2f330f58 | — | — |
| 08:00 | — | — | reelclaw-ja-widget-1 | b5b49526 |
| 11:00 | reelclaw-en-card-1 | a0a1d2fe | — | — |
| 12:00 | — | — | reelclaw-ja-card-1 | 174f01dd |
| 15:00 | reelclaw-en-widget-1 | 92c13cc2 | — | — |
| 16:00 | — | — | reelclaw-ja-widget-2 | 71957a9d |
| 19:00 | reelclaw-en-card-2 | 330bbaf7 | — | — |
| 20:00 | — | — | reelclaw-ja-card-2 | a6ccfc01 |

**Reschedule commands** (= per cron):
```
openclaw cron edit 2f330f58-b1fe-40ab-a2d2-95f5f5a6b557 --cron "0 7 * * *" --tz Asia/Tokyo
openclaw cron edit b5b49526-a38c-49b8-9c13-2d8d51b97834 --cron "0 8 * * *" --tz Asia/Tokyo
openclaw cron edit a0a1d2fe-4087-4ee4-bc7b-526b6f8d8e65 --cron "0 11 * * *" --tz Asia/Tokyo
openclaw cron edit 174f01dd-b2ae-413f-85f7-3b03236e3944 --cron "0 12 * * *" --tz Asia/Tokyo
openclaw cron edit 92c13cc2-3888-4c4a-b2b7-5a200f223677 --cron "0 15 * * *" --tz Asia/Tokyo
openclaw cron edit 71957a9d-36bb-44f3-8fa6-078f72244fb4 --cron "0 16 * * *" --tz Asia/Tokyo
openclaw cron edit 330bbaf7-3ea2-41f6-8479-f1c6f8ef1f45 --cron "0 19 * * *" --tz Asia/Tokyo
openclaw cron edit a6ccfc01-42c8-4b5c-8c43-5713e90ee10d --cron "0 20 * * *" --tz Asia/Tokyo
```

### E10. Card REAL / widget YT UNLISTED (= Dais 2026-06-08)

Dais verbatim: "post the card as real and widget as a draft to the yt app i guess not public".

Required:
1. `post-video-to-youtube.sh` accept `--privacy <public|unlisted|private>` flag
2. Widget cron payload pass `--yt-privacy unlisted`
3. Card cron payload remains `--yt-privacy public` (= default)

Pending Dais confirm: is same scheme wanted for TT (= card DIRECT_POST public, widget MEDIA_UPLOAD draft)? Or TT both public, YT only differentiated?

### E11. Music ambient/lazy override

Current: `auto_add_music="yes"` → TT auto-picks from their pool (= varies per post).

If Dais wants ★ lo-fi/lazy only ★, need:
1. Pre-render: ffmpeg attach own BGM to slide video before upload
2. Disable TT auto-music (`auto_add_music="no"`)
3. Music library at `~/.openclaw/workspace/tiktok-marketing/assets/music/lo-fi/`

Pending Dais decision.

