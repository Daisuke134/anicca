# Skill Interface Contracts: naist-funds

**Date**: 2026-02-24

## scripts/fetch.js

```
入力: なし（環境変数 FIRECRAWL_URL で上書き可能）
出力: Grant[] — JSON文字列をstdoutに出力
エラー: exit code 1 + stderr にエラーメッセージ

動作:
  1. Firecrawl CLIでJSPS/JST/JFUNDをスクレイピング
  2. Markdownをパースして Grant[] に変換
  3. JSON.stringify(grants) を stdout に出力
```

## scripts/notify.js

```
入力: なし（fetch.js の出力を内部で呼び出す）
出力: Slack投稿結果サマリーをstdoutに出力
      例: "5件の新着情報を投稿しました（スキップ: 3件）"
エラー: exit code 1 + stderr にエラーメッセージ

動作:
  1. fetch.js を実行して Grant[] を取得
  2. cache.json と照合して未通知のみ抽出
  3. 締切30日以内に ⚠️ マーク付与
  4. Slackに投稿
  5. cache.json を更新
```

## scripts/guide.js

```
入力: process.argv[2] = 検索キーワード文字列
出力: 申請手順をstdoutに出力（Slack投稿形式）
エラー: exit code 1

動作:
  1. guides.json を読み込む
  2. キーワード部分一致で検索
  3. HIT → steps を番号付きで出力
  4. MISS → officialUrl案内メッセージを出力

使用例:
  node scripts/guide.js "学振DC1"
  node scripts/guide.js "CREST"
```

## scripts/scan.js（cronエントリポイント）

```
入力: なし（cronから起動）
出力: Slackに投稿 + stdoutにサマリー
エラー: exit code 1 + SlackにエラーURL通知

動作:
  1. notify.js のロジックを実行
  2. 失敗時はSlackにエラー通知
  3. 成功時は "スキャン完了: N件新着" をstdoutに出力
```

## scripts/utils/storage.js

```
loadCache() → NotifiedCache
saveCache(cache: NotifiedCache) → void  // tmp + renameSync で原子的書き込み

loadGuides() → { guides: GuideKnowledge[] }
```

## scripts/utils/slack.js

```
sendMessage(message: string) → void
  内部: exec `openclaw message send --channel slack --target $SLACK_CHANNEL_ID --message "..."`

環境変数:
  SLACK_CHANNEL_ID: 投稿先チャンネルID（必須）
```

## Slack メッセージ形式

```
📢 *助成金・奨学金 新着情報* (2026-02-24)

⚠️ *[締切間近] 学術研究助成基金助成金*
🏢 JSPS | 💰 上限500万円 | 📅 締切: 2026-02-28
概要: 若手研究者向け助成金。単独PIが対象。
🔗 https://www.jsps.go.jp/...

*JST さきがけ 2026年度公募*
🏢 JST | 💰 上限4,000万円/3年 | 📅 締切: 2026-04-15
概要: 戦略的創造研究推進事業。博士号取得者対象。
🔗 https://www.jst.go.jp/...

---
新着: 5件 | スキップ（既通知）: 8件
```
