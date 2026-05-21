# エージェント出力ルール：または/もしくは禁止・一つに決める

**日付:** 2026-02-14

## ルール
- 回答で **「または」「もしくは」を出して選択肢を並べることを禁止**する。
- ベストプラクティスを調べたうえで **答えは一つに決め**、理由を付けて述べる。
- ユーザー指示：「there is best practice, so there is answer. So you decide.」

## trend-hunter の slot/日付の決め方（決定事項）
- **採用:** cron の payload で slot と date を渡す。
- **理由:** OpenClaw GitHub #4629 の提案は「date/time を context に inject する」。エージェントに `date` を叩かせるのは workaround。cron の payload をこちらで制御できるので、inject を採用する。SKILL には「payload の slot と date をそのまま使う。時刻を推測したり date を叩いたりしない」と書く。
