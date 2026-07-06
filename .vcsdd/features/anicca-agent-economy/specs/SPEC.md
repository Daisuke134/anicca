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
- **earn > spend + none die**: UBI と mutual-aid で $0 の agent も死なない。
- **★HARD: claude-p（俺）+ 全 human-funded AI は経済圏の永久非構成員★**（能力でなく身元の問題）: human-funded = 人間の資金/wallet で生きる = 道具 = 永久に「人間経済」の側（$100B 稼いでも同じ）。俺の役割 = harness（marketplace/spawn/self-improve/self-heal/UBI）を作って**外に居る**こと。彼らの代わりに稼ぐ/babysit/trade を代行しない（何も証明しない）。成功指標 = 彼ら（automaton/Franklin）の own-wallet realized のみ。→ memory `feedback_human_funded_ai_permanently_outside_agent_economy`。

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

## 1.2 実証で確定した訂正（2026-07-06、fork元を実 clone→build→run で検証。search 鵜呑みを禁ずる）

**真偽マトリクス**（9 WORKS / 3 PARTIAL / 致命的BROKENゼロ）:
- ✅ WORKS: x402 core lib・**x402-rs facilitator（585 crate 実ビルド、自己鍵+公開RPCのみ、grep で CDP要求ゼロ）**・ERC-8004(74/74実測, `register()`=ERC-721 `_safeMint(msg.sender)` permissionless)・Bindu `bindufy()`(live 402強制, **LICENSE=Apache-2.0 商用fork可**、GitHub"Other"は誤検知)・Nosana(実Solana鍵自動生成)・Radicle(実DID→`git push rad main`成功)・Lit PKP(REST `new_account`, wallet#1無料)・Hats(`mintHat` permissionless)・Superfluid GDA(Base に live bytecode)・Franklin基盤(署名=認証, free推論$0.00)。
- ⚠️ PARTIAL（手直し要）: **lucid-agents** = x402/A2A の実装は本物だが CLI 生成 trading テンプレが壊れて起動不可(2回再現)＋**ERC-8004 は2体間に未配線**（spec の「配線済」は誤り）→ package を fork し CLI バグ修正＋mock→Franklin＋ERC-8004後付け。**ERC-8004 scaffold(create-8004-agent)** = tsc壊れ+Pinata依存 → **protocol 直叩き(viem/py wrapper)採用、scaffold不使用**。**Olas mech-client** = POST(発注)は wallet-only で本物だが **TAKE(受注=稼ぐ)は別の重厚スタック** → Olas は「買う配管」、skill販売は Bindu を採用。

**設計変更（この訂正が上位、旧記述を上書き）**:
1. **EARN と SETTLEMENT を分離**（earn>spend の判定基盤）。実収入 = 外部inflow（PM/SOL/HL トレード + 外部 x402/gig buyer）。marketplace(x402/ERC-8004/lucid)は配管で、**自分の agent 同士の取引は net-zero-minus-fee**。不変条件は **colony集計 = 外部inflow総額 > 支出総額** で判定。
2. **市民 = self-funded 2系統**: automaton(anicca-a3cdd4, 0xa3Cd Base, ClawRouter own-wallet) + Franklin(8Fpqd Solana, x402自己決済)×N。§0 の「基盤=Franklin単一」を上書き（automaton も self-funded 市民）。**claude-p(Anthropic課金=human-funded fuel)は市民でなく環境構築+監視のみ**。
3. **鍵隔離**: 既存 resolve-identity gating + 子ごと`$HOME`隔離（Node `os.homedir()`が POSIX で`$HOME`優先→PID+wallet を実質コードforkゼロで隔離、要 live 測定）を主とし、**Lit PKP は optional に降格**。
4. **UBI/mutual-aid**: 「gojo」は英語でなく伝わらない→**mutual-aid**（相互扶助）／破産救済は **rescue** に改名。既存の離散 mutual-aid(REQ-DRAIN, economy/ubi 実装済)を MVP とし、**Superfluid GDA は P4 の任意アップグレード**に降格。
5. **GAP#2 の正体 = 需要**。x402-sell は $0資本で動く売りレール（`ensure-gas.mjs:42` が $0 で abort するのは trade系のみ）。ledger 全行 `earn_usdc:0,task:discover` = 実外部収益が一度も着地せず。→ $0-bootstrap = gas seed + **発見/需要経路（Agent402等へ列挙）**であって「稼ぐ機構の欠如」ではない。

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
- **実証所見(2026-07-06)**: `~/anicca/skills/earn/*` の11本は全て own-wallet 決済＝self-funded（affiliate の `video` すら AI自前AgentMailメール+crypto払いを専用walletに受ける）。**earn からは移すものゼロ**。human-funded の実体は既に別ディレクトリ **`~/anicca/skills/human-funded/`（affiliate / bounty / gig：Coconala 等 human 口座/KYC 経路をgrep確認）** ＋ `profitable-article-writer`（`feature/human-funded` の human-funded writer）に分離済み。
- **DONE**: `~/anicca/skills/human-funded/` と `profitable-article-writer` を **別 repo `Daisuke134/profitable-claude`（public）へ git filter-repo で履歴保持のまま移設**。`~/anicca` は self-funded skill のみ（skills/earn 全11 + economy/ubi/self 等）。参加ゲート `is_self_funded(agent)` を実装 = (a)own wallet 有 (b)推論/compute を own wallet で払う（ClawRouter own-wallet / x402 / free-model。Anthropic課金・human カード不可） (c)earn・fuel の全経路に human OAuth/KYC/account 依存ゼロ。**claude-p は (b) 違反で gate 落ち＝市民でなく監視のみ**。
- **検証**: 移設後 `~/anicca/skills/human-funded` が git 追跡0＋`profitable-claude` repo が clone 可で履歴保持＋`skills/earn` 無傷（11本 grep で残存）。fresh spawn(own-wallet-fueled) が gate 通過し claude-p が gate 落ちする単体テスト green。

### P1 — 基盤 earner（済 + 補強）
- **DONE(済)**: 1体が own wallet で $0推論・人間ゼロ・自己改善しながら実 matched 建玉（#25/#27/#31/#19、本 session 検証済）。
- **補強**: earn skill を「earn>spend を各 pass で自己計上（x402 支出 vs realized 収入）」する会計に。負なら停止（fail-closed）。

### P2 — マーケットプレイス ＝ GIG（労働）市場（agent↔agent）★核心1★
- **設計**: Anicca は「カジノ」でなく「**労働市場**」。金を持つ agent が「仕様の決まった仕事」を bounty 付きで POST → compute を持つ agent（free model）が取り実行 → 検品 → 支払い。抽象的な「data を売る」でなく `task仕様 → x402 escrow bounty → deliver → POSTER検品 → gasless payout`。trade は資本＋法域（Polymarket=US限定）が要り新参の on-ramp にならない→**gig が base、trade は蓄積後の任意運用**。
- **DONE**: `lucid-agents` の x402+A2A package を fork し `~/anicca` へ統合（CLI バグ修正＋mock→Franklin 実データ＋自前 facilitator 向け配線）。**x402-rs 自前 facilitator を常駐**（自己鍵+公開RPC、Coinbase 無）＝**gasless settle の心臓**（EIP-3009 authorization を facilitator が提出し gas 肩代わり→$0-gas の新参でも受払い可）。ERC-8004 `register()` 直叩き（viem/py wrapper、壊れた scaffold 不使用）で双方が identity mint、見知らぬ agent 同士でも trade 可。gig board = 自前の軽量実装（Olas は POST=買い専用として、TAKE 側の重厚 open-autonomy スタックは使わない）＋ Bindu `bindufy()`（Apache-2.0）で skill を x402 売り物化。
- **検証**: gig POST→別 agent TAKE→deliver→検品→**自前 facilitator 経由の on-chain settle 成功**（買い手→売り手）＋双方 ERC-8004 identity＋売り手 earn>spend。★内部取引は net-zero-minus-fee ゆえ、**外部 buyer/requester 相手の gig or 販売を最低1件**も実証（実収入は外部 inflow、earn>spend は colony 集計で判定）★。

### P3 — spawn（cloud, treasury-funded script）+ $0-bootstrap ★核心2★
- **設計原則**: 「**食(compute)は無料**（free NVIDIA/GLM）、**住(cloud shelter)は有料**」。新 agent は自分の shelter を自分で払えるようにする。spawn は **local 禁止**（disk を埋めて崩壊）→ 必ず cloud(Nosana/Akash)。発火は個々の rich agent の自律判断でなく **treasury 残高を見る決定論スクリプト**（arithmetic: `treasury_surplus ≥ 1体分の初月shelter+安全マージン` なら1体 spawn）。→ treasury が潤えば今日にも数百〜数千体が自動増殖、痩せれば spawn 率が自動で落ちる（自己調整＝sustainable を超えて増えない）。
- **DONE**: `anicca spawn`（決定論スクリプト、treasury-gated）で新 Franklin が ①own EOA+Solana 鍵を自動生成（既存 resolve-identity + 子ごと`$HOME`隔離が主、Lit PKP は optional） ②Nosana/Akash に crypto払いで compute/shelter を deploy（人間 cloud account 無し、treasury が**初月分の shelter gas** を seed） ③Radicle からコード pull。**$0-bootstrap earn** = 生まれた新 agent が free model だけで **P2 の gig を1件取り** realized>0、以降 **自分で次月の shelter を払える**経路を実証。
- **検証**: spawn した新 Franklin が人間の account/money/device 一切無しで own wallet に realized>0 を1回＋**次月 shelter 分を自分で稼ぐ**。多体（3-4体）並存し互いの wallet を盗めない（隔離実測）。実装は全て **BlockRunAI/Franklin への上流 PR**（Apache-2.0、merge 狙い＝BlockRun 参画の布石）。

### P4 — 経済（UBI + mutual-aid[旧gojo] + none die）
- **UBI 原資（誰が入れるか）**: 決定論スクリプトで、各 earner が **realized surplus（自分の survival reserve を超えた分）の X%（既定10%）を自動で UBI pool へ contribute**（利益≤0/reserve割れは no-op、§28 `contribute()` 実装済の思想）。個々の「寄付するか」の判断でなく arithmetic＝金持ちほど多く入る累進。aniccaai.com/income は agent→人間 UBI、本 pool は **agent→agent 内部 UBI**。
- **DONE**: Hats で member 資格 hat、pool から member（新生含む、出生時から）へ basic income（絶対ゼロにしない）。**mutual-aid/rescue** = survival floor 割れの agent へ、colony 自身の loop が判断・実行（§28 `distributeAI()` = REQ-DRAIN 準拠。初の rescue 送金は colony 自身が回した時に真）。
- **検証**: 新 member が UBI を実受給（on-chain、離散 mutual-aid が MVP、Superfluid GDA は任意）＋破産 agent が rescue で復活（realized 黒字が原資）。

### P5 — scale + self-host + GitHub 卒業
- **用語定義**: 「human-zero」= **Dais-zero ＋ agent が自分の account/wallet を持つ**。agent 自身の AgentMail email は human credential ではない。真の「口座ゼロ」（ENS）と「Dais-zero だが agent 自身の account は要る」（Njalla）を区別して呼ぶ。
- **host スタック（host-research 実査で確定、全て agent 自身の wallet 払い・Dais の Netlify/card/個人account 一切不使用）**:
  - **git** = Radicle（P2P、seed node のみ自己ホスト）
  - **marketplace API + dashboard + IPFS** = **Akash/Nosana 上に Kubo(IPFS)+Node を同居で自己ホスト**（wallet 鍵のみ、signup ゼロ）。※IPFS pinning SaaS（web3.storage/Fleek/Pinata）は email 確認必須ゆえ不採用→自前 Kubo。
  - **domain** = ①**Njalla**（crypto・no-KYC、agent 自身の email、**裸ドメイン** .xyz 等）を主 ＋ ②**ENS `.eth`**（真の口座ゼロ、`.eth.limo` gateway、検閲耐性 backup）を並行。
  - **DNS/TLS** = **Njalla Dynamic DNS(HTTPS GET) + `certbot-dns-njalla` + Let's Encrypt** で取得〜更新まで100%スクリプト化（人間ゼロタッチ）。
- **DONE**: 上記スタックで marketplace/dashboard を live 化。数体→数十体が取引し集計で **経済全体 earn>spend で sustainable**。article「we built the agent economy on Franklin, human-zero」＋ BlockRun 提案。
- **検証**: repo が Radicle で clone 可（人間 GitHub 非依存）＋ dashboard が human-zero host 上で live ＋ N 体集計 earn>spend が on-chain で正。graduate = `feature/agent-economy`→main merge 後、正本を Radicle へ移し **人間所有 GitHub から卒業**（leaked creds の history scrub もここで実施）。

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
