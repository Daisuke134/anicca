# SPEC — Franklin: ERC-8004 Reputation 採用 + Gas 自動化（gasless への布石）

> 設計spec（GLVS の Goal 具体化 / VCSDD の入力）。2026-07-12。対象コード = `~/anicca` repo の `skills/economy/gig/**` + `skills/economy/lending/**`。evidence 正本 = [[../../loop-engineering/17-agent-economy-deep-research-2026-07-10]] §9/§10 + [[../../loop-engineering/23-anicca-loop-architecture-redesign]] §11。VCSDD feature 名 = `franklin-reputation-gasless`（既存 feature と衝突しない）。

## 0. なぜやるか（3つの実痛）
1. **gas 痛**: `identity.mjs` L24-26 — 「gasless/relay 経路が無い。書き込み毎に呼び出し wallet が native ETH 必須。mainnet gas 補給は手動 transfer」。→ 恒常的に「insufficient gas」で on-chain 操作が落ち、人間が手で ETH を補給している。
2. **trust-blind**: `gig.mjs:gigVerifyAndPay` は payout 後 `paid` にするだけで ERC-8004 Reputation に何も書かない。全 gig が毎回ゼロから信用構築。
3. **lending cold-start**: `lending-gate.mjs` の与信は自前 `loans.jsonl`（返済回数）のみ。信用が可搬せず、新規 lender/他 instance 間でリセット。

## 1. Goal（検証可能な done 条件、全て MUST）
- **G1（gas）**: 全 on-chain 書き込みの前に `ensureGas()` preflight が走る。native 残高が閾値未満のとき、**testnet では**指定 funder から hard cap 内で自動 drip し、**mainnet では自動送金せず**「必要 gas 量つき構造化エラー」を返す（silent fail 禁止・想定外 spend 禁止）。done = Base Sepolia で register→giveFeedback が**手動 ETH 補給ゼロ**で通る E2E ログ。
- **G2（reputation 書込）**: `gigVerifyAndPay` 成功時に `giveFeedback(takerAgentId, +100, "gig-complete", gigId)`、reject 時に `-100` を Reputation Registry へ書く（fail-open: 書込失敗で payout 自体は失敗させない）。done = Base Sepolia で完了 gig の feedback tx hash + `getSummary` の count 増を独立 `eth_call` で確認。
- **G3（reputation gate）**: `lending/lib/reputation-gate.mjs` の `passesOnchainReputationGate({borrowerAgentId,minScore,minJobCount})` を lending 与信に合成。**未設定（min=0）なら素通り = fail-open で段階導入**。done = 閾値設定時に実績不足 borrower が弾かれる unit + testnet 実証。
  - ★2026-07-12 spec 訂正（adversary FIND-002 起因、phase 1c 判断）: gate は**本番の lending 判定経路に実配線する**こと。`isBorrowerEligibleWithReputationGate` を新設して誰も呼ばない dead code にしてはならない。**実経路 = `lending-orchestrator.mjs:executeLoanIssuanceAttempt`（借入発行の実入口）で、eligibility 判定の直後に gate を合成する**（`wake-gate.mjs` が eligibility を別途行うならそこも）。既定 fail-open（min=0 で全通過）ゆえ、閾値未設定なら既存挙動と完全に同一＝安全に配線できる。done に「本番経路からの呼び出しが grep で1件以上」を追加。
- **G4（gasless 布石）**: ERC-4337 + paymaster（AgentKit `CdpSmartWalletProvider`）による真の gasless を**評価し**、`lib/wallet-provider.mjs` に差し替え可能な seam を作る（本 spec では**実配線しない**、seam のみ）。done = seam の存在 + 評価メモ。

## 2. Non-goals（この spec でやらない）
- mainnet の live-money 有効化（Reputation の mainnet 書込は別の gated step）。本 spec は **testnet(Base Sepolia) first**。
- ERC-4337 スマートアカウントへの資金移行（G4 は seam まで）。
- ERC-8004 Validation registry の採用（別 spec）。

## 3. 触るファイル境界（worktree 内のみ）
- 新規: `skills/economy/gig/lib/reputation.mjs`、`skills/economy/gig/lib/ensure-gas.mjs`、`skills/economy/lending/lib/reputation-gate.mjs`、`skills/economy/gig/lib/wallet-provider.mjs`（seam）。
- 変更: `skills/economy/gig/gig.mjs`（verify/reject 経路に giveFeedback 追加、書込前に ensureGas）、`skills/economy/lending/lib/lending-gate.mjs`（gate 合成関数の新設、既存 pure 判定 `isBorrowerEligible` は壊さない）、**`skills/economy/lending/lib/lending-orchestrator.mjs`（★FIND-002 訂正: G3 gate を本番の借入発行経路に実配線。fail-open 既定ゆえ挙動不変）**、必要なら `skills/economy/lending/lib/wake-gate.mjs`（eligibility を別途行う箇所があれば同様に）。
- テスト: 各 lib の unit + Base Sepolia E2E スクリプト。

## 4. ★ MONEY-SAFETY（MUST、違反=即 FAIL）★
- **絶対に触らない**: wallet 秘密鍵、`.env`、`.solana-session`、`ledger.mjs`、spend cap、`SOL_TRADE_MAX_SPEND`（0 のまま）、`.vcsdd/features/anicca-agent-economy/**`。
- **testnet first**: 全 E2E は Base Sepolia。mainnet 書込は本 spec の done に含めない。
- **gas 自動 drip は testnet のみ + hard cap**（例: 1 op あたり ≤ 0.0005 ETH、1 日 ≤ N 回、cap 超過で停止）。mainnet は自動 spend せず構造化エラー。
- **reputation は fail-open**: 書込/読取の失敗で payout・lending の本処理を壊さない（資金は既に確定済）。
- 破壊的 git 操作禁止（reset --hard / clean -f / force-push）。

## 5. Verification（VCSDD adversary + 自己完結 E2E）
- **RED→GREEN**: 各 lib の pure ロジック（ensureGas の閾値判定、gate の閾値合成、giveFeedback の引数組立）を unit test で先に落とす。
- **E2E（Base Sepolia、fresh evidence）**: (a) register→giveFeedback が手動補給ゼロで通る tx ログ (b) getSummary の count 増を独立 `eth_call` (c) 閾値設定時に低実績 borrower が gate で弾かれる。
- **adversary（fresh Sonnet、§dev-workflow）**: diff + money-safety 章の全 MUST を機械照合。blocking 0 かつ E2E green まで反復（最大5）。
- **honesty**: 「mainnet で動く」は testnet E2E だけでは主張しない。proven(testnet) と not-yet(mainnet) を分けて STATE に書く。

## 6. 実装順（23 §11 の優先順と一致）
1. G1 `ensure-gas.mjs`（gas 痛を先に消す＝以降の全 on-chain 作業が楽になる）
2. G2 `reputation.mjs` + `gigVerifyAndPay` 配線（proof-of-earning/評判層の第一歩）
3. G3 `reputation-gate.mjs`（lending cold-start 緩和）
4. G4 `wallet-provider.mjs` seam + gasless 評価メモ（真の gas 解の布石）

## 7. なぜこれが「理想」に近づくか（file 17 §10 対応）
- 部品⑦評判・部品⑧検証(proof-of-earning) の未成熟層に実際に踏み込む（業界公認フロンティア、a16z「検証が希少」）。
- 部品③wallet の gas 運用痛を自動化 → onboarding のボトルネックを外す。
- 配管(x402/ERC-8004 Identity)は既採用＝再発明せず、その隣の未使用部品を copy して繋ぐ。
