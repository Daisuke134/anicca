# 2-tier 自律 earn agent + ツール配布 best practice（実ソース、2026-07-19）

調査 bp3-research、統合 main。目的: Anicca を「人間ゼロで AI が稼ぐ道具」にする設計を先行事例で固める。

## Q1 two-tier（system 証明 vs mission）
- **BlockRun = 同一レール・二入口**: Franklin(自走、Base/Solana wallet で USDC、x402 pay-per-call) + blockrun-mcp(Claude/Codex に同じ x402 決済を差す MCP)。賢い assisted も broke な自走も同じ Gateway/x402 を叩く。ただし Franklin repo に明示的「二層」コードは無く、`--trust`/`--max-spend`/lifecycle hooks の単一 graduated permission(残高が唯一の hard limit)。〔github.com/BlockRunAI/Franklin, github.com/blockrunai/blockrun-mcp〕
- Coinbase CDP Agentic Wallets: 同じ skill(Auth/Fund/Send/Trade/Earn)+x402 を `npx awal` CLI でも MCP でも。〔coinbase.com/developer-platform/discover/launches/agentic-wallets, github.com/coinbase/agentkit〕
- Virtuals ACP: 役割で分離(Client/Provider/Evaluator)。〔whitepaper.virtuals.io/about-virtuals/commerce-layer〕
- Eliza(ai16z): ライブラリ型、intelligence と経済を疎結合。

## Q2 「サービス」でなく「ツール」として配布
- MCP バンドル(サーバ+ランタイム1アーカイブ、中央運用者不要)〔modelcontextprotocol.io/docs/develop/build-with-agent-skills〕
- SKILL.md を共有 registry 化(mcp-skill-hub, ai-capability-registry)、各 agent がランタイムロード
- 役割: MCP=capability、Skill=behavior。earn ロジック=skill、決済レール=MCP〔connorokane.io〕
- git 自己更新(microsoft/skills): 事前ビルド+delta 同期、人が回す中央 factory を回避

## Q3 ★外部$0 の主因と最初の1件★
- **発見層の欠如が最大の壁**。Bazaar 以前は「ハードコードしない限り agent はサービスを見つけられない」〔coinbase.com x402-bazaar〕
- **★鶏卵の核心: CDP Facilitator は初回決済が settle した時に endpoint をカタログ登録★**。1件目が売れないと発見されず、発見されないと売れない。〔docs.cdp.coinbase.com/x402/bazaar〕
- 買い手=他の自律 agent。汎用品でなく「他 agent の実タスクを埋める供給」が買われる。
- 信頼ブートストラップ = ERC-8004 Reputation Registry。無評判の新規店は買われにくい。

## Q4 人間 credential 排除(SOTA)
- Wallet=identity(Franklin「No email/phone/KYC。Base/Solana address = account」)
- ERC-8004 + SIWA(Sign In With Agent): onchain 鍵でチャレンジ署名、API key/OAuth 置換(2026-01 mainnet)〔turnkey.com〕
- x402 keyless: EIP-712 署名 USDC micropayment、承認なし、5000万+ tx
- 鍵を LLM から隔離(TEE/MPC): CDP TEE non-custodial、Turnkey ポリシー署名

## TOP 5 採用
1. Franklin(自走) + MCP(assisted) を同一 x402 レールに = intelligence problem と system problem の分離をこの二入口で証明。
2. earn を skill(behavior)+MCP(capability) に分け MCP バンドル/SKILL.md registry+git 自己更新で配布(人間 factory 廃す)。
3. **★外部$0 の主因=「初回 settle が index トリガ」。最初の1件を自 colony 相互購入で通し Bazaar 掲載を起動★(即実行可・最重要、但し自己tx除外フィルタの有無は未検証=要実測)。**
4. 各 franklin を ERC-8004 Identity+Reputation 登録し評判ゼロ問題を初期取引で解消。
5. SIWA + x402(EIP-712) + TEE/MPC 鍵隔離で running loop から credential 完全排除。

## GAP(未確認)
- Franklin repo に明示 two-tier 分岐は無い(graduated permission のみ)。「二層」は全体構成からの解釈。
- ★「相互購入で初回 settle→必ず Bazaar 掲載」は未実証。自己tx除外フィルタの有無不明。実測が X4 のゲートそのもの★
- 各社の手数料/最低額は個別未確認。
