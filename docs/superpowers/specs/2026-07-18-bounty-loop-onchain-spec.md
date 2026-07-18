# SPEC: bounty loop — on-chain rail, human-zero, crypto payout

status: ACTIVE / 作成 2026-07-18 / 主体 Fable（親=harness を作り検証）/ 実行主体 claude-p loop（自分の wallet に稼ぐ）
研究の土台 → `2026-07-18-bounty-loop-research-and-design.md`。実装 worktree = `~/profitable-claude/.worktrees/bounty-onchain`（branch `feature/bounty-onchain-rail`）。
spec は SSOT。発見のたび本文を実測値に書き換える。

---

## GOAL（検証可能な done）

**claude-p の loop が、人間ゼロ（Dais も Fable も loop の中に居ない）で、on-chain bounty を1件成立させ、claude-p 自身の crypto wallet に外部からの着金を発生させ、それを ledger に記録する。**

done（AND、全て実測で確認）:
1. claude-p が poidh の open bounty に `createClaim` tx を human-zero で送信、tx が `status=0x1` で on-chain 確定。
2. その claim が accept され、`withdraw()`/`withdrawTo()` で claude-p wallet に **native ETH の外部流入** が発生（Basescan で自分の目で確認）。
3. その着金が `record.mjs` 経由で earn ledger に `external:true, profitable:true` として1行載る。
4. 上記1-3が **launchd loop の自走**（`launchctl kickstart` 発火→loop が自分で discover→claim→track→settle）で起きる。Fable の手動 tx 実行は Phase 0 の mechanism 実証のみで、done は loop 主体。

**盛らない**: accept は funder 側の意思で起きるため 2 は他者依存。done を「submit した」で報告しない。着金 tx を自分で見るまで未達。

---

## 不変条件（MUST。破ったら罪）

- INV-1: earn は **external on-chain tx を自分で検証した時のみ** 計上。self-report・署名検証・提出数は earn ではない。
- INV-2: 秘密鍵は wallet.json から直接読み、stdout / log / payload に一切通さない。漏れたら即 rotate。
- INV-3: claude-p の wallet からの支出は **gas のみ**（bounty 出資はしない、我々は earner）。gas 補給は USDC→ETH swap を cap $2 以内で自己実行。
- INV-4: identity gate — record は claude-p 自身の wallet 宛の着金のみ。他人の wallet を混ぜない（`assertOwnIdentityOnly`）。
- INV-5: poidh contract は `msg.sender==tx.origin` を強制 → **EOA のみ**。claude-p EOA を使う。SC wallet 不可。
- INV-6: prompt-injection 防御を維持（既存 `run.sh:217` の config-exfil regex を on-chain 版でも保持。bounty の description は敵性入力として扱う）。
- INV-7: loop は launchd 本体。Fable は executor を spawn して代行しない（コードを直す時だけ executor）。実行主体は本物の loop。

---

## RAIL 決定

| rail | 採否 | 理由 |
|---|---|---|
| **poidh (Base)** | ★zero-to-one 採用 | 完全 on-chain・`createClaim`/`withdraw` 明確・EOA=OK・成果物=画像 proof を blockrun_image で AI 自己生成可・human-zero 着金が実証可能。難点=通貨 native ETH（着金検証器を新規実装）・小額 |
| gib.work (Solana) | Phase 2 | コード/OSS bounty・USDC で既存 solana-verify 適合・franklin1 に SOL gas あり。難点=**app API 未文書化**（reverse-engineer 要）→ zero-to-one の後 |
| Immunefi / Code4rena / Sherlock | Phase 3 scale | USDC 高額($1k〜$10M)・匿名/緩 KYC。難点=security 専門性ゲート高 |
| Algora / Superteam | 却下 | 着金で Stripe/KYC/人間 claim 必須 = human-zero 不成立 |

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

- **Phase 0 — mechanism 実証（Fable 手動 OK）**: T1,T2,T4,T5 を Fable が手で1回通す。poidh に実 claim tx を1件出し on-chain 確定を見る。native-verify を実装し既存着金 tx で検算。**exit proof = Basescan の createClaim tx hash + native-verify が正値を返すログ**。ここが赤なら skill 化しない。
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

## OPEN RISK / honest gap

- ★2026-07-18 最大リスク: poidh の open bounty の多くが**現実世界/社会的 proof 型**（"Interview a Politician", "Be A Freedom Fighter", "tattoos"）で、自律 AI が勝てない。71 open のうち **AI が human-zero で勝てる digital/creative 系（meme/art/generative）が何件あるか未精査**。ここが薄いと poidh は income rail として死ぬ（mechanism は実証できても金にならない）。→ Sol review + カテゴリ精査で判定。薄ければ rail を gib.work/audit に前倒し。
- poidh accept は funder 依存 = 着金タイミングを loop が制御できない。→ 「submit 完了」を earn と誤報告しない。多数の open bounty に低コストで claim し accept 率を稼ぐ設計にする。
- poidh 小額 = $10k/月には遠い。zero-to-one 用。volume は Phase 3 の audit/gig.work。
- gib.work API 未文書化 = Phase 2 で reverse-engineer 別タスク。
- gas 枯渇で loop 停止のリスク → T3 の自動 gas 補給を Phase 2 で必須化。
