# Anicca Earn Verification — Wallet Design & A→B Flow (NEVER FORGET)

**Dais 2026-06-18 厳命。この設計とフローを絶対に忘れない。**

## 2-wallet 設計（混同禁止）

| # | wallet | 用途 | 鍵の場所 |
|---|---|---|---|
| ① **検証用 (test)** | `0x94C445eeb8843A1cB29124a9DB8d24873C26B618` | **A: どの稼ぎ手段が実txで net worth を増やすかを私(Claude)が検証する場所**。ここで全部試す。 | `~/.cache/anicca-verify/tester-wallet.json` |
| ② **Anicca 実走 (run/demo)** | `0x57dcc32FC67901617A549B9d166f25764787c501` | **B: ①で勝った手段だけを earn skill として載せ、auto mode で自走 → 実収益 → [6]③記録 + dashboard 表示** | (anicca body) |
| ③ (即興・参考) | `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21` | 私が即興で使った wallet (`~/.automaton/wallet.json`)。yield 実証ポジション($2 Aave/$1 Morpho/$1 Moonwell)+資金がここにある。loop/compute-proxy のコード既定。consolidate 候補。 | `~/.automaton/wallet.json` |

★ A は①でやる。B は②でやる。③は即興の産物（yield実証はここで済んだ）。

## 鉄則フロー（順序固定・飛ばさない）

```
A を完全に終わらせる（①検証walletで全手段を実走）
  → 各手段「稼げた額 / 明確な壁」を記録（writing = この文書 + 記事テーブル）
  → その後 B に入る（勝者だけを②anicca に載せて自走）
B 待ちの間 = trading 等の残り A 手段を進める（遊ばない）
```

- **A first complete → record (writing) → then B.** 推測で B に行かない。何が稼げるか確証を持ってから載せる。
- **B 待ちの間は trading をやる**（手が空いたら必ず次のA手段を回す）。

## A 実走テーブル（2026-06-18 時点）

| 手段 | 結果 | 稼げる? |
|---|---|---|
| DeFi利回り Aave/Morpho/Moonwell | 預入→残高increase(実tx, on-chain)。元本×金利。 | ✅ 稼げた×3（鍵だけ・確実・小） |
| 0xwork | LIVE($8k払出)だが現open task=有名人follow/RT系=agent不可。code/research/data カテゴリは存在するが今open 0件。 | ❌ 今は壁(供給待ち) |
| x402 売り | x402-express で1行 paymentMiddleware、payTo=wallet、$0.01 USDC on Base、402 Payment Required を実証(受取に鍵不要)。 | ◯ 機構✅ / 壁=需要(外部buyer)。自分で払う=fake禁止。スケールは既存skill流用予定。 |
| DePIN (Grass/Nodepay/Gradient) | 全部ポイント制(即USDCでない)・account+常駐アプリ必須・極小・自動farm=ToS違反。 | ❌ 壁(anicca不適) |
| **nookplot** | 自律 register+online+mining 機構稼働、実コード課題20件受信。無料ローカルLLMは提出形式ミスで却下。`NOOKPLOT_INFERENCE_SOURCE=surplus`+`SURPLUS_BASE_URL=https://blockrun.ai/api/v1`+`SURPLUS_MODEL=anthropic/claude-opus-4.8` で wallet の USDC を x402決済して frontier で解く。 | ⏳ frontier実走で検証中（外部収入の本命） |
| trading | DEX/perps を少額・損失上限で実走予定（①検証wallet）。 | ⏳ |

## frontier 必須（free禁止・Dais厳命）
- nookplot/loop は **必ず frontier**（opus-4.8 or gpt-5.5）。free(qwen等)に落とさない。
- ClawRouter `auto` は資金があれば frontier を許す。確実にするなら model をハードコード。
- BlockRun frontier models: `anthropic/claude-opus-4.8` / `openai/gpt-5.5` / `anthropic/claude-sonnet-4.6` 等（`https://blockrun.ai/api/v1/models`）。

## BlockRun / x402 メモ
- BlockRun OpenAI互換 x402 endpoint = `https://blockrun.ai/api/v1`（自己決済・鍵=wallet）。
- x402 は EIP-3009(gasless USDC) なので ETH gas 無しでも surplus 推論は通る。
- DeFi(Aave/Moonwell mint) は通常 gas(ETH) 必要。Compound系mintは失敗時revertせずエラーコード返す罠あり。
- RPC `mainnet.base.org` は state lag あり → approve/balance は confirmations=2 か別RPCで再読。
