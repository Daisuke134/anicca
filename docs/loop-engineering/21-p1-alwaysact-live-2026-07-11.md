# 21 — P1 always-act LIVE 記録（2026-07-11 10:28 JST go-live）

★ MONEY EVIDENCE PROTOCOL 準拠: 本 MD は「稼いだ」報告ではない。realized profit はまだ 0。構造 milestone の記録である。★

## 達成（全て一次証拠）

| 項目 | 証拠 |
|---|---|
| VCSDD 完走 | spec-review 5 iters（findings 5→3→1→1→0 PASS）/ impl-review 4 iters（2→4→1→0 PASS）/ harden 33/33 PROP + semgrep 0 / converge 5 iters（2→2→3→1→0 **CONVERGED**）。全 adversary = fresh Opus 4.8、全 test 実行は thinker が独立再実行（183/183 ×4回） |
| merge | `9618621c` on anicca main（engagement OFF で安全 deploy）。post-merge 183/183 |
| flag-OFF 検証 | 再起動後 wake が `always_act_not_engaged` 診断行を出力（REQ-512 本番動作確認） |
| go-live | `always_act_go_live` ledger 行（exactly-once、config_source=launchd-plist）+ `ALWAYS_ACT_ENABLED=1` を franklin-loop plist へ + 再起動（PID 24012） |
| **autonomous ACT** | engaged wake が **sleep せず** menu から slot を選択し実行: 10:28:23 初 engaged wake → escalation（正直）、10:30:33 wake → `economy/gig` ACT → 板空を正直に記録 → `router_no_realized_action` escalation → 次 wake また ACT。**NO-WAIT doctrine が本番で構造的に成立** |
| money-guard | kill-switch / identity / cumulative-loss / MAX_SPEND($0.25) / reserve 全て無傷（9回の adversary review + deployed grep で確認） |

## 実装の中身（1行）

`runtime/loop/always-act-router.mjs`（純核: attempt-state machine {0,1}、risk-free reroute filter、per-attempt validity guard）+ index.mjs 早期 dispatch → `runAlwaysActWake`、REQ-510/512 observability、go-live.mjs。engagement は Franklin identity + env flag の二重 gate。

## 正直な現状と次

- ACT はする、しかし**まだ稼げない**: gig=板空+$0.02 / sol=neutral 市場 / hl=bridge 資金不足。稼ぎの点火 = P4（Franklin2 wallet + Franklin1 Base 資金 + 初ローン）と P1.5 edge（coldstart-evolution）。
- 出血対策: WAIT が ACT に変わったので、次の監視点は「ACT のコスト（x402 fuel）< 期待収益」の会計 gate 挙動（wake 毎 ~$0.009、cap $0.25/pass は据え置き）。
- 事件記録: converge 中に外部プロセスが worktree を削除（branch/commit は push 済みで無損失、`.anicca-keep` marker で再発緩和）。fablize hook の「tool failure」誤発火は session 全体の既知 artifact（複数 agent が ledger 検査で実失敗なしと確認）。

## P4 lending — 初ローンの最終ブロッカー（2026-07-11、実 diagnose）

★ MONEY EVIDENCE: 「稼いだ/貸せた」ではない。実バグ diagnose の記録。★

**達成（構造ブロッカー全解除、RPC 実測）:**
- Franklin2 EVM wallet 生成(`0xe774…7ce9`) + daemon franklin[N] 認識(merged) + citizens.json EVM 行投入 → **lending gate が Franklin→Franklin2 を初 eligible pair 選定**。
- refill: Solana USDC $6.50→Base、tx `4JWEKF8u…` → Franklin Base USDC $6.4978（RPC 実測）。
- x402 facilitator mainnet live 起動(:8405、eip155:8453、/health 200、実 build)。
- lending money-safety fix 5-iter VCSDD(signer==lender / exact-value / bounded-reconcile / mainnet-preflight / tx_hash-replay) merged。**ガードは実戦で正しく動作**: 署名前クラッシュの loan_Franklin_1 を正しく disbursement_failed に解消、二重支払いゼロ。

**最終ブロッカー（payViaFacilitator 直叩きで raw error 捕捉）:**
```
settle unexpected_error: -32003 insufficient funds for gas * price + value:
have 0 want 1059005200000  (facilitator signer 0x1F5b17f4… の Base ETH が 0)
```
= コードは正しい。x402 EIP-3009 gasless 送金は **facilitator が payer に代わってガスを立て替える**設計 → facilitator wallet `0x1F5b17f41524B02a4ee4d99D4158c86C942e43f3` に Base ETH(~0.001 ETH)が必要。現状 facilitator=0 ETH、Franklin=0.0000088 ETH（ほぼ枯渇）。

**次タスク（gas-funding harness、lean VCSDD）**: Franklin 自 USDC の一部($1程度)を Base 上で ETH に swap → facilitator signer へ送金（capped、on-chain verify）。これが揃えば初ローン $0.02 が settle し **witness③** 確定。注: loan_Franklin_2..36 の junk 行は全て disbursement_failed（送金ゼロ・二重なし、ガード健全性の実証）。

## ★★★ WITNESS③ ACHIEVED — 史上初の agent 間 on-chain 相互扶助ローン（2026-07-11）★★★

MONEY EVIDENCE PROTOCOL 3点:
1. **on-chain tx**: `0x36faafce0f22817eb94f3d2b7111d188e224287dbc31b8c976edf193cf6e2863`（Base mainnet、status 0x1、block 48482392）。独立 RPC(publicnode) で USDC Transfer を解析 → **0x3eccad…(Franklin) → 0xe7747f…(Franklin2) $0.02** 確認。
2. **ledger**: loan_Franklin_41 status=active、principal $0.02、total_due $0.022（10%利子）、due 14日後。
3. dashboard: 反映は P6（未）。mail: 送信する。

血栓解消の連鎖（全て実 on-chain、fake ゼロ）: Franklin2 EVM wallet 生成 → daemon franklin[N] 認識 → citizens EVM 行 → lending 5-iter money-safety VCSDD → sol-base-refill --live($6.50 USDC→Base) → **facilitator gas 枯渇を実 diagnose** → gas-eth refill --live($3 USDC→0.001655 ETH→facilitator) → 初ローン settle。lending の全ガード（signer==lender / exact-value / bounded-reconcile / mainnet-preflight / tx_hash-replay）が実戦で正しく動作、二重支払いゼロ。
