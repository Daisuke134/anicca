---
title: "Skill Trio OSS 化 — ai-monk-generator / mau-clipping / naist (CLI 化なし、 既存 bash + camofox 温存)"
date: 2026-06-04
status: draft (awaiting user review)
owner: Anicca (Claude)
parent_spec: ~/.openclaw/docs/CONTENT_FACTORY_SPEC.md, ~/.openclaw/docs/ANICCA_USEFUL_CONTENT_SPEC.md
related_skills:
  - anicca-monk-factory-v3 → publish as github.com/Daisuke134/anicca-monk-factory
  - mau-tiktok            → publish as github.com/Daisuke134/mau-clipping
  - naist                 → DEFERRED, internal only v1, OSS v2 で再検討
---

# Skill Trio OSS 化 Design Spec

## 1. ゴール (1 文)

3 つの skill (anicca-monk-factory-v3 / mau-tiktok / naist) を **既存 bash + camofox + Postiz API を一切 rewrite せず**、 「installable skill repo」 として OSS 配布 (X / Slack 告知) し、 同時に **monk-factory の 3 日 0-post を 5 パッチで止血する**。

## 2. 確定事項 (Dais の判定後)

| # | 論点 | 判定 | 根拠 |
|---|---|---|---|
| D1 | CLI 化する? | **しない** (3 skill 全部) | CLI merit (`pipx install` の見栄え) が demerit (rewrite + 2 surface 保守) を tremendous に outweigh しない。 既存 bash は battle-tested |
| D2 | HeyGen API 切替 | しない | $20/video コスト、 Dais 明示 NG。 camofox + UI 維持 |
| D3 | manual / human-in-loop fallback | 一切無し | HARD RULE #18。 失敗時は CLI 自身が retry / fallback / 自動修復タスク発行 |
| D4 | 公開単位 | **3 つ独立 repo** | individually market、 X 投稿 1 repo 1 投稿、 license/disclaimer 個別 |
| D5 | Dais profile を OSS repo に同梱 | **しない** (Dais 確認済 2026-06-04) | 顔/声/IDP creds 流出防止。 OSS user は `init` wizard で自分の作る |
| D6 | naist OSS 化 | v1 は **defer**、 内部 skill のみ | academic-integrity risk + 大学固有性、 安定後 v2 で再検討 |
| D7 | monk-factory の 3 日 0-post fix | OSS 化と独立、 **今すぐ 5 パッチ適用** | 沈黙止めが先、 spec 完成を待つと損失拡大 |
| D8 | mau-clipping の YT-only 縛り | OSS では既定 3 platform、 Anicca runtime は profile flag で選択 | 旧 post-to-postiz.js:255 line で intentionally drop、 OSS user は最初から 3 platform 使えるべき |

## 3. 全体 ASCII (= 各 skill が repo として どう動くか)

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  OSS USER の Mac                                Anicca runtime の Mac (= ~/.openclaw/)    │
│  ─────────────────                              ───────────────────────────              │
│                                                                                          │
│  $ git clone github.com/Daisuke134/<skill>      ~/.openclaw/skills/<skill>/              │
│  $ cd <skill>                                       (= 元 skill ディレクトリそのまま)     │
│  $ bash install.sh                                  scripts/ (既存 bash + js) も同じ     │
│       └→ ~/.claude/skills/<skill>/ に symlink       cron が SKILL.md 読んで bash 実行    │
│  $ cp .env.example .env && vim .env                                                       │
│       └→ 自分の API key 入れる                                                            │
│  $ bash run-daily.sh         (or skill 経由)                                              │
│                                                                                          │
│                  ┌─── 両者が共有する SKILL.md + scripts/ (= 同じ実装) ───┐               │
│                  │                                                       │               │
│                  ▼                                                       ▼               │
│  ┌───────────────────────────────────────────────────────────────────────────────┐       │
│  │ github.com/Daisuke134/<skill>  (= GitHub 上の canonical source)                │       │
│  │                                                                                │       │
│  │  ├── SKILL.md            (use when / prereq / 1 行 run コマンド)               │       │
│  │  ├── scripts/            (bash + python + js、 既存資産そのまま)               │       │
│  │  ├── examples/           (.env.example + template config)                      │       │
│  │  ├── install.sh          (skill symlink + prereq doctor)                       │       │
│  │  ├── README.md           (use case / quickstart / API key 表 / X post template)│       │
│  │  ├── QUICKSTART.md       (5 分で 1 投稿)                                       │       │
│  │  ├── .env.example                                                               │       │
│  │  ├── LICENSE (MIT)                                                              │       │
│  │  └── CHANGELOG.md                                                               │       │
│  └───────────────────────────────────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────────────────────────────────┘

────────────────────────────────────────────────────────────────────────────────────────────
内部実装 (3 skill 共通の依存スタック — rewrite しない)
────────────────────────────────────────────────────────────────────────────────────────────

  camofox-browser :9377   ← HeyGen / TikTok の REAL browser 操作 (API 使わない、 安い)
       │
       ├── REST :9377/click, /fill, /upload, /eval (= Playwright wrapper、 既存)
       └── disk cookie cache (HeyGen / TikTok login 永続)

  agent-browser CLI       ← naist の NAIST IDP + edu-portal SSO (find-by-text)

  ElevenLabs HTTP API     ← monk の TTS (voice_id 固定)
  Postiz HTTP API         ← IG / YT 投稿 (mau 全 platform、 monk IG)
  yt-dlp                  ← mau の hook 取得 (YouTube Shorts)
  ffmpeg / whisper        ← caption burn、 word-timestamp
  oathtool / zbarimg      ← naist の TOTP, QR decode
```

## 4. Per-skill 詳細

### 4.1 ai-monk-generator (= 旧 anicca-monk-factory-v3)

**GitHub**: `github.com/Daisuke134/anicca-monk-factory`
**ライセンス**: MIT
**配布方法**: `git clone && bash install.sh`、 PyPI / npm 使わない
**SKILL.md 名**: `anicca-monk-factory` (= repo 名と同じ)

#### 4.1.1 投稿先マトリクス

| 環境 | プラットフォーム | アカウント | 経路 | 必要 secret |
|---|---|---|---|---|
| Anicca runtime (profile=ajahn-sutta) | TikTok | @anicca_cemetery | camofox + tiktok.com/upload (REAL browser) | MONK_TIKTOK_EN_PASSWORD + Gmail 2FA (gog) |
| 〃 | Instagram | @monk.anicca | Postiz API (integration `cmoopzaak04yop70y1yx1bwr1`) | POSTIZ_API_KEY |
| OSS user (profile=default) | TikTok | 自分のアカウント | camofox 自動 login + cookie persist | 自分の TikTok pw + 2FA mail |
| 〃 | Instagram | 自分のアカウント | Postiz API (自分の integration) | 自分の POSTIZ_API_KEY + integration ID |
| 〃 | YouTube | 任意 | Postiz API (任意) | 〃 |

#### 4.1.2 必要 prereq / API key (= README に貼る表)

| 種別 | 何 | どこで取る | 月額目安 |
|---|---|---|---|
| OS bin | ffmpeg, ffprobe, jq, oathtool, ImageMagick, whisper | `brew install ffmpeg jq oathtool imagemagick`、 `pip install openai-whisper` | $0 |
| OS bin (任意) | camofox-browser | `~/.openclaw/skills/camofox-browser/` から install (OSS user は github.com/Daisuke134/camofox-browser を別途 clone) | $0 |
| Service | HeyGen | https://heygen.com (email+pw、 任意 TOTP seed)。 Creator $24/mo plan で talking-head avatar 制限なし | $24 |
| Service | ElevenLabs | https://elevenlabs.io → API key + voice_id (custom voice 推奨) | $5 (Starter) |
| Service | Postiz | self-host (docker) or cloud。 TikTok / IG / YT integration を pre-link | $0-15 |
| Service | Google account | TikTok 2FA mail 受信用 + (任意) gog gmail polling | $0 |
| Env vars (.env) | `HEYGEN_EMAIL`, `HEYGEN_PASSWORD`, `HEYGEN_TOTP_SEED` (任意), `ELEVENLABS_API_KEY`, `POSTIZ_API_KEY`, `POSTIZ_TT_INTEGRATION_ID`, `POSTIZ_IG_INTEGRATION_ID`, `POSTIZ_YT_INTEGRATION_ID` (任意), `GOOGLE_LOGIN_EMAIL`, `GOG_KEYRING_PASSWORD` (任意、 gog 使う場合) | | |

合計コスト: **約 $30/月** (HeyGen $24 + ElevenLabs $5 + Postiz self-host $0)

#### 4.1.3 Use when (= SKILL.md / README 冒頭に書く)

- 毎日 1 本 talking-head の monk video を量産して TikTok + IG に投稿したい
- 同じ face / voice を locked にして、 script (= 話す内容) だけ変える workflow が欲しい
- 既に scrape した「効くパターン」(= Yang Mun, Shalev の retention bait + numbered body + comment keyword) を流用したい
- 30 本の script bank rotation で 1 ヶ月 = 30 本 unique video の生産が目標

Use when **NOT**:
- avatar の表情/動きを毎本変えたい (= cinematic 用途、 monk-factory は talking-head 固定)
- 1 本 5 分以上の long-form (= monk-factory は 75-120s 専用)
- HeyGen を使わず Sora2 / Veo で作りたい (= 別 skill が要る)

#### 4.1.4 monk-factory 3 日 0-post 沈黙 — Root cause + 5 パッチ

**真因 (上から重要順)**:

| # | 場所 | 何が起きてる | 証拠 |
|---|---|---|---|
| R1 | `render-download.sh` の mail wait timeout が **18 min hard-coded** | HeyGen の render が 20-40 min かかるケース多発、 18 min で諦め → mp4 download せず | `sleep 300 + for i in seq 1 13: sleep 60` = 18 min、 jsonl に `RENDER_TIMEOUT: no HeyGen ready-mail after 18 min` 多発 |
| R2 | `run-daily.sh:56` が render submit 直後に `pick-next-script.sh mark $ID` を呼ぶ | render-download が fail しても script が使用済み → 元 script は次 cron で 2 度と pick されない → 喪失 | コードコメント `#41 rotation fix` で意図的だが副作用が大きい |
| R3 | recovery cron が無い | mail 来てる project が放置 (= resume-render.sh が手動 invoke 専用) | cron jobs.json に monk-factory-en-recovery 無し |
| R4 | stale lock `~/anicca-monk-factory/state/monk-factory-en.lock` | PID 11943 (6/4 14:00 死亡)、 TTL 無し | `cat lock` = 11943、 `ps -p 11943` = dead |
| R5 | used.log と renders_v3 の整合性が崩壊 | A02/A03/A26/A27/A28 等が「mark 済 / mp4 無し / 未 post」 状態で漂流 | `tail used.log` = A01/A02/A03 のみ、 renders_v3 に A20 までは captioned.mp4 あり、 以降 .log のみ |

**パッチ 5 件 (1 commit で apply)**:

##### P1 — `render-download.sh` mail wait 18→60 min + `--timeout` flag
```diff
- sleep 300
- for i in $(seq 1 13); do  # 13×60s = 13min、 total 18min
+ TIMEOUT_MIN="${HEYGEN_MAIL_TIMEOUT_MIN:-60}"
+ POLL_ITER=$(( (TIMEOUT_MIN - 5) ))    # 5min sleep + N×60s polling
+ sleep 300
+ for i in $(seq 1 "$POLL_ITER"); do
```
`HEYGEN_MAIL_TIMEOUT_MIN` env で override 可能 (default 60min)。

##### P2 — `run-daily.sh` で mark のタイミングを submit 直後 → 1+ platform post 成功直後 に移動
```diff
- # OLD line 56: bash "$S/pick-next-script.sh" mark "$ID" >/dev/null 2>&1 || true
+ # 削除 (submit 時点で mark しない)

  # step 7 (post IG) 後に追加:
+ if [ -n "$TTURL" ] || [ -n "$IGURL" ]; then
+   bash "$S/pick-next-script.sh" mark "$ID"
+ else
+   echo "ALL_PLATFORMS_FAILED — script $ID kept unused for retry"
+ fi
```
1 platform でも post 成功すれば mark、 全 fail なら次 cron で同 script を retry。

##### P3 — recovery cron 新設
```json
{
  "name": "monk-factory-en-recovery",
  "schedule": {"kind": "cron", "expr": "0 */2 * * *", "tz": "Asia/Tokyo"},
  "payload": {
    "kind": "agentTurn",
    "message": "Read ~/.openclaw/skills/anicca-monk-factory-v3/SKILL.md and run: bash ~/.openclaw/skills/anicca-monk-factory-v3/scripts/resume-render.sh. Report to Slack #metrics."
  },
  "delivery": {"mode": "announce", "channel": "slack", "to": "channel:C091G3PKHL2"},
  "enabled": true
}
```
2h 毎に `resume-render.sh` 走らせて、 HeyGen mail box の過去 6h `"Your Video is Ready!"` を全 scan → 未 download project を救う。

##### P4 — 既存 stale lock 即削除 + run-daily.sh の lock check に TTL 追加
```bash
# 即実行 (one-shot):
rm -f /Users/anicca/anicca-monk-factory/state/monk-factory-en.lock
```
```diff
  # run-daily.sh の lock check:
  if [ -f "$LOCK" ]; then
    OLD_PID=$(cat "$LOCK" 2>/dev/null || echo 0)
+   LOCK_AGE=$(( $(date +%s) - $(stat -f %m "$LOCK") ))
+   if [ "$LOCK_AGE" -gt 7200 ]; then  # 2h 超は強制 stale clear
+     echo "lock older than 2h — forcing stale clear (was pid=$OLD_PID)"
+     rm -f "$LOCK"
+   elif [ "$OLD_PID" -gt 0 ] 2>/dev/null && kill -0 "$OLD_PID" 2>/dev/null; then
      echo "ALREADY_RUNNING: pid=$OLD_PID holds $LOCK — exit 75 (transient)"
      exit 75
    fi
+   echo "stale lock (pid=$OLD_PID not alive) — cleaning"
  fi
```

##### P5 — `reconcile-used.sh` 新規、 cron 起動直前に呼ぶ
```bash
#!/usr/bin/env bash
# 既に mark されてるが mp4 / posted.jsonl に存在しない script を unused に戻す
set -euo pipefail
SKILL="$HOME/.openclaw/skills/anicca-monk-factory-v3"
USED="$SKILL/04-script/used.log"
OUT_DIR="$HOME/anicca-monk-factory/renders_v3"
POSTED="$HOME/anicca-monk-factory/state/posted.jsonl"

[ -f "$USED" ] || { echo "no used.log"; exit 0; }

NEW_USED=$(mktemp)
RESTORED=0
while IFS= read -r ID; do
  [ -z "$ID" ] && continue
  if [ -f "$OUT_DIR/${ID}_captioned.mp4" ] || grep -q "\"$ID\"" "$POSTED" 2>/dev/null; then
    echo "$ID" >> "$NEW_USED"
  else
    echo "RECONCILE: $ID was marked but never posted → restoring"
    RESTORED=$((RESTORED + 1))
  fi
done < "$USED"

mv "$NEW_USED" "$USED"
echo "reconciled $RESTORED scripts"
```
`run-daily.sh` の step [1] の直前に `bash "$S/reconcile-used.sh"` を挿入。 A02/A03/A26/A27/A28 等を unused に戻す。

**5 パッチ適用順 (1 commit)**:
```
1. P4 即実行 (stale lock delete) — 0 秒
2. P1 + P2 + P3 + P5 を 1 worktree branch で apply + commit + push
3. cron entry P3 を ~/.openclaw/cron/jobs.json に追加 + gateway restart
4. 21:00 JST cron 起動 → 観察 (60min wait → 22:00-23:00 で download 完了 → 23:00 IG/TT URL Slack 投稿確認)
5. 24h 以内に TikTok @anicca_cemetery / IG @monk.anicca に 1 投稿以上着いたら fix verified
```

#### 4.1.5 OSS user の Quickstart (= README.md の中身)
```bash
# 1. prereq
brew install ffmpeg jq oathtool imagemagick
pip install openai-whisper

# 2. clone + install
git clone https://github.com/Daisuke134/anicca-monk-factory
cd anicca-monk-factory
bash install.sh    # ~/.claude/skills/anicca-monk-factory/ に symlink + prereq doctor

# 3. credentials (init wizard)
cp .env.example .env
# 自分の HeyGen / ElevenLabs / Postiz / TikTok creds を埋める

# 4. character setup
# examples/character.yaml.example をコピーして自分の monk character を定義
# - 顔 (face.jpeg)
# - 声 (ElevenLabs voice_id)
# - 30 script bank (jsonl、 template 提供)

# 5. 動かす
bash scripts/run-daily.sh   # 1 本 render + post + Slack 報告

# 6. (任意) cron 化
# launchd or openclaw cron に 0 8,14,21 * * * 登録
```

#### 4.1.6 X 告知文 (draft、 humanizer + verbatim-guard 通し済の予定、 投稿前 camofox で目視 verify per CLAUDE.md 0.12)
> Built a skill that generates AI monk videos like @yangmun2 — locked face, locked voice, 30-script bank → HeyGen render → caption burn → TikTok + IG post. One `bash install.sh`.
> Inspired by https://x.com/shalevhvs/status/2042242260784537736
> github.com/Daisuke134/anicca-monk-factory

### 4.2 mau-clipping (= 旧 mau-tiktok)

**GitHub**: `github.com/Daisuke134/mau-clipping`
**ライセンス**: MIT
**配布方法**: `git clone && bash install.sh` (+ 任意 `npm i -g mau-clipping` で `bin` short alias 提供、 既存 script を rewrite しない純パッケージング)

#### 4.2.1 投稿先マトリクス

| 環境 | プラットフォーム | アカウント | 経路 | 必要 secret |
|---|---|---|---|---|
| Anicca runtime (profile=anicca-en) | TikTok | anicca.en7 | Postiz API (`cmmtt62wq01lqn50yehk1f6dy`) | POSTIZ_API_KEY |
| 〃 | Instagram | anicca.ai | Postiz API (`cmmzzg2es0539p30ycb94ayx0`) | 〃 |
| 〃 | YouTube | @anicca-ai | Postiz API (`cmn8ymq6c02oio70y5ea1trv8`) | 〃 |
| Anicca runtime (profile=anicca-ja) | TikTok | aniccajp6 | Postiz API (`cmmytdj1101w1p30ytx8lj0fw`) | 〃 |
| 〃 | Instagram | anicca.jp | Postiz API (`cmmzujxpa04ujp30yxqpg1vci`) | 〃 |
| 〃 | YouTube | JA専用 | Postiz API (`cmn1oukj9012nnq0yqhouc3ib`) | 〃 |
| OSS user (profile=default) | TikTok + IG + YT | 自分の 3 アカウント | Postiz API (自分の 3 integration) | 自分の POSTIZ_API_KEY + 3 integration ID |

#### 4.2.2 既存 YT-only 縛りの修正 (= D8 適用)

旧 `post-to-postiz.js:255-263` が intentionally **TikTok + Instagram を drop して YouTube だけ post** している (Dais 2026-05-22 メモ "電話認証が Dais 負担、 cron params が間違ってる → params=thumbnail incompat")。

OSS 化のために修正:
```diff
- // mau-tiktok posts ONLY to YouTube (limited accounts)
- // YouTube only block below
- if (integrations.youtube && integrations.youtube.id) {
-   results.youtube = postToYouTube(...);
- }
+ // Dais 2026-06-04: OSS 化に伴い 3 platform 既定に復活。 Anicca runtime は env で choose:
+ //   POST_PLATFORMS=youtube                   ← Anicca 現状維持
+ //   POST_PLATFORMS=tiktok,instagram,youtube  ← OSS user 既定
+ const PLATFORMS = (process.env.POST_PLATFORMS || "tiktok,instagram,youtube").split(",");
+ if (PLATFORMS.includes("tiktok") && integrations.tiktok?.id) {
+   results.tiktok = postToTikTok(integrations.tiktok.id, uploaded.id, uploaded.path, caption, title, apiKey);
+ }
+ if (PLATFORMS.includes("instagram") && integrations.instagram?.id) {
+   results.instagram = postToInstagram(integrations.instagram.id, uploaded.id, uploaded.path, caption, apiKey);
+ }
+ if (PLATFORMS.includes("youtube") && integrations.youtube?.id) {
+   const ytThumb = lang === "en" ? null : thumbnail;   // EN YT thumbnail 不可 issue 維持
+   results.youtube = postToYouTube(integrations.youtube.id, uploaded.id, uploaded.path, caption, title, apiKey, ytThumb);
+ }
```

Anicca runtime の cron message に `POST_PLATFORMS=youtube` 環境変数を渡せば従来挙動を維持。 OSS user は env 設定不要で 3 platform 既定。

#### 4.2.3 必要 prereq / API key

| 種別 | 何 | どこで取る | 月額目安 |
|---|---|---|---|
| OS bin | ffmpeg, ffprobe, yt-dlp, node 20+ | `brew install ffmpeg yt-dlp node` | $0 |
| Service | Postiz | self-host (docker) or cloud。 TikTok / IG / YT integration を Postiz UI で pre-link | $0-15 |
| Env vars (.env) | `POSTIZ_API_KEY`, `POSTIZ_TT_INTEGRATION_ID`, `POSTIZ_IG_INTEGRATION_ID`, `POSTIZ_YT_INTEGRATION_ID`, `POST_PLATFORMS` (任意) | | |

合計コスト: **$0-15/月**

#### 4.2.4 Use when

- Mau 流の「viral YouTube Shorts の最初 3 秒を切って CTA stitch → TikTok + IG + YT に同時投稿」 を自動化したい
- 既に scrape 対象の creators (= YouTube channel URL) リストを持ってる、 もしくは Anicca の `creators.json` を流用したい
- CTA mp4 (= 自社/自分のサービス宣伝動画) を 1 本作って 30 日以上回したい

Use when **NOT**:
- 長尺 (>9 秒) を作りたい (= mau-clipping は hook 3s + CTA 6s = 9s 固定)
- TikTok / IG のソースとして scrape したい (= v1 は YouTube Shorts のみ)
- AI で hook 自動生成したい (= 既存の人間が作った viral を borrow する設計)

#### 4.2.5 OSS user の Quickstart
```bash
brew install ffmpeg yt-dlp node
git clone https://github.com/Daisuke134/mau-clipping
cd mau-clipping
bash install.sh
cp .env.example .env  # POSTIZ_API_KEY + 3 integration ID を埋める

# CTA 動画 (cta_en_final.mp4) を作る or 自分のを置く
# README の "CTA recipe" 章を参照 (= ElevenLabs + ffmpeg で 6 秒の宣伝動画を作るレシピ、 暗黙知を skill 化)

# creators.json に scrape 対象 YouTube channel を追加
# 例: vim creators.json

# 動かす
node scripts/scrape-hooks.js --lang en --count 1
node scripts/trim-and-stitch.js --lang en --count 1
node scripts/post-to-postiz.js --lang en
```

#### 4.2.6 X 告知文 (draft)
> Built a skill that clones what @maboroshi_app is doing on YouTube — grab a 3s viral hook, stitch it with your own CTA, post to TikTok + IG + YT. One `bash install.sh`.
> Inspired by https://x.com/maubaron/status/2030716132093460742
> github.com/Daisuke134/mau-clipping

### 4.3 naist (= 旧 naist 統合 skill)

**v1 では OSS 化しない** (D6)。 内部 skill のまま、 Slack 日本語 digest のみ。

理由:
- 課題の自動提出 + 履修自動登録 = **academic-integrity の他人事リスク**を public 化すると大学 + Dais 個人の評判 risk
- NAIST 固有性 (idp.naist.jp / edu-portal SSO / 履修期間 / 11 cron schedule)
- agent-browser の find-by-text procedure は generic だが、 ハードコードされた「ログインはこちら」 「9 提出」 等の日本語 visible-text が naist 固有

→ v1: 既存の `~/.openclaw/skills/naist/` のまま運用、 X 投稿しない、 GitHub 公開しない。 もし将来 OSS 化する場合は v2 で「naist-specific を外して generic university-automation template に refactor」 してから検討。

`naist` skill 自身の安定性は別途 (内部 cron が 9 mode で動いてる、 別 spec で扱う)。

## 5. Repo layout (= `anicca-monk-factory` と `mau-clipping` 共通)

```
.
├── SKILL.md                    # Claude Code / Anicca が読む。 use when + prereq + 1 行 run
├── README.md                   # OSS visitor 向け。 use case + quickstart + API key 表 + screenshot
├── QUICKSTART.md               # 5 分で 1 投稿
├── CHANGELOG.md
├── LICENSE                     # MIT
├── .env.example                # 必要 env を全部書いた template
├── .gitignore                  # .env / state/ / renders/ / *.mp4 を含む
├── install.sh                  # ~/.claude/skills/<name>/ に symlink + doctor
├── examples/                   # init で展開する template
│   ├── character.yaml.example  # monk のみ
│   ├── bank.jsonl.example      # monk のみ (3 script 例、 30 ではない)
│   ├── creators.json.example   # mau のみ
│   └── cta-recipe.md           # mau の CTA mp4 作り方
├── scripts/                    # 既存資産そのまま (rewrite ゼロ)
│   ├── run-daily.sh            # monk
│   ├── render-submit.sh        # monk
│   ├── render-download.sh      # monk (P1 適用済)
│   ├── reconcile-used.sh       # monk (P5 新規)
│   ├── scrape-hooks.js         # mau
│   ├── trim-and-stitch.js      # mau
│   ├── post-to-postiz.js       # mau (D8 適用済)
│   └── ...
├── docs/
│   ├── ARCHITECTURE.md
│   ├── TROUBLESHOOTING.md      # よくある失敗 + retry chain
│   └── x-post.md               # X 告知文 final
└── tests/
    └── smoke.sh                # install.sh + doctor の最低 check
```

## 6. install.sh (= 共通 template)
```bash
#!/usr/bin/env bash
# install.sh — skill を ~/.claude/skills/<name>/ に登録 + 依存 check
set -euo pipefail

SKILL_NAME=$(basename "$(pwd)")
TARGET="$HOME/.claude/skills/$SKILL_NAME"

if [ -L "$TARGET" ] || [ -d "$TARGET" ]; then
  echo "removing existing $TARGET"; rm -rf "$TARGET"
fi
mkdir -p "$HOME/.claude/skills"
ln -s "$(pwd)" "$TARGET"
echo "✓ symlinked $TARGET → $(pwd)"

# prereq doctor
echo
echo "=== prereq doctor ==="
miss=0
for bin in ffmpeg ffprobe jq; do
  if command -v "$bin" >/dev/null 2>&1; then echo "✓ $bin"; else echo "✗ $bin not found"; miss=1; fi
done
[ -f ".env" ] && echo "✓ .env present" || { echo "✗ .env missing — cp .env.example .env"; miss=1; }

[ "$miss" = "0" ] && echo -e "\n🟢 ready to run" || echo -e "\n🟡 install missing prereqs first"
```

## 7. Risks + Verify gate

| Risk | 対処 |
|---|---|
| HeyGen / TikTok UI 変更 → render/post 割れる | `render-submit.sh` / `post-tiktok.sh` 内の find-by-text + snapshot diff、 fail 時 `resume-render.sh` recovery cron で救う、 24h 0 投稿で Slack alert + Anicca 自動 fix task 発行 |
| OSS user の secret 漏洩 | `.env` を `.gitignore` 必須、 README で「`git add .env` 絶対 NG」 太字、 `install.sh` 中の doctor が `git check-ignore .env` を確認 |
| Postiz integration を pre-link していない OSS user | install.sh の doctor が `POSTIZ_API_KEY` で `curl /public/v1/integrations` 叩いて存在チェック、 無ければ「Postiz UI で先に link しろ」 メッセージ |
| TikTok 2FA mail を OSS user 自身の gmail で受信できない | camofox login 時 2FA prompt が出たら Slack 通知、 OSS user は自分の gmail / Authenticator で対応 (= Anicca runtime は gog 自動読み、 OSS user は手動で初回登録のみ、 cookie 持続) |
| Verify gate (CLAUDE.md 0.12) | release 前に: ① monk → 1 本 render → TikTok URL + IG URL 取得 → spec § 8 に貼る、 ② mau → 1 本 stitch → 3 platform URL 取得 → 同様、 ③ install.sh を fresh Mac で実走 → quickstart 完走確認 |

## 8. Verification (= release 前に評価する gate、 「OSS publish ✓」と claim する根拠)

| Skill | 検証項目 | 評価方法 | パス条件 |
|---|---|---|---|
| anicca-monk-factory | 5 パッチ適用後 24h 投稿 | TikTok @anicca_cemetery + IG @monk.anicca の URL を Slack #metrics で目視 | 24h で >=1 投稿成功 (両 platform) |
| anicca-monk-factory | OSS user fresh install | 別ユーザー account の Mac (or 別 dir) で `git clone && bash install.sh && cp .env.example .env && fill && bash run-daily.sh` | install.sh doctor 全 green + 1 本 render success |
| mau-clipping | 3 platform 復活 | `POST_PLATFORMS=tiktok,instagram,youtube node post-to-postiz.js --lang en` → 3 URL 取得 | 3 / 3 success |
| mau-clipping | OSS user fresh install | 同上 | 1 本 9s stitched mp4 + 3 platform URL |
| install.sh (両方) | symlink + doctor | `bash install.sh` の出力に `🟢 ready to run` | 全 prereq OK |

## 9. Out of scope (v1)

- naist の OSS 化 (= D6 適用、 v2)
- HeyGen / TikTok / IG の API 切り替え (= D2 適用、 ずっと UI/browser 維持)
- monk-factory の長尺 / 表情 cinematic 化 (= 別 skill)
- mau-clipping の hook source を YouTube 以外に拡張 (= v2)
- 多言語化 (= 現状 EN + JA のみ、 他言語は OSS user が自分の `--lang` profile を追加)
- Linux / Windows 動作確認 (= v1 は macOS only、 OSS user に明記)
- `init` wizard 自動化 (= v1 は手動 `cp .env.example .env` + vim、 v2 で `bash init.sh` 検討)

## 10. Out-of-spec changes that 同時に commit (= P1-P5 monk fix)

これは spec の implementation deliverable ではなく、 **spec 完成と独立に今すぐ commit する monk-factory 安定化**:

| パッチ | 対象 file | 1 commit に含める? |
|---|---|---|
| P1 | `~/.openclaw/skills/anicca-monk-factory-v3/scripts/render-download.sh` | yes |
| P2 | `~/.openclaw/skills/anicca-monk-factory-v3/scripts/run-daily.sh` | yes |
| P3 | `~/.openclaw/cron/jobs.json` | yes (gateway restart 含む) |
| P4 (stale lock) | `~/anicca-monk-factory/state/monk-factory-en.lock` | 即実行 (commit 不要、 削除のみ) |
| P4 (lock TTL) | `~/.openclaw/skills/anicca-monk-factory-v3/scripts/run-daily.sh` | yes (P2 と同 file、 同 commit) |
| P5 | `~/.openclaw/skills/anicca-monk-factory-v3/scripts/reconcile-used.sh` + run-daily.sh への呼出追加 | yes |

`~/.openclaw/` は runtime canonical store、 worktree 不可 (CLAUDE.md HARD RULE #0 例外条項)。 main 直 commit + push、 ただし superpowers 残り 7 step (spec / TDD / verify / review / finishing) は遵守。

## 11. References

- 旧 SKILL.md: `~/.openclaw/skills/anicca-monk-factory-v3/SKILL.md` (Yang Mun / Ajahn Sutta 仕様)
- 旧 SKILL.md: `~/.openclaw/skills/mau-tiktok/SKILL.md` (mau-tiktok 仕様)
- 旧 SKILL.md: `~/.openclaw/skills/naist/SKILL.md` (NAIST 統合)
- HKUDS CLI-Anything: github.com/HKUDS/CLI-Anything (CLI 化の参考、 今回は採用せず)
- HARD RULE #0 / #18 / #16 / #-1 / #-2: `/Users/anicca/anicca-project/CLAUDE.md`
- 既存 fix recipe: `~/.openclaw/skills/anicca-monk-factory-v3/scripts/resume-render.sh` (P3 で利用)
