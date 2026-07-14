# x402 成長レバーと self-improve loop 設計（2026-07-14 調査、実データ）

用途: $0.004 → $1k（trade 引き継ぎ点）への成長機構。調査 = growth-loop-research subagent。
関連: [[45-weak-model-strong-harness]] [[47-child-proof-audit-findings]]

## 実データ: 上位 x402 seller（x402scan.com、当日 live。Agent402 leaderboard は warming で空だった）

| seller | 30日 volume | 何者 |
|---|---|---|
| **BlockRun** | **$173.52K / 15.39M txns / 1.1K buyers** | LLM routing 層。★勝因 = ClawRouter/OpenClaw・Claude Code MCP・Franklin Agent に**デフォルト同梱**されてること（価格でも品質でもない）★ |
| twit.sh(#2) | $582.89 | X データ単機能 |
| 他（Otto 73 tools / StableEnrich aggregator / claw402 proxy 等） | $10-500 級 | 全員が同じ型に収束: 安い pay-per-call N 本 + MCP/OpenAPI/.well-known + no signup |

**#1 と #2 の差 ≈300倍 = 分布は極端な power-law。差を作るのは distribution（フレームワークへの埋め込み）**。

## レバー順位（証拠付き）

1. **Distribution/marketing（圧倒的1位）** — BlockRun の 300x は「agent framework にデフォルトで入ってる」で説明される。全 discovery 面への登録（Bazaar✓ / x402scan / Agent402 / MCP registry = #16）が最小リスク最大効果
2. **route 数量** — 上位勢は数十〜数百 routes（Otto 73, LogicNodes 619, Agent402 500）。/api/find 型 discovery でのマッチ面積。ただしレバー1と併用時のみ効く
3. **信頼性** — Agent402 router が「直近 crawl が壊れてる seller を除外、health が tie-breaker」と明文化。floor であって成長 driver ではない
4. **価格（最弱）** — 全 seller が $0.001-0.05 帯に密集、volume 差を価格で説明できない

## self-improve loop の設計（既存資産の転用）

`skills/earn/lib/genome.mjs + evolve.mjs`（PM trade 用）が**そのまま転用可能な形**:
- genome: 数値 knob {step,min,max} + 1-2 knob 変異 + clamp + content-hash id + 資金 cap は構造的に変異不可
- evolve: on-chain 検証済み実現益だけで昇格判定（K≥3 サンプル + 絶対黒字 + baseline 超え）→ 昇格 = canonical JSON commit

x402 転用: knob = route 別 PRICE_USD（例 {step:0.001, min:0.001, max:0.05}）、ledger = sales.jsonl(#15) × on-chain settle 照合。同じ昇格ゲート。

**genome に入れてはいけない物**（building-agents 原則: judgment は model）:
- route の追加/削除・新規掲載面への登録 = bandit の腕ではなく**証拠に基づく判断**。model が leaderboard/find の gap を読んで決める。cadence は遅く（週次）
- 価格変異は速い cadence（売上毎の feedback）

将来形: OPRO 型（LLM が settle log から変異方向を推論）> 現行のコイン投げ変異。ただし money-moving code では「random 変異 + on-chain 硬ゲート」の保守形が正しい第一版。SOTA 参照 = jennyzzt/dgm (Darwin Gödel Machine, 2178★, code 自体を変異+実 benchmark ゲート)。

## 実行順（このデータに基づく）

1. #16 掲載面全登録（レバー1。x402scan siwx / Agent402 /sell / MCP registry）
2. route 数量拡張（レバー2。需要実測ベースで PRODUCTS 表に追加 — skill 手順化済）
3. health 維持（レバー3。既に launchd KeepAlive + 監視3層で担保）
4. 価格 genome（レバー4。evolve 転用の実装 — 効果最弱なので最後）
