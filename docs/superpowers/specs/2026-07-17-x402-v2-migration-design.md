# T3': x402-express v1 → @x402/express v2 移行 — 設計

日付: 2026-07-17 / ブランチ: feature/clip-rewards / 方式: superpowers (brainstorming → writing-plans → executing-plans)

## 目的（1文）

4店の x402 決済を @x402/express@2.17.0 に移行し、x402scan.com への登録を通す（現状 v1 応答で "migrate to v2" 拒否）。

## 制約（不変条件・破ったら全無効）

- **INV-EARNER**: 稼ぎ頭 claude-p(:443/:8443、唯一の実売 $0.337)を最後まで壊さない。franklin2(売上$0)→franklin1→claude-p の順でロールアウト。
- **INV-SETTLE-V2**: 売上記録は settle 成功時のみ。★v2.6.0+ は settle 失敗時にも `PAYMENT-RESPONSE` ヘッダを付ける★ため、`!!res.getHeader()` は使えない。base64 デコードして `SettleResponse.success === true` を確認する。payer:null / 失敗の行が sales に入ってはならない（FIX-3 の再発防止）。
- **INV-DISCOVER**: 8商品が Bazaar catalog に載り続ける（v2 では `discoverable:true` → `extensions.bazaar` 宣言に変わる。移行漏れで消えてはならない）。
- **INV-NO-REGRESSION**: 402応答・決済着金・attempts分離・8商品handler・CDP鍵 が既存同等に動く。

## 採用アプローチ（決定済み）

**franklin2 先行・別ファイル(`serve-v2.mjs`)**。
- 理由: 稼ぎ頭を触らず、$0 の franklin2 で実HTTP検証してから展開。段階移行は本番決済の鉄則。env分岐は複雑化+v1コード残存、全店一括は稼ぎ頭を危険に晒す → 却下。
- リファレンス: 既存の `serve-mainnet.mjs`(2026-06-28、未配線の v2 実装例)を copy+tweak。ゼロから書かない。
- v2 は既にインストール済み(`@x402/express@2.17.0`、package.json 宣言済み、npm install 不要)。

## 変更点（serve-v2.mjs = serve.mjs の v2 版）

| 箇所 | v1 | v2 |
|---|---|---|
| import | `x402-express` paymentMiddleware | `@x402/express`(paymentMiddleware, x402ResourceServer) + `@x402/core/server`(HTTPFacilitatorClient) + `@x402/evm/exact/server`(ExactEvmScheme) |
| facilitator | `{url}` or createFacilitatorConfig | `new x402ResourceServer(new HTTPFacilitatorClient({url, createAuthHeaders})).register(NETWORK, new ExactEvmScheme())`。CDP の createFacilitatorConfig 出力はそのままラップ可 |
| network | `"base"` | `"eip155:8453"`(CAIP-2 必須) |
| routes | `{price, network, config:{discoverable:true}}` | `{accepts:{scheme:'exact', price, network, payTo, extra}, resource, description, extensions: declareDiscoveryExtension(...)}` |
| middleware | `paymentMiddleware(payTo(), routes, facilitator)` | `paymentMiddleware(routes, resourceServer)` (payTo は route.accepts へ) |
| settleゲート | `!!res.getHeader("X-PAYMENT-RESPONSE")` | `PAYMENT-RESPONSE` を base64デコード → `decoded.success === true` のみ settled |
| 手書きmanifest | `x402Version:1` | プロトコルと整合するよう更新 |

## テスト（TDD・実HTTPで検証する不変条件）

franklin2 で実測（本番HTTP、モックでない）:
1. 未payment → 402 が返り、`x402Version:2` を含む
2. X-PAYMENT ヘッダ付き再送 → 決済着金(on-chain tx)
3. ★settle 成功 → sales-*.jsonl に settled:true★
4. ★settle 失敗を注入 → attempts に入り sales に入らない★(INV-SETTLE-V2 の要、v2で最も壊れやすい)
5. Bazaar catalog に franklin2 の8商品が載る(bazaar-scan 実測)
6. x402scan.com が franklin2 を受理する(v1拒否が消える)

## ロールアウト順

1. serve-v2.mjs を書く(serve-mainnet.mjs ベース)
2. franklin2 の boot だけ serve-v2.mjs に切替 → 上記1-6を実HTTP検証
3. green なら franklin1 の boot を切替 → 再検証
4. 最後に claude-p(:443/:8443)を切替 → 再検証(稼ぎ頭、最慎重)
5. 全店 green で旧 serve.mjs を deprecate

## 未確認(実装中に実測する)

- CDP facilitator が CAIP-2 network を受理するか(v1は"base"文字列で動いた実績のみ)
- v2 の402の x402Version 実値 + 旧買い手クライアント(x402-fetch@1.2.0)との相互運用
- `decoded.payer` が FIX-3 の payer 抽出を置換できるか

## done when

- franklin2 で1-6全て実測green
- 3店(franklin1/claude-p:443/claude-p:8443)も同様にgreen
- x402scan.com に4店が登録される(v1拒否の消失を実測)
- 既存の実売(claude-p)が移行後も settle→sales を正しく記録
