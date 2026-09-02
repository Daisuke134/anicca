# Lancers Money End-to-End Atomic Plan

**Goal:** `life-manager-main`の実績あるLancers loopをsingle-writerで復帰し、最大応募からbanked netまでを閉じる。Eliza forkは実行基盤にせず、将来の自前General Agent harnessの参考資料に限定する。

**Current facts:** Eliza Lancers runtime process 0、tmux session 0。Lancers applicationはSHA `d93386bd…`の隔離releaseからsingle writer exact 1でloadedされ、`StartInterval=60`、自然wake `runs=2`、直前exit 0を公式launchd readbackで確認した。preflightはUID、Directory Services、Aqua manager UID/PID、GUI domain readbackが全てPASSし、対象限定apply後も141/153とRemote切断は0。最初の自然wakeは39件を判断したが、Lunaが案件5595850へ不正な過去年 `1014-10-14`を返しvalidatorが拒否したため応募0件。正本promptへ`tick_date翌日〜60日`を明記したcommit `6ffa75269`をpush済みで、現loaded releaseへの反映とfresh公式Proposalは未完。案件5595764 / Proposal `27880270`はこの経路の有限runで成立した。Eliza migration checkoutはAlpaca作業中なので削除せず、Lancers runtimeとしては使用しない。

## Fixed order

- [x] **1 — Apply経路比較:** Coconala `hf-gig-apply-direct`とLancers `lancers-revenue-application`を実call graphで比較した。Coconalaは`application_direct.py → application_parent.py → application_planner.py → application_effect_fence.py → application ledger/work_event_projector → TelegramOutbox/apply_telegram_report.py`。Lancersは`application_loop.py → agent_runner.py → application_tick.py → shared application_transaction.py → Lancers official readback → lancers telegram_report.py`。Lancersはagent runnerとapplication transactionを既に共有するが、planner contract、orchestration、effect/ledger projection、Telegram outboxを別実装する。比較中の有限runはplanner待ちで停止し、submitter到達前、external application/Telegram effect 0。
- [x] **2 — shared inventory:** 実callerで分類した。真の共有は`runtime/agent-runner/agent_runner.py`（Coconala/Lancers）、`_shared/marketplace-core/application_transaction.py`（Lancers/CrowdWorks）、同coreの`contracts.py`・`ledger.py`・`telegram_outbox.py`（Lancers receipt/report）。部分共有は`gig/application_planner.py::common_marketplace_feasibility_policy`（Coconala/Upworkのみ）と`application_decisions.schema.json`（Coconala/Lancers）。二重実装はLancers内のfeasibility長文、Coconala用とmarketplace-core用のTelegramOutbox、application orchestration、receipt projection。provider固有discovery/submit/readbackはadapterとして保持する。
- [x] **3 — smallest deduplication:** common feasibility本文だけを`_shared/marketplace-core/scripts/feasibility_policy.py`へ移し、Coconala/Upworkの既存公開関数は互換entrypointとして同じshared正本を返し、Lancersはshared正本を直接読む。Lancers固有snapshot・hard prohibition schema・proposal constraints・provider adapterは保持した。Coconala policy focused checkは3/3 PASS。Lancers focused suiteはimport error 23件を解消して全24件を実行し、19 PASS、残4件はこのbranchで既に導入済みの複数応募・quota撤廃・evidence緩和と旧期待値の不一致でありStep 3差分由来ではない。
- [x] **4 — Lancers Apply single writer:** SHA `acbc8b07…`の隔離releaseを対象限定applyし、owner exact 1、`StartInterval=60`、自然wake `runs=1`、terminal exit 0を確認した。preflight全PASS、141/153、Remote切断、二重writerは0。
- [x] **5 — fresh official Proposal:** 自然wakeで案件5595850を90,000円、納期2026-09-09で送信し、公式Proposal ID `27880898`、ledger sequence 58を取得した。
- [x] **6 — per-item Telegram ACK:** 同案件の正式title、ID、90,000円、2026-09-09、Proposal ID `27880898`を含む案件別ACKをTelegram provider message ID `48685`で確認した。同wakeの新規outbox 7件は全件delivered。
- [x] **7 — replay-zero:** 2回目自然wakeは案件5595850をplanner入力から除外し、同Proposal receipt exact 1、ledger sequence `58→58`、pending 0、provider再送0でexit 0。新規Telegram 3件も全delivered。
- [x] **8 — continuous natural Apply:** `--exhaustive`が同じ全件探索＋Luna判断を3巡していた一行を修正し、探索範囲を変えず1巡へ統一した。SHA `4e608343…`の自然wakeは約4分44秒でexit 0、次wake `runs=2`が自動再発した。single writer、全fresh一括判断、eligible全送信、official readback、案件別outboxを維持する。
- [ ] **9 — independent Storefront（active）:** StorefrontをApplyと別owner・別reportとして確認する。
- [ ] **10 — independent Negotiate:** buyer-last返信、見積、契約を別ownerで処理し、公式ContractReceiptを得る。
- [ ] **11 — Paid real contract:** funded contractだけを制作し、QA、公式納品、DeliveryReceipt、PaymentReceiptを閉じる。
- [ ] **12 — positive banked net:** payoutと銀行明細を照合し、外部buyer由来のverified banked netを正にする。
- [ ] **13 — Gig Money Loop Skill:** Coconala/Lancersの複数実receiptで有効だった構造と、本人事実・resume・portfolio・能力証拠・提案素材から成るshared profile assetを再利用recipeとしてSkillへ記録する。provider adapterは表示形式だけを変え、別人を装う名前・画像・経歴は作らない。
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

## Step 2 shared inventory receipt

| component | actual callers | classification | next action |
|---|---|---|---|
| `runtime/agent-runner/agent_runner.py` | Coconala Apply and Lancers Apply/Work Sync | shared and live | keep |
| `_shared/marketplace-core/application_transaction.py` | Lancers and CrowdWorks application ticks | shared and live | keep |
| `_shared/marketplace-core/contracts.py` / `ledger.py` | Lancers application receipt/report | shared contract/ledger | keep; later connect Coconala only after live parity |
| `_shared/marketplace-core/telegram_outbox.py` | Lancers reporter | shared location, one live provider caller | keep |
| `gig/application_planner.py::common_marketplace_feasibility_policy` | Coconala and Upwork | proven shared policy | Step 3: reuse from Lancers |
| `gig/schemas/application_decisions.schema.json` | Coconala parent | shared contract candidate | Lancers currently reads parallel `skills/gig-work` schema; do not move in Step 3 |
| `gig/scripts/telegram_outbox.py` | Coconala Apply/Reply/Paid/Storefront | Coconala working shared-within-gig | do not replace before Lancers Apply receipt |
| Lancers discovery/form/readback | Lancers only | valid provider adapter | keep |
| Lancers embedded feasibility prose | Lancers only, duplicates common policy | duplicated judgment guidance | delete copy in Step 3 |

## Step 3 smallest-deduplication receipt

`skills/_shared/marketplace-core/scripts/feasibility_policy.py`をprovider-neutralな唯一の本文正本にした。Coconala/Upworkのcaller契約
`application_planner.common_marketplace_feasibility_policy()`は名前を変えずshared正本を返すため、既存consumerの変更は不要である。Lancersは大きな
Coconala plannerをimportせず、leaf policyだけを直接loadする。これにより最初の直接import案で発生した`application_snapshot` sibling import errorを除き、
provider固有discovery、submit、official readback、receipt、Telegram、schedulerには変更を加えていない。

## Step 4 current owner receipt

installed `~/Library/LaunchAgents/ai.anicca.lancers-revenue-application.plist`はlabel exact一致、`StartInterval=60`、loop ID
`lancers-revenue-application`を持つ。一方、read-only `launchctl print gui/501/ai.anicca.lancers-revenue-application`は
`Could not find service`を返す。したがってplist fileの存在を稼働と数えず、continuous Apply ownerは0、Step 4は未完である。
さらにinstalled plistのargv/envは旧release SHA `e9d59c327bcae0f3cfa07e3544c85af8349d80be`を指す。単純な`lm-loop start`では修正版にならないため、
正規operator actionはpush済み検証SHAのreleaseをapplication label一件へ`lm-loop apply`し、load/readbackまで同じtransactionで閉じることである。
branchへ最新mainを取り込んだ統合SHA `03c8754bf1054ff129284cb3bca1e2483af7a824`はfocused 26/26 PASS。global currentを触らない隔離releaseを
`~/.local/state/life-manager/staging/lancers-step4/current`へ作成し、SHA、shared policy、共通operator/runner、read-only `unloaded`を確認した。
残る正規GUI-owner commandは`LIFE_MANAGER_RELEASE_ROOT="$HOME/.local/state/life-manager/staging/lancers-step4/current" LIFE_MANAGER_APPLY_TARGET=lancers-revenue-application "$HOME/.local/state/life-manager/staging/lancers-step4/current/bin/lm-loop" apply`の一つである。
loop開発protocolも同じ欠落を再発させないよう更新した。今後はplist、release、test、手動finite runでは`ON/shipped`にせず、loaded owner exact 1、
意図したSHAの自然wake、terminal eventと公式readbackまでを必須にする。現在のLancers Applyはこの定義でOFFである。
同じread-only監査でCoconala Apply `ai.anicca.hf-gig-apply-direct`は同じGUI domainにloaded、60秒cadence、runs 36、finite
`lm-loop-run` processありだった。LancersだけにCodex app-serverが必要なのではなく、差はCoconala ownerが既にload済みでLancers ownerがabsentな点である。
OpenAI公式資料ではapp-serverはrich client integration用、automation/CIはCodex SDK、script/scheduled jobの有限runは`codex exec`、Desktop
Scheduled Tasksはdesktop appが管理する別schedulerである。したがってLancersはCoconalaと同じlaunchd supervisorをsingle ownerとして再利用し、
意味判断だけを既存agent runnerへ渡す。app-server、Scheduled Tasks、第二schedulerを追加しない。

Sources:
- OpenAI, `Codex App Server`: https://developers.openai.com/codex/app-server — rich clients向けで、automation jobsにはSDKを使うと明記。
- OpenAI, `Non-interactive mode`: https://developers.openai.com/codex/noninteractive — `codex exec`はscripts、CI、scheduled jobs向け。
- OpenAI, `Scheduled tasks`: https://developers.openai.com/codex/automations — local project taskはdesktop app稼働が必要で、CLIは管理UIを持たない。
既存exact-SHA installerは新しいshared policyをrelease allowlistへ含めていなかったため、
`skills/_shared/marketplace-core/scripts/feasibility_policy.py`をmanifestへ追加した。isolated reconcile/normal installer testは2/2 PASSし、
production state、plist、launchd effectは0。残るStep 4 actionは正しいpushed commitをproduction releaseへinstallし、single ownerをloadすることだけである。
旧installerの`origin/main`祖先必須は、このplanの「pushed feature branchから隔離E2Eし、全acceptance後だけmainへ一度merge」と矛盾していた。
release provenanceをpush済みremote branchへ一般化し、local-only commitは引き続き拒否する。これによりmainを先に変更せずbranch releaseを実測できる。
Pushed branch commit `6a76454ac1c9cb29706117da52054ad53d41a2b6`をtest-only bypassなし、activate 0のisolated normal installへ渡し、
deployed SHA exact一致、26 files、shared policy packaged、`--exhaustive`、label exact一致を確認した。production external effect 0。
同branch codeをproduction stateへ`--reconcile-only`で一回実行し、exit 0、`submitted=false`、reconciled/verified/unresolved各0を確認した。
新規discovery、application、Telegram effectは0で、旧logの`profile_preflight_failed`は現call pathに存在しない。
既存focused testに残っていた「最初のeligible一件だけ送信」「10件でdaily quota」「plannerが案件を欠落しても成功」の旧期待は、固定済みの
最大応募contractと逆だったため現在仕様へ更新した。製品コード変更0で、application 24件＋installer 2件の合計26/26 PASS。

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
