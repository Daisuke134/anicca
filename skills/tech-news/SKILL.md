---
name: tech-news
description: "X から AI/iOS/行動変容の最新テックニュースを取得する"
metadata: {"openclaw":{"emoji":"📰","os":["darwin","linux"]}}
---

# tech-news

## 目的
X（Twitter）から AI・iOS・行動変容・マインドフルネス関連の最新テックニュースを取得。Anicca の MRR 改善に直結する情報を抽出する。

## 保存先
| 種類 | フルパス |
|------|----------|
| ニュース | `/Users/anicca/.openclaw/workspace/tech-news/news_YYYY-MM-DD.json` |

## 必須 env
| キー | 用途 |
|------|------|
| `X_BEARER_TOKEN` | X API 認証 |

## ソース制限
**x-research スキルのみ使用。web_search は禁止。**

X API クレジットが枯渇している場合（402 エラー）→ status: error として「X API credits depleted」を記録。フォールバックしない。

## 実行手順

### 1. x-research で検索（3クエリ）
```bash
cd ~/.openclaw/skills/x-research

# AI/LLM ニュース
bun run x-search.ts search "AI app subscription revenue OR LLM mobile app" --sort likes --limit 10 --quick

# iOS 行動変容
bun run x-search.ts search "iOS behavioral change app OR mindfulness app growth" --sort likes --limit 10 --quick

# RevenueCat / paywall 最適化
bun run x-search.ts search "RevenueCat paywall optimization OR trial conversion rate" --sort likes --limit 10 --quick
```

### 2. 結果をフィルタ・要約
各ツイートについて:
- 元URL（`https://x.com/{user}/status/{id}`）
- いいね数・RT数
- **5行以上の詳細要約**（1行要約は禁止。何が起きたか、誰が言ったか、データは何か、を具体的に書く）
- **MRR への影響**: このニュースが Anicca の収益にどう関係するか（具体的な数値・ファイルパス込み）
- **implementation**: 実装手順（これが「今日やること」。別フィールドにしない）

### 3. 出力 JSON
```json
{
  "date": "YYYY-MM-DD",
  "executedAt": "YYYY-MM-DDThh:mm:ss+09:00",
  "status": "success|error",
  "errorMessage": null,
  "queries": ["query1", "query2", "query3"],
  "articles": [
    {
      "title": "要約タイトル",
      "url": "https://x.com/user/status/xxx",
      "author": "@username",
      "likes": 150,
      "retweets": 30,
      "summary": "5行以上の詳細要約。何が起きたか、データは何か、誰が言ったか、背景は何か、を具体的に書く。",
      "mrrImpact": "Aniccaへの具体的影響。CVR改善の可能性、実装難易度、前提条件。",
      "implementation": "1. 具体的な実装ステップ\n2. 対象ファイルパス\n3. 検証方法",
      "category": "ai|ios|behavioral|revenue"
    }
  ],
  "topInsight": "今日の最重要インサイト（MRR直結）"
}
```

**⚠️ todayAction フィールドは使わない。implementation が「今日やること」そのもの。**

### 4. Slack 報告
**【絶対】** Slack #metrics（`{{profile.channels.reportChannel}}`）に投稿。

```
📰 tech-news (HH:mm JST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔝 今日の最重要インサイト:
[MRR直結の最重要発見を2-3行で]

━━━ 記事詳細 ━━━

📌 [1] タイトル
@author (❤️XX 🔁XX) — URL

詳細: 5行以上の詳細要約。何が起きたか、データは何か、
誰が言ったか、背景は何か。1行要約は禁止。

🎯 MRR影響: Aniccaへの具体的影響。数値込み。

🔧 実装:
1. 具体的ステップ
2. 対象ファイルパス
3. 検証方法

━━━

📌 [2] タイトル
@author (❤️XX 🔁XX) — URL
（同じ形式で）
```

## 失敗時
- X API 402 (credits depleted) → status: error。フォールバック禁止。
- その他エラー → status: error、理由記録。

## Cron
- 1回/日: 05:20 JST
