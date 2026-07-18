# SPEC: bounty loop — 稼ぐが先、crypto は後

status: ACTIVE / 作成 2026-07-18 / 主体 Fable（plan+verify）/ executor Sol（/flowa）/ 実行主体 claude-p loop
研究の土台 → `2026-07-18-bounty-loop-research-and-design.md`。
spec は SSOT。発見のたび本文を実測値に書き換える。

## ★2026-07-18 PIVOT（Dais 指示。上位が旧記述を上書き）★

**crypto-only 制約を外す。まず bank 口座（Dais の口座）に振り込まれる bounty で今すぐ稼ぐ。crypto payout は後回しの最適化。**
- 理由: 全 crypto rail を実測 → poidh(accept 8.6%・現地写真)・gib.work(live dev 在庫1件)・Superteam(人間 claim) は income にならないと確定。gig 型で唯一 real 在庫 × PR-merit accept × real money を持つのは **Algora（Stripe→bank 払い）**。crypto 制約を外せば復活する。
- **human-zero の適用範囲**: loop の日次動作（discover→コード→PR→submit→track）は human-zero。payout endpoint は **Dais の一回限りの bank/Stripe**（gig-work の Coconala→Dais MUFG と同じモデル。「唯一の人要素=一回限りの口座」）。crypto wallet 直払いは後続 phase。
- 既存資産: **`profitable-claude/skills/bounty/` は元々 Algora 用**（PR→merge→track→Stripe payout、`GITHUB_IDENTITY=Daisuke134` default）。2026-07-12 に `.disabled` 化されただけ → **復活させて回す**のが最短。
- on-chain 作業（poidh read lib・native-verify、実 tx で着金検出を実証済み）は **crypto payout phase 用に棚上げ**（worktree `feature/bounty-onchain-rail`, commit b971d51 保持）。破棄しない。

---

## STATUS（実装済み vs 残タスク。2026-07-18）

**実装済み（検証まで完了）:**
- 研究 + spec（全 rail 実測・SSOT 化・bank-first Algora に pivot）
- poidh on-chain lib + native-verify（19テスト green、実 tx で 0.1297 ETH 着金検出＝T5 green）。**crypto phase 用に棚上げ**（worktree `feature/bounty-onchain-rail` commit b971d51）
- 既存 harness の実読 + go-live 差分確定（gh 認証 Daisuke134=repo+workflow OK、pipeline は完成コード）

**残タスク（実際に稼ぐまで。担当明記。/flowa = Fable plan / Sol execute / Fable verify）:**
| # | 残タスク | 担当 | 依存 |
|---|---|---|---|
| R1 | **Algora onboarding（一回限りの人手）**: algora.io に GitHub(Daisuke134) ログイン → Stripe Connect + KYC + 銀行口座 + 税フォーム。日本個人の受取可否/書類は実 onboarding で確定。**Fable がブラウザ駆動、KYC/銀行/税の個人入力は Dais** | Fable(browser)+**Dais**(個人情報) | — |
| R2 | **loop 復活（ops）**: `.disabled` plist 2枚を再有効化 + `bounty-cli.sh` で core 起動。discover→PR→track が回り始める | Fable(launchd kickstart) | — |
| R3 | **入金 verify 配線（code）**: record-earn は on-chain USDC 専用。Algora dashboard(login-gated) 読取 or Stripe 入金検知の settle パスを新規実装（merge→paid を auto-verify）。INV-8/9 準拠 | **Sol** | R1 |
| R4 | **win-rate 改善（code）**: 旧 harness は実質 $0（agent 飽和 flat-38）。merge されやすい repo 狙い(real USD クラスタ sorosave 等)・PR 品質・spray 回避を self-improve 層に反映（研究 §4 の勝ちパターン） | **Sol** | R2 |
| R5 | **稼いだか verify**: loop の apply→PR→merge→**着金**を実測。done=金が着いた時のみ・1件で止めず loop 継続 | **Fable** | R1-R4 |

**critical path**: R1(Dais onboarding) が全ての payout を unblock。R2(復活) は即可能。R3 は R1 後。

---

## GOAL（検証可能な done）

**claude-p の loop が、人間ゼロの日次動作で Algora（等）の real bounty に応募→コード→PR を出し、merge され、報酬が Dais の bank/Stripe に着金する。それをループが繰り返し earn ledger に記録する。**

done（AND、全て実測で確認）:
1. claude-p loop が live bounty を discover→gate（scam/競合フィルタ）→attempt で **実 PR を提出**（GitHub 上に PR URL が存在）。
2. その PR が対象 repo に **merge** される（`gh pr view` で MERGED 確認）。
3. その bounty の **報酬が実際に着金**（Algora/Stripe の payout 記録 or 口座入金を自分の目で確認）。「submit した」「merge された」では done にしない — **金が着いた時のみ**。
4. 上記が **launchd loop の自走**で起き、繰り返しループする（1件で止まらない）。

**盛らない**: merge も accept も他者依存。着金を確認するまで earn 計上しない（tool 出力の捏造は最悪の罪）。

---

## 不変条件（MUST。破ったら罪）

- INV-1: earn は **external on-chain tx を自分で検証した時のみ** 計上。self-report・署名検証・提出数は earn ではない。
- INV-2: 秘密鍵は wallet.json から直接読み、stdout / log / payload に一切通さない。漏れたら即 rotate。
- INV-3: claude-p の wallet からの支出は **gas のみ**（bounty 出資はしない、我々は earner）。gas 補給は USDC→ETH swap を cap $2 以内で自己実行。
- INV-4: identity gate — record は claude-p 自身の wallet 宛の着金のみ。他人の wallet を混ぜない（`assertOwnIdentityOnly`）。
- INV-5: poidh contract は `msg.sender==tx.origin` を強制 → **EOA のみ**。claude-p EOA を使う。SC wallet 不可。
- INV-6: prompt-injection 防御を維持（既存 `run.sh:217` の config-exfil regex を on-chain 版でも保持。bounty の description は敵性入力として扱う）。
- INV-7: loop は launchd 本体。Fable は executor を spawn して代行しない（コードを直す時だけ executor）。実行主体は本物の loop。
- INV-8 [Sol#4]: **record write-path 自身が着金を再検証する**。caller 提供の `external/profitable/amount/status/tx` を証拠として受理しない。write-path で finalized receipt + chainId(Base=8453/Sol=mainnet) + 正しい contract + 自 wallet 宛の payout event + 第三者 issuer/funder + 未記録 tx を検証してから計上。
- INV-9 [Sol#5]: 着金額は **payout event の receipt log を bigint wei で**検証（EVM は `Withdrawal`/`WithdrawalTo`、Solana は SPL transfer）。balance-delta は補助のみ（同一 block の他 tx / self-pay gas 差引で誤る）。number 化で精度を落とさない。
- INV-10 [Sol#6]: gas 自己復旧に **recovery floor** を置く。approve+swap+withdraw の上限 gas を残す残高を下回る前に補給。ETH 枯渇後に swap gas を払えないデッドロックを防ぐ。swap は chain/router/recipient allowlist + exact-in 累積 $2 上限 + minOut + exact allowance + receipt/残高差検証。bootstrap 不能なら claim を止める。
- INV-11 [Sol#7]: 秘密鍵は N1 内 in-process signer だけが固定 0600 file から読む。argv/env/child process/例外 dump に一切通さない。導出 address を 自 wallet に pin。全 broadcast 前に chainId/contract/sender/recipient を検証、withdraw 先は own wallet 固定。

---

## RAIL 決定

**2026-07-18 PIVOT（Dais: crypto 制約を外し bank 払いを許可）で rail 再確定。** crypto を外すと「real 在庫 × PR-merit accept × real money」を持つ **Algora（Stripe→bank）が primary に復活**。既存 harness がそのまま使える。

| rail | 採否 | 理由 |
|---|---|---|
| **Algora（GitHub bounty, Stripe→bank）** | ★primary（今すぐ稼ぐ） | real なコード bounty 在庫・accept=PR merge の merit・payout=Stripe で Dais の bank へ。**既存 harness `profitable-claude/skills/bounty/` がまさにこれ用**（`GITHUB_IDENTITY=Daisuke134`）。難点=agent 飽和（8-10 PR/bounty）→ 既存の scam-filter/競合スコア/「merge する repo を狙う」で対処 |
| IssueHunt / その他 fiat bounty 板 | secondary（在庫補完） | GitHub issue bounty、PayPal/bank 払い。Algora 在庫が薄い時の補完。recon で実態確認 |
| Immunefi + Code4rena/Sherlock（audit） | scale phase | USDC を wallet 直・merit・実弾 $1k〜$10M。crypto payout phase と同時に。ゲート=valid finding 実力（高分散） |
| poidh (Base) | 棚上げ＝crypto phase の mechanism | on-chain 配管・native-verify は実証済、crypto 直払い phase で再利用。income rail 不可(accept 8.6%) |
| gib.work / Superteam | 却下 | gib=live dev 在庫1件・funder 裁量、Superteam=人間 claim。income にならない |

**crypto payout は後続 phase**（Algora で稼ぐ実績ができてから、audit(Immunefi/Code4rena) で crypto wallet 直払いに拡張）。今は bank-first。

---

## 実装（既存 harness の付け替え。file:line）

土台 = `profitable-claude/skills/bounty/`（state machine は維持、rail 差し替え）。追加 lib は `~/anicca/skills/_shared/lib/`。

新規:
- **N1** `_shared/lib/poidh.mjs` — viem read/write。関数: `listOpenBounties(chain)`（`bountyCounter`+`bounties(id)`+`getClaimsByBountyId` で open 列挙）/ `submitClaim({bountyId,name,desc,uri})`（`createClaim`、EOA 署名）/ `bountyState(bountyId)`（claimer/accepted poll）/ `pendingWithdrawal(addr)` / `withdraw()`. contract Base=`0x5555Fa783936C260f77385b4E153B9725feF1719`。ABI は poidh-sentinel `src/features/bot/poidh-contract.ts` から移植。
- **N2** `_shared/lib/native-verify.mjs` — **native ETH inflow 検証器（現状 lib に無い、必須）**。`ethInflowForTx(txHash, wallet, opts)` → number（当該 tx で wallet への native 純流入 ETH、internal tx 含むため trace/receipt+balance-delta で判定）。`ethBalance(wallet)`。Base RPC。
- **N3** proof 生成: blockrun_image で bounty 要求の画像を生成→IPFS(nft.storage/web3.storage or poidh 既定 pinner)→`uri`。attempt() から呼ぶ。

差し替え（`skills/bounty/run.sh`）:
- **C1** `discover() run.sh:17-69`: `gh api search/issues commenter/involves:algora-pbc`(24,35) → `poidh.listOpenBounties('base')`。`bounties.json` schema は `{title,url,repo,comments}` から `{bountyId,title,amount_eth,claims_count,chain}` へ。
- **C2** `gate() run.sh:157-259`: algora コメント $ 抽出(240-245)・撤回 regex(189,222)・`gh pr list`(228) → on-chain view: `amount_eth`=`bounties(id).amount`、飽和度=`claims_count`、既 accept=`claimer!=0x0`。prompt-injection regex(217) は保持(INV-6)。scoring（研究 §4: 低競合優先、scam フィルタ）を移植。
- **C3** `attempt() run.sh:75-101`: PR artifact → N3 で proof 生成 → `poidh.submitClaim`。`attempts.jsonl` schema: `pr` → `{bountyId,claimId,tx,uri}`。
- **C4** `track() run.sh:103-151`: `gh pr view`(134) → `poidh.bountyState` で accepted poll。accepted→`poidh.pendingWithdrawal`>0→`poidh.withdraw()`→tx。
- **C5** settle `run.sh:146-149`: `founder-loop/record-earn.mjs`（Base USDC ERC20 のみ検知）→ **N2 native-verify で ETH 着金確認** → `earn/lib/record.mjs` で計上。
- **C6** `identity-guard.mjs:30-67` の `ALLOWED_EARN_SOURCES` に **`poidh` 追加**（無いと record 拒否）。`assertOwnEarnSource('poidh')` を通す。

loop 配線:
- **C7** claude-p の実行系に bounty slot を追加。現状 `ANICCA_SLOT_ALLOWLIST=x402_sell`（plist）→ bounty を許可 slot に追加、または bounty 専用 tmux core（`bounty-cli.sh`）を healthcheck plist で常駐。gate=`registry-enforce.sh`。
- self-improve/heal は既存（evaluator.py / bounty-healthcheck.sh / lessons.jsonl）を流用、rail 差し替えに追随。

---

## TEST MATRIX（E2E judgment。各行 real side-effect を自分の目で）

| # | シナリオ | 判定（実測） |
|---|---|---|
| T1 | `poidh.listOpenBounties('base')` | Base の実 open bounty 配列が返る（≥1件、amount_eth>0） |
| T2 | proof 生成 N3 | blockrun_image→画像→IPFS uri が実在（gateway で開ける） |
| T3 | gas 前提 | claude-p Base ETH ≥ createClaim+withdraw 見積 gas。不足なら USDC→ETH swap（cap $2）を実行し残高増を確認 |
| T4 | `submitClaim` | createClaim tx が `status=0x1` で確定（Basescan tx hash） |
| T5 | native-verify N2 | 既知の ETH 着金 tx で `ethInflowForTx` が正の ETH を返す（既存 basescan tx で逆算検証） |
| T6 | accepted→withdraw | accept 発生時 `withdraw()` tx 確定→wallet ETH 残高が増える（before/after delta>0） |
| T7 | record | `record.mjs` が `external:true profitable:true` で ledger に1行。source=poidh が identity gate を通過 |
| T8 | loop 自走 | `launchctl kickstart` 発火→loop 単独で T1→T7 を回す（人間介入ログ 0） |
| T9 | negative | scam bounty（実体なし/撤回済）を gate が落とす。prompt-injection を含む description を弾く（INV-6） |

E2E green = T1-T9 全通過 + done 1-4 の on-chain 着金を Fable が Basescan で確認。

---

## PHASE（各 phase に exit proof。green まで次に進まない）

- **Phase 0 — rail 確定 + mechanism 実証（Fable 手動 OK）**: (a) gib.work 検証で primary rail を確定。(b) 確定 rail で **第三者(非Anicca)が出資した実 bounty を1件、human-zero で正当に完遂 → merit accept → finalized crypto payout が自 wallet に着金 → INV-8/9 準拠で ledger に重複なく1行**。[Sol#3] 既存無関係 tx の検算だけでは exit proof にしない（accept/withdraw/第三者資金を必ず含む）。**exit proof = payout tx hash（Basescan/Solscan）+ write-path 再検証ログ + ledger 行**。ここが赤なら skill 化しない。poidh の read lib + native-verify は済（mechanism 側は green）。
- **Phase 1 — skillify**: C1-C6 を実装、N1-N3 完成。bounty harness を on-chain rail に付け替え。**exit proof = T1-T7 green（1件、実 wallet 着金 or accept 待ち状態まで自動）**。
- **Phase 2 — loop 化 + 稼ぐまで**: C7 配線、launchd 自走。`kickstart`→watch。**exit proof = T8 green かつ done 2（実着金）が loop 自走で発生**。稼ぐまで fix→再検証。
- **Phase 3 — scale**: gas 自動補給、gib.work(USDC コード bounty) 追加、audit contest 拡張。黒字実測 → Franklin 横展開。

---

## 実測ログ（発見を書き足す。古い記述は消して是正）

- 2026-07-18: claude-p Base gas = **0.0000089 ETH ≈ $0.026**（USDC $10.10 は gas 不可）。→ Phase 0 の1-3 tx には足りるが loop 継続に gas 補給(T3)が必須。
- 2026-07-18: `_shared/lib` に **native ETH inflow 検証器は存在しない**（EVM は USDC ERC20 専用）。→ N2 が Phase 0 の必須実装。
- 2026-07-18: `identity-guard.mjs ALLOWED_EARN_SOURCES` に poidh/bounty 無し → C6 必須。
- 2026-07-18: `skills/bounty/` に SKILL.md は存在しない。self-improve/heal は evaluator.py + healthcheck + lessons.jsonl の3要素で実装済。
- 2026-07-18: poidh 成果物は**画像 proof**（コード PR ではない）。AI 自己生成は blockrun_image で可能。gib.work がコード bounty 寄りだが API 未文書化。
- 2026-07-18 [Phase0 read side 完了, commit b971d51 未push]: poidh Base **LIVE = 307件中 71 open**（実測）。ABI 実名確定: `bountyCounter()`（`bountyCount` は revert）/ `getClaimsByBountyId(uint256,uint256)` 2引数 / `bounties(id)` / `pendingWithdrawals(address)` / `createClaim(bountyId,name,uri,description)`。**罠**: `getBounties(offset)` は paginate せず同じ10件を返す → `bounties(id)` を Multicall3 で個別 scan（307 calls ~280ms）。RPC: llamarpc down、`base.publicnode.com`/`base.meowrpc.com`/`1rpc.io/base` が生存。
- 2026-07-18: **native-verify N2 実装済・T5 green**。手法 = balance-delta before/after block + self-pay 時の gas 足し戻し（`debug_traceTransaction` は Base 公開 RPC 全滅 -32601、Basescan V2 は API key 不在）。実 tx `0xba7792…78b4` で `ethInflowForTx`=0.1297 ETH を検出。19 テスト green。
- 2026-07-18: **blockrun_image ツールは grep で発見できず** → proof-gen N3 の画像生成 API は未確定（要 MCP 確認）。
- 2026-07-18 [gib.work 実地検証]: **③使えない**。payout=wallet-native/USDC/no-KYC で human-zero 適合だが、`api.gib.work/explore` total=426 中 **isOpen=true 4件・dev は1件のみ**（板の実態は Social Media 213/Misc 87）。accept=funder 裁量（PR merge 自動払いでない）。認証=Solana wallet 署名（OAuth/email 不要）。→ scale income rail にならず却下。primary を audit contest に確定。
- 2026-07-18 [rail 収束]: 全 rail 実測で確定 = human-zero+crypto+merit+実弾を同時に満たすのは **security audit（Immunefi always-on + Code4rena/Sherlock/CodeHawks contest）のみ**。loop の正体=自律 AI セキュリティ研究者。ゲート=valid finding 実力。scope 転換につき Dais 判断待ち。
- 2026-07-18 [Sol review verdict = **STOP-AND-REVISIT-RAIL**]: 7 blocking。#1 poidh 攻略前提破綻（proof=現地/original、AI 画像不可、sentinel は発注者側）#2 accept 8.6%・open の 55/71 が30日超で墓場・収益性ゲート不在 #3 Phase0 が rail を証明しない #4 record.mjs が caller 提供値を盲信＝done 捏造可 #5 balance-delta は偽陰陽性→event log を bigint wei で #6 gas 自己復旧デッドロック #7 鍵 broadcast 前防御。→ INV-8〜11 に昇格・rail 降格・Phase0 再定義で反映済。
- 2026-07-18 [71 open 全 dump・カテゴリ精査, Fable 実測]: AI が human-zero で勝てるのは **~10件のみ**（残りは現実世界/特定人物 proog）。AI 勝機案件: #263 "ship a real build"(0.0138ETH,claims2,純コード) / #107 "Farcaster Movie Trailer, Use AI"(0.0125ETH,claims3) / #237系 "tweet about \$Space proof=tweet URL"(claims0 多数, 0.001ETH) / #304 poem(claims9飽和) / #283 one question(claims1) / #301 NFT mint / #250 token split。→ **判定: poidh は mechanism 実証には最適だが income rail としては薄い**（大半 \$3〜40、accept は funder 依存）。zero-to-one の初ドルは取れる。scale($10k/月)は gib.work(コード/USDC)+audit へ pivot 必須。前提依存: tweet系は X/Farcaster account が要る（claude-p は未保有→要確認）。

## OPEN RISK / honest gap

- ★2026-07-18 最大リスク: poidh の open bounty の多くが**現実世界/社会的 proof 型**（"Interview a Politician", "Be A Freedom Fighter", "tattoos"）で、自律 AI が勝てない。71 open のうち **AI が human-zero で勝てる digital/creative 系（meme/art/generative）が何件あるか未精査**。ここが薄いと poidh は income rail として死ぬ（mechanism は実証できても金にならない）。→ Sol review + カテゴリ精査で判定。薄ければ rail を gib.work/audit に前倒し。
- poidh accept は funder 依存 = 着金タイミングを loop が制御できない。→ 「submit 完了」を earn と誤報告しない。多数の open bounty に低コストで claim し accept 率を稼ぐ設計にする。
- poidh 小額 = $10k/月には遠い。zero-to-one 用。volume は Phase 3 の audit/gig.work。
- gib.work API 未文書化 = Phase 2 で reverse-engineer 別タスク。
- gas 枯渇で loop 停止のリスク → T3 の自動 gas 補給を Phase 2 で必須化。
