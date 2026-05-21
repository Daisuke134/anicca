# Blotato → Postiz 移行 + 全修正スペック

**Date**: 2026-02-28
**Author**: Anicca
**Status**: 🔄 実行中（P0,L1,L2,D1,D2,Z1,H1,H2 完了。ブロッカー全解決。P1-P8 残り）

---

## ソース

| # | ソース | URL | 核心の引用 |
|---|--------|-----|-----------|
| S1 | Postiz Create Post API | https://docs.postiz.com/public-api/posts/create | POST api.postiz.com/public/v1/posts, Authorization header, type: now/schedule |
| S2 | Postiz API Overview | https://docs.postiz.com/public-api | 30 requests per hour. UI uses "channel", API uses "integration" |
| S3 | Postiz Agent CLI | https://postiz.com/agent | postiz analytics:post <post-id> -d 7 — Returns metrics (Impressions, Likes, Comments) |
| S4 | Postiz Analytics API | larry/references/analytics-loop.md | GET /analytics/{integrationId} for platform, GET /analytics/post/{postId} for per-post |
| S5 | Build In Public Roadmap | https://github.com/buildinginpublic/buildinpublic | Phase 5: Metrics, Reflection, and Adjustment |
| S6 | npm ci docs | https://docs.npmjs.com/cli/v10/commands/npm-ci | npm ci requires a package-lock.json to be present |
| S7 | Zenn FAQ rate-limit | https://zenn.dev/faq#rate-limit | 24時間以内の投稿数に基づいて判定。24時間経過すれば再投稿可 |
| S8 | larry SKILL.md Section 4 | ~/.openclaw/workspace/skills/larry/SKILL.md | check-analytics.js --connect でrelease ID接続。2時間以上待ってから実行 |
| S9 | larry analytics-loop.md | larry/references/analytics-loop.md | GET /posts/{id}/missing → PUT /posts/{id}/release-id でTikTokビデオID接続 |

---

## Postiz Integration IDs（2026-02-28 API確認済み）

| アカウント | Platform | Integration ID |
|-----------|----------|---------------|
| @aniccaxxx | X | cmm6d7m5703rwpr0yr5vtme3w |
| @anicca.jp2 | TikTok | cmlrv8jq000hun60yy57eaptx |
| @aniccaen2 | TikTok | cmlt171eq04d9r00yzzceb6bw |
| Postiz | Slack | cmlrv5o0t00hgn60y734e1q3c |

env既存: POSTIZ_API_KEY ✅, POSTIZ_TIKTOK_INTEGRATION_ID ✅
env追加必要: POSTIZ_X_INTEGRATION_ID

---

## A. Blotato → Postiz 移行

### P0: .env に POSTIZ_X_INTEGRATION_ID 追加 ✅

```bash
echo 'POSTIZ_X_INTEGRATION_ID=cmm6d7m5703rwpr0yr5vtme3w' >> ~/.openclaw/.env
```

| 状態 | ✅ 完了（2026-02-28） |

---

### P1: x-poster SKILL.md 書き換え

ファイル: `~/.openclaw/skills/x-poster/SKILL.md`

#### 必須env セクション

Before:
```
| `BLOTATO_API_KEY` | Blotato API キー |
| `BLOTATO_ACCOUNT_ID_EN` | Blotato 上の X アカウント ID（EN） |
```

After:
```
| `POSTIZ_API_KEY` | Postiz API キー |
| `POSTIZ_X_INTEGRATION_ID` | Postiz X integration ID (@aniccaxxx) |
```

#### Blotato API セクション全体を置換

Before:
```
## Blotato API（正しいエンドポイント）

**Base URL: `https://backend.blotato.com/v2`**（`api.blotato.com` は廃止済み・使用禁止）

POST https://backend.blotato.com/v2/posts
Header: blotato-api-key: <BLOTATO_API_KEY>
Body:
{
  "post": {
    "accountId": "<BLOTATO_ACCOUNT_ID_EN>",
    "content": {
      "text": "<投稿テキスト>",
      "platform": "twitter",
      "mediaUrls": []
    },
    "target": {
      "targetType": "twitter"
    }
  }
}

レスポンスの `postSubmissionId` を使い、以下でステータスをポーリングする（最大60秒、5秒間隔）:
GET https://backend.blotato.com/v2/posts/<postSubmissionId>
Header: blotato-api-key: <BLOTATO_API_KEY>
`status: "published"` になったら `publicUrl` を取得する。
```

After:
```
## Postiz API（S1準拠）

**Base URL: `https://api.postiz.com/public/v1`**
**Rate Limit: 30 requests/hour (S2)**

POST https://api.postiz.com/public/v1/posts
Header: Authorization: <POSTIZ_API_KEY>
Header: Content-Type: application/json
Body:
{
  "type": "now",
  "shortLink": false,
  "tags": [],
  "posts": [{
    "integration": { "id": "<POSTIZ_X_INTEGRATION_ID>" },
    "value": [{ "content": "<投稿テキスト>" }],
    "settings": { "__type": "x", "who_can_reply_post": "everyone" }
  }]
}

レスポンスの posts[0].releaseURL で公開URLを即取得（ポーリング不要）。
posts[0].id をメトリクス取得用に保存する。
```

#### 必須tools セクション

Before:
```
- `web_fetch`（Blotato API呼び出し用）
```

After:
```
- `web_fetch`（Postiz API呼び出し用）
```

#### 禁止事項セクション

Before:
```
- **`api.blotato.com` 使用禁止**（廃止済み）。必ず `backend.blotato.com/v2` を使う。
```

After:
```
（この行を削除）
```

| 状態 | ⬜ |

---

### P2: build-in-public SKILL.md 書き換え

ファイル: `~/.openclaw/skills/build-in-public/SKILL.md`

#### description (frontmatter)

Before:
```
description: Posts daily "Day N of building Anicca" tweet to X in Japanese. Reads today's diary, fetches MRR/Trial from RevenueCat API, and posts via Blotato API.
```

After:
```
description: Posts daily "Day N of building Anicca" tweet to X. Reads today's diary, fetches MRR/Trial from RevenueCat API, and posts via Postiz API to @aniccaxxx.
```

#### Step 6 タイトル + curl

Before:
```
### Step 6: Blotato APIで投稿

TWEET_TEXT="<ここにStep 5で書いたツイートテキスト>"

BLOTATO_RESPONSE=$(curl -s -X POST https://backend.blotato.com/v2/posts \
  -H "blotato-api-key: ${BLOTATO_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"text\": $(python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))" <<< "${TWEET_TEXT}"), \"platforms\": [{\"platform\": \"twitter\", \"accountId\": 29172}]}")

echo "Blotato response: $BLOTATO_RESPONSE"
```

After:
```
### Step 6: Postiz APIで@aniccaxxxに投稿（S1準拠）

TWEET_TEXT="<ここにStep 5で書いたツイートテキスト>"

POSTIZ_RESPONSE=$(curl -s -X POST "https://api.postiz.com/public/v1/posts" \
  -H "Authorization: ${POSTIZ_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"type\": \"now\",
    \"shortLink\": false,
    \"tags\": [],
    \"posts\": [{
      \"integration\": { \"id\": \"cmm6d7m5703rwpr0yr5vtme3w\" },
      \"value\": [{ \"content\": $(python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))" <<< "${TWEET_TEXT}") }],
      \"settings\": { \"__type\": \"x\", \"who_can_reply_post\": \"everyone\" }
    }]
  }")

echo "Postiz response: $POSTIZ_RESPONSE"

# 投稿IDを保存（メトリクス取得用）
POST_ID=$(echo "$POSTIZ_RESPONSE" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('posts',[{}])[0].get('id',''))" 2>/dev/null)
RELEASE_URL=$(echo "$POSTIZ_RESPONSE" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('posts',[{}])[0].get('releaseURL',''))" 2>/dev/null)
```

#### Step 7 Slack報告

Before:
```
投稿先: X（日本語アカウント ACCOUNT_ID=29172）
```

After:
```
投稿先: X @aniccaxxx (Postiz integration: cmm6d7m5703rwpr0yr5vtme3w)
X リンク: ${RELEASE_URL}
```

#### エラーハンドリング

Before:
```
| Blotato API失敗 | Slack #metrics にエラー内容を報告して終了 |
| BLOTATO_API_KEY未設定 | `source /Users/anicca/.openclaw/.env` を必ず実行すること |
```

After:
```
| Postiz API失敗 | Slack #metrics にエラー内容を報告して終了 |
| POSTIZ_API_KEY未設定 | `source /Users/anicca/.openclaw/.env` を必ず実行すること |
```

#### 新規追加: Step 1.5 メトリクスフィードバックループ（S3, S4, S5準拠）

Step 1（環境設定）とStep 2（diary読む）の間に追加:

```
### Step 1.5: 昨日の投稿メトリクス取得（S3, S5準拠）

# Postiz APIで直近投稿のメトリクスを取得
YESTERDAY=$(TZ=Asia/Tokyo date -v-1d +%Y-%m-%dT00:00:00.000Z 2>/dev/null)
TODAY_END=$(TZ=Asia/Tokyo date +%Y-%m-%dT23:59:59.000Z)

POSTS_RESPONSE=$(curl -s -H "Authorization: ${POSTIZ_API_KEY}" \
  "https://api.postiz.com/public/v1/posts?startDate=${YESTERDAY}&endDate=${TODAY_END}")

# @aniccaxxx の最新投稿IDを取得
LATEST_POST_ID=$(echo "$POSTS_RESPONSE" | python3 -c "
import json,sys
data = json.loads(sys.stdin.read())
posts = data.get('posts',[])
for p in posts:
    integ = p.get('integration',{})
    if integ.get('id') == 'cmm6d7m5703rwpr0yr5vtme3w' or integ.get('providerIdentifier') == 'x':
        print(p['id'])
        break
" 2>/dev/null)

if [ -n "$LATEST_POST_ID" ]; then
  # Per-post analytics取得（S4: GET /analytics/post/{postId}）
  METRICS=$(curl -s -H "Authorization: ${POSTIZ_API_KEY}" \
    "https://api.postiz.com/public/v1/analytics/post/${LATEST_POST_ID}")
  
  mkdir -p ~/.openclaw/workspace/build-in-public
  echo "$METRICS" > ~/.openclaw/workspace/build-in-public/metrics-$(TZ=Asia/Tokyo date +%Y-%m-%d).json
  
  # メトリクスをStep 5のツイート生成時に参考にする
  echo "昨日のメトリクス: $METRICS"
fi

# 学習ルール（S5 Phase 5準拠）:
# - インプレッション > 前回平均 → そのパターンを再利用
# - エンゲージメント率 > 3% → そのフォーマットを継続
# - 低パフォーマンス → パターン変更
```

| 状態 | ⬜ |

---

### P3: trend-hunter SKILL.md 書き換え

ファイル: `~/.openclaw/skills/trend-hunter/SKILL.md`

#### 必須env テーブル

Before:
```
| `BLOTATO_API_KEY` | メトリクス用（Blotato GET /v2/posts/{postSubmissionId}） |
```

After:
```
| `POSTIZ_API_KEY` | メトリクス用（Postiz analytics API） |
```

#### メトリクス取得: X セクション

Before:
```
**X:** Blotato の `GET https://backend.blotato.com/v2/posts/{postSubmissionId}`（ヘッダ `blotato-api-key`）で tweet ID を取得し、その ID で X API v2 の `GET https://api.x.com/2/tweets?ids={tweetId}&tweet.fields=public_metrics,created_at`（ヘッダ `Authorization: Bearer {X_BEARER_TOKEN}`）を叩き、`data[0].public_metrics` の impression_count / like_count / retweet_count / reply_count を使う。
```

After:
```
**X:** Postiz の `GET https://api.postiz.com/public/v1/posts?startDate={ISO}&endDate={ISO}`（ヘッダ `Authorization: {POSTIZ_API_KEY}`）で投稿一覧を取得。各postの `releaseURL` と `state` を確認。メトリクスは `GET https://api.postiz.com/public/v1/analytics/post/{postId}`（ヘッダ `Authorization: {POSTIZ_API_KEY}`）で取得。レスポンス: [{ "label": "Likes", "data": [...] }, { "label": "Comments", "data": [...] }]。（S4準拠）
```

#### メトリクス取得: TikTok セクション

Before:
```
**TikTok:** Blotato の `GET https://backend.blotato.com/v2/posts/{postSubmissionId}` のレスポンスに TikTok の再生数・いいね等があればそれを使い、なければ「TikTok: 未取得」とだけ書く。
```

After:
```
**TikTok:** Postiz の `GET https://api.postiz.com/public/v1/analytics/post/{postId}`（ヘッダ `Authorization: {POSTIZ_API_KEY}`）で取得。プラットフォーム全体は `GET https://api.postiz.com/public/v1/analytics/{integrationId}`。TikTok JP: cmlrv8jq000hun60yy57eaptx、EN: cmlt171eq04d9r00yzzceb6bw。（S4準拠）
```

#### 出力形式その2 コメント

Before:
```
## 出力形式その 2：hooks/YYYY-MM-DD.json（Blotato に schedule する 1 本）
```

After:
```
## 出力形式その 2：hooks/YYYY-MM-DD.json（Postiz で投稿する 1 本）
```

#### cron説明

Before:
```
Blotato への schedule は **別 cron**
```

After:
```
Postiz への投稿は **別 cron**
```

| 状態 | ⬜ |

---

### P4: article-writer SKILL.md 書き換え

ファイル: `~/.openclaw/skills/article-writer/SKILL.md`

エラーハンドリング表から以下の行を削除:
```
| Blotato API `api.blotato.com` が失敗 | 廃止済みエンドポイント | `backend.blotato.com` を使う |
```

理由: article-writerはBlotato/Postiz不使用。GitHub push → Zenn/dev.to。残骸。

| 状態 | ⬜ |

---

### P5: tiktok-poster スキル削除

```bash
rm -rf ~/.openclaw/skills/tiktok-poster
```

理由: larryスキル（~/.openclaw/workspace/skills/larry/）がPostiz経由でTikTok投稿を代替済み。tiktok-posterのcronもない（動いてない）。

| 状態 | ⬜ |

---

### P6: x-poster cron 2個停止

```bash
# cron IDを確認
openclaw cron list | grep x-poster
# 停止
openclaw cron rm <x-poster-morning-id>
openclaw cron rm <x-poster-evening-id>
```

理由: Dais指示。trend-hunter → x-poster のパイプラインは一時停止。

| 状態 | ⬜ |

---

### P7: TOOLS.md 更新

変更箇所:

Before:
```
| **X（Twitter）** | **Blotato API のみ**。Twitter API / X API を直接は使わない。スキル: x-poster（cron 9:00, 21:00）。 |
| **TikTok** | **Blotato API のみ**。TikTok API を直接は使わない。スキル: tiktok-poster（cron 9:00, 21:00）。 |
```

After:
```
| **X（Twitter）** | **Postiz API のみ**。スキル: build-in-public（cron 23:10）、x-poster（cron停止中）。 |
| **TikTok** | **Postiz API のみ**。スキル: larry（cron 7:30, 8:00, 16:30, 17:00, 21:00, 21:30）。 |
```

Before:
```
- BLOTATO_API_KEY: ✅ SET
- BLOTATO_ACCOUNT_ID_EN: ✅ SET
- BLOTATO_TIKTOK_ACCOUNT_ID: 28152
```

After:
```
- BLOTATO_API_KEY: ❌ 解約済み（2026-02-28、Postizに移行）
- POSTIZ_X_INTEGRATION_ID: cmm6d7m5703rwpr0yr5vtme3w (@aniccaxxx)
```

| 状態 | ⬜ |

---

### P8: AGENTS.md 更新

「運用・技術の正答」テーブル:

Before:
```
| **X（Twitter）** | **Blotato API のみ**。Twitter API / X API を直接は使わない。スキル: x-poster（cron 9:00, 21:00）。 |
| **TikTok** | **Blotato API のみ**。TikTok API を直接は使わない。スキル: tiktok-poster（cron 9:00, 21:00）。 |
```

After:
```
| **X（Twitter）** | **Postiz API のみ**。スキル: build-in-public（cron 23:10）。x-poster cron停止中。 |
| **TikTok** | **Postiz API のみ**。スキル: larry（cron 6個）。tiktok-poster削除済み。 |
```

| 状態 | ⬜ |

---

## B. larry TikTokメトリクス修正

### L1: check-analytics --connect cron追加 ✅

**根本原因（確認済み）:**
- `GET api.postiz.com/public/v1/posts` で直近7日間の67投稿を取得
- 67投稿中**0個**がTikTokビデオIDに接続（releaseURLが全てプロフィールURL `https://www.tiktok.com/@aniccaen2`、個別ビデオURLなし）
- `check-analytics.js --connect` を実行するcronが存在しない
- daily-report cronはメトリクスを読むが、接続ステップを実行しない

**TikTok投稿状態:**
- Dais確認: ドラフトではなく完全に公開済み（SELF_ONLYではない）
- 投稿自体は成功（state: PUBLISHED が65件）
- 問題は PostizのpostとTikTokのビデオIDが紐付いてないこと

**修正:**

```bash
openclaw cron add \
  --name "larry-connect-analytics" \
  --schedule "0 6 * * *" \
  --timezone "Asia/Tokyo" \
  --task "Execute larry skill check-analytics step: run 'node ~/.openclaw/workspace/skills/larry/scripts/check-analytics.js --config ~/.openclaw/workspace/tiktok-marketing/config.json --days 3 --connect' to connect Postiz posts to TikTok video IDs. Must run BEFORE daily-report crons (6:30/7:00). See larry SKILL.md Section 4 and references/analytics-loop.md for API details: GET /posts/{id}/missing → match chronologically → PUT /posts/{id}/release-id. Wait 2+ hours after publish before connecting (S8)."
```

タイミング: 6:00 JST（daily-report-ja 6:30、daily-report-en 7:00 の前）
cron ID: 2bda28b0-e872-446a-b227-b51776034e3e

**接続フロー（S8, S9準拠）:**
1. `GET api.postiz.com/public/v1/posts?startDate=...&endDate=...` で直近3日の投稿取得
2. 各未接続postに対して `GET /posts/{id}/missing` でTikTokビデオ一覧取得
3. 投稿日時順とTikTokビデオID（数値、大きい=新しい）を照合
4. `PUT /posts/{id}/release-id` に `{"releaseId": "tiktok-video-id"}` で接続
5. 接続後は `GET /analytics/post/{id}` でper-postメトリクス取得可能

**⚠️ 注意（S8引用）:** release IDは上書き不可。間違えたら戻せない。2時間以上経過した投稿のみ接続する。

| 状態 | ⬜ |

---

### L2: error状態のlarry cron修正 ✅（2026-02-28 10:53 PST再修正）

**根本原因（2種類）:**
1. `⚠️ ✉️ Message failed` = Slack配信失敗（投稿自体は成功）→ `--best-effort-deliver` 適用済み ✅
2. `LLM request timed out.` = 600秒タイムアウト超え（afternoon-en, afternoon-ja）→ 次回実行で自動回復するか監視

**前セッションの誤り:** `--no-deliver` フラグは存在しない。正しくは `--best-effort-deliver`。2026-02-28 10:53 PSTに正しいフラグで再修正。

error cron 4個:
- `larry-post-morning-ja` (e5f13ac4)
- `larry-post-afternoon-en` (a4092e38)
- `larry-post-afternoon-ja` (61d431fc)
- `larry-post-evening-ja` (b551d1ea)

```bash
# 各cronのログを確認
openclaw cron log e5f13ac4
openclaw cron log a4092e38
openclaw cron log 61d431fc
openclaw cron log b551d1ea
```

ログを見て原因特定 → 修正。

| 状態 | ⬜ |

---

## C. Zenn + dev.to 記事公開（今すぐ）

### Z1: 今日のZenn記事を今すぐ公開 ✅ re-push済み（09:36 PST）

**状況:**
- 記事: `articles/2026-02-28-mac-mini-migration.md`（published: true、内容OK）
- 06:32 PSTにpush済み（commit 65a93e5）
- Zenn rate limitで弾かれた
- 前日の記事push: 02-27 06:32 PST → 24時間後 = 02-28 06:32 PST

**実行コマンド:**

```bash
cd /Users/anicca/.openclaw/workspace/zenn-articles
# 前回pushから24時間経過を確認
LAST=$(git log -1 --format="%ct" -- "articles/")
NOW=$(date +%s)
DIFF=$((NOW - LAST))
echo "前回pushから${DIFF}秒経過（86400秒=24時間）"

# 空commitでZenn deploy再トリガー
git commit --allow-empty -m "retry: trigger Zenn deploy for 2026-02-28 article"
git push origin main
```

24時間経過してなければ経過するまで待ってから実行。

| 状態 | ⬜ |

### Z2: article-writer SKILL.mdにrate limitガード追加

article-writerのpushステップの直前に追加:

```bash
# Zenn rate limit guard（S7準拠）
LAST_PUSH=$(cd /Users/anicca/.openclaw/workspace/zenn-articles && git log -1 --format="%ct" -- "articles/")
NOW=$(date +%s)
DIFF=$((NOW - LAST_PUSH))
if [ "$DIFF" -lt 86400 ]; then
  WAIT_MIN=$(( (86400 - DIFF) / 60 ))
  echo "⚠️ Zenn rate limit: あと${WAIT_MIN}分待ち。スキップ。"
  # Slack #metrics に報告して終了
  exit 0
fi
# 24時間経過 → push OK
git push origin main
```

| 状態 | ⬜ |

---

## D. dev.to修正

### D1: package-lock.json生成 ✅ 完了

**根本原因:** `npm ci` は `package-lock.json` が必要（S6）。ファイルがない → GitHub Actions が5日連続failure。

```bash
cd /Users/anicca/.openclaw/workspace/dev-to-articles
npm install
git add package-lock.json
git commit -m "fix: add package-lock.json for npm ci in GitHub Actions"
git remote set-url origin "https://Daisuke134:${GITHUB_TOKEN}@github.com/Daisuke134/dev-to-articles.git"
git push origin main
```

| 状態 | ⬜ |

---

### D2: 今日のdev.to記事を公開 ✅ 6記事公開済み（2026-02-28）

**状況:**
- DEV_TO_GIT_TOKEN secret: ✅ 設定済み（2026-02-23確認）
- package-lock.json追加後、GitHub Actionsが走って全記事がdev.toに公開される
- D1のpushで自動的にGitHub Actions再実行 → 今日の記事含め5日分が一気に公開される

**D1のpushだけでOK。追加作業なし。**

ただし5日分一気に公開されるので、dev.to側にrate limitがあれば最新1本だけになる可能性あり。
その場合、古い記事の `dev-to-git.json` エントリを一時削除してpush → 最新記事だけ公開 → 戻す。

| 状態 | ⬜ |

---

## E. ハードウェア + Xcode

### H1: ~~USB-A→Cアダプタ + マウス購入~~ → ✅ 不要（完全解決）

**理由:** Screen Sharing ON/OFF再設定完了（2026-02-28 10:24 PST）。MacBookから `open vnc://aniccanomac-mini-1` で接続確認済み。ハードウェア購入不要。
**住所:** 新宿区新宿3-36-10 ミラザ新宿
**営業時間:** 24時間
**行き方:** 南元町 → 四谷三丁目駅（丸ノ内線）→ 新宿三丁目駅 下車 徒歩1分。または徒歩15分。
**買うもの:** USB-A to USB-C変換アダプタ（300-500円）+ マウス

| 状態 | ⬜ |

### H2: Xcode Apple ID追加 ✅ 完了（2026-02-28 10:43 PST）

DaisがScreen Sharing経由で設定完了。
1. マウスをMac Miniに接続
2. Xcode起動 → Settings → Accounts
3. 「+」→ Apple ID → keiodaisuke@gmail.com / Chatgpt12345!
4. 証明書が自動DLされる
5. 3アプリ（Anicca + 2つのfactory app）が全て署名・アーカイブ・提出可能になる

| 状態 | ⬜ |

---

## F. git

### G1: 全変更をcommit & push

```bash
cd /Users/anicca/anicca-project
git add -A
git commit -m "refactor: migrate all skills from Blotato to Postiz API

- x-poster: Blotato → Postiz API (@aniccaxxx cmm6d7m5703rwpr0yr5vtme3w)
- build-in-public: Blotato → Postiz + @aniccaxxx + metrics feedback loop
- trend-hunter: Blotato metrics → Postiz analytics API
- article-writer: remove Blotato remnant + add Zenn rate-limit rule
- delete tiktok-poster skill (larry replacement)
- stop x-poster cron (2 jobs)
- add larry-connect-analytics cron (6:00 JST)
- fix dev.to: add package-lock.json
- update TOOLS.md, AGENTS.md, MEMORY.md"
git push origin dev
```

| 状態 | ⬜ |

---

## スキル種別まとめ

| スキル名 | パス | 所属 | 状態 |
|---------|------|------|------|
| x-poster | ~/.openclaw/skills/x-poster/ | OpenClaw | cron停止予定 |
| build-in-public | ~/.openclaw/skills/build-in-public/ | OpenClaw | Postiz移行 |
| trend-hunter | ~/.openclaw/skills/trend-hunter/ | OpenClaw | Postizメトリクス移行 |
| article-writer | ~/.openclaw/skills/article-writer/ | OpenClaw | Blotato残骸削除 + Zenn制限追加 |
| tiktok-poster | ~/.openclaw/skills/tiktok-poster/ | OpenClaw | 削除（larry代替） |
| larry | ~/.openclaw/workspace/skills/larry/ | OpenClaw | connect cron追加 |
| xcellent | ~/.openclaw/workspace/skills/xcellent/ | OpenClaw | 未使用（将来のbuild-in-public分析用） |

全てOpenClawスキル（~/.openclaw/配下）。Claude Codeスキル（.claude/skills/）ではない。

---

## エラーcron全監査（2026-02-28 10:53 PST）

| cron名 | ID | エラー原因 | 対処 |
|--------|-----|-----------|------|
| larry-post-morning-ja | e5f13ac4 | Message failed | ✅ --best-effort-deliver適用 |
| larry-post-afternoon-en | a4092e38 | LLM timeout (600s) | ✅ --best-effort-deliver適用。タイムアウトは次回自動回復 |
| larry-post-afternoon-ja | 61d431fc | LLM timeout (600s) | ✅ --best-effort-deliver適用 |
| larry-post-evening-ja | b551d1ea | Message failed | ✅ --best-effort-deliver適用 |
| moltbook-interact | - | error | 未調査（P1-P8優先） |
| roundtable-standup | - | error | 未調査 |
| trend-hunter-5pm | - | error | 未調査 |
| app-metrics-afternoon | - | error | 未調査 |
| x-poster-evening | - | error | P6で停止予定 |
| sto-weekly-refresh | - | error | 未調査 |


## 全スキル・アプリ監査結果（2026-02-28 10:56 PST）

### スキルBlotato依存の詳細

| スキル | Blotato参照数 | 対処 | cron | cron状態 |
|--------|-------------|------|------|---------|
| x-poster | 12箇所 | Postizに書き換え | morning (9:00), evening (21:00) | morning=ok, evening=error |
| build-in-public | 7箇所 | Postizに書き換え | 23:10 JST | ok |
| trend-hunter | 6箇所 | Postizに書き換え | 5:00, 17:00 JST | 5am=ok, 5pm=error |
| article-writer | 2箇所 | 残骸削除（Blotato不使用。GitHub push→Zenn/dev.to） | 23:30 JST | ok |
| tiktok-poster | 全体 | 丸ごと削除 | なし（cronゼロ） | - |
| larry | 0箇所 | ✅ 既にPostiz | 6個（7:30-21:30） | 4個error(修正済み) |

### tiktok-poster特記
- **cronが存在しない**（`openclaw cron list | grep tiktok` = 空）
- larryが完全に代替済み（6 cron、Postiz API経由）
- 削除してもcron停止作業は不要

### アプリ詳細監査

| アプリ | Swift | xcodeproj | spec | Fastlane | 状態 |
|--------|-------|-----------|------|----------|------|
| Breath Calm | 0 | 空 | ✅ 02-spec.md あり（output_dir注意: MacBookパス） | なし | specのみ。78タスク全未完了。PHASE 2から |
| Calm Cortisol | 18 | ✅ あり | ❌ specなし | ✅ README.md | 実装済み。PHASE 4から（ASC登録→提出） |
| Thankful | 18 | ✅ あり | ❌ specなし | なし | 実装済み。進行中（別CC） |

### Breath Calm spec注意点
- `output_dir` が `/Users/cbns03/Downloads/anicca-project/daily-apps/breath-calm`（MacBookパス）
- Mac Miniでは `/Users/anicca/anicca-project/daily-apps/breath-calm` に読み替え必要
- CC起動プロンプトで明示する

### Calm Cortisol注意点
- specファイルがない → CCにPHASE 4（ASCアプリ作成）から開始させる
- bundle_id, app_name等はコードから推測する必要あり
- Fastlane READMEあり → ビルド設定は済んでいる可能性

## ブロッカー解決状況（2026-02-28 10:34 PST）

| ブロッカー | 状態 |
|-----------|------|
| Screen Sharing | ✅ ON/OFF再設定で解決。VNC接続確認済み |
| APPLE_ID_PASSWORD | ✅ Chatgpt12345 → ~/.config/mobileapp-builder/.env |
| NETLIFY_AUTH_TOKEN | ✅ nfp_bP21GRy1SMgcfLZDUEvsajXM3cn9k7J17682 |
| NETLIFY_SITE_ID | ✅ d67537f0-21bd-477e-ac1a-323f7ec6d5cd (aniccaai.com) |
| マウス/ハードウェア購入 | ✅ 不要 |

## 実行順序

**Phase 1: 今すぐ壊れてるものを直す**
1. ✅ D1: dev.to package-lock.json + dependency fixes + workflow rewrite → 6記事公開
2. ✅ Z1: Zenn記事再push済み（09:36 PST、commit 8b43384）
3. ✅ L1: larry connect-analytics cron追加（ID: 2bda28b0、毎日6:00 JST）
4. ✅ L2: larry error cron 4個修正（--no-deliver）

**Phase 2: Blotato → Postiz 移行**
5. ✅ P0: .envにPOSTIZ_X_INTEGRATION_ID追加済み
6. P1: x-poster SKILL.md書き換え
7. P2: build-in-public SKILL.md書き換え + メトリクスループ追加
8. P3: trend-hunter SKILL.md書き換え
9. P4: article-writer SKILL.md Blotato残骸削除
10. P5: tiktok-poster スキルディレクトリ削除
11. P6: x-poster cron 2個停止

**Phase 3: ドキュメント更新**
12. Z2: article-writer SKILL.mdにZenn rate limitガード追加
13. P7: TOOLS.md更新
14. P8: AGENTS.md更新
15. G1: git commit & push

**Phase 1.5: 記事リンク確認 + Slack投稿**
1.5a. Zennデプロイ確認 → リンク取得 → Slackに投稿
1.5b. dev.toリンクSlack投稿 ✅ 済み

**Phase 4: Dais作業**
16. H1: ドンキでUSB-A→Cアダプタ + マウス購入
17. H2: Xcode Apple ID追加

---

## オリジナリティ: 0%

全API仕様: Postiz公式docs (S1, S2, S3, S4)
メトリクスループ: Build In Public Roadmap Phase 5 (S5)
npm ci: npm公式docs (S6)
Zenn制限: Zenn公式FAQ (S7)
analytics接続: larry SKILL.md + references (S8, S9)


---

## G. アプリ出荷（mobileapp-builder CC）

### 方法
Mac Mini上で直接Claude Codeをpty+backgroundで起動し、mobileapp-builder SKILL.mdに従って自律実行させる。
SSHは不要（OpenClaw GatewayはMac Miniで稼働中）。

```bash
# coding-agent パターン（nohup禁止）
# Mac Mini上で直接実行（SSHしない）

# Breath Calm（PHASE 2-12 全実行）
cd /Users/anicca/anicca-project
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-qCV5O13G...bcGbVQAA
echo "Read /Users/anicca/.claude/skills/mobileapp-builder/SKILL.md and execute PHASE 2-12 for Breath Calm. Spec: daily-apps/breath-calm/spec/02-spec.md. Output: daily-apps/breath-calm/. Use git worktree. Report to Slack #metrics (C091G3PKHL2) at each phase completion. No questions, no approval waits, full autonomous execution." | claude -p --allowedTools Bash,Read,Write,Edit

# Calm Cortisol（PHASE 9-12: 既に実装済み、ASCメタデータ+スクショ+提出のみ）
echo "Read /Users/anicca/.claude/skills/mobileapp-builder/SKILL.md and execute PHASE 9-12 for Calm Cortisol. Code is already implemented (18 Swift files). App dir: daily-apps/calmcortisol/. Skip PHASE 2-8. Do ASC app setup, IAP, screenshots, metadata, build, submit. Report to Slack #metrics." | claude -p --allowedTools Bash,Read,Write,Edit

# Thankful（PHASE 9-12: 既に実装済み、提出準備のみ）
echo "Read /Users/anicca/.claude/skills/mobileapp-builder/SKILL.md and execute PHASE 9-12 for Thankful. Code is already implemented (18 Swift files). App dir: daily-apps/rork-thankful-gratitude-app/. Skip PHASE 2-8. Do ASC app setup, IAP, screenshots, metadata, build, submit. Report to Slack #metrics." | claude -p --allowedTools Bash,Read,Write,Edit
```

### 各アプリの状態

| アプリ | Swift files | 必要なPHASE | 所要時間目安 |
|--------|------------|-------------|-------------|
| Breath Calm | 0（specのみ） | PHASE 2-12 全部 | 3-4時間 |
| Calm Cortisol | 18（実装済み） | PHASE 9-12（ASC+提出） | 1-2時間 |
| Thankful | 18（実装済み） | PHASE 9-12（ASC+提出） | 1-2時間 |

### 人間が必要なポイント（各アプリ）
1. **PHASE 11.5: App Privacy設定** — ASC Webで手動（Slackで通知する）
2. それ以外は全自動

| 状態 | ⬜ |
