# Lancers Money End-to-End Atomic Plan

**Goal:** `life-manager-main`の実績あるLancers loopをsingle-writerで復帰し、最大応募からbanked netまでを閉じる。Eliza forkは実行基盤にせず、将来の自前General Agent harnessの参考資料に限定する。

**Current facts:** Eliza Lancers runtime process 0、tmux session 0、旧Lancers application serviceもabsentで、continuous application ownerは0。`life-manager-main`には既存の60秒registry row、`entry_dispatch.py`、`application_loop.py --exhaustive`、Luna判断、複数eligible連続送信、公式Proposal readback、Telegram reporterが残る。案件5595764 / Proposal `27880270`はこの経路の有限runで成立した。Eliza migration checkoutはAlpaca作業中なので削除せず、Lancers runtimeとしては使用しない。

## Fixed order

- [x] **A1 — failback source:** `config/loop-registry.json`へ最後に実績のある60秒rowを復元し、`retired_labels`から同labelを除いた。既存dispatchの欠落`--exhaustive`も復元した。
- [x] **A2 — focused validation:** registry JSON parse PASS、既存`runtime.loop.tests.test_entry_dispatch` 15/15 PASS、`git diff --check` PASS。新test/frameworkは追加していない。
- [x] **A3 — branch staging release:** pushed branch `db82bc6ca`から隔離release `20260902T194904-db82bc6c`を作成し、有限runを実行した。以後は過剰なfull buildを避け、worktreeの既存Pythonから直接testする。`gui/$UID`操作0。
- [ ] **A4 — old loop single-writer failback（active）:** Eliza Lancers実行を撤退済みとして固定する。既存registry/entrypoint/application loop/reporterの最小差分だけを使い、GUI-domain操作を含まない正規release経路から旧application ownerを一つだけ復帰する。復帰前後にwriter exact 1を確認する。
- [ ] **A5 — maximal apply and per-item reporting:** 同一wake内で全fresh案件をLunaが判断し、全`submit_required`を連続送信する。各案件ごとに公式title、ID、apply/skip、自然言語理由、提案額、納期、Proposal IDをTelegramへ即時送信する。`fresh N / 候補0`の集計だけで終了しない。
- [ ] **A5R — official receipt/replay-zero:** 新しい実応募の公式Proposal IDを取得し、同じ案件の再実行でprovider execute 0、ledger insert 0を確認する。5595764 / `27880270`は既存回帰証拠として保持するが、新owner合格の代用にしない。
- [ ] **A6 — profile/assets:** Lunaがlive profile画面でresume、職務経歴、portfolio、avatar、自己紹介、本人確認、振込設定を確認し、事実に基づく不足だけを既存private assetから補う。
- [ ] **A7 — negotiation:** buyer返信を案件別に読み、返信・見積・条件交渉を行い、公式ContractReceiptを得る。
- [ ] **A8 — fulfillment/delivery:** funded contractだけを制作し、QA、公式納品、DeliveryReceiptを閉じる。
- [ ] **A9 — payment/banked:** PaymentReceipt、payout、銀行明細を照合し、外部buyer由来のverified banked netを正にする。
- [ ] **A10 — self-owned General Agent harness:** Lancers/Coconalaで実証したGoal、Luna判断、browser、assets、lease、checkpoint、effect fence、official readback、receipt、Telegramを`life-manager-main`のprovider-neutral harnessへ抽出する。Elizaは参考実装として読むだけでruntime dependencyにしない。同じharnessへGoalを渡してCrowdWorks、Fiverrを開始する。全項目PASS後にbranchを一度だけmainへmergeしproductionへ昇格する。
- [ ] **A11 — stale artifact cleanup（部分完了）:** 停止済みEliza Lancers log followerと、4条件を満たした統合済み旧worktree `lm-lancers-spec-live`、`lm-lancers-stale-zero-capacity`、`life-manager-retire-lancers-writer`および対応local branchを削除し、`git worktree prune`済み。残候補はA4〜A10の現役source/rollbackを固定後に同じ条件で監査する。Alpacaが使うEliza checkout、active、dirty、unmerged、locked、rollback sourceは保持する。

## Exact A1 patch

```diff
--- a/config/loop-registry.json
+++ b/config/loop-registry.json
@@ loops
+    "lancers-revenue-application": {
+      "cadence": {"start_interval_seconds": 60},
+      "cleanup": {"max_age_days": 14, "max_runs": 100},
+      "domain": "earn",
+      "effect_class": "application",
+      "entrypoint": "runtime/loop/entry_dispatch.py",
+      "label": "ai.anicca.lancers-revenue-application",
+      "log_root": "~/.local/state/anicca/lancers/logs",
+      "provider_route": "deterministic",
+      "state_root": "~/.local/state/anicca/lancers"
+    },
@@ retired_labels
-    "ai.anicca.lancers-revenue-application",
```

The application command remains the existing mapping in `runtime/loop/entry_dispatch.py`; no new Lancers script, browser, selector collection, scheduler, ledger, or Telegram sender is added.
