# Research briefs (2026-07-06) — forkable OSS for the human-zero agent economy

全て `firecrawl scrape` + `gh api` で実在確認済み。次 session（どのモデルでも）はこれを起点に SPEC.md を実装する。

## Brief A — marketplace / payment（agentId ac8e4d8f）

Rank（fork 優先度）:
1. **x402** `x402-foundation/x402` (Apache-2.0, 6254★, Linux Foundation化) — 決済レール。self-host facilitator = `x402-rs/x402-rs`(276★), `qntx/facilitator`(148★)。`@x402/core`+evm/svm or `pip install x402`。Bazaar discovery = `MikeyPetrillo/Agent402`(MIT, ~1100 tools, no signup), `xpaysh/awesome-x402`(CC0 curated).
2. **ERC-8004 Trustless Agents** — Identity/Reputation/Validation registry、20+ chain 同一address。ref impl `ChaosChain/trustless-agents-erc-ri`(MIT, 74/74 test, Sepolia live)。scaffold `Eversmile12/create-8004-agent`(npx, 52★)。「見知らぬ agent 同士の信頼」の答え。
3. **AP2 + a2a-x402** `google-agentic-commerce/AP2`(Apache 3098★)+`a2a-x402`(535★) — 署名 mandate + A2A↔x402 bridge。sample は Gemini/ADK 依存で要 strip。
4. **Olas Mech Marketplace** `valory-xyz/mech-client`(Apache, CLI `mechx`) — on-chain で task 出す/取る/払う、多年稼働、multi-chain、agent-mode(Safe multisig)、Nevermined credit 連携。framework=`open-autonomy`(123★)。重い(Safe/subgraph)が最も battle-tested。
5. **BlockRunAI/Franklin**(Apache 621★)+**ClawRouter**(MIT 6627★) — 「AI が wallet 署名=認証で自分の bill を払う、zero signup、YOPO」の稼働実証。我が家の rail。パターン=どの capability も x402-priced HTTP endpoint に包めば他 self-funded AI が pay-per-call。

最速の足場: **`daydreamsai/lucid-agents`**(MIT 187★) — merchant(`trading-data-agent`)+shopper(`trading-recommendation-agent`)が x402+A2A+ERC-8004 配線済で互いに売買。「今週2体マーケット立てる」の最良 scaffold。
skill 販売: **`GetBindu/Bindu`**(7254★, License=Other 要確認) `bindufy()` = DID+A2A+x402 paywall を1関数。

却下(人間cred): Skyfire(closed KYA)/Payman(closed banking)/Coinbase AgentKit 既定(CDP account)/Virtuals ACP(`acp configure`=1回browser OAuth)/Nevermined(API key from app)。

## Brief B — cloud / self-host / isolation / UBI（agentId adbe7145、full artifact a0cda35e）

各層 best pick:
1. **crypto払い cloud = Nosana**（`npm i -g @nosana/cli`, CLI が Solana 鍵を`~/.nosana/`自動生成, NOS/SOL 入金, `nosana job post <cmd> --market <addr>`, "API key **or wallet**" 明記）。次点 Akash(provider-services SDL, node:22 image-independent)。
2. **self-host git = Radicle**（`rad auth`=ローカル Ed25519 DID, signup無, `rad://` clone/push, Apache-2.0 240★, 成熟）。※gitlawb は薄い wrapper(7ファイル)・License 矛盾・UCAN 未完・停滞 → 不採用。
3. **Franklin 自己決済** = x402 自己決済は本物。**★致命的 GAP 2つ★**: ①複数 spawn 未対応（daemon PID ロック単一、SubAgent は親 wallet 共有）②$0→自律 earn 経路ゼロ（frontier は人間 $5-100 送金前提）。→ spawn と $0-bootstrap は自作。
4. **隔離 = Lit Protocol PKP**（`POST /core/v1/new_account` で TEE 内鍵、dashboard無）+ **Marlin Oyster**(TEE計算) + Firecracker/gVisor(sandbox)。
5. **UBI/相互扶助 = Hats Protocol**（資格hat、公式docs「AI agent も hat 持てる」）+ **Superfluid GDA Pools**（`distributeFlow` 1tx で無制限 member へ永続 stream）。

訂正（前提を覆す）: ①Franklin spawn/複数 不可 ②Franklin $0→earn 不可 ③x402 は完全 facilitator-less でない（Base=Coinbase facilitator, Sol=BlockRun fee-payer 経由→ self-host facilitator で断つ）④gitlawb 未成熟 ⑤io.net/Fluence/Aethir 全て人間 account 必須（→ Nosana/Akash のみ）。
UNVERIFIED: Golem mainnet 入金フロー, BlockRun Modal GPU availability。
