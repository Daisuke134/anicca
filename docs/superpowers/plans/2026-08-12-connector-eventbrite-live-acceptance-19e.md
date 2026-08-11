# Connector Eventbrite official live acceptance 19E Plan

## Goal

Schedule-unloadedのofficial production entrypointをforegroundでexact 1回だけ実行し、Eventbriteを含む6-provider順、外部作用のreadback、Calendar/evidence/Telegram bundle、terminal report、cleanupをdurable evidenceで受け入れる。

## Preconditions

- Pushed HEAD、Git clean/upstream 0/0。
- Native、healthcheck、Healer shadow、host bridgeの4 labelsはUNLOADED。
- Connector process 0、lock absent、current CDP pageとConnector target ledgerのintersection 0。
- Baseline: applied bundles 13、wake reports 129、wake deliveries 141、actions 1322、Eventbrite audit 0、current unrelated CDP pages 4。
- 実Eventbrite registration `1997468673573`はproduction workflowのaction 0 readbackで`registered`確認済み。final submitを再実行しない。

## Execute

1. `skills/connector/run.sh`を660秒hard timeout付きforegroundでexact 1回実行する。plist load、launchctl kick、Node直呼び、manual browser/provider action、second executorは0。
2. 30〜60秒ごとにprocess、append-only count、owned target lifecycleを観測する。ブラウザ本体やunrelated pagesをstop/closeしない。
3. terminal後、new wake report/delivery/action/audit/bundleだけをsafe fieldsで照合する。private profile、email、order ID、Calendar本文を出力しない。

## Acceptance

- Existing registered Eventbrite candidateへ到達した場合、pre-readback `registered`でfinal Submit 0、provider receipt、Calendar exact-once readback、privacy-safe artifact SHA、positive Telegram message/photo IDを一つの`applied_bundle`へ束ねる。
- CandidateなしまたはCalendar conflictならEventbrite auditをdurable保存し、external write 0、positive every-wake reportを`completed_no_effect`として受け入れる。safe gateを緩めない。
- Any `effect_unknown` stops the wake with duplicate mutation 0; no same-turn second wake.
- 終了後process/lock/owned target 0、unrelated pages unchanged、4 labels UNLOADED、Git clean/upstream。

## Deferred

Live結果で新たな実故障が出た場合はその先頭1件だけを次のPonytail/Superpowers sliceで修復する。production acceptance完了後にREADME Mermaid、SSOT TODO、single daily schedule/cleanup/canonical merge gateを続ける。
