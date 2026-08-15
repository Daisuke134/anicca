# Gig pass runbook

`gig_pass.sh` が4つの収益laneを同一passで実行する。実行主体は既存の
Life Manager runtimeであり、この文書から別executorを起動しない。

## Portable runtime contract

各entrypointは最初に `scripts/gig_paths.sh` を読み、次の値だけを使う。

| 変数 | 役割 |
|---|---|
| `LIFE_MANAGER_REPO` | 現在のLife Manager checkout |
| `LIFE_MANAGER_HOME` | 利用者ごとのruntime root |
| `GIG_DIR` | canonical Gig package |
| `GIG_RUNNER_DIR` | `runtime/agent-runner` |
| `GIG_BROWSER_DIR` | `skills/browser` |
| `GIG_STATE_DIR` | Gig ledger/evidence state |
| `GIG_HOST_STATE_DIR` | supervisor/control state |
| `GIG_LOG_DIR` | runtime log |
| `GIG_ENV_FILE` | credential environment |

別repo、開発者固有HOME、個人Telegram IDを既定値として参照しない。

## One pass

| 順 | lane | 完了証拠 |
|---:|---|---|
| 1 | 納品・有償作業 | buyer-visible artifact、talkroom readback、canonical ledger |
| 2 | 出品 | seller画面readback、service ID、listing ledger |
| 3 | 返信 | send ACK、talkroom readback、reply ledger |
| 4 | 応募 | submit helper ACK、公式応募管理readback、application ledger |

各laneは「モデルが成功と言った」だけでは完了しない。外部画面のreadbackと
canonical ledgerが一致して初めてclosureとなる。副作用後にACKを失った場合は
blind retryせず、canonical readbackでreconcileする。

### STEP 0.5 LEARN

pass開始時に `pending_deliveries_review` を読み、すべての未納品案件について
前倒しできるものが無いかを確認する。着手可能な有償作業を先送りせず、次の
納品laneへ渡す。

### PRE-STEP

fresh snapshotとcanonical ledgerを照合し、直前passの未確定副作用をreconcileする。

### B1 NURTURE ALL

契約済み案件は、成果物が完成した時点で以前申告した納期を待たず、buyer-visibleな
成果物を直ちに提出する。提出後はtalkroom readbackとcanonical ledgerの両方で確認する。

### PURCHASE-STATUS

契約・購入状態をfresh snapshotから確定し、未契約案件を納品済みに数えない。

### B2 APPLY BROADLY

応募文に安全マージンとして日数を足さず、能力と作業キューから
正直に実行可能な最短日を提示する。STEP 0で算出した `category_order` を探索と応募の
優先順位に使う。

### B3 LEARN

応募、返信、契約、納品、入金の実測値をcategory別に記録し、次passの順位へ戻す。

## Search-until-result

応募laneは newest、対象category、keyword、単発、継続をdurable cursorで探索する。
eligible案件が見つからないページだけでpassを終了せず、wall-clock budget内で次sourceへ
進む。終了条件は次のどちらかだけ。

1. 応募を成立させ、三重証拠を保存した。
2. 全sourceを一周し、探索量・除外理由・次cursorを保存した。

## Reporting

実応募、出品、返信、納品は成立直後にTelegram outboxへ入れる。pass終了時、
hourly pulse、日報、週報も同じ `ReportEnvelope` snapshotから生成する。
`GIG_REPORT_CHAT` は利用者がruntime環境へ設定し、sourceに個人IDを埋め込まない。

## Self-heal and self-improve

pass後にfresh funnelを作り、SLO collectorがscheduler/lane/browser/disk/sandbox/
application/Telegramを独立監視する。repair controllerは1回に1つだけ修復し、
fresh observationでfingerprintが消えるまでrecoveredにしない。

自己改善は同時に1 experimentだけを許可する。source URL、baseline、変更前後、
評価期限、minimum sampleを保存し、reply/win/paid率でkeep/revertする。

### EXPERIMENT FREEZE GATE

`may_start_experiment=false` の間は新しい実験を開始しない。ただし、すでに開始済みで
`experiments_due` に入った実験のevaluated判定、keep/revert、証拠保存は継続する。
