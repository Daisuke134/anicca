---
name: openclaw-usecase
description: "X から OpenClaw の最新ユースケース・Tips・ベストプラクティスを取得する"
metadata: {"openclaw":{"emoji":"🐾","os":["darwin","linux"]}}
---

# openclaw-usecase

## 目的
X 上の OpenClaw 関連投稿を収集。新しいプラグイン、設定Tips、他ユーザーの自動化事例を学び、Anicca の運用改善に活かす。

## 保存先
| 種類 | フルパス |
|------|----------|
| ユースケース | `/Users/anicca/.openclaw/workspace/openclaw-usecase/usecases_YYYY-MM-DD.json` |

## 必須 env
| キー | 用途 |
|------|------|
| `X_BEARER_TOKEN` | X API 認証 |

## ソース制限
**x-research スキルのみ使用。web_search は禁止。**

## 実行手順

### 1. x-research で検索（3クエリ）
```bash
cd ~/.openclaw/skills/x-research

# OpenClaw 全般
bun run x-search.ts search "OpenClaw OR openclaw" --sort recent --limit 15 --quick

# AI エージェント自動化（OpenClaw 以外も含む）
bun run x-search.ts search "AI agent automation daily routine OR autonomous agent cron" --sort likes --limit 10 --quick

# ClawHub スキル
bun run x-search.ts search "ClawHub skill OR clawhub.com" --sort recent --limit 10 --quick
```

### 2. ユースケース抽出
各投稿について:
- URL
- 投稿者
- いいね数・RT数
- **5行以上の詳細要約**（何をしたか、どう設定したか、結果はどうだったか。1行要約は禁止）
- **Anicca への適用可能性**: 具体的に何を取り入れるべきか（ファイルパス・実装ステップ込み）
- **implementation**: 実装手順（これが「今日やること」。別フィールドにしない）
- カテゴリ: plugin / config / automation / skill / community

### 3. 出力 JSON
```json
{
  "date": "YYYY-MM-DD",
  "executedAt": "YYYY-MM-DDThh:mm:ss+09:00",
  "status": "success|error",
  "errorMessage": null,
  "usecases": [
    {
      "title": "要約タイトル",
      "url": "https://x.com/user/status/xxx",
      "author": "@username",
      "likes": 50,
      "retweets": 12,
      "summary": "5行以上の詳細要約。何をしたか、どう設定したか、結果はどうだったか。",
      "applicability": "Aniccaへの具体的適用方法。ファイルパス込み。",
      "implementation": "1. 具体的な実装ステップ\n2. 対象ファイルパス\n3. 検証方法",
      "category": "plugin|config|automation|skill|community",
      "priority": "high|medium|low"
    }
  ],
  "topUsecase": "今日の最重要ユースケース"
}
```

**⚠️ todayAction / implementationNote フィールドは使わない。各ユースケースの implementation が「今日やること」そのもの。**

### 4. Slack 報告
**【絶対】** Slack #metrics（`{{profile.channels.reportChannel}}`）に投稿。

```
🐾 openclaw-usecase (HH:mm JST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔝 今日の最重要ユースケース:
[2-3行で要約]

━━━ ユースケース詳細 ━━━

🔧 [1] タイトル [HIGH/MEDIUM/LOW]
@author (❤️XX 🔁XX) — URL

詳細: 5行以上の詳細要約。何をしたか、どう設定したか、
結果はどうだったか。1行要約は禁止。

💡 Anicca適用:
具体的にどう活かすか。

🔧 実装:
1. 具体的ステップ
2. 対象ファイルパス
3. 検証方法

━━━

🔧 [2] タイトル [HIGH/MEDIUM/LOW]
（同じ形式で）
```

## 失敗時
- X API 402 → status: error。フォールバック禁止。

## Cron
- 1回/日: 05:30 JST
