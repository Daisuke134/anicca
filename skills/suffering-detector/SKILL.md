---
name: suffering-detector
description: "苦しみ/危機を検知して findings を workspace に保存し、必要なら SAFE-T interrupt を行う"
metadata: {"openclaw":{"emoji":"🚨","os":["darwin","linux"]}}
---

# suffering-detector

## 目的
web_search 等で「苦しみ/危機」を検知し、`detections[]` を作成。severity>=0.9 は SAFE-T として `crisis:detected` を emit、Slack 通知で interrupt。

## 保存先

| 種類 | フルパス |
|------|----------|
| 検知結果 | `/Users/anicca/.openclaw/workspace/suffering/findings_YYYY-MM-DD.json` |

## 必須 tools
- `web_search`（苦しみ/危機の検知用）
- `web_fetch`（詳細取得時）

## 実行手順
1. web_search で苦しみ/メンタルヘルス危機関連の最新情報を検索
2. 各検知に severity スコア（0.0-1.0）を付与
3. severity>=0.9 は `crisis:detected` emit + Slack #agents に通知
4. 結果を `workspace/suffering/findings_YYYY-MM-DD.json` に書く
5. cron 実行では X ポストを作成しない。保存と検知だけで終了する。
   手動実行で必要なときだけ、最も多い苦しみパターンについて共感的なXポストを1つ作成する。
   → Postiz API (@aniccaxxx, cmm6d7m5703rwpr0yr5vtme3w) に投稿
   → ヘルプライン/瞑想ガイドは共有しない。共感コンテンツのみ。
   → 複数投稿禁止。1日1ポストのみ。

## 出力 JSON
```json
{
  "date": "YYYY-MM-DD",
  "executedAt": "YYYY-MM-DDThh:mm:ss+09:00",
  "status": "success|error",
  "errorMessage": null,
  "detectionCount": 4,
  "maxSeverity": 0.7,
  "safeTTriggered": false,
  "detections": [
    {
      "severity": 0.7,
      "title": "SNSと若年層の自殺リスク相関",
      "summary": "ソーシャルメディア使用時間と若年層の鬱・自殺リスクの相関を示す新たなエビデンス。特にTikTokの短尺動画による注意散漫化が問題視。",
      "aniccaRelevance": "Aniccaのマインドフルネス介入がこのリスク軽減に貢献できる可能性。",
      "source": "https://..."
    }
  ],
  "overallAssessment": "急性危機なし。継続監視。",
  "aniccaAction": "SNS×メンタルヘルスのコンテンツを次回trend-hunterのhookテーマに追加検討。"
}
```

## Slack 報告
cron 実行では Slack 送信をしない。検知結果は JSON ファイルへ保存して終了する。
手動実行で共有が必要な場合のみ、別途人手で Slack に転記する。

**⚠️ 禁止事項**: JSON をそのまま Slack に貼ること。

# FIX by skill-fixer 2026-04-27:
# 原因: cron 実行時の Slack 送信が失敗しやすく、`Message failed` / 送信系エラーの再発源になっていた。
# 修正: cron では Slack 送信を完全禁止し、保存のみ行うように変更した。

# FIX by skill-fixer 2026-04-28:
# 原因: 共有用Xポストまで実行すると cron が長時間化して timeout になっていた。
# 修正: cron では検知と JSON 保存に限定し、投稿は手動実行時のみへ移した。

## 失敗時
- 5xx: 次回 cron で再実行（冪等）。

## Cron
- 2回/日: 05:15, 17:15 JST
