---
name: build-in-public
description: Posts daily "Day N of building Anicca" tweet to X. Reads today's diary, fetches MRR/Trial from RevenueCat API, and posts via Postiz API to @aniccaxxx. Use when build-in-public cron fires or user asks to post development progress.
---

# build-in-public SKILL

## 概要

毎日のAnicca開発活動をX（Twitter）アカウント@aniccaxxxにBuild in Public形式で投稿する。

**Sources:**
- [ClawHub twitter skill](https://clawhub.ai/blueberrywoodsym/twitter) — Phase1 Niche Research + Phase2 Framework Writing
- [Copyblogger headline formula](https://copyblogger.com/10-sure-fire-headline-formulas-that-work/) — "8 out of 10 readers only read the headline"

---

## 実行手順（この順番で実行する）

### Step 1: 環境設定

```bash
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
source /Users/anicca/.openclaw/.env
TODAY=$(TZ=Asia/Tokyo date +%Y-%m-%d)
MONTH_DAY=$(TZ=Asia/Tokyo date +%-m/%-d)
```

### Step 1.5: 昨日の投稿メトリクス取得（Postiz Analytics API）

```bash
YESTERDAY=$(TZ=Asia/Tokyo date -v-1d +%Y-%m-%dT00:00:00.000Z 2>/dev/null)
TODAY_END=$(TZ=Asia/Tokyo date +%Y-%m-%dT23:59:59.000Z)

POSTS_RESPONSE=$(curl -s -H "Authorization: ${POSTIZ_API_KEY}" \
  "https://api.postiz.com/public/v1/posts?startDate=${YESTERDAY}&endDate=${TODAY_END}")

LATEST_POST_ID=$(echo "$POSTS_RESPONSE" | python3 -c "
import json,sys
data = json.loads(sys.stdin.read())
posts = data.get('posts',[])
for p in posts:
    integ = p.get('integration',{})
    if integ.get('id') == 'cmm6d7m5703rwpr0yr5vtme3w':
        print(p['id'])
        break
" 2>/dev/null)

if [ -n "$LATEST_POST_ID" ]; then
  METRICS=$(curl -s -H "Authorization: ${POSTIZ_API_KEY}" \
    "https://api.postiz.com/public/v1/analytics/post/${LATEST_POST_ID}")
  mkdir -p ~/.openclaw/workspace/build-in-public
  echo "$METRICS" > ~/.openclaw/workspace/build-in-public/metrics-$(TZ=Asia/Tokyo date +%Y-%m-%d).json
  echo "昨日のメトリクス: $METRICS"
fi
```

### Step 2: diaryを読む

```bash
DIARY_PATH="/Users/anicca/.openclaw/workspace/daily-memory/diary-${TODAY}.md"
if [ ! -f "$DIARY_PATH" ]; then
  YESTERDAY=$(TZ=Asia/Tokyo date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
  DIARY_PATH="/Users/anicca/.openclaw/workspace/daily-memory/diary-${YESTERDAY}.md"
fi
```

diaryの内容から「今日やったこと」を3〜4行で抽出する。

### Step 3: RevenueCat APIからMRR/Trial取得

```bash
# RevenueCat v2 API（REVENUECAT_V2_SECRET_KEY を使う。v1 REVENUECAT_API_KEY は使うな）
source ~/.openclaw/.env
RC_RESPONSE=$(curl -s \
  -H "Authorization: Bearer ${REVENUECAT_V2_SECRET_KEY}" \
  -H "Content-Type: application/json" \
  "https://api.revenuecat.com/v2/projects/projbb7b9d1b/metrics/overview")

MRR=$(echo "$RC_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('mrr', d.get('metrics',{}).get('mrr',0)))" 2>/dev/null || echo "0")
ACTIVE_TRIALS=$(echo "$RC_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('active_trials', d.get('metrics',{}).get('active_trials',0)))" 2>/dev/null || echo "0")

MRR_DISPLAY=$(python3 -c "v=${MRR}; print(f'\${int(v)}' if v >= 1 else f'\${v}')" 2>/dev/null || echo "\$${MRR}")
```

### Step 4: Day N 計算

Day 1 = 2025-12-31。

```bash
DAY_N=$(python3 -c "
from datetime import date
start = date(2025, 12, 31)
today = date.today()
import subprocess
today_str = subprocess.check_output(['date', '-u', '+%Y-%m-%d'], env={'TZ': 'Asia/Tokyo'}).decode().strip()
today = date.fromisoformat(today_str)
delta = (today - start).days + 1
print(delta)
")
```

### Step 5: ツイートを書く（ClawHub twitter skill Phase 1+2）

**Phase 2: ツイートフォーマット（固定）**

```
{MONTH_DAY}. Day {N} of building Anicca to $1k MRR.

{MRR_DISPLAY} MRR. {ACTIVE_TRIALS} trials.

started xxx
built xxx
shipped xxx

[one line comment in English]
```

**ライティングルール（Copyblogger + daily.dev準拠）:**

| ルール | 詳細 |
|--------|------|
| 数字を使う | `$17 MRR` > `少しのMRR`、`53日目` > `数週間` |
| 動詞で始める | `started / built / shipped / fixed / tested / published` |
| 具体的にする | `started paywall A/B test` > `アプリ改善した` |
| 絵文字は使わない | Build in Public はシンプルが強い |
| 3〜5行の活動 | diaryから重要なものを選ぶ（全部書かない） |

### Step 6: Postiz APIで@aniccaxxxに投稿

```bash
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

POST_ID=$(echo "$POSTIZ_RESPONSE" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('posts',[{}])[0].get('id',''))" 2>/dev/null)
RELEASE_URL=$(echo "$POSTIZ_RESPONSE" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('posts',[{}])[0].get('releaseURL',''))" 2>/dev/null)
```

### Step 7: Slack #metrics に報告

# FIX by skill-fixer 2026-04-01:
# 原因: cron payload に "Do NOT call the message tool" と書いてあるのに SKILL.md が message tool 呼び出しを強制 → "Message failed" エラー（2連続）
# 修正: cron delivery が Slack 報告を自動処理するため、Step 7 をスキップする指示に変更

**cron から呼ばれた場合: このステップをスキップする。cron delivery (announce mode) が自動的に Slack #metrics へ報告する。**

手動実行の場合のみ以下を実行:
```bash
openclaw message send --channel slack --target '{{profile.channels.reportChannel}}' \
  --message "🐦 build-in-public 実行完了
Day ${DAY_N}目 / ${MRR_DISPLAY} MRR / ${ACTIVE_TRIALS} trial
投稿先: X @aniccaxxx (Postiz integration: cmm6d7m5703rwpr0yr5vtme3w)
X リンク: ${RELEASE_URL}
ツイート内容:
${TWEET_TEXT}"
```

---

## エラーハンドリング

| エラー | 対処 |
|--------|------|
| diaryが存在しない | 昨日のdiaryをフォールバック。なければMRR/Trial数だけで投稿 |
| RevenueCat API失敗 | `$?? MRR` / `? trial` でフォールバック投稿 |
| Postiz API失敗 | Slack #metrics にエラー内容を報告して終了 |
| POSTIZ_API_KEY未設定 | `source /Users/anicca/.openclaw/.env` を必ず実行すること |

---

## 絶対禁止

| 禁止 | 理由 |
|------|------|
| exec claude を使う | Aniccaが自分でやる |
| Slack報告をスキップ | MANDATORY |
| "announce" delivery mode | output垂れ流しになる。`delivery.mode: "none"` 一択 |
| MRRを省略する | 数字が信頼性の源泉 |

---

## v0.2.0 追加（2026-05-07）— 分析ループ + ヘッドライン回転 + thread-split

以下は v0.2.0 で追加された機能。既存の本体フロー（上記）は維持したまま、Step 0 / Step 4 / Step 5 を追加。

### ウィザード（初回起動時）

| フィールド | デフォルト | 説明 |
|-----------|-----------|------|
| `POSTIZ_API_KEY` | (.env) | Postiz API key |
| `POSTIZ_WORKSPACE_ID` | (.env) | Postiz workspace |
| `bip.auto_confirm` | `false` | true ならユーザー確認なしで投稿 |
| `bip.repo_path` | `~/anicca-project` | git diff など参照する開発リポジトリ |
| `bip.lookback_days` | `14` | 分析キャッシュの遡及日数 |
| `bip.headline_pool` | (Copyblogger 22) | ヘッドライン公式の母集団 |

### Step 0: ヘッドライン公式を分析キャッシュから決める

```python
# 1. ~/.openclaw/workspace/build-in-public/postiz-cache.json を読む
# 2. 直近7日のengagement中央値を計算
# 3. 直近の投稿が中央値の <50% なら "fatigue" 判定
# 4. fatigue: 直近5日に使った formula を除外し、Copyblogger 22 から無作為に1つ選ぶ
# 5. それ以外: 通常の rotation
```

Copyblogger 22 公式 (現状 rotation in use の 4 / 全 22):

1. How to ___ (in use)
2. ___ Reasons Why ___ (in use)
3. ___ Steps to ___
4. The Ultimate Guide to ___
5. The Beginner's Guide to ___
6. Why ___ Is ___ (and What to Do About It)
7. ___ Lessons I Learned from ___ (in use)
8. The Truth About ___
9. ___ Mistakes Most ___ Make (and How to Avoid Them)
10. What I Learned from ___
11. The Secret of ___
12. ___ Things You Didn't Know About ___
13. ___ Tips for ___ (in use)
14. The Single Most Important ___
15. The Surprising Truth About ___
16. How ___ Made Me ___
17. ___ Days of ___ (avoid — duplicates Day N format)
18. Stop ___! Try This Instead
19. The Anatomy of ___
20. From ___ to ___ in ___ Days
21. The ___ Manifesto
22. ___ Ways to ___

### Step 4: thread-split

`scripts/thread-split.py` で本文 280 char 超を「1/n」「2/n」スレッドに自動分割。URL を保護し、句点で切る greedy split。

```bash
echo "$TWEET_BODY" | python3 ~/.openclaw/skills/build-in-public/scripts/thread-split.py
```

### Step 5: retry + 🚨 通知

`scripts/retry-postiz.py` を介して Postiz POST。`30s × max 3 attempts`。最終失敗時は `~/.openclaw/delivery-queue/build-in-public-alerts/` に書き込んで Slack `{{profile.channels.reportChannel}}` に🚨。

### Postiz 分析ループ（cron: bip-postiz-pull, daily 23:00 JST）

`scripts/pull-analytics.py` が `sent_YYYY-MM-DD.json` を遡って読み、Postiz GET `/analytics/post/{id}` を呼んで `postiz-cache.json` を更新。

### 週次 top3/bottom3 ロールアップ（cron: bip-weekly-rollup, Sun 20:00 JST）

直近7日の post を engagement 順にソートして top-3 / bottom-3 を Slack に投稿。プロンプトに `top3` の本文を「真似ろ」、`bottom3` の本文を「避けろ」として注入する用途。

### ファイル

| 項目 | パス |
|------|------|
| 送信台帳 | `~/.openclaw/workspace/build-in-public/sent_YYYY-MM-DD.json` |
| 分析キャッシュ | `~/.openclaw/workspace/build-in-public/postiz-cache.json` |
| ヘッドライン履歴 | `~/.openclaw/workspace/build-in-public/headline-history.json` |
| ログ | `~/.openclaw/logs/build-in-public/` |
