# Life Manager Builds Life Manager

発表スライド正本。研究室／社内共通18枚、20分。

記事正本:
[AIが自分の失敗を観測し、Evalを作り、自分を修正するまで](../articles/self-improving-ai-without-human-loop-ja.md)

PowerPoint:
[life-manager-builds-life-manager.pptx](./life-manager-builds-life-manager.pptx)

再生成:
`NODE_PATH=/opt/homebrew/lib/node_modules node docs/presentations/build-self-improving-ai-deck.js`

## Presentation contract

| Item | Decision |
|---|---|
| One story | wake callがprovider timeoutで届かない |
| One thesis | self-editing is not self-improvement |
| Explanation order | Observability → Eval → Graph → Loop |
| Current truth | durable product loopsはexisting、Self-Builderはtarget |
| Demo | synthetic timeoutをIssue→Eval→candidate→Checkerへ通す |
| Claim boundary | human-free execution、immutable governance |

---

## Slide 1 — Life Manager Builds Life Manager

### 画面

**AIが自分の失敗を観測し、Evalを作り、自分を修正するまで**

Observability → Eval → Graph → Loop

### Visual

暗い制御室。中央に一本の循環線。四つのnodeだけを表示する。

### Speaker note

今日は「AIにcodeを書かせる方法」ではなく、Life Managerが自分の失敗から
自分を直すsystemをどう作るかを、一件の失敗だけで説明する。

---

## Slide 2 — 午前7時、電話は鳴らなかった

### 画面

```text
Scheduler: DONE
Agent:     "wake call sent"
Provider:  TIMEOUT
User:      no call
```

**System activity ≠ real-world effect**

### Visual

左にgreenのinternal DONE、右にredのsilent phone。中央のreceiptが欠落。

### Speaker note

Agentの自己申告やAPI responseではなく、外部効果のreceiptが必要。これが
Self-Builderへ入る最初のevidenceになる。

---

## Slide 3 — 自己編集は自己改善ではない

### 画面

```text
code changed                      = self-editing
task completed                    = autonomy
candidate beats baseline safely   = self-improvement
```

**変更ではなく、改善の証拠が必要。**

### Speaker note

PR数、commit数、Agent稼働時間を成功metricにしない。以前より良く、別の面で
悪化せず、戻せることを示して初めて改善と呼ぶ。

---

## Slide 4 — 四つは同じ身体の器官

### 画面

| Organ | Job |
|---|---|
| Observability | 感じる |
| Eval | 採点する |
| Graph | 分岐する |
| Loop | 継続する |

### Visual

四つの円を左から右へ。色はcyan、amber、violet、green。

### Speaker note

用語を別々に覚えない。失敗を感じ、直ったか採点し、安全な経路を選び、
実世界の結果まで繰り返す一つのsystemとして理解する。

---

## Slide 5 — Observabilityは感覚器

### 画面

```text
schedule.claim
 -> context.load
 -> provider.call
 -> effect.verify
 -> outcome.observe
```

Log · Metric · Trace · Effect receipt

### Visual

一本のtrace waterfall。`effect.verify`だけ赤。

### Speaker note

OpenTelemetryの共通schemaでrunをつなぐ。Agent telemetryはdebugだけでなく、
evalを作り改善するfeedback inputになる。

### Source

[OpenTelemetry](https://opentelemetry.io/blog/2025/ai-agent-observability/):
“telemetry is also used as a feedback loop”

---

## Slide 6 — 何千人分をどう観測するか

### 画面

| 全run | 深く保持 | 原則出さない |
|---|---|---|
| error / latency / cost | failures / safety | raw prompt |
| version / receipt | redacted exemplar | health / location |
| state transition | bounded debug | calendar / Telegram |

**Aggregate everyone. Read nobody by default.**

### Visual

大量の薄い点がaggregateへ集まり、少数のred traceだけdrill-down。

### Speaker note

全ユーザーの内容を読むのではない。全runから軽量なsystem evidenceを取り、
失敗だけをredactして深掘る。tenant identityはpseudonymous hash。

---

## Slide 7 — Automated Eval Engineeringは試験工場

### 画面

```text
trace
 -> redact
 -> fixture
 -> baseline FAIL
 -> seal grader
 -> eval_id
```

**Production failure becomes a falsifiable contract.**

### Visual

赤いtraceがamberのtest cardへ変わる。

### Speaker note

AIに感想を採点させる話ではない。失敗を何度でも再現できる
instruction + environment + fixture + verifierへ変える。

### Source

[LangChain](https://www.langchain.com/blog/towards-automating-eval-engineering):
“mine traces -> identify a failure -> build an eval”

---

## Slide 8 — 一つの点数では昇格しない

### 画面

```text
Reproduction
  + Unit / Integration
  + Real E2E
  + Sealed holdout
  + Security / Policy
  + Cost / Latency
  + Canary outcome
```

### Visual

七つのgate。candidateが全gateを通って初めてgreenになる。

### Speaker note

Makerはsealed answerを読めない。Checkerはcandidateを書き換えない。LLM judgeは
semantic補助であり、唯一のpromotion gateではない。

---

## Slide 9 — Graph Engineeringは状態と証拠

### 画面

```text
OBSERVED -> CLUSTERED -> REPRODUCED -> EVAL_READY
-> IMPLEMENTED -> VERIFIED -> CANARY -> MEASURED
```

Failure: RETRY_WAIT · QUARANTINED · ROLLED_BACK · CIRCUIT_OPEN

### Visual

main pathをviolet、failure pathをcoralで描く。

### Speaker note

Timerはtriggerでしかない。Graphは現在state、次へ進むreceipt、失敗時の戻り先を
定義する。Makerの「done」ではstateは進まない。

### Source

[LangChain](https://www.langchain.com/blog/3-years-of-graph-engineering-with-langgraph):
“loops are simple graphs”

---

## Slide 10 — Loop Engineeringはpromptする人を置き換える

### 画面

```text
observe -> diagnose -> evaluate -> change
-> verify -> promote/rollback -> measure -> learn
```

**The loop closes at outcome, not at merge.**

### Visual

Slide 9のgraphを円環で囲み、`measure -> observe`を太くする。

### Speaker note

人間が仕事を見つけ、渡し、確認し、次を決めていた部分をsystemにする。
PR mergeではなく、実metricとlearning receiptまで戻ってloopが閉じる。

### Source

[Addy Osmani](https://addyosmani.com/blog/loop-engineering/):
“replacing yourself as the person who prompts the agent”

---

## Slide 11 — 内側で観測し、外側で修正する

### 画面

```text
PRODUCT PLANE
Life Manager -> trace / metric / receipt
                       |
                       v
CONTROL PLANE
Collector -> Eval Builder -> Maker -> Checker -> Promoter
```

### Visual

上下二層。credential境界を太い線で分ける。

### Speaker note

Productがmerge tokenを持たない。Self-Builderが壊れてもLife Managerは動き、
Life Managerが壊れても外側のSelf-Builderが修理できる。

---

## Slide 12 — 採用tool stack

### 画面

| Layer | Tool |
|---|---|
| Telemetry | OpenTelemetry |
| Trace / Eval UI | Langfuse |
| Durable Graph | Inngest |
| Authority | Postgres |
| Work / Gates | GitHub |
| Outcomes | Mixpanel + Sentry |
| Workers | Codex Terra / Sol |

### Visual

中央にPostgres、周囲を役割別toolが囲む。tool logoより役割名を大きくする。

### Speaker note

GraphのためにLangGraphを追加しない。Life Managerがすでに使うInngestを再利用。
Node evalを先に使い、Harborはportable container taskが必要になってから。

---

## Slide 13 — 現在あるもの

### 画面

**Existing**

- 6 Inngest durable functions
- tenant failure isolation
- Node eval / contract tests
- provider receipts / product signals
- GitHub Actions / protected branches
- Writer holdout / revert patterns

### Visual

六つのexisting blockをgreen outlineで表示。

### Speaker note

Life Managerはゼロからではない。product loop、durability、isolation、eval、
receipt、rollback patternはある。ここまではcodeで確認できる現在地。

---

## Slide 14 — まだないもの

### 画面

**Target**

- common OTel trace envelope
- failure cluster store
- automated reproduction Eval factory
- evidence Issue projector
- Maker / independent Checker dispatcher
- canary → outcome lineage

### Visual

Slide 13と同じ六blockをdashed amberで表示。

### Speaker note

ここを隠さない。現時点で「Life Managerが自分のcodeをproductionへ自動mergeして
いる」とは言わない。architectureと実装順が確定した段階。

---

## Slide 15 — 最初のvertical slice

### 画面

```text
synthetic provider timeout
-> one trace
-> one cluster
-> one failing eval
-> one Issue
-> one isolated PR
-> one independent verdict
-> one learning receipt
```

### Visual

一件の赤いfailureが右端でgreen receiptへ変わる。

### Speaker note

全sourceを一度につながない。この一本でdedupe、reproduction、isolation、
independent verification、recovery、lineageをE2E実証する。

---

## Slide 16 — 自動mergeは契約

### 画面

```yaml
allowlisted_low_risk: true
baseline: fail
candidate: pass
sealed_holdout_delta: ">= 0"
security_regression: false
sensitive_path: false
rollback_ready: true
```

**Else: quarantine, never “ask the same agent.”**

### Visual

左にmachine-readable policy、右にgreen merge / coral quarantineの二分岐。

### Speaker note

最初の対象はlocalized bug、bounded retry、parser、observability、testだけ。
auth、billing、migration、permission、SAFE-T、secretは自動mergeしない。

---

## Slide 17 — No Human Loopの境界

### 画面

**Remove humans from execution.**

**Encode humans into goals, evidence, permissions, and rollback.**

| Mutable | Immutable |
|---|---|
| prompt / tool / local code | goal / policy |
| routing / retry | secret / sealed holdout |
| worker config | promoter / audit history |

### Visual

左に可変の明るい領域、右にimmutable kernel。

### Speaker note

目的や採点器まで自由に自己編集すると、問題・解答・採点・昇格が同じ主体になる。
私たちのNo-Human-Loopはbounded human-free executionである。

---

## Slide 18 — 最後に

### 画面

**Self-improving AI is not a model.**

**It is a loop that can prove it got better.**

```text
Observe honestly.
Evaluate independently.
Promote reversibly.
Learn from outcomes.
```

### Visual

四つの色が一つの閉じた円になる。

### Speaker note

最初に強くするのはAIの思考時間ではない。何を証拠に前へ進み、どこで止まり、
どう戻るかをcodeにする。その時、Life ManagerはLife Managerをbuildし始める。

---

# Audience adaptation

| Audience | 追加する論点 | 削る論点 |
|---|---|---|
| NAIST研究室 | holdout、false positive、causal outcome、再現性、threats to validity | tool導入手順 |
| 社内 | risk allowlist、SLA、cost per promoted fix、rollback、privacy | benchmark史 |

# Demo runbook

| Time | Action | Evidence shown |
|---|---|---|
| 0:00 | synthetic timeoutを2回送る | trace exact2 |
| 0:30 | clusterを見る | cluster exact1 |
| 1:00 | baseline evalを実行 | expected FAIL |
| 1:30 | Issueとcandidate SHAを見る | lineage |
| 2:00 | Checkerを実行 | PASS / policy receipts |
| 2:30 | bad candidateを流す | automatic reject |
| 3:00 | learning receiptを見る | end-to-end closure |

# Source pack

| Source | Core quote |
|---|---|
| [OpenTelemetry — Agent Observability](https://opentelemetry.io/blog/2025/ai-agent-observability/) | “telemetry is also used as a feedback loop” |
| [LangChain — Automated Eval Engineering](https://www.langchain.com/blog/towards-automating-eval-engineering) | “mine traces -> identify a failure -> build an eval” |
| [LangChain — Graph Engineering](https://www.langchain.com/blog/3-years-of-graph-engineering-with-langgraph) | “loops are simple graphs” |
| [Addy Osmani — Loop Engineering](https://addyosmani.com/blog/loop-engineering/) | “replacing yourself as the person who prompts the agent” |
| [Inngest](https://github.com/inngest/inngest) | “Steps ... can run for months and recover from failures.” |
| [Langfuse](https://github.com/langfuse/langfuse) | “develop, monitor, evaluate, and debug AI applications.” |
| [OWASP Agent Observability Standard](https://github.com/OWASP/www-project-agent-observability-standard) | “inspectable, traceable and instrumentable” |
| [Colony Builds Colony](https://runcolony.com/blog/colony-builds-colony/) | “This isn’t a closed loop.” |

# Q&A

| Question | Answer |
|---|---|
| 本当に人間ゼロか | low-risk executionから人間承認を外す。目的・policy・sealed eval・auditはimmutable |
| Cronとの違いは | Cronはtrigger。Graphはstate、receipt、分岐、resume、rollbackを持つ |
| Observability toolを入れれば改善するか | しない。traceをEvalとpromotion decisionへ変換して初めてloopになる |
| LLM judgeだけでよいか | だめ。deterministic、sealed、E2E、security、cost、outcomeを重ねる |
| 最初に何を作るか | synthetic provider timeoutの一つのvertical slice |
