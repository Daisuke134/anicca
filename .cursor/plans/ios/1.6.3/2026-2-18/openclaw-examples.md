# OpenClaw実例集（2026-02-17調査）

## トップユースケース（実装候補）

### 1. CEOダッシュボード＋朝ブリーフ (@danpeguine)
- タスクの重要度・緊急度をアルゴリズムでスコアリング
- カレンダーにタスクをタイムブロック
- 毎朝のデイリーブリーフ: 天気、週目標、健康統計、会議予定、リマインダー、トレンド、読むべき記事、名言
- 打ち合わせ前に相手を調査してブリーフィング資料作成
- サブエージェントをスポーンしてビジネスアイデアリサーチ

### 2. 4エージェント体制 (@iamtrebuh)
- Milo（リーダー）：戦略・計画
- Bob（開発）：コーディング
- Angela（マーケ）：リサーチ・コンテンツ
- Josh（ビジネス）：価格・メトリクス
- 共有メモリ + エージェント個別コンテキスト
- Telegram経由で24/7稼働

### 3. アイデア→夜間実験→朝レビュー (@antonplex)
- アイデアをTASKとしてログ
- 夜間cronでサブエージェントがリサーチ・実験
- 朝レビュー → Decision Record（ADR形式）

### 4. 15+エージェント軍団 (@jdrhyne)
- 10,000通のメール初日クリア
- GA4/Jira/GSCスキルをその場で自作→ClawHub公開
- Codexエージェントをオーケストレーション
- LinkedIn/Xの投稿を自分の声で下書き

### 5. 生活完全自動化 (@dreetje)
- メール/スパム削除/買い物注文/GitHub Issue/1Password読み書き
- 友人チャットでなりすまし/電話で会話

### 6. 犬の散歩中にデプロイ修正 (@georgedagg_)
- Railway失敗検出→ログレビュー→原因特定→設定修正→再デプロイ→PR提出
- 全部音声で完了

### 7. 食事プランニング (@stevecaldwell)
- Notionに365日食事プラン、店舗・通路別買い物リスト、天気連動

### 8. ヘルス+生活統合 (@bangkokbuild)
- Garmin Watch連携、Obsidian日次ノート、東京地震モニタリング、沈黙時安否確認

## ツール確認結果
- Firecrawl CLI v1.3.1: 10,243クレジット、search/scrape/crawl/agent全動作
- Playwright CLI: screenshot/pdf/codegen全動作（VPS）
- OpenClaw browser: CDP経由ビルトイン

## Codex vs Claude Code
- Codex: 遅いが正確。リファクタリング・実装向き。ツール/MCP使えない
- Claude Code: 速い。ツール/スキル/MCP得意。慎重な実装には不向き

## ワークツリールール
- dev branch → originated worktree ALWAYS
- night-builderは各タスクを別ワークツリーで並列実装
