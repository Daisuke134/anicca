# 2026-02-17 1.6.3運用監査（GitHub Actions・APN・コスト異常）

- 更新日時: 2026-02-17
- 範囲: GitHub Actions / OpenClaw(VPS) Cron / 1.6.3ルールベース運用の理解
- 方針: 修正は行わず、現状の実態と影響だけを整理

## 1) まず結論（短く）

- **Apify 402** は「不正利用」ではなく、**Apifyの課金状態・権限・契約アクター条件**由来の `Payment Required`。
- `sora2/text-to-video` は、今回確認できた範囲では**現行実行フローのメインで使われていない**。
- **1.6.3の本線は「APN + ルールベース」中心**として使えるが、`generateNudges.js` はそのまま残る限り「完全停止」にはならない。
- `generateNudges` は **現在も手動起点で復活させられる**。
- GitHub Actions と VPS(OpenClaw) cron は**別系統**。片方を消してももう片方は生きる。
- `daily-metrics` の失敗は Apify とは別で、**環境変数不足（MIXPANEL）＋ Slack 送信失敗**。

---

## 2) GitHub Actions YAML一覧（削除可否）

### `.github/workflows/fetch-tiktok-metrics.yml`
- 役割: 毎日 01:00 UTC 定期 + 手動実行で TikTok メトリクス取得。
- 実装: `scripts/anicca-agent/fetch_metrics.py` が Apify `clockworks~tiktok-scraper` を叩く。
- 影響: `402 Payment Required` の元。
- **削除可否:** メトリクス参照が不要なら削除可能。

### `.github/workflows/fetch-x-metrics.yml`
- 役割: 毎日 01:00 UTC 定期 + 手動で X 指標の取得。
- 実装: `scripts/x-agent/fetch_x_metrics.py`。
- **削除可否:** X指標を使わないなら削除可能。

### `.github/workflows/daily-metrics.yml`
- 役割: 日次レポート生成・Slack通知。
- 失敗時エラー: `MIXPANEL_SERVICE_ACCOUNT` が無い + Slack `no_service`。
- **削除可否:** このレポート運用を捨てるなら削除。必要なら設定修正必須。

### `.github/workflows/trigger-commander.yml`
- 役割: `workflow_dispatch` のみ。手動で `/api/admin/trigger-nudges` を呼ぶ。
- **重要:** これは `generateNudges` を起動させる入口。
- **削除可否:** もう使わないなら削除が適切（安全）。

### `.github/workflows/anicca-daily-post.yml`
- 役割: 手動投稿（TikTok Agent）。
- 画像生成〜投稿ルートを含む。
- **削除可否:** TikTok運用を維持するなら残す。日次自動化不要なら削除。

### `.github/workflows/anicca-x-post.yml`
- 役割: 手動投稿（X）。
- **削除可否:** X運用を維持するなら残す。

### `.github/workflows/cross-post-tiktok-to-ig.yml`
- 役割: TikTok→Instagram クロスポストの手動ワークフロー。
- **削除可否:** クロスポストを行わないなら削除。

### `.github/workflows/tiktok-card-post.yml`
- 役割: TikTok カード投稿（予約・Git 管理・投稿）
- **削除可否:** 毎日カード投稿を継続するなら残す。

---

## 3) Apify 402 が意味すること

- メッセージ: `Apify scrape failed: 402 Client Error: Payment Required for url: https://api.apify.com/v2/acts/clockworks~tiktok-scraper/runs`
- 意味: **Actor 実行に対する課金条件未充足または権限不足**。
- 具体的には、
  - APIトークンに残高/請求上の制約
  - そのActorの有料機能/プラン権限
  - 口座側で課金状態が無効
  
のいずれか。

- したがってこれは「ハッキング」サインではなく、**実行先の課金条件問題**として扱う。

---

## 4) `sora2/text-to-video` の扱い（高コスト懸念）

- `data/viralfal (2).json` に残る `text-to-video` は、保存・履歴データにある可能性が高い。
- 現行ワークフローの主幹（今回確認範囲）は、
  - 画像系モデル（例: `fal-ai/nano-banana-pro`）
  - Blotato を使った投稿
  が中心。
- よって今回のコスト急増を**即 `sora2/text-to-video`の強制実行」とは切り分けるべき。
- ただし「将来別プロセスで誤実行している」可能性はゼロでないため、実サービス側の実行履歴（APIfactory/請求明細）で最終確認が必要。

---

## 5) 1.6.3 の「誰が何を作るか」

- 現在の理解では、
  - **APN ルールベース配信**（常時運用）
  - に対して、`generateNudges.js` は「完全停止」ではない。

### `generateNudges.js` について
- 該当ジョブは完全ルールベースではなく、条件で LLM 経路を含む実装。
- `CRON_MODE=nudges` か、管理者手動の `/api/admin/trigger-nudges` を経由して起動。
- 運用上は、
  - 「APN で rule-basedだけで回したい」なら `generateNudges` の起動経路を止める or ガードする。
  - APNは別系統で残せる。

---

## 6) Railway Cron / VPS(OpenClaw) Cron の関係

- GitHub Actions = GitHub 側のジョブ。
- OpenClaw/VPS = VPS 側 `jobs.json` ベースのcron。
- **完全に独立**。
- したがって `trigger-commander` を消しても、VPSの app-nudge cron が生きていると実働は継続する。
- 逆も同様。

---

## 7) `daily-metrics` の失敗意味

- `Mixpanel failed: KeyError: 'MIXPANEL_SERVICE_ACCOUNT'`
  - 必須の環境変数が未設定。
- `Slack API returned 404: no_service`
  - Slack 送信先設定が壊れている/未設定。
- この失敗は「APN停止」や「sora2利用」と直接は同じ原因ではない。

---

## 8) ユーザー質問への個別回答（そのまま返答用）

- 「GitHub Actions は全て VPS で実行しているのか？」
  - いいえ。VPSは別系統。
- 「GitHub Actions YAML は何が走ってる？」
  - 上記 8 ファイルが該当。削除可否は運用目的次第。
- 「fetch_tiktok の 402 はハック？」
  - いいえ。Apify利用権/請求条件エラー。
- 「sora2/text-to-video 参照は悪用か？」
  - 直近実行フローの主軸では「履歴・保存データの痕跡」が濃い。即時悪用とは断定できない。
- 「1.6.3 はルールベース+APNだけか？」
  - APNルートは可能。`generateNudges.js` は別に残っているので、完全停止ではない。
- 「generateNudgesを消すべき？」
  - LLM経路を将来再利用しないなら、起動入口（スケジュール・手動トリガ）も含めて停止・削除するのが安全。
- 「cronは消すべき？」
  - 役割別に分離して判断。不要なら削除可能だが、APNルートを維持したいなら必要なジョブだけ残す。

---

## 9) 今回の結論（最短版）

- `sora2/text-to-video` の参照だけで「今まさに使われており不正に消費されている」とは言えない。
- 402 は支払い/権限エラー。
- 1.6.3を「毎日ルールベース+APN」に寄せるなら、
  - GitHub Actions は機能削減リストにあるもの（`trigger-commander`, `fetch-*`, `daily-metrics` など）を削除。
  - ただし投稿系(`tiktok-card-post`, `anicca-daily-post`, `anicca-x-post`, 必要なら cross-post)は保持。
  - `generateNudges` は手動トリガ経路を止めないと、完全停止ではない。

## 2026-02-17: 追加実行方針（現在決定）

- 方針: 当面は GitHub Actions の cron 停止 + LLM経路を止めた状態でルールベース運用を継続。
- 前提: VPS(OpenClaw) 側は別系統のため、現時点は触らない。

### ToDo（確定）

1) GitHub Actions cron 停止（対象3ファイル）
- `.github/workflows/fetch-tiktok-metrics.yml`
  - `schedule: '0 1 * * *'` を削除（`workflow_dispatch` のみ残す）
- `.github/workflows/fetch-x-metrics.yml`
  - `schedule: '0 1 * * *'` を削除（`workflow_dispatch` のみ残す）
- `.github/workflows/daily-metrics.yml`
  - `schedule: '15 20 * * *'` を削除（`workflow_dispatch` のみ残す）
- 補足: `daily-metrics.yml` は重複表記しない。対象は実体1ファイル。

2) `generateNudges.js` をルールベース固定に変更
- `shouldUseLLM` 判定経路を無効化（LLM分岐不可にする）
- ルールベース経路だけで nudge を生成する状態にする
- `trigger-commander.yml` は今は残す（手動テスト用途）。

3) 最小検証
- `trigger-commander` をステージングで1回実行し、LLM利用ログが出ないことを確認
- 生成結果がルールベース由来であることを確認
- cron 停止＋LLM固定化の効果を `ops-audit.md` に記録

### 受け入れ条件
- 当該3つの workflow が定期実行しないこと
- `generateNudges` 実行時に `sora系`/LLMテキスト生成経路に進まないこと
- 既存ユーザー向けのルールベース処理への影響を出さないこと
