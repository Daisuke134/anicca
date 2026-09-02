# Lancers Money End-to-End Atomic Plan

**Goal:** Lancersの応募を直ちにsingle-writerで継続し、応募からbanked netまでを閉じ、同じshared agent harnessを次marketplaceへ再利用する。

**Current facts:** 旧Lancers application writerは退役済み。CloakBrowser ownerとCoconala ownerは正常。Eliza bounded proofはtask dispatchとLuna起動まで進んだがbrowser action・新Proposal IDへ到達せず不合格。一時tmux ownerは停止済み。

## Fixed order

- [x] **A1 — failback source:** `config/loop-registry.json`へ最後に実績のある60秒rowを復元し、`retired_labels`から同labelを除いた。既存dispatchの欠落`--exhaustive`も復元した。
- [x] **A2 — focused validation:** registry JSON parse PASS、既存`runtime.loop.tests.test_entry_dispatch` 15/15 PASS、`git diff --check` PASS。新test/frameworkは追加していない。
- [ ] **A3 — immutable release:** main由来releaseを作り、正規ownerの自然反映を待つ。Remoteから`launchctl ... gui/$UID`を実行しない。
- [ ] **A4 — live apply PASS:** 自然wakeを観測し、fresh案件ごとのtitle、ID、金額、納期、apply/skip理由をTelegramで個別ACKする。aggregate-onlyを失敗とする。
- [ ] **A5 — official receipt/replay-zero:** 新しい公式Proposal IDを最低1件取得し、同じ案件の再送0を公式履歴とledgerで確認する。
- [ ] **A6 — profile/assets:** Lunaがlive profile画面でresume、職務経歴、portfolio、avatar、自己紹介、本人確認、振込設定を確認し、事実に基づく不足だけを既存private assetから補う。
- [ ] **A7 — negotiation:** buyer返信を案件別に読み、返信・見積・条件交渉を行い、公式ContractReceiptを得る。
- [ ] **A8 — fulfillment/delivery:** funded contractだけを制作し、QA、公式納品、DeliveryReceiptを閉じる。
- [ ] **A9 — payment/banked:** PaymentReceipt、payout、銀行明細を照合し、外部buyer由来のverified banked netを正にする。
- [ ] **A10 — generalize:** cadence/lease/checkpoint/effect/readback/report/assetsをshared coreへ保持し、Lancers専用semantic判断を追加せずCrowdWorks、Fiverrを同じharnessで開始する。

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
