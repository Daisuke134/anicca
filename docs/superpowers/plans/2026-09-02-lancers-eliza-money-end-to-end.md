# Lancers Money End-to-End Atomic Plan

**Goal:** Lancersの応募を直ちにsingle-writerで継続し、応募からbanked netまでを閉じ、同じshared agent harnessを次marketplaceへ再利用する。

**Current facts:** `launchctl print`で旧Lancers application serviceはabsent。plistは残るがloadedではない。CloakBrowser ownerは正常。Eliza Bun runtimeは生存し`plugin-browser`とAutonomyServiceをloadするが、Lancers browser action・Proposal receiptは0。最新公式Proposal `27880270`はworktreeの有限Python runによる。continuous application ownerは現在0であり、24/7最大応募は停止中。一時`eliza-lancers` tmuxは存在するが、process生存だけでapplication ownerとは数えない。Lancers開発はこのworktreeと現在branch一つだけで完了まで継続する。

## Fixed order

- [x] **A1 — failback source:** `config/loop-registry.json`へ最後に実績のある60秒rowを復元し、`retired_labels`から同labelを除いた。既存dispatchの欠落`--exhaustive`も復元した。
- [x] **A2 — focused validation:** registry JSON parse PASS、既存`runtime.loop.tests.test_entry_dispatch` 15/15 PASS、`git diff --check` PASS。新test/frameworkは追加していない。
- [x] **A3 — branch staging release:** pushed branch `db82bc6ca`から隔離release `20260902T194904-db82bc6c`を作成し、有限runを実行した。以後は過剰なfull buildを避け、worktreeの既存Pythonから直接testする。`gui/$UID`操作0。
- [ ] **A4 — live apply PASS（active）:** 案件5595764は公式Proposal `27880270`、ledger sequence 57、Telegram ID 48547まで成立。ただしreconcileがtitleを`案件5595764`へ劣化し金額・納期を落とした。branch `e61dae788`でclick後の公式履歴readbackとtitle/98,000円/2026-09-23/report保持を修正済み。現在の自然wakeは旧release `8f956147…`から動くPython batchで、修正branchでもEliza General Agentでもない。最新wakeは公開40/fresh18/候補0のため不合格。次はworktree修正から新しい実応募を一件行い、title・案件ID・提案額・納期・Proposal IDのTelegram ACKと、fresh全件の個別decision ACKをlive確認する。そこまでA5以降へ進まない。
- [x] **A5 — official receipt/replay-zero:** 5595764の公式Proposal ID `27880270`を取得し、pending reconcileは同じ応募を再送せず公式履歴だけを読み、ledger sequence 57へ一回だけ記録した。
- [ ] **A6 — profile/assets:** Lunaがlive profile画面でresume、職務経歴、portfolio、avatar、自己紹介、本人確認、振込設定を確認し、事実に基づく不足だけを既存private assetから補う。
- [ ] **A7 — negotiation:** buyer返信を案件別に読み、返信・見積・条件交渉を行い、公式ContractReceiptを得る。
- [ ] **A8 — fulfillment/delivery:** funded contractだけを制作し、QA、公式納品、DeliveryReceiptを閉じる。
- [ ] **A9 — payment/banked:** PaymentReceipt、payout、銀行明細を照合し、外部buyer由来のverified banked netを正にする。
- [ ] **A10 — generalize and promote:** cadence/lease/checkpoint/effect/readback/report/assetsをshared coreへ保持し、Lancers専用semantic判断を追加せずCrowdWorks、Fiverrを同じharnessで開始する。全項目PASS後にbranchを一度だけmainへmergeし、production releaseへ昇格する。

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
