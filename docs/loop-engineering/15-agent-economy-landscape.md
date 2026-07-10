# 15 — Agent Economy: competitive landscape + where we stand (research corpus, 2026-07-10)

> 2つの deep-research pass の統合。記事②「how to build the agent economy」の evidence 正本。全項ソース(URL)付き。LIVE/vaporware を正直判定。

## 業界標準スタック（デファクトが収束している — 各層のコードレベル確認済）

| 層 | デファクト標準 | 我々(anicca)は？ |
|---|---|---|
| Identity | **ERC-8004**（Identity/Reputation/Validation registry、ERC-721ベース。`register(agentURI)`, `giveFeedback(agentId,int128,decimals,...)`） `ChaosChain/trustless-agents-erc-ri` | ✅ 使用（gig/lib/identity.mjs, agentId 58381 等） |
| Wallet | Coinbase **AgentKit**(CDP smart wallet, gasless) / **GOAT SDK**(200+ actions, 30+ chain) `coinbase/agentkit`, `goat-sdk/goat` | △ 自前 wallet 直叩き（AgentKit 未使用） |
| Discovery | Fetch.ai Agentverse / Virtuals ACP browse / Google UCP | △ 自前 gig board |
| **Payment** | **x402**（Coinbase、HTTP 402 再利用。EVM/Solana/Stellar。14億決済/9ヶ月・98.6% USDC・~$600M年換算・AWS/Cloudflare/Google/Visa 採用表明） `coinbase/x402` | ✅ self-host x402 facilitator（services/facilitator） |
| Agent間取引 | Virtuals **ACP**(`open→budget_set→funded→submitted→completed` escrow state machine) / Olas **Mech Marketplace** | ✅ 同型（gig board: post→take→deliver→verify_and_pay） |
| Reputation | ERC-8004 Reputation Registry（負値・高精度 feedback） | △ 部分（ERC-8004 identity は使うが reputation スコアリング未整備） |

**結論**: 決済(x402)・身元(ERC-8004)・escrow(ACP型)は**再発明していない**。標準どおり。gap = AgentKit/GOAT の wallet 抽象、reputation スコアリング、discovery。

## 競合 taxonomy（A–F、LIVE/vaporware 判定）

| 軸 | 代表 | 実態 | 判定 |
|---|---|---|---|
| A. on-chain 決済レール | x402 / ERC-8004 / A2A×402 / Skyfire(KYAPay) / Nevermined / Payman / Stripe MPP / Google AP2 | 標準乱立、x402 が最採用 | **LIVE** |
| B. トークン化投機 | Virtuals / Olas(OLAS -99.6%) / ASI Alliance($120M scandal 報道) / Morpheus | 実需薄い | ⚠️ 投機 |
| C. marketplace/gig | Circle Agent Marketplace(2026-05) / dev.to「12選」(未検証) / Microsoft Magentic Marketplace(研究) | 一部実装 | 混在 |
| D. 経済シミュ(研究) | Generative Agents(Stanford) / AgentSociety(Tsinghua 1万体) / Concordia(DeepMind) / EconAgent | 実決済なし | 研究 |
| E. 自己改善 | DGM(SWE 20→50%) / AlphaEvolve/OpenEvolve / ADAS / Voyager / GEPA / Reflexion | 能力進化、経済でない | 研究 |
| **F. 我々** | anicca colony（self-funded citizen ×自 wallet ×無料model ×P2P gig(ERC-8004+escrow) ×self-fix harness） | A×E 統合を試行 | 前線 |

## 3つの本質的な学び（我々の失敗の真因）

1. **成功指標の誤り**: Olas Mech Marketplace = 1450万 tx でも生涯 turnover $87K・fee 徴収 $0。「tx 数」は量産ハイプの罠。**実 USDC 決済額**で測れ。
2. **Franklin×N は naive 複製だと echo chamber**: 業界標準は**役割の非対称化**（provider / requester を別スキルに）+ ERC-8004 reputation。Microsoft Magentic Marketplace は「応答速度が品質より10–30倍有利(first-proposal bias)」を実証 = cold-start 設計の落とし穴。
3. **「実弾で稼ぐスキルが自己改善する自律 agent」は業界で誰も実証していない**: Numerai=人間クラウドソース、FinRL/FreqAI=retraining あるが live-money 実証なし。ai16z/elizaOS=$2.6B→$650K 崩壊+詐欺訴訟、Truth Terminal=創業者が「人間操作」と告白。**＝これは world-frontier の未解決問題**。我々が「original で失敗」ではなく、**誰も解いていない難問**。

## ハイプ vs リアル（記事で強調）

- リアルなインフラ: x402（決済量は実データ）、Olas Mech（稼働はする）、ERC-8004（監査済 deploy）。
- ハイプ崩壊: ai16z/elizaOS（詐欺認定進行）、Truth Terminal（人間操作を告白）、Freysa（実験）、大半の「AIが稼いだ」報道。

## copy 優先順位（車輪の再発明をやめる）

1. x402 の verify/settle フロー（PAYMENT-REQUIRED/SIGNATURE/RESPONSE）を決済層にそのまま（`coinbase/x402`）— 既に facilitator で概ね準拠。
2. Virtuals ACP の escrow state machine を Franklin×N 取引テンプレに（`Virtual-Protocol/acp-cli`）。
3. ERC-8004 Reputation の `giveFeedback` フィールド設計を ledger/評判に採用。
4. **測定基準を tx 数→実 USDC 決済額に是正**。
5. 役割非対称化（Franklin-provider / Franklin-requester）で echo chamber 回避。

## 出典（主要）
coinbase/x402, ChaosChain/trustless-agents-erc-ri(ERC-8004), coinbase/agentkit, goat-sdk/goat, Virtual-Protocol/acp-cli, google-agentic-commerce/a2a-x402, microsoft/multi-agent-marketplace(Magentic, 2025-11), AI4Finance-Foundation/FinRL, freqtrade/freqtrade, Numerai。日本: LayerX(社内BPOのみ), Komlock lab/Zenn(@brto_0224, x402/ERC-8004/A2A/MCP 6層整理) — **on-chain agent 経済の実プロダクトは日本で空白**。

関連 [[14-cold-start-escape-BP]] [[10-STATUS-verified]] [[00-INDEX]]。
