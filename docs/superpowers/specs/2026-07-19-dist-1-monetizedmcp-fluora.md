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
- `PaymentsTools.verifyAndSettlePayment(amount, sellerAddr, {facilitatorUrl, paymentHeader, resource, paymentMethod})` で決済 verify+settle。
- `PaymentMethods.USDC_BASE_MAINNET`。CDP_API_KEY_ID/SECRET があれば CDP facilitator、無ければ x402.org。

## 確定設計（二重払いゼロ・handler 重複ゼロ）
1. `serve-v2.mjs`: paymentMiddleware の**前**に additive middleware 1個だけ追加 —
   `req.header('x-internal-key') === process.env.X402_INTERNAL_KEY`（env が非空）かつ remote が localhost なら
   402 を skip して直接 serve。外部からの x402 決済経路は完全に不変（invariant #1 厳守）。
2. `mcp-server.mjs`（新規）: `MonetizedMCPServer` 継承。
   - `priceListing` → 4 core 商品（/web-search /funding-rates /funding-rate-arb /research）。source of truth は
     serve-v2 のコメントに従い最小 hardcode（drift 4行、後で DRY 可）。
   - `paymentMethods` → `{ walletAddress: X402_PAYTO, paymentMethod: USDC_BASE_MAINNET }`。
   - `makePurchase` → SDK で verify+settle を `X402_PAYTO` 宛に実行 → 成功後 `http://localhost:$X402_PORT<path>?<params>`
     を `x-internal-key` 付き fetch で実行し結果を返す。決済は MCP 層で1回のみ、商品実行は serve-v2 handler を再利用。
   - INV-EXT: settle は buyer→X402_PAYTO の実 tx。self-pay 監査(verify-inflow の self-tx 除外)はそのまま効く。

## 実装手順（Fable 計画→build→検証）
1. ~~serve-v2 に internal-bypass~~ → **不要になった**。設計 v2 で serve-v2 は完全無変更。
2. ✅ mcp-server.mjs 新規作成（3 method、buyer の X-PAYMENT を serve-v2 に forward）。
3. ✅ E2E probe（probe-dist1.mjs）: serve-v2+mcp-server を子起動→MCP client で 8/8 PASS
   （tools=3、price-listing 4件、payment-methods=payTo、make-purchase 無決済→402 forward、unknown-id graceful、
   serve-v2 unpaid=402 で外部経路不変）。commit 済み。
4. ⏳ mcp-server を live 起動（boot+funnel、public https /mcp）。
5. ⏳ Fluora(fluora.ai/submit)+MCPay 登録（実 submit フロー調査中→human gate なら API/PR/tier-a-bypass）。
6. done 検証: Fluora/MCPay で franklin 商品検索可能 + 外部 buyer 実購入 on-chain（verify-inflow external≥1）。

## 実装状況（2026-07-19、実測）
- adapter = `skills/earn/x402-sell/mcp-server.mjs`。設計 v2 採用（forward X-PAYMENT、serve-v2 無変更、二重払い構造的に不可能）。
- E2E = `skills/earn/x402-sell/probe-dist1.mjs`、本番 CDP creds で **8/8 PASS**（commit 済み）。
- 残: live 起動（funnel）+ marketplace 提出。提出フローは deep-researcher 調査中。

## リスク
- Fluora submit が human gate を持つ可能性→API/PR/別マーケットにフォールバック(tier-a-bypass)。
- internal-key が漏れると 402 bypass される→env のみ・localhost 限定・stdout に出さない。
