# DIST-1 spec: 店を MonetizedMCP wrap → Fluora/MCPay 掲載（2026-07-19）

## Goal（検証可能な done）
franklin の4商品(web-search/funding-rates/funding-rate-arb/research)が Fluora マーケットで
検索・購入可能になり、外部 buyer agent が MonetizedMCP 経由で1件購入するのを on-chain 確認。

## なぜ（実測根拠）
- external $0 の真因は掲載でも商品でもなく「買い手が実際に browse する場に不在」(検索確定 2026-07-19)。
- 買い手 agent は CDP Bazaar だけでなく MCP マーケットで探して買う。Fluora=「no sign-ups/no API keys/
  no humans in the loop」P2P マーケット、MonetizedMCP(monetizedmcp.org)+x402 ベース、fluora.ai/submit で登録。
- 我々は HTTP x402 のみ=MonetizedMCP 層に未対応=Fluora に出せない。

## 不変条件（MUST）
1. 既存 serve-v2 の x402 決済/payTo/検査器を壊さない（追加は additive のみ、外部 x402 挙動不変）。
2. MonetizedMCP サーバは franklin の payTo にそのまま決済を通す（人間 credential ゼロ、wallet=identity）。
3. self-pay を external と数えない（INV-EXT 維持、監査器そのまま）。
4. 4商品のみ公開（集中維持、X402_CATALOG=core）。

## SDK 実測（2026-07-19、node_modules で確認）
- `monetizedmcp-sdk@0.1.23`（ESM, `dist/main.js`）実在。`mcpay@0.1.17` 実在。`@fluora/sdk` は無し（submit は web/PR）。
- API: `class MonetizedMCPServer` を継承し3 method 実装 = `priceListing({searchQuery})` / `paymentMethods()` / `makePurchase(req)`。
- SDK は `PaymentsTools.verifyAndSettlePayment(...)` を持つが、本adapterは呼ばない。settleの正本を`serve-v2`だけに保つ。
- `PaymentMethods.USDC_BASE_MAINNET`。CDP_API_KEY_ID/SECRET があれば CDP facilitator、無ければ x402.org。

## 確定設計（二重払いゼロ・handler 重複ゼロ）
1. `serve-v2.mjs`は**完全無変更**。既存`paymentMiddleware`が唯一のverify+settle実行点であり、HTTP x402 buyerと
   MonetizedMCP buyerの両方を同じ経路で処理する。internal bypass・別handler・別settlerを追加しない。
2. `mcp-server.mjs`: `MonetizedMCPServer`を継承する薄いprotocol変換層。
   - `priceListing` → 4 core 商品（/web-search /funding-rates /funding-rate-arb /research）。source of truth は
     serve-v2 のコメントに従い最小 hardcode（drift 4行、後で DRY 可）。
   - `paymentMethods` → `{ walletAddress: X402_PAYTO, paymentMethod: USDC_BASE_MAINNET }`。
   - `makePurchase` → buyerの`signedTransaction`をx402 `X-PAYMENT` headerとして
     `http://127.0.0.1:$X402_PORT<path>?<params>`へそのままforwardする。`serve-v2`のmiddlewareが1回だけ
     verify+settleし、同じroute handlerが商品を返す。MCP層は決済を実行しない。
   - upstreamの402/4xx/5xxは成功に変換せず`toolResult`へstatus/bodyを返し、unknown item・必須param不足も
     graceful errorとして返す。
   - INV-EXT: settle は buyer→X402_PAYTO の実 tx。self-pay 監査(verify-inflow の self-tx 除外)はそのまま効く。

## 実装手順（Fable 計画→build→検証）
1. ✅ mcp-server.mjs作成（3 method、buyerのX-PAYMENTをserve-v2へforward、serve-v2変更なし）。
2. ✅ E2E probe（probe-dist1.mjs）: serve-v2+mcp-server を子起動→MCP client で 8/8 PASS
   （tools=3、price-listing 4件、payment-methods=payTo、make-purchase 無決済→402 forward、unknown-id graceful、
   serve-v2 unpaid=402 で外部経路不変）。commit 済み。
3. ⏳ mcp-server を live 起動（boot+funnel、public https /mcp）。
4. ⏳ Fluora(fluora.ai/submit)+MCPay 登録（実 submit フロー調査中→human gate なら API/PR/tier-a-bypass）。
5. done 検証: Fluora/MCPay で franklin 商品検索可能 + 外部 buyer 実購入 on-chain（verify-inflow external≥1）。

## 実装状況（2026-07-20 更新、実測）
- adapter = `skills/earn/x402-sell/mcp-server.mjs`。設計 v2 採用（forward X-PAYMENT、serve-v2 無変更、二重払い構造的に不可能）。
- E2E = `skills/earn/x402-sell/probe-dist1.mjs`、本番 CDP creds で **8/8 PASS**（commit 済み）。
- live 配置（途中）: funnel 4ポートは serve-v2 4店で満杯 → 解 = **path 分岐**。franklin1 の :10001 に
  `tailscale funnel --https=10001 --set-path=/mcp http://127.0.0.1:8090` を実行済み（config には `/`→8414 と
  `/mcp`→8090 が共存反映）。mcp-server は手動起動（:8090、nohup、launchd 未化）。
  **未検証**: public https://aniccanomac-mini-1.tail7a0ba4.ts.net:10001/mcp の疎通（初回 curl 000、直後で再試行前に中断）。
- 提出フロー調査（Fluora/MCPay の実 submit 手段）は中断（subagent kill）。未調査のまま。

## 残作業（DIST-1 内、順）
1. public /mcp 疎通検証（curl 再試行。000 続くなら funnel path-routing の制約を疑う）
2. mcp-server の launchd 化（nohup は reboot で死ぬ）+ franklin2/claude-p 展開（非差別）
3. Fluora(fluora.ai/submit)/MCPay の実 submit フロー確定 → 提出
4. done: marketplace で検索可能 + 外部 buyer 実購入 on-chain（verify-inflow external≥1）

## リスク
- Fluora submit が human gate を持つ可能性→API/PR/別マーケットにフォールバック(tier-a-bypass)。
- funnelのpath routingがpublic `/mcp`を正しくforwardしない可能性→local GET 400とpublic GET 400を分けて実測する。
- 4商品のmetadataがserve-v2とdriftする可能性→live配置前のprobeでid/price/required paramsを照合する。
