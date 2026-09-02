# Lancers Eliza Money End-to-End Implementation Plan

**Goal:** LancersでGeneral Agentが継続的に案件を探索・応募し、交渉、契約、制作、納品、入金、銀行着金までを公式receiptで閉じ、同じcoreを次marketplaceへ再利用する。

**Architecture:** 常駐する一つのEliza AgentRuntime内でCore TaskServiceを唯一のclockとし、`plugin-scheduling`の一つのpersistent money taskが`plugin-life-manager`のcustom dispatcherを起動する。Lunaが既存CloakBrowserを目と手として判断し、deterministic codeはcheckpoint、authorization、effect fence、official readback、receipt、金額計算だけを担当する。

**Tech Stack:** ElizaOS AgentRuntime、`@elizaos/plugin-scheduling`、`@elizaos/plugin-browser`、`plugin-life-manager`、PGlite、CloakBrowser CDP `:9227`、OpenClaw Telegram transport。

## Global Constraints

- Lancers専用brain、planner、scheduler、ledger、form sender、selector collectionを追加しない。
- 案件のfeasibility、profit、proposal、交渉、制作方法、次actionはLunaがlive画面から判断する。
- 応募数や予測収益を売上にしない。公式Proposal ID、Contract ID、Delivery ID、Payment ID、bank transactionだけを数える。
- 一つのapplication writerだけを許可する。Elizaとlaunchdを同時writerにしない。
- Remoteから`launchctl ... gui/$UID`へ入らない。launchd failbackは非Remote Aqua ownerが`lm-loop apply`で行う。
- 新dependency、新browser、新Telegram sender、新provider-specific production fileを追加しない。

## Current evidence baseline

- 旧`ai.anicca.lancers-revenue-application` label/processは不在。
- Eliza PIDは生存し、CloakBrowser `:9227`も生存する。
- running Eliza processは13:57開始で、16:38 mergeの`02f8acf2ff`を読み込んでいない。
- runtime logはmoney task `st_mtjg3546_exxn8ja5`で`SCHEDULED_DISPATCH_RENDER_FAILED`を4回記録する。
- 公式ledger最終値はsequence 56、Proposal ID `27879626`、17:09:33 JST。以後増分0。

## Phase A — application ownerを10分で証明またはfailbackする

### A1. 最新Eliza sourceとlauncherを固定する

**Files:**
- Inspect: `/Users/anicca/Projects/life-manager-eliza-migration/plugins/plugin-life-manager/src/money-loop.ts:28-123`
- Inspect: `/Users/anicca/Projects/life-manager-eliza-migration/plugins/plugin-scheduling/src/scheduled-task/runner-service.ts:552-565`
- Inspect: `/Users/anicca/.local/state/life-manager/eliza-lancers-runtime/start.sh:1-17`

**Change:** なし。`money-loop.ts:30-80`は既にcustom channel dispatcherを登録し、`runner-service.ts:552-565`は登録channelをdefault notification rendererより先に直接dispatchする。まずstale processだけを置換する。

**Commands:**

```bash
cd /Users/anicca/Projects/life-manager-eliza-migration
git fetch origin migration/eliza-docs
git merge --ff-only origin/migration/eliza-docs
git rev-parse HEAD
rg -n 'registerScheduledTaskChannelDispatcher|everyMinutes: 1|handleMessage' plugins/plugin-life-manager/src/money-loop.ts
```

Expected: HEADがPR #90以後で、上記3 symbolが一つの`money-loop.ts`に存在する。

### A2. Eliza single writerを正規launcherで置換する

**Files:**
- Execute: `/Users/anicca/.local/state/life-manager/eliza-lancers-runtime/start.sh`
- State: `/Users/anicca/.local/state/life-manager/migration/elz-l/l07/pglite-recovery-20260902`

**Commands:**

```bash
tmux kill-session -t eliza-lancers
tmux new-session -d -s eliza-lancers \
  -c /Users/anicca/Projects/life-manager-eliza-migration \
  /Users/anicca/.local/state/life-manager/eliza-lancers-runtime/start.sh
ps -axo pid,lstart,command | rg 'bun run.*start runtime'
```

Expected: Eliza runtime一process、旧application writer 0、PGlite directory不変。

### A3. 10分application canaryをlive観測する

**Files:**
- Read: `/Users/anicca/.local/state/life-manager/eliza-lancers-runtime/runtime.log`
- Read: `/Users/anicca/.local/state/anicca/lancers/marketplace-ledger.sqlite3`

**Commands:**

```bash
timeout 600 tail -n 0 -F /Users/anicca/.local/state/life-manager/eliza-lancers-runtime/runtime.log \
  | rg --line-buffered 'money|Message received|BROWSER|proposal|SCHEDULED_DISPATCH|terminalFailure'

sqlite3 -header -column /Users/anicca/.local/state/anicca/lancers/marketplace-ledger.sqlite3 \
  "select sequence,external_id,occurred_at from marketplace_events where event_type='application_verified' order by sequence desc limit 10;"
```

**PASS:** 新しい公式Proposal IDが最低1件増え、同一effect key再実行の追加送信0。

**FAIL:** 10分で新Proposal 0、または`SCHEDULED_DISPATCH_RENDER_FAILED`、Luna未到達、browser未到達のいずれかが再発する。

### A4. PASS時だけ案件別Telegram ACKを閉じる

**Files:**
- Modify only if current callback does not deliver: `/Users/anicca/Projects/life-manager-eliza-migration/plugins/plugin-life-manager/src/money-loop.ts:49-61`
- Reuse: `/Users/anicca/Projects/life-manager-eliza-migration/packages/core/src/services/message.ts:13299-13304`
- Reuse: `/Users/anicca/Projects/life-manager-eliza-migration/packages/core/src/types/components.ts:262-271`
- Reuse: `/Users/anicca/Projects/life-manager-eliza-migration/plugins/plugin-scheduling/src/scheduled-task/connector-dispatch.ts:175-239`

**Change:** `handleMessage(runtime, memory)`へ既存`HandlerCallback`を渡し、案件ごとのmodel outputを既存runtime connectorへ渡す。prompt内の`openclaw message send`命令は削除する。connectorの`providerMessageId`をdispatch receiptへ保存する。独自outbox/transportは作らない。

**Focused check:**

```bash
cd /Users/anicca/Projects/life-manager-eliza-migration
bun run --cwd plugins/plugin-life-manager typecheck
git diff --check
```

**PASS:** 応募・skipの各decisionが別messageになり、title、案件ID、金額、納期、理由、応募時Proposal ID、Telegram provider message IDを持つ。aggregateだけのwakeは0。

### A5. Eliza FAIL時はlaunchd application ownerへ戻す

**Files:**
- Modify: `config/loop-registry.json:1079-1094`相当へ`lancers-revenue-application` rowを復帰
- Modify: `config/loop-registry.json`の`retired_labels`から`ai.anicca.lancers-revenue-application`を削除
- Reuse unchanged: `runtime/loop/entry_dispatch.py:93-96`
- Focused test: `runtime/loop/tests/test_entry_dispatch.py:217`

**Registry row:**

```json
"lancers-revenue-application": {
  "cadence": {"start_interval_seconds": 60},
  "cleanup": {"max_age_days": 14, "max_runs": 100},
  "domain": "earn",
  "effect_class": "application",
  "entrypoint": "runtime/loop/entry_dispatch.py",
  "label": "ai.anicca.lancers-revenue-application",
  "log_root": "~/.local/state/anicca/lancers/logs",
  "provider_route": "deterministic",
  "state_root": "~/.local/state/anicca/lancers"
}
```

**Commands:**

```bash
python3 -m unittest runtime.loop.tests.test_entry_dispatch
git diff --check
git add config/loop-registry.json runtime/loop/tests/fixtures/macos-loop-jobs.json
git commit -m 'fix(lancers): restore proven application owner'
git push
python3 bin/cut-loop-release.sh origin/main
```

非Remote Aqua ownerだけが実行:

```bash
~/loops/current/bin/lm-loop apply
~/loops/current/bin/lm-loop status lancers-revenue-application
```

**PASS:** loaded argvが一つのimmutable releaseを指し、60秒自然wakeから新しい公式Proposal IDが増える。Eliza application taskはpauseし、二重writer 0。

## Phase B — 最大応募を継続する

### B1. Profile/Assetsをlive画面で完成する

**Files:**
- Read assets: `~/.config/anicca/job-search/profile.json`
- Runtime instruction: `/Users/anicca/Projects/life-manager-eliza-migration/plugins/plugin-life-manager/src/money-loop.ts:20-21`
- Browser action: `/Users/anicca/Projects/life-manager-eliza-migration/plugins/plugin-browser/src/index.ts`

**Agent operation:** LunaがLancers profileを観察し、職務経歴書、resume、portfolio、avatar、自己紹介、対応可能業務、本人確認、振込設定を公式画面で確認する。欠落assetだけを既存private SSOTからuploadする。資格・経験は捏造しない。

**PASS:** 各profile fieldの公式readbackとasset hashをcheckpointへ保存する。

### B2. 一wakeで全fresh opportunityを処理する

**Files:**
- Modify prompt only if needed: `/Users/anicca/Projects/life-manager-eliza-migration/plugins/plugin-life-manager/src/money-loop.ts:20-21`
- Reuse effect fence: `/Users/anicca/Projects/life-manager-eliza-migration/plugins/plugin-life-manager/src/effect-receipt-kernel.ts:318-390`
- Reuse provider admission: `/Users/anicca/Projects/life-manager-eliza-migration/plugins/plugin-life-manager/src/provider-admission.ts:36-58`
- Reuse checkpoint: `/Users/anicca/Projects/life-manager-eliza-migration/plugins/plugin-life-manager/src/goal-work-item.ts:122-230`

**Behavior:** Lunaが検索結果をterminal pageまで観察し、各fresh案件を一件ずつ判断する。system/software案件は実現可能なら応募する。skipは応募済み、受付終了、虚偽資格必須、物理作業必須、規約違反、capacity超過など実際のhard blockerだけ。件数quotaを成果にせず、存在する全positive-EV案件を処理する。

**PASS:** 3回連続自然wakeで、`fresh = applied + explicitly_skipped`、未判断0、各appliedに公式Proposal ID、duplicate 0。

## Phase C — 応募からbanked netまで閉じる

### C1. Buyer reply / negotiation

**Files reused:**
- `plugins/plugin-life-manager/src/money-loop.ts:20-123`
- `plugins/plugin-life-manager/src/goal-work-item.ts:122-230`
- `plugins/plugin-life-manager/src/effect-receipt-kernel.ts:318-390`
- `plugins/plugin-life-manager/src/db/schema.ts:122-309`

**Behavior:** 同じmoney taskが公式inboxを毎wake読み、buyer-last threadごとにLunaが返信、質問、見積、条件交渉を判断する。

**PASS:** buyer message ID→seller reply ID→公式offer/contract IDのchainを保存する。

### C2. Funded contract

**Files reused:** 上記4 files。

**Behavior:** 仮払い済み契約だけをfulfillmentへ進め、scope、price、deadline、counterparty、Contract IDをofficial readbackする。

**PASS:** `contract-receipt.json`相当のreceiptがPGlite outcome receiptへ保存される。

### C3. Fulfillment / QA / delivery

**Files reused:** 上記4 filesと既存Agent tools/Skills/Assets。

**Behavior:** Lunaが契約要件から制作方法を決める。必要ならcapability-gap WorkItemを同じGeneral Agentへ作る。artifact hash→QA result→official delivery IDをeffect kernelで一度だけ送る。

**PASS:** artifact、QA、deliveryの3 receiptが同じcontract IDへjoinし、delivery duplicate 0。

### C4. Payment / payout / bank match

**Files reused:**
- `plugins/plugin-life-manager/src/db/schema.ts:209-309`
- `plugins/plugin-life-manager/src/goal-reflection.ts:234-310`
- `plugins/plugin-life-manager/src/effect-receipt-kernel.ts:318-390`

**Behavior:** platform payment、fee/refund、payout ID、銀行transactionをofficial sourceから読み、同一payoutへjoinする。

**PASS:** `bank delta - payout net = 0`で、self-pay/top-upを除外した外部buyer由来のverified banked netが正になる。ここで初めて「Lancersで稼いだ」と判定する。

## Phase D — 同じGeneral Agentを全marketplaceへ展開する

### D1. CrowdWorks zero-shot child Goal

**Files reused unchanged:**
- `plugins/plugin-life-manager/src/money-loop.ts`
- `plugins/plugin-life-manager/src/goal-work-item.ts`
- `plugins/plugin-life-manager/src/effect-receipt-kernel.ts`
- `plugins/plugin-life-manager/src/db/schema.ts`
- `plugins/plugin-life-manager/src/goal-reflection.ts`

**Behavior:** marketplace名、signup URL、economic Goalだけをchild Goalへ渡す。Lunaが既存browserでsignup、profile、探索、応募を行う。

**PASS:** CrowdWorks専用brain/script/selector 0のまま、account receipt→ApplicationReceipt→replay-zeroを閉じる。

### D2. Fiverr以降

同じD1を繰り返す。新marketplaceで新production codeを許すのは、既存general browserで利用できない公式API、machine-readable receipt、法的protocol境界だけ。semantic判断とclick順は追加しない。

### D3. Self-improvement

**Files reused:**
- `plugins/plugin-life-manager/src/goal-reflection.ts:234-310`
- `plugins/plugin-life-manager/src/db/schema.ts:122-309`

**Behavior:** Application→Contract→Delivery→Payment→Banked receiptをGoal、Skill、Asset、proposal、priceへ帰属し、成功率・net・時間を比較する。改善候補はcanary後だけ昇格する。

**PASS:** 同じGeneral Agentがmarketplace child Goalを作成し、収益性とcapacityによりscale/pause/retireする。

## Final acceptance

- Lancers application writer 1。
- 3回以上の連続自然wake。
- 全fresh positive-EV案件の個別判断と公式Proposal ID。
- replay external effect 0。
- 案件別Telegram provider ACK。
- funded contract→artifact→QA→delivery→payment→payout→bank transactionが一つのreceipt chainになる。
- verified banked netが正。
- CrowdWorksをprovider-specific brain/scriptなしで開始する。
