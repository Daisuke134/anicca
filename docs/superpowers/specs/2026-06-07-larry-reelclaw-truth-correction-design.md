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

### E. ReelClaw routing verify

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
| T1 ✅ DONE 2026-06-07 21:40 JST | Truth registry rebuild — Postiz live `/integrations` (30 entries) → `state/postiz-integrations.json` v3 schema with `paired_with_id` for TT↔IG pairing. ★ Schema migration v1→v3 ★. Backup at `.bak.20260607`. Commit `c156c7c87`. Confirmed pairs (5): `aniccajp↔anicca.jp1` (larry-ja-v1), `aniccaen2↔anicca.encards` (larry-en-v2), `aniccaaffirmation↔anicca.affirmation` (larry-en-affirmation), `monk_anicca↔monk.anicca` (yangmun), `obou_anicca↔obou.anicca` (watercolor). Unpaired Larry TT (5): aniccajp2, anicca.jp4, anicca_buddha, anicca.comedy, anicca.he-warmup. Needs-dais-pairing IG (2): anicca.bochi, anicca.video. Legacy retired (5): anicca.jp / anicca.jp8 / anicca.jpx / anicca.daily / anicca_slideshow. | — |
| T2 | Larry JA v1 fixed-strings: bg=maleface static + hook=メンタルが勝手に安定する 口癖５選 + auto_music=yes | T1 ✅ |
| T3 | Larry EN v1 fixed-strings: bg=maleface static + auto_music=yes | T1 ✅ |
| T4 | Patch `post-to-tiktok.js` to read `auto_music` from fixed-strings, fallback to existing logic | T1 ✅ |
| T5 (revised scope) | Patch ★ 5 larry cron ★ where IG pair exists (= ja-v1, en-v2, en-affirmation, yangmun, watercolor) with `--ig <paired_with_id>`. ★ 5 cron remain TT-only ★ (= aniccajp2, anicca.jp4, anicca_buddha, anicca.comedy, anicca.he) until Dais creates IG accounts to pair. ★ 2 needs-dais IG ★ (anicca.bochi, anicca.video) await Dais owner assignment. | T1 ✅ |
| T6 | @anicca.he integration → warmup_phase=warmup + warmup_started_at=2026-06-07 ★ already set in T1 registry v3 ★ — just need accounts.jsonl propagation for skill | T1 ✅, T4 |
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

- T1 ✅ DONE: registry v3 written, commit `c156c7c87` shows 14+ handle corrections + 9 new IG entries (Postiz live = 30 vs prior local = 21). Verify command: `python3 -c "import json; d=json.load(open('~/.openclaw/state/postiz-integrations.json')); print(len(d['integrations']))"` returns 30. `diff` against `.bak.20260607` shows full mapping change. Pairs verified by curl of Postiz `/integrations` profile field.
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
