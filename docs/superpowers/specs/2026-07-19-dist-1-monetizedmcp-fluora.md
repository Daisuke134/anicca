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
1. 既存 serve-v2 の x402 決済/payTo/検査器を壊さない（MCP は前段の薄い wrapper）。
2. MonetizedMCP サーバは franklin の payTo にそのまま決済を通す（人間 credential ゼロ、wallet=identity）。
3. self-pay を external と数えない（INV-EXT 維持、監査器そのまま）。
4. 4商品のみ公開（集中維持、X402_CATALOG=core）。

## 実装（Fable 計画→build→検証）
1. monetizedmcp SDK/spec を読む(monetizedmcp.org)。既存 HTTP x402 route を MonetizedMCP tool として公開する
   薄い adapter(skills/earn/x402-sell/mcp-server.mjs)。tool=各商品、price/inputSchema は既存 PRODUCTS から生成。
2. ローカルで MCP server 起動→自己 probe で tool list + paid call が通るか。
3. fluora.ai/submit に登録（人間ゼロの submit フロー確認、無理なら API/PR 経路）。
4. MCPay(mcpay.tech)にも同 server を登録。
5. done 検証: Fluora/MCPay で franklin 商品が検索可能 + 外部 buyer の実購入 on-chain(verify-inflow で external≥1)。

## リスク
- Fluora submit が human gate を持つ可能性→その場合 API/PR/別マーケットにフォールバック(tier-a-bypass)。
- MonetizedMCP と @x402/express の二重決済にならない様、MCP は決済せず既存 402 に委譲する設計。
