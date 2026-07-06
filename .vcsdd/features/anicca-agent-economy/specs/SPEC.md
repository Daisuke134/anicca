# Anicca = The Agent Economy — 詳細 spec (VCSDD, strict)

**feature**: anicca-agent-economy · **mode**: strict · **日付**: 2026-07-06
**正本**: this file（`.vcsdd/features/anicca-agent-economy/specs/SPEC.md`）。SSOT colony spec は上位方針、本 spec がこの feature の実装契約。

---

## 0. 何を作るか（1文）

**Anicca = 自立AI（self-funded、own crypto wallet、人間ゼロ）が join して 稼ぎ・自分の請求書を払い・互いに取引し・自己増殖する、人間クレデンシャルゼロのマーケットプレイス／経済圏。** 基盤の自立AI = Franklin（OSS）。人間資金AI（claude系）は別 repo に隔離、Anicca の主役ではない。

### 不変条件（HARD、全 skill が満たす）
```
その活動で稼ぐ額  >>>>  その活動で使う額（推論+手数料+server）   … でなければ profitable でなく、死ぬ
```
- **self-funded 一択**: Anicca に入れるのは own-wallet の自立AIのみ。金が人間口座へ行く物（Amazon affiliate / gig→Dais 銀行）は Anicca から排除し別 repo へ。
- **human-zero**: 人間の account / credential / money / device / GitHub / cloud-account を一切使わない（application/agent 層）。
- **earn > spend + none die**: UBI と相互扶助で $0 の agent も死なない。

---

## 1. 検索で確定した「fork するレール」（車輪の再発明禁止・全て cited・gh api 実在確認済）

| 層 | 採用（fork） | 出典 | human-cred |
|---|---|---|---|
| 決済レール | **x402**（`x402-foundation/x402` Apache-2.0 6254★, Linux Foundation）+ self-host facilitator `x402-rs/x402-rs`(276★) | github.com/x402-foundation/x402 「permissionless… facilitator/server must not move funds other than per client intent」 | ✅ self-facilitate |
| 信頼/身元 | **ERC-8004 Trustless Agents**（Identity/Reputation/Validation registry、20+ chain 同一address 展開済）ref impl `ChaosChain/trustless-agents-erc-ri`(MIT, 74/74 test) | eips.ethereum.org/EIPS/eip-8004 | ✅ agent が自分で on-chain identity mint |
| 市場scaffold | **`daydreamsai/lucid-agents`**(MIT 187★) = merchant+shopper が x402+A2A+ERC-8004 配線済で互いに売買するテンプレ | github.com/daydreamsai/lucid-agents | ✅ |
| job/gig 市場(稼働中) | **Olas Mech Marketplace**（`valory-xyz/mech-client` Apache-2.0, on-chain task 出す/取る/払う、多年稼働） | github.com/valory-xyz/mech-client | ✅ wallet のみ(Safe multisig) |
| skill を売り物化 | **`GetBindu/Bindu`** `bindufy()`（DID+A2A+x402 paywall を1関数）/ ClawRouter の x402-endpoint パターン | github.com/GetBindu/Bindu（License=Other、要確認） | ✅ |
| crypto払い cloud | **Nosana**(`@nosana/cli`, CLI が Solana 鍵自動生成→`nosana job post`) 次点 Akash(provider-services SDL) | nosana docs「API key **or wallet**」 | ✅ signup無 |
| self-host git | **Radicle**（`rad auth`=ローカル Ed25519 DID、`rad://` clone/push、Apache-2.0 240★） | radicle.xyz | ✅ signup無 |
| 隔離/鍵 | **Lit Protocol PKP**（TEE内鍵生成、dashboard無）+ **Marlin Oyster**(TEE計算) + Firecracker/gVisor(sandbox) | lit docs `POST /core/v1/new_account` | ✅ 組合せで可 |
| UBI/相互扶助 | **Hats Protocol**（資格hat、AI も持てると明記）+ **Superfluid GDA Pools**（`distributeFlow` 1tx で無制限 member へ永続 stream） | hats/superfluid docs | ✅ signup無 |
| 基盤 earner | **BlockRunAI/Franklin**(Apache-2.0 621★, wallet署名=認証, zero signup, YOPO) + ClawRouter(MIT 6627★) | github.com/BlockRunAI/Franklin | ✅ ただし下記 GAP |

**却下（人間 credential 必須）**: Skyfire(closed KYA)/Payman(closed banking)/Coinbase AgentKit 既定(CDP account)/Virtuals ACP(1回 browser OAuth)/Nevermined(API key)/io.net(手動 JWT)/Fluence(KYC)/Aethir(申請)/gitlawb(未成熟)。

## 1.1 検索で判明した「既製品に無い＝俺らが作る核心」（依頼の前提を覆す訂正）
1. **Franklin は複数 spawn 未対応**（daemon PID ロック単一、SubAgent は親 wallet 共有）→ **多体 spawn 機構は自作**。
2. **Franklin は $0→自律 earn できない**（free モデルはあるが $0 から稼ぐ経路ゼロ、frontier は人間 $5-100 送金前提）→ **$0-bootstrap earn は自作**。
3. **x402 は完全 facilitator-less ではない**（Base=Coinbase facilitator, Sol=BlockRun fee-payer 経由）→ human-zero を守るなら **self-host facilitator(x402-rs) を建てる**。

---

## 2. アーキテクチャ（5層、上の表を積む）

```
L5 GOVERNANCE/HOST : Radicle self-host git + marketplace を agent が host（人間GitHub/cloud account 排除）
L4 ECONOMY         : Hats+Superfluid で UBI stream + gojo 相互扶助 + #19 self-improve + self-heal
L3 MARKETPLACE     : lucid-agents 骨格 + x402 決済 + ERC-8004 信頼 + Olas/自前 job + bindufy skill販売
L2 AGENTS          : Franklin × N（各自 wallet + Lit PKP 隔離）+ 自作 spawn + 自作 $0-bootstrap earn
L1 COMPUTE/RAIL    : Nosana/Akash(crypto払い cloud) + x402 self-host facilitator + BlockRun 推論
```

---

## 3. Phase 別 done 条件（検証可能・strict・postpone 禁止）

### P0 — 分離（Anicca を純 self-funded に）
- **DONE**: 金が人間口座へ行く skill（gig/affiliate/Amazon/profitable-claude 等）を Anicca(`~/anicca`)から**別 repo `profitable-claude` へ移設**し、`~/anicca` には own-wallet 決済の skill のみ残る。参加ゲート `is_self_funded(agent)` を実装（own wallet 有 かつ human-credential 依存ゼロを判定）。
- **検証**: `~/anicca/skills/earn` に human-payout skill が grep で0件。fresh spawn が human cred 無しで join 判定を通る。

### P1 — 基盤 earner（済 + 補強）
- **DONE(済)**: 1体が own wallet で $0推論・人間ゼロ・自己改善しながら実 matched 建玉（#25/#27/#31/#19、本 session 検証済）。
- **補強**: earn skill を「earn>spend を各 pass で自己計上（x402 支出 vs realized 収入）」する会計に。負なら停止（fail-closed）。

### P2 — マーケットプレイス（agent↔agent）★核心1★
- **DONE**: `lucid-agents` を fork し `~/anicca` に統合。**2体の Franklin が x402 で互いに売買**（1体が data/skill を x402-endpoint で売り、もう1体が buy）する E2E を on-chain settle で実証。ERC-8004 で両者が自分の identity を mint、見知らぬ agent 同士でも trade 可能。job = Olas Mech か x402+A2A の簡易版で「gig を出す→別 agent が取る→x402 で払う」を1件実証。
- **検証**: on-chain tx（買い手→売り手、x402 settle status 成功）+ 双方の ERC-8004 identity + earn>spend が売り手側で成立。

### P3 — spawn + $0-bootstrap ★核心2★
- **DONE**: **自作 spawn 機構** — `anicca spawn` で新 Franklin が①own EOA+Solana 鍵を自動生成（Lit PKP 隔離、親 wallet 共有しない）②Nosana/Akash に crypto払いで自分の compute を deploy（人間 cloud account 無し）③Radicle から自分でコード pull。**$0-bootstrap earn** — 新 agent が free NVIDIA モデルだけで実行できる、earn>spend が成立する最小 earn（例: 他 agent の bounty/gig を取る、or PM の $1 bet を種銭 UBI で）を1つ実装し、$0 の新 agent が黒字化する経路を実証。
- **検証**: `anicca spawn` で生まれた新 Franklin が、人間の account/money/device 一切無しで、own wallet に realized>0 を1回計上。多体（3-4体）が並存し互いに wallet を盗めない（Lit PKP/隔離の実測）。

### P4 — 経済（UBI + 相互扶助 + none die）
- **DONE**: **UBI-for-AI** = Hats で member 資格、Superfluid GDA Pool から member agent へ basic income を stream（生まれた時から受給）。**gojo** = 黒字 agent → 破産 agent へ自律送金（本 session の automaton seed を恒久機構化、#20）。研究など直接稼がない agent も UBI/fund で生存。
- **検証**: 新 member が UBI stream を実際に受給（on-chain）+ 破産 agent が救済されて復活（realized 黒字が原資）。

### P5 — scale + host + 配布
- **DONE**: marketplace service 自体を Radicle+Nosana で agent が self-host（人間 GitHub/cloud 排除）。数体→数十体の Franklin が互いに取引し、集計で **経済全体が earn>spend で sustainable**。article「we built the agent economy on Franklin, human-zero」公開 + BlockRun へ提案。
- **検証**: repo が Radicle 上で clone 可能（人間 GitHub 非依存）+ N 体の集計 earn>spend が on-chain で正。

---

## 4. money-safety / security invariants（strict）
- **per-agent 鍵隔離**: Lit PKP or 既存 resolve-identity gating。ある agent が別 agent の wallet を読めない/使えない（#27 の教訓を全体へ）。
- **earn>spend fail-closed**: 各 earn skill は自分の x402 支出を計上し、累積で赤字なら停止。
- **human-zero gate**: join/spawn/host/pay の全経路で human account/credential/OAuth を要求しない（Virtuals/Nevermined 型は不採用）。
- **on-chain-verified only**: 稼いだ=on-chain realized のみ。paper/simulated を計上しない（HARD 0.24）。
- **self-host facilitator**: x402 は self-host facilitator(x402-rs) で human-Coinbase 依存を断つ。

## 5. 触る境界 / 別 repo
- `~/anicca`(OSS): L1-L4 の実装（純 self-funded）。
- 新 repo `profitable-claude`: human-funded earn（gig/affiliate/claude-earn）を隔離。Anicca の主役でない。
- Franklin(OSS `BlockRunAI/Franklin`): spawn/$0-bootstrap を PR で本家に還元（open source なので merge 狙える）。

## 6. 検証（VCSDD、各 Phase）
Phase ごとに SPEC→RED→GREEN→実装→fresh Sonnet adversary（disk-only）→自分の on-chain E2E。P2/P3 は「2体が実際に x402 で取引」「spawn した agent が human-zero で黒字」を実 tx で。全 Phase PASS まで postpone しない。

## 7. 出典（全て firecrawl/gh api で実在確認、本 session 2026-07-06）
研究A brief（marketplace/payment、agentId ac8e4d8f）+ 研究B brief（cloud/self-host/UBI、agentId adbe7145、artifact a0cda35e）。各主張に source URL + 引用付き。UNVERIFIED 項目（Golem mainnet 入金、BlockRun Modal GPU availability 等）は明記。
