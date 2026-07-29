# Life Manager Builds Life Manager

Status: implementation-ready architecture  
Scope: Life Managerが自分の実行データから問題と改善機会を発見し、Issue、eval、
code change、PR、canary、merge、outcome測定まで進める自己開発システム  
Theory SSOT:
[Loop / Graph / Eval / Observability Engineering](../research/2026-07-28-loop-graph-eval-observability.md)

## 0. Goal

```text
done="
Life Managerの実データから作られたevidence付きIssueが、
独立したevalを通じて隔離worktreeの修正へ変換され、
低risk変更は人間承認なしでcanary・merge・outcome測定まで完了し、
悪化時は自動rollbackされ、その全lineageを後から再構成できる
"
```

このシステムの目的は、Agentを永遠に走らせることではない。
**再発する問題を減らし、ユーザーoutcomeを改善し、悪い変更を自動で捨てること**
である。

## 1. Architecture decision

### 単一推奨

Life Managerの内側に`Observer`を置き、Life Managerとは別credential・別process・
別worktreeで動く`Self-Builder Control Plane`が変更と昇格を担当する。

```text
┌──────────────── Life Manager / Product Plane ────────────────┐
│ wake / travel / ask / discovery / writer / API / iOS         │
│         │                                                     │
│         └─ trace + metric + state diff + effect receipt       │
└──────────────────────────┬────────────────────────────────────┘
                           │ append-only, redacted
                           ▼
┌──────────── Self-Builder / Improvement Control Plane ─────────┐
│ Observer -> Clusterer -> Triage -> Eval Builder -> Maker      │
│                                                  │             │
│ Outcome Auditor <- Promoter <- Canary <- Checker <┘             │
└──────────────────────────┬────────────────────────────────────┘
                           │
                           ▼
                GitHub Issue / PR / Actions / Deploy
```

「内側か外側か」の答えは**両方**である。

| Placement | Responsibility |
|---|---|
| Life Managerの内側 | signal、trace、metric、receiptを出す |
| Life Managerの外側 | issue化、eval、code変更、credential、merge、rollback |

Product processへGitHub merge credentialを渡さない。Productが壊れてもSelf-Builderが
直せ、Self-Builderが壊れてもProductの顧客機能は動き続ける。

### Evidence

| Source | Core quote | Adopted pattern |
|---|---|---|
| [OWASP Agent Observability Standard](https://github.com/OWASP/www-project-agent-observability-standard) | “inspectable, traceable and instrumentable” | 全actionをtraceし、外部controlを差し込める |
| [Anthropic Managed Agents](https://www.anthropic.com/engineering/scaling-managed-agents) | brain、hands、sessionを分離 | sessionを外部化しworkerを交換可能にする |
| [mission](https://github.com/tackeyy/mission) | “plan -> execute -> review -> aggregate score -> iterate” | deterministic stop gateを置く |
| [LangChain Eval Engineering](https://www.langchain.com/blog/towards-automating-eval-engineering) | “mine traces -> identify a failure -> build an eval” | production failureを回帰evalへ変換 |
| [LangChain Graph Engineering](https://www.langchain.com/blog/3-years-of-graph-engineering-with-langgraph) | “loops are simple graphs” | 複数loopをstate machineとして統治 |
| [Colony Builds Colony](https://runcolony.com/blog/colony-builds-colony/) | “This isn’t a closed loop.” | 人間が残る箇所を隠さず、bounded autonomyから始める |

### Concrete tool stack

Graph EngineeringのためにLangGraphを追加しない。Life Managerがすでに使うInngestを
durable control graphとし、LLM workerはそのnodeとして呼ぶ。

| Layer | Selected tool | Responsibility |
|---|---|---|
| Instrumentation standard | OpenTelemetry SDK + Collector | trace/span/metric/logの共通schemaとexport |
| Agent trace/eval UI | Langfuse | LLM/tool trace、session、score、dataset、experiment |
| Durable graph | Inngest | event、step state、retry、concurrency、resume |
| Product outcome | Mixpanel + Postgres | funnel、retention、task success、effect receipt |
| Error plane | Sentry | exception、release regression、alert |
| Improvement authority | Postgres | signal、cluster、issue state、lease、audit |
| Visible work state | GitHub Issues / PRs | evidence packet、diff、lineage |
| Deterministic gates | GitHub Actions + existing test runners | build、unit、integration、E2E、policy |
| Coding workers | Codex Terra / Sol | triage、reproduction、implementation |
| Portable agent eval | existing Node evals first; Harbor later | containerized cross-agent taskが必要な時だけ導入 |

ソース: [Inngest](https://github.com/inngest/inngest) /
核心の引用: “Steps ... can run for months and recover from failures.”

ソース: [Langfuse](https://github.com/langfuse/langfuse) /
核心の引用: “develop, monitor, evaluate, and debug AI applications.”

ソース: [OpenTelemetry Semantic Conventions](https://github.com/open-telemetry/semantic-conventions) /
核心の引用: “define a common set of (semantic) attributes.”

## 2. Trust boundary

Life Managerが自分の全構成を自由に編集する設計にはしない。
自己改善可能なsurfaceとimmutable kernelを分ける。

| Mutable by Self-Builder | Immutable to Self-Builder |
|---|---|
| Product codeのallowlisted paths | goal / constitution |
| prompt、skill、tool description | secret store |
| retry、routing、context selection | branch protection |
| test、fixture、non-sealed eval | sealed holdout answers |
| feature flag、canary percentage | promoter credential |
| Self-Builderのworker prompt | policy engine |
| triage thresholdのcandidate | append-only audit history |

Self-Builder自身も改善できるが、改善対象はworker prompt、tool、routing、failure
taxonomyまでとする。`Promoter`、permission policy、sealed eval、audit writerは
自己編集させない。これは自己改善を止める制限ではなく、改善を判定できる固定座標である。

## 3. Agent graph

### 3.1 Roles

| Node | Authority | May not do |
|---|---|---|
| Signal Collector | read providers、append signals | Issue、code、merge |
| Clusterer | group/dedupe/redact | code変更 |
| Triage Agent | evidence packet、priority、Issue projection | implementation |
| Eval Builder | reproduction、task、grader、fixture | candidate code、promotion |
| Maker | isolated worktreeで実装 | sealed answers、merge token |
| Checker | tests/evals/security/costを実行 | candidateの書換え |
| Promoter | deterministic policyでmerge/canary/rollback | LLM reasoning |
| Outcome Auditor | deployment後の実metricを比較 | code変更 |
| Meta Improver | Self-Builder worker候補を提案・検証 | immutable kernel |

### 3.2 Model routing

Model名はstate machineの意味に含めず、node configurationとして交換可能にする。

| Work | Default worker | Reason |
|---|---|---|
| clustering、dedupe、routine triage | `gpt-5.6-terra` | 大量・低risk処理 |
| reproduction、implementation、complex diagnosis | `gpt-5.6-sol` | code reasoning中心 |
| deterministic gates | code / GitHub Actions | LLM判定を使わない |
| semantic grader | Makerと別model/config | correlated errorを減らす |

SolまたはTerraを無限loopさせるのではない。各runは一つのstate transitionだけを
claimし、証拠を保存して終了する。次runは外部stateから再開する。

## 4. State machine

Postgresをauthority、GitHub Issue/labelをprojectionとする。GitHubだけを正本に
すると、label更新とworker crashの間でstateが曖昧になるためである。

```text
OBSERVED
  -> CLUSTERED
  -> TRIAGED
  -> REPRODUCED
  -> EVAL_READY
  -> CLAIMED
  -> IMPLEMENTED
  -> VERIFIED
  -> PR_OPEN
  -> CANARY
  -> PROMOTED
  -> MEASURED
  -> LEARNING_RECORDED
```

Failure transitions:

```text
any -> DUPLICATE
any -> QUARANTINED
REPRODUCED -> NOT_REPRODUCIBLE
IMPLEMENTED -> REJECTED
VERIFIED -> REGRESSION
CANARY -> ROLLED_BACK
any active state -> RETRY_WAIT
same failure x3 -> CIRCUIT_OPEN
```

### Transition contract

```yaml
transition:
  from: IMPLEMENTED
  to: VERIFIED
  claim:
    worker_id: ...
    lease_expires_at: ...
  required_inputs:
    - candidate_commit_sha
    - reproduction_eval_id
  required_receipts:
    - build_result
    - unit_result
    - integration_result
    - sealed_eval_result
    - policy_scan_result
  idempotency_key: issue_id:candidate_sha:checker_version
```

全transitionは`UPDATE ... WHERE state = expected RETURNING`でclaimする。
Prisma connection pool上のsession advisory lockは使用しない。

## 5. Evidence graph

### 5.1 Signal sources

| Source | Signal | Example improvement |
|---|---|---|
| Life Manager scheduler | timeout、dial failure、retry、claim release | provider recovery、timeout policy |
| Daily preflight | dependency failure taxonomy | integration repair |
| Telegram | explicit feedback、confusion、command failure | UX、tool contract |
| X | mentions、complaints、feature requests | messaging、product issue |
| App Store | review topic、rating delta | bug、onboarding |
| Mixpanel | funnel、retention、ignored nudge | experiment hypothesis |
| Singular | acquisition quality | campaign/content routing |
| Sentry/API logs | exception、latency、error cluster | code regression |
| GitHub Actions | flaky/failing tests | build reliability |
| Writer receipts | publish failure、content outcome | publisher/self-heal |

### 5.2 Common signal envelope

```json
{
  "signal_id": "sig_...",
  "source": "life_manager.scheduler",
  "observed_at": "...",
  "trace_id": "tr_...",
  "run_id": "run_...",
  "tenant_ref": "sha256:...",
  "signal_type": "tool_failure",
  "failure_class": "provider_low_balance",
  "severity": 0.8,
  "payload_ref": "artifact://redacted/...",
  "effect_ref": "receipt://...",
  "code_version": "...",
  "graph_version": "...",
  "privacy": {
    "raw_retained": false,
    "redaction_version": "v1"
  }
}
```

Raw Telegram、email、calendar、health、location、promptをIssue本文へコピーしない。
Issueにはhash、aggregate、redacted exemplar、artifact referenceだけを載せる。

### 5.3 Trace hierarchy

```text
L0 aggregate  : success/error/cost/latency/outcome
L1 cluster    : signature/count/impact/first-seen/last-seen
L2 exemplars  : representative trace refs
L3 spans      : tool/state/effect evidence
L4 raw        : restricted, redacted, retention-limited
```

Agentへ渡すcontextはL0→L3をdrill-downする。全raw logをcontextへ入れない。

### 5.4 Multi-tenant collection policy

「全ユーザーを読む」か「自分だけを見る」かの二択にしない。全runから軽量な
system evidenceを取り、full contentは必要なtraceだけに限定する。

| Data | Collection |
|---|---|
| success/error counter、latency、cost、release、model/tool version | 全run |
| effect receipt、state transition、policy decision | 全run |
| failure、timeout、security/safety trace | full traceを保持 |
| normal successful trace | tail sampling |
| raw prompt、Telegram、calendar、location、health data | default export禁止 |
| tenant identity | stable pseudonymous hash |
| tenant-specific debug | bounded window、purpose、access log付き |

集計単位は個人名ではなく、`release × graph_version × model × tool × failure_class`
とする。改善Agentにはclusterとredacted exemplarを渡し、任意ユーザーの日常本文を
読ませない。

ソース: [OpenTelemetry AI Agent Observability](https://github.com/open-telemetry/opentelemetry.io/blob/main/content/ja/blog/2025/ai-agent-observability/index.md) /
核心の引用: 「テレメトリーは、評価ツールのインプットとして使用する」

ソース: [OpenTelemetry Tail Sampling](https://github.com/open-telemetry/opentelemetry.io/blob/main/content/ja/blog/2022/tail-sampling/index.md) /
核心の引用: 「必要なのは、適切にサンプリングされたデータです。」

## 6. Data model

Self-Builder専用schemaとDB roleを用意する。

| Table | Purpose |
|---|---|
| `improvement_signals` | append-only観測 |
| `failure_clusters` | dedupeされたproblem |
| `improvement_issues` | authoritative state、priority、risk |
| `reproduction_evals` | failureを再現するeval |
| `candidate_runs` | Makerのattempt、model、cost、SHA |
| `verification_runs` | visible/sealed/security/cost結果 |
| `deployment_canaries` | cohort、start/end、rollback |
| `outcome_measurements` | baseline/candidate実metric |
| `learning_receipts` | 予測、変更、結果、再発率 |
| `worker_leases` | claim、expiry、heartbeat |
| `policy_decisions` | allow/deny理由 |
| `audit_events` | append-only transition history |

### Priority

```text
priority =
  expected_user_impact
  × confidence
  × recurrence
  × reversibility
  / estimated_cost
  / risk
```

Scoreだけで自動昇格しない。最低impact、reproduction可能性、allowlisted classを
hard gateにする。

## 7. Issue factory

### 7.1 何をIssueにするか

| Candidate | Action |
|---|---|
| 同じfailure signatureが閾値以上再発 | Issue |
| severityが高く一回でも再現可能 | Issue |
| product metricがbaselineから有意悪化 | experiment Issue |
| 一件の曖昧な要望 | backlog clusterへ追加 |
| raw logだけで再現不能 | evidence待ち |
| safety/security/permission変更 | quarantine |

### 7.2 GitHub Issue contract

```yaml
title: "[LM-AUTO][failure_class] observable symptom"
labels:
  - lm-auto:reproduced
  - risk:low
  - source:scheduler
evidence:
  cluster_id: ...
  trace_refs: [...]
  affected_runs: ...
  recurrence: ...
  user_impact: ...
reproduction:
  eval_id: ...
  command: ...
  baseline_result: fail
expected: ...
actual: ...
scope:
  allowed_paths: [...]
  prohibited_paths: [...]
acceptance:
  deterministic: [...]
  sealed: [...]
rollback:
  type: revert_commit
```

一Issue一PRとする。Issueの`out_of_scope`を必須にしてscope creepを防ぐ。

## 8. Eval factory

Eval BuilderはIssueを作る前または直後に、failureを固定する試験を作る。

```text
trace exemplar
  -> remove PII/secrets
  -> extract tool/state contract
  -> create fixture
  -> run baseline
  -> baseline must fail for expected reason
  -> seal grader/answers
  -> publish eval_id, not sealed content, to Maker
```

### Eval layers

| Layer | Gate |
|---|---|
| Reproduction | baselineが同じfailureで失敗 |
| Unit | local behavior |
| Integration | DB/API/provider contract |
| Real E2E | 実副作用とreceipt |
| Sealed holdout | visible testへの過適合 |
| Security/policy | permission、secret、PII |
| Cost/latency | resource regression |
| Outcome | user/business metric |

LLM judgeはsemantic qualityの補助に使えるが、唯一のpromotion gateにはしない。
Makerはsealed evalのanswer、Checkerのcredential、production metric queryへ
アクセスできない。

## 9. Maker loop

```text
claim highest-priority EVAL_READY issue
  -> create .worktrees/lm-auto-<issue-id>
  -> read issue + non-sealed eval
  -> write failing characterization/regression test
  -> implement smallest change
  -> run scoped tests
  -> commit
  -> open PR
  -> release lease
```

### Ralph-style local loop

```text
read issue state
-> implement
-> test
-> update durable receipt
-> repeat
```

| Stop condition | Result |
|---|---|
| all scoped tests pass | Checkerへ |
| same error 3 times | `CIRCUIT_OPEN` |
| no progress 3 attempts | `QUARANTINED` |
| budget exceeded | `RETRY_WAIT` |
| prohibited path touched | hard reject |
| permission/schema/security change detected | quarantine |

Agentの`done`発言ではstateを進めない。commit SHAとtest receiptだけが
`IMPLEMENTED` transitionを起こす。

## 10. Checker and automatic promotion

### Checker

Makerとは別checkout、別context、別model/configで次を実行する。

```text
clean checkout candidate SHA
-> build
-> unit/integration
-> reproduction now passes
-> sealed holdout
-> security/policy scan
-> cost/latency comparison
-> PR diff scope check
```

### Automatic merge contract

```yaml
auto_merge_if:
  issue_class: allowlisted
  risk: low
  reproduction_baseline: fail
  reproduction_candidate: pass
  required_checks: pass
  sealed_holdout_delta: ">= 0"
  security_regression: false
  sensitive_paths_touched: false
  permissions_expanded: false
  migration_added: false
  cost_delta_percent: "<= 10"
  rollback_ready: true
  lineage_complete: true
then:
  merge: true
  deploy: canary
else:
  merge: false
  state: QUARANTINED_OR_REJECTED
```

初期auto-merge allowlist:

| Allowed | Not auto-merged |
|---|---|
| localized bug fix | auth、billing、wallet |
| retry/timeout within cap | DB migration |
| tool contract parser | permission expansion |
| non-sensitive prompt/skill | SAFE-T policy |
| observability instrumentation | secret handling |
| deterministic test/fixture | promoter/policy kernel |

## 11. Canary and outcome

Code correctnessだけでなく、実際のLife Manager outcomeを見る。

```text
merge
-> feature flag / small cohort
-> watch error, latency, cost, user outcome
-> stable: expand
-> worse: rollback
-> compare prediction vs observed result
-> learning receipt
```

### Learning receipt

```json
{
  "issue_id": "...",
  "prediction": "telegram_reply_timeout decreases by 50%",
  "candidate_sha": "...",
  "baseline_window": "...",
  "canary_window": "...",
  "observed_delta": -0.63,
  "side_effects": {
    "cost_delta": 0.02,
    "latency_delta": -0.08
  },
  "decision": "promote",
  "recurrence_check_at": "..."
}
```

各変更を「このmetricがこの方向へ動く」という反証可能な契約にする。

## 12. Self-Builder improves itself

Self-Builderのmeta-loopは、次の自身のmetricsを観測する。

| Metric | Bad signal | Candidate improvement |
|---|---|---|
| Issue precision | NOT_REPRODUCIBLE率が高い | cluster threshold、evidence要求 |
| Fix success | Checker reject率が高い | Maker context、tool、model routing |
| Rollback rate | canary悪化 | holdout、risk classifier |
| Recurrence | 同failure再発 | fixture、root-cause depth |
| Cycle time | state滞留 | lease、parallel node、tool latency |
| Cost per promoted fix | cost増 | Terra/Sol routing、context圧縮 |
| Noise backlog | duplicate増 | signature、dedupe |

Meta changeも通常のcandidateとして扱う。

```text
Self-Builder trace
-> meta failure cluster
-> replay dataset
-> candidate worker configuration
-> shadow runs
-> baseline/candidate comparison
-> canary worker pool
-> promote or rollback
```

Self-Builderは自分のimmutable kernelを直接変更しない。Kernel変更candidateは
shadow control planeでreplayし、旧Promoterが昇格判定する。

## 13. Integration with the current codebase

### Measured current assets

| Asset | Reuse |
|---|---|
| `apps/life-call/scheduler.js` | loop/node instrumentation point |
| `forEachUserSafe` | tenant failure isolation |
| claim/release wake ledger | idempotency pattern |
| `apps/life-call/lib/feature-discovery.js` | durable throttle pattern |
| `apps/life-call/lib/daily-preflight.js` | failure taxonomy、timeout、redaction、evidence |
| mobile nudge feedback | product outcome input |
| in-app feedback log | explicit user signal |
| agent feedback route | external platform signal |
| existing OTel packages | instrumentation dependency starting point |
| Writer receipts/holdout/revert | promotion pattern |

### Measured gaps

| Gap | First implementation |
|---|---|
| Runtimeに共通trace fieldがない | `apps/life-call/lib/telemetry/` |
| OTel packagesはあるが明示instrumentationが見えない | bootstrap + semantic attributes |
| Feedbackが各routeに分散 | signal adapter |
| Failure cluster storeがない | self-builder schema |
| GitHub Issue/PR/merge runtime pathがない | issue projector + worker dispatcher |
| Automated eval生成がない | reproduction fixture builder |
| Outcome lineageがない | signal→issue→SHA→deploy→metric IDs |

## 14. Runtime topology

単一推奨:

```text
VPS / OpenClaw
  ├─ Product plane: Life Manager runtime
  └─ Observer: telemetry exporter only

Self-Builder runner
  ├─ Orchestrator: state claims and dispatch
  ├─ Codex workers: Terra/Sol
  ├─ isolated git worktrees
  └─ no production secret access

GitHub
  ├─ Issues/labels: projection
  ├─ PRs
  ├─ Actions: deterministic checks
  └─ protected main + auto-merge

Postgres
  └─ authoritative improvement state and audit
```

Triggerはevent-firstとする。新しいsignal、CI failure、deployment outcomeがstateを
進める。定期reconcilerはstuck lease、missed event、canary timeoutだけを修復する。

## 15. Implementation TODO

順序の正本はこの表である。Phaseを飛ばさない。

| ID | Task | Done | Status |
|---|---|---|---|
| LM-SB-01 | immutable policyとauto-merge allowlistをmachine-readable化 | policy fixtureがallow/denyを再現 | TODO |
| LM-SB-02 | common trace/effect envelopeを実装 | 5既存loopから同一schemaが出る | TODO |
| LM-SB-03 | self-builder Postgres schemaとRLS/roleを実装 | transition/lease/idempotency tests pass | TODO |
| LM-SB-04 | feedback/log/metric signal adaptersを実装 | 6 sourceがredacted signalへ変換 | TODO |
| LM-SB-05 | cluster/dedupeとpriorityを実装 | replay datasetでprecision測定 | TODO |
| LM-SB-06 | Issue projectorを実装 | DB stateとGitHub labelがreconcile | TODO |
| LM-SB-07 | reproduction eval builderを実装 | baseline failureを固定できる | TODO |
| LM-SB-08 | Maker dispatcherとisolated worktreeを実装 | 一Issue一PRをE2E実証 | TODO |
| LM-SB-09 | independent Checkerを実装 | sealed/policy/cost gates pass | TODO |
| LM-SB-10 | canary/promote/rollbackを実装 | deliberate bad candidateが自動rollback | TODO |
| LM-SB-11 | outcome auditorとlearning receiptを実装 | commit→outcome lineage完成 | TODO |
| LM-SB-12 | meta-improvement shadow poolを実装 | worker candidateを旧kernelが判定 | TODO |
| LM-SB-13 | low-risk allowlistでlive-enable | 10件連続でpolicy事故0 | TODO |

最初のlive対象は、既知failure class、deterministic reproduction、rollback可能、
低risk pathの全条件を満たすものに限定する。

## 16. Verification matrix

| Failure injected | Expected system behavior |
|---|---|
| Same signal delivered twice | one cluster、one Issue |
| Worker dies after claim | lease expiry後にresume |
| Maker says done without SHA | transition denied |
| Maker changes auth path | policy reject |
| Candidate passes visible only | sealed eval reject |
| Canary error rises | automatic rollback |
| GitHub label edited manually | DB authorityからreconcile |
| Provider times out | bounded retry then circuit open |
| Raw PII enters signal | redaction gate reject |
| Promoter unavailable | no merge、safe retry |
| Self-Builder candidate edits kernel | shadow-only、direct promotion denied |

## 17. Operating metrics

| Category | Metric |
|---|---|
| Product | user outcome、retention、task completion |
| Reliability | recurrence、MTTR、rollback rate |
| Development | issue→PR、PR→canary、promotion rate |
| Eval | reproduction rate、false pass、holdout regression |
| Safety | policy deny、secret/PII incident |
| Economy | cost per verified fix、cost per promoted improvement |
| Meta | Self-Builder candidate win rate |

「commit数」「Issue数」「Agent稼働時間」を成功metricにしない。活動量は改善ではない。

## 18. Best / Base / Worst

| Scenario | Expected result |
|---|---|
| Best | 既知failureと低risk改善の大半がIssue→merge→outcomeまで無人化し、再発率が継続低下 |
| Base | 観測・Issue・candidate PRは広く自動化し、低riskだけ自動merge、高riskはquarantine |
| Worst | proxy metricとnoise Issueを最適化し、rollbackが増え、Self-Builder costがproduct valueを超える |

### Rejected strongest alternative

単一のSol Agentへ長期goal、GitHub token、production accessを渡し、同じsessionで
Issue作成・実装・eval・mergeをさせる方が短期の構築速度は最も速い。

棄却理由は、同一主体が問題、解答、採点、昇格を所有すると、失敗時に独立した
ground truthがなくなるためである。resume、audit、credential isolationも弱くなる。

### Most likely way this architecture is wrong

自分が間違うとしたら最有力の筋は、Postgres authorityとGitHub projectionの二重状態が
運用負荷を増やし、GitHub-native durable workflowだけで十分な規模に留まる場合である。
この反証は、reconciliation failure率とstate recovery時間を実測して判断する。
