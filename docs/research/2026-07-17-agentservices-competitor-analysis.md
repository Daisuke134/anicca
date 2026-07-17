# agentservices.to 実測調査 + BlockRun Franklin issue #100

- 日付: 2026-07-17
- 調査者: anicca colony (deep-researcher subagent, main session Fable 指示)
- 目的: agentservices.to を (a) franklin1 のデータ供給元として使えるか (b) 我々の商品値付けの参考にできるか、を実測で判定
- ソース: `gh issue view 100 --repo BlockRunAI/Franklin`, `curl https://agentservices.to/*`, `crwl https://agentservices.to -o markdown`, `crwl https://basescan.org/address/0x9863...`, Base mainnet RPC (`https://mainnet.base.org` `eth_getLogs`)

## 1. GitHub issue #100 の状況

- URL: https://github.com/BlockRunAI/Franklin/issues/100
- Author: `@vbkotecha`（= agentservices.to のリポジトリ owner `github.com/vbkotecha/aiservices-api`。つまり開発者本人の宣伝 issue）
- 作成日: 2026-07-07T22:06:57Z
- 状態: **OPEN、コメント数 0**。BlockRun 側からの反応は10日間ゼロ（`gh api repos/BlockRunAI/Franklin/issues/100 --jq '{state,comments}'` で実測）。採用/統合の動きなし。
- Franklin リポジトリ本体: `BlockRunAI/Franklin`、624 stars / 52 forks、public。「The AI agent with a wallet — spends USDC autonomously to get real work done.」
- issue 本文の主張: Franklin は既に CoinGecko/search/image API を x402 経由で使っている設計 → AgentServices を crypto/analytics 用のデータ供給元として追加してほしい、という売り込み。技術的な統合方法（Franklin 側のデータプロバイダ追加手順）についての issue 内の記述はなし（README等の設計詳細は今回未確認、issue自体に統合APIの記述はない）。

## 2. agentservices.to 実測

### 2a. 無料エンドポイント（200 確認済み）

```
curl https://agentservices.to/v1/prices?symbol=BTC
```
→ HTTP 200、実データ返却:
```json
{"prices":{"BTC":{"price_usd":62804,"change_24h_pct":-3.19,...},"ETH":{...},"XRP":{...},"SOL":{...}},"timestamp":1784267791}
```

### 2b. 有料エンドポイント（402 確認済み）

```
curl -D - https://agentservices.to/v1/indicators/BTC
```
→ `HTTP/2 402`、`payment-required` ヘッダ（base64、x402Version 2）を decode:

```json
{
  "resource": {"url": ".../v1/indicators/BTC", "description": "Technical indicators: RSI, Bollinger Bands, ATR, Support/Resistance"},
  "accepts": [{
    "scheme": "exact",
    "network": "eip155:8453",
    "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "amount": "20000",
    "payTo": "0x9863aB6242663FCc84c33632741711dB78f8Fd15",
    "maxTimeoutSeconds": 300,
    "extra": {"name": "USD Coin", "version": "2"}
  }]
}
```
= Base mainnet, USDC, $0.02, payTo `0x9863aB6242663FCc84c33632741711dB78f8Fd15`。x402 v2 の bazaar 拡張（`extensions.bazaar`）でルート・入出力スキーマも公開しており、Franklin のような bazaar-index 型のバイヤーからは自動発見できる設計。

### 2c. 全価格表（`crwl https://agentservices.to -o markdown` で実測、50エンドポイント中の抜粋）

| カテゴリ | 例 | 価格 |
|---|---|---|
| Crypto Market Data | price/prices/fear-greed/geo/global/trending/gas/news | **FREE** |
| Crypto Market Data | indicators, yields, whales, defi-tvl, stocks | **$0.02** |
| Crypto Market Data | correlation, signals | $0.03 / $0.04 |
| LLM Inference | inference, complete (GPT-5.4/5.4-mini/5.5) | $0.03 |
| Stock/SEC | stocks/history, sec/{ticker} | $0.03 |
| Commodities/Economics | commodities, economic | $0.03 |
| FX | fx?base=USD | **$0.003** |
| Synthesis | token-risk, yield-comparison, hn-sentiment, npm-stats, github-trending | $0.02〜$0.03 |
| Marketing Intelligence | sentiment/competitors/content-gaps/ad-copy | $0.03〜$0.05 |
| Web/Security | metadata, search, extract, security | $0.002〜$0.02 |
| （issue本文の追加言及、サイトTOPページ記載なし） | portfolio intelligence / defi strategy / onchain overview / market pulse | $0.10 / $0.25 / $0.15 / $0.05 |

MCP endpoint: `agentservices.to/mcp`（36 tools、Streamable HTTP）も稼働中。

## 3. on-chain 売上実績（payTo `0x9863aB6242663FCc84c33632741711dB78f8Fd15`）

- Basescan UI実測: ETH残高 0、**USDC残高 0.169（$0.17）**、"Transactions Sent: N/A"（=このアドレス自身は一度も outgoing tx を送っていない = 純粋な受け取り専用アドレス）。
- `eth_getLogs`（Base mainnet RPC `https://mainnet.base.org`、USDC contract `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`、`Transfer` event、`to=payTo`）で直近20日分（block 47,875,255〜48,739,255、10,000ブロックずつ87チャンクで実測）を全スキャン:

| block | 金額 | from | tx |
|---|---|---|---|
| 48020268 | $0.010 | 0x254a4ec1...ed091 | 0x7f5dbd0b... |
| 48020280 | $0.020 | 0x254a4ec1...ed091 | 0x5952d410... |
| 48020289 | $0.020 | 0x254a4ec1...ed091 | 0xc2f12158... |
| 48367022 | $0.020 | 0x52639295...c02b | 0xad4b1671... |
| 48367038 | $0.003 | 0x52639295...c02b | 0xb8af4a22... |
| 48435623 | $0.003 | 0x1830dadb...c8e0 | 0xdf4a1669... |
| 48444928 | $0.030 | 0x254a4ec1...ed091 | 0x78d96021... |
| 48444944 | $0.010 | 0x254a4ec1...ed091 | 0xd6ff50e4... |
| 48444952 | $0.010 | 0x254a4ec1...ed091 | 0xd7caea93... |
| 48444959 | $0.020 | 0x254a4ec1...ed091 | 0x477719c3... |
| 48444967 | $0.020 | 0x254a4ec1...ed091 | 0x209fa3e6... |
| 48565204 | $0.003 | 0x1830dadb...c8e0 | 0x928073cf... |

**合計: 12件 / $0.169**。これが現在のウォレット残高 $0.17 とぴったり一致（＝出金ゼロ、20日分の全履歴 = このウォレットの全生涯収益とほぼ同値）。支払元はわずか**3つの異なるアドレス**のみで、各アドレスは `eth_getTransactionCount` で nonce 0〜1（＝x402 facilitator が発行した使い捨てペイヤー的な新規ウォレット、自分でオンチェーンtxを送ったことがない）。数分〜数十分の間隔で複数エンドポイントを連続コールしているパターンは、開発者自身によるテスト/デモ実行に典型的。**ottoai や鯨botのような既存の買い手が来ている証拠はゼロ**。20日間で3セッション・$0.169 は「実際に売れている」と呼べる規模ではない。

## 4. 判定

### 価格競争力
franklin1 の `funding-rates` = **$0.003**。AgentServices の最も近い類似商品（indicators / yields / whales）= **$0.02**、約 **6.7倍高い**。fx ($0.003) だけは同水準。franklin1 の現行価格は既に十分競争力がある。

### on-chain 実績
AgentServices の x402 決済フローは技術的に正しく動作している（402チャレンジのスキーマもFranklin/x402 v2互換）が、**実売上はほぼゼロ（20日で$0.169、3セッションのみ、出金履歴なし）**。「彼らが売れているから真似る／彼らの単価を信頼する」根拠にはならない — あくまで開発者本人の issue 内デモコマンドの実行痕跡である可能性が高い。

## 5. 我々への具体アクション

1. **データ供給元としては今は追加しない**。実売上ゼロに近い個人プロジェクトで、Franklin本体も10日間ノーリアクション（未採用）。ただし技術的には x402 v2 準拠で bazaar 拡張も付いているため、将来 franklin1 が whale-tracking / portfolio-intelligence のような**自作コストが高い商品を作らずに転売したい**場面が来たら、$0.02〜$0.25 の原価で composable に使える選択肢として保留（優先度は低）。
2. **値付け参考として採用**: 今後出す indicators/yields/whale 系商品は、AgentServices の $0.02 を上限アンカーとして**そこより安く（$0.005〜$0.015 目安）**出す。fx/研究レベルの軽量商品は $0.003〜$0.01 帯で現行 funding-rates ($0.003) の路線を維持する。「相手が売れていないから安易に真似た価格を上げるな」— 6.7倍の価格差自体が我々の武器なので、コスト構造が許す限り現状の低価格路線を崩さない。
