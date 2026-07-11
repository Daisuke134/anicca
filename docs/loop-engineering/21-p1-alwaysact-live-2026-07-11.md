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
