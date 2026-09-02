# Lancers Money End-to-End Atomic Plan

**Goal:** `life-manager-main`の実績あるLancers loopをsingle-writerで復帰し、最大応募からbanked netまでを閉じる。Eliza forkは実行基盤にせず、将来の自前General Agent harnessの参考資料に限定する。

**Current facts:** Eliza Lancers runtime process 0、tmux session 0、旧Lancers application serviceもabsentで、continuous application ownerは0。`life-manager-main`には既存の60秒registry row、`entry_dispatch.py`、`application_loop.py --exhaustive`、Luna判断、複数eligible連続送信、公式Proposal readback、Telegram reporterが残る。案件5595764 / Proposal `27880270`はこの経路の有限runで成立した。Eliza migration checkoutはAlpaca作業中なので削除せず、Lancers runtimeとしては使用しない。

## Fixed order

- [x] **1 — Apply経路比較:** Coconala `hf-gig-apply-direct`とLancers `lancers-revenue-application`を実call graphで比較した。Coconalaは`application_direct.py → application_parent.py → application_planner.py → application_effect_fence.py → application ledger/work_event_projector → TelegramOutbox/apply_telegram_report.py`。Lancersは`application_loop.py → agent_runner.py → application_tick.py → shared application_transaction.py → Lancers official readback → lancers telegram_report.py`。Lancersはagent runnerとapplication transactionを既に共有するが、planner contract、orchestration、effect/ledger projection、Telegram outboxを別実装する。比較中の有限runはplanner待ちで停止し、submitter到達前、external application/Telegram effect 0。
- [ ] **2 — shared inventory（active）:** 既に存在するshared部品を一覧化し、実際のcallerとreceiptを付ける。名前だけsharedでprovider固定のものはshared扱いしない。
- [ ] **3 — smallest deduplication:** 重複している最小部品を一つだけsharedへ寄せ、Coconalaのproduction挙動を変えずLancersから直接再利用する。
- [ ] **4 — Lancers Apply single writer:** 共有済み経路を使うLancers Apply ownerをexact 1で起動する。Eliza Lancers runtime、tmux、二重writerは0。
- [ ] **5 — fresh official Proposal:** 新しい実応募を送り、公式Proposal IDを取得する。
- [ ] **6 — per-item Telegram ACK:** 各案件のtitle、ID、apply/skip、具体理由、提案額、納期、Proposal IDを個別Telegram ACKで確認する。aggregateだけで終了しない。
- [ ] **7 — replay-zero:** 同じ案件の再実行でprovider execute 0、ledger insert 0を確認する。
- [ ] **8 — continuous natural Apply:** 自然wakeを継続し、全fresh案件を判断して全`submit_required`を同一wake内で連続応募する。
- [ ] **9 — independent Storefront:** StorefrontをApplyと別owner・別reportとして確認する。
- [ ] **10 — independent Negotiate:** buyer-last返信、見積、契約を別ownerで処理し、公式ContractReceiptを得る。
- [ ] **11 — Paid real contract:** funded contractだけを制作し、QA、公式納品、DeliveryReceipt、PaymentReceiptを閉じる。
- [ ] **12 — positive banked net:** payoutと銀行明細を照合し、外部buyer由来のverified banked netを正にする。
- [ ] **13 — Gig Money Loop Skill:** Coconala/Lancersの複数実receiptで有効だった構造だけを再利用recipeとしてSkillへ記録する。
- [ ] **14 — CrowdWorks thin adapter:** shared core＋薄いobserve/effect/readback adapterだけでCrowdWorksを開始する。
- [ ] **15 — Freelancer.com repair:** 同じshared構造へ既存Freelancer.com loopを接続して修復する。
- [ ] **16 — autonomous loop factory:** 3市場目以降はLife Manager自身が新市場を発見し、Skillを使ってadapter、canary、receipt、loop起動、改善まで行う。

この順序はDaisが明示的に変更しない限り不変。各項目を完了して正本を更新してから次へ進む。profile/assetsはApply経路比較で不足を観測しても順序を飛ばさず、Step 8までの応募成立に必要な既存assetだけを再利用する。残cleanupは現役source/rollbackが確定した後に行い、Alpacaが使うEliza checkoutは削除しない。

## Step 1 comparison receipt

| boundary | Coconala working path | Lancers current path | verdict |
|---|---|---|---|
| registry/entry | `hf-gig-apply-direct` → `application_direct.py --all-eligible` | `lancers-revenue-application` → `application_loop.py --exhaustive` | provider-specific entrypoints are expected |
| discovery | Coconala B2 source/context | Lancers exhaustive queries/status | provider adapter responsibility |
| model | shared `runtime/agent-runner/agent_runner.py` | same shared runner | already shared |
| feasibility/planner | `gig/application_planner.py` common policy + shared schema | Lancers embeds a second long policy and validates its own decisions | duplicated; inventory in Step 2 |
| effect fence/transaction | `gig/application_effect_fence.py` + parent lifecycle | `application_tick.py` loads `_shared/marketplace-core/application_transaction.py` | transaction core partly shared, fence/projection differ |
| provider effect/readback | Coconala-specific browser/provider | Lancers-specific browser/form/readback | thin adapter responsibility |
| receipt/ledger | gig application ledger + work-event projection | Lancers marketplace ledger/result object | duplicated contract/projection |
| Telegram | shared `TelegramOutbox` + `apply_telegram_report.py` | Lancers outbox bridge + `telegram_report.py` | duplicated; aggregate wake is the observed UX defect |

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
