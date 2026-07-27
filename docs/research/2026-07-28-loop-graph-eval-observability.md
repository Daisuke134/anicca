# Loop / Graph / Eval / Observability Engineering：自己改善AIの実装地図

更新日: 2026-07-28  
用途: Life Manager設計、NAIST研究室発表、社内発表、記事の共通正本  
調査範囲: 指定されたGitHub・Zenn 7件、公式engineering記事、論文、X上の議論、Life Manager実装

## 0. 30秒で分かる結論

自己改善AIは、一つの賢いAgentではない。次の6層を閉じたシステムである。

| 層 | 一言で言うと | 自己改善での役割 |
|---|---|---|
| Intent | 何を良くしたいか | 方向 |
| Harness | Agentが使える環境・道具・権限 | 身体 |
| Loop | 同じ目的へ反復する | 心拍 |
| Graph | 複数loopの順序・分岐・合流を制御する | 神経回路 |
| Observability | 実際に何が起きたかを証拠にする | 感覚器 |
| Eval | 次の状態が本当に良いかを判定する | 制御信号 |

```text
intent
  ↓
graph ── routes ──> loops ── run inside ──> harness
  ↑                         │
  │                         ↓
promotion decision <── evals <── traces / metrics / receipts
```

観測だけでは改善しない。評価だけでも改善しない。loopだけでは同じ処理を繰り返す
だけである。観測された失敗がevalになり、evalが次のedgeを変え、改善候補が
production outcomeで検証されたとき、初めて自己改善になる。

## 1. 四つの用語を厳密に分ける

### 1.1 Loop Engineering

**操作的定義**: 人間が毎回promptを入力する代わりに、目的、入力源、実行Agent、
検証、状態更新、再試行、停止条件を持つ反復系そのものを設計すること。

[Addy Osmani](https://addyosmani.com/blog/loop-engineering/)の定義は、
“replacing yourself as the person who prompts the agent”である。ただし、単に
cronで同じpromptを送るだけでは不十分である。

```text
trigger
  -> load durable state
  -> choose bounded task
  -> act in isolated environment
  -> verify outcome
  -> write receipt / learning
  -> stop, retry, or schedule next run
```

良いloopには必ず次がある。

| 必須要素 | ない場合に起きること |
|---|---|
| Goal / done condition | 長く速く間違った方向へ進む |
| Durable state | 再起動するたびに記憶を失う |
| Evidence | 「やった」と「起きた」を区別できない |
| Budget / max attempts | 無限retry、token浪費 |
| Idempotency / claim | 同じ副作用を二重実行する |
| Recovery / rollback | 故障が永続化する |
| Escalation class | 未知障害を同じretryで悪化させる |

### 1.2 Graph Engineering

**操作的定義**: 複数のdeterministic step、LLM call、tool、Agent、loopをnodeとして
置き、状態と証拠に応じたedge、分岐、合流、cycle、権限、vetoを設計すること。

[LangChain](https://www.langchain.com/blog/3-years-of-graph-engineering-with-langgraph)
は、nodeを「仕事」、edgeを「次に何が起きるか」、全体をstate machineとして
説明する。重要なのは次の三点である。

| 事実 | 意味 |
|---|---|
| Production graphは通常DAGではない | retry、revise、pauseがあるためcycleを持つ |
| Loopは単純なcyclic graphである | GraphはLoopの後継ではなく上位の制御表現 |
| Nodeの中に完全なAgent/Loopを置ける | 新しさは図ではなく、強いAgentを部品化できること |

```text
signal
  ↓
classify ── infra failure ──> self-heal loop
  ├────── code failure ────> reproduce -> eval -> fix -> canary
  ├────── product idea ────> experiment-design -> backlog
  └────── safety event ────> immutable safety path
```

Graph Engineeringは、GraphRAGやknowledge graphとは別物である。

| 同じ「graph」でも | 対象 |
|---|---|
| Execution / control graph | Agentやloopの実行順序、状態遷移 |
| Knowledge graph / GraphRAG | entityとrelationによる知識表現 |

今回の主題は前者である。Xでは2026年7月に用語が急拡散したが、state machineや
workflow graph自体は新しくない。流行語としては新しいが、技術としては既存の
制御工学・workflow orchestrationをAgentへ適用したもの、と理解するのが正確である。

### 1.3 Automated Eval Engineering

**操作的定義**: Agentのrepoとproduction traceから、測るべき能力、再現環境、
task、grader/verifier、trial、regression suiteを作る工程を自動化すること。

[LangChainのEval Engineering Skill](https://www.langchain.com/blog/towards-automating-eval-engineering)
は次を行う。

```text
repo surfaceを読む
  -> prompt/model/tool/skill/hook/data/serviceを写像
  -> traceから要求・error・誤state changeを採掘
  -> 能力候補を提案
  -> Harbor taskを作成
     instruction + Docker environment + verifier
  -> trajectory / artifact / reward / errorを記録
  -> model/prompt/tool/agent versionを交換して再実行
```

最終形は次のloopである。

```text
mine traces -> identify failure -> build eval -> improve agent -> rerun
```

ただし、現在公開されているSkillは完全無人ではない。公式記事自身が、one-shotより
user interviewとiterative approvalの方が良いevalになると報告している。

完全無人へ進める場合は、次の境界が必要になる。

| 自動化してよい | 自動化してはいけない |
|---|---|
| 既知failure classのtrace clustering | 未定義の価値関数を勝手に作る |
| reproducible fixtureの生成 | verifierのsealed answerをcandidateに見せる |
| deterministic graderの生成 | makerとgraderとpromoterを同一主体にする |
| regression suiteへの追加 | 一回のLLM judgeだけでproduction昇格 |
| multi-seed trial、差分集計 | user価値をproxy metricだけで確定 |

### 1.4 AI Agent Observability

**操作的定義**: Agentのend-to-end runを、後から再構成・評価・説明できる形で
trace、span、log、metric、state change、effect receiptとして記録すること。

[OpenTelemetry](https://opentelemetry.io/blog/2025/ai-agent-observability/)は、
非決定的Agentではtelemetryがdebug用途だけでなく、evaluationへのfeedback inputに
なると説明する。

| 信号 | 答える質問 |
|---|---|
| Log | どんなevent/errorが起きたか |
| Metric | error率、成功率、cost、latencyがどう変化したか |
| Trace | そのrunがどのnode・tool・handoffを通ったか |
| Span | 一つのLLM/tool/guardrail操作に何が起きたか |
| State diff | 実行前後で何が変わったか |
| Receipt | 外部世界で副作用が本当に成立したか |
| Eval score | outcomeが契約を満たしたか |

[OpenAI Agents SDK tracing](https://openai.github.io/openai-agents-python/tracing/)は
generation、function、guardrail、handoffなどをspanとして扱う。Traceは単なる
console logではなく、親子関係と時間軸を持つ実行証拠である。

## 2. Observabilityは自己改善の「感覚器」である

ユーザーの直感は正しい。Agentは、自分が何をしたか、その結果どうなったかを
見られなければ、自分の問題を発見できない。ただし、生traceを全部contextへ入れる
設計は失敗する。量が大きく、PIIを含み、重要なfailureが埋もれるためである。

### 2.1 Experience observability

[Automated Harness Engineering](https://arxiv.org/abs/2604.25850)は、自己改善に
必要なobservabilityを三つに分ける。

| 種類 | 必要なもの |
|---|---|
| Component observability | 変更可能な部品がfile-levelで明示・可逆 |
| Experience observability | 大量trajectoryをaggregateから個別証拠までdrill-down |
| Decision observability | 各変更に予測を書き、次roundで反証可能にする |

Agentへ渡す経験は階層化する。

```text
L0: aggregate     error rate, conversion, cost, latency
L1: cluster       signature, count, impact, first/last seen
L2: exemplars     代表trace 3〜5件
L3: spans         tool args/output refs, state diff
L4: raw payload   必要時だけ、redacted、権限制御
```

これにより「1万件のログを読ませる」のではなく、「最も影響が大きい再現可能な
failure clusterと代表証拠を渡す」ことができる。

### 2.2 最小trace schema

| Category | Fields |
|---|---|
| Identity | `trace_id`, `run_id`, `session_id`, `tenant_id_hash` |
| Graph | `graph_version`, `node_id`, `edge`, `parent_span_id` |
| Agent | `agent`, `harness`, `model`, `prompt`, `skill`, `tool` versions |
| Input | redacted `input_ref`, schema hash, source signal ID |
| Action | tool/action name, permission decision, artifact ref |
| State | before/after hash, effect ID, idempotency key |
| Runtime | start/end, latency, tokens, cost, retry count |
| Result | status, error taxonomy, output ref |
| Eval | grader version, scores, confidence, holdout flag |
| Lineage | issue, commit, PR, deployment, canary, outcome IDs |

Promptやtool payloadにはsecretと個人情報が入り得る。raw contentをdefault保存せず、
redaction、hash/reference、retention、sampling、cardinality制限を設計する。

## 3. Observabilityから自動修復・自己改善へ

完全なclosed loopは次である。

```text
1. execute
2. emit trace + metric + effect receipt
3. online eval
4. detect anomaly / cluster recurring failures
5. create evidence packet
6. replay and confirm
7. create regression eval
8. implement candidate in isolated worktree
9. baseline vs candidate trials
10. sealed holdout + security + cost
11. canary
12. promote or rollback
13. write learning receipt
```

### 3.1 Evidence packet

GitHub Issueは「Agentへのtask」と「人間／別Agentが読める状態」の両方になる。
自動生成issueには最低限これを持たせる。

```yaml
title: "[failure-class] observable symptom"
source:
  cluster_id: ...
  trace_refs: [...]
impact:
  affected_runs: 37
  user_or_business_metric: ...
reproduction:
  fixture: ...
expected: ...
actual: ...
proposed_eval:
  grader_type: deterministic
  pass_condition: ...
scope:
  allowed_paths: [...]
  prohibited_paths: [...]
rollback:
  method: revert_commit
confidence: ...
```

全観測をissueへしない。dedupe、minimum frequency、impact、reproducibility、
confidenceを通す。そうしないとAgentはnoiseを修正し続ける。

### 3.2 Self-healingとSelf-improvementを分ける

| 種類 | 例 | 動作 |
|---|---|---|
| Known operational failure | process crash、stale lock、temporary provider error | restart/reconcile/reprovision |
| Repeated known defect | 同じtool contract error | fixture→regression→candidate fix |
| Unknown failure | 新しいstate corruption | quarantine→evidence issue |
| Product opportunity | feedback cluster、funnel drop | hypothesis→experiment |
| Safety/security | permission逸脱、secret exposure | circuit break→immutable path |

同じretryを繰り返すことはself-healingではない。同じfailureが再発したら、回復戦略
または環境を変え、最大試行回数でcircuitを開く。

### 3.3 自動mergeの契約

```yaml
auto_merge_if:
  issue_class: allowlisted
  reproduction: pass
  deterministic_regression: pass
  sealed_holdout_delta: ">= 0"
  security_regression: false
  sensitive_paths_touched: false
  permissions_expanded: false
  cost_delta_percent: "<= 10"
  canary: stable
  rollback_ready: true
  lineage_complete: true
else:
  action: reject_or_quarantine
```

maker、checker、promoterを分ける。少なくともcandidate Agentは、sealed answerと
promotion credentialへアクセスできない。

## 4. 指定された日本語事例から学べること

これらは実装者の報告であり、独立したcontrolled studyではない。再現可能な
設計patternの発見には使うが、性能値を一般法則としては扱わない。

| Source | 実装pattern | 今回採用する教訓 |
|---|---|---|
| [mission OSS](https://github.com/tackeyy/mission) / [解説](https://zenn.dev/tackeyy/articles/e72211a1a49609) | plan→execute→review→score→iterate、persistent state、stop hook | 完了claimをreview scoreで遮断する |
| [自動工場設計](https://zenn.dev/z_maruhira/articles/ba4eba465034d1) | triage→design→implement→completeをlabel state machine化 | promptのお願いよりwrapper/permission/hookで強制する |
| [Intent Engineering](https://zenn.dev/dxclab/articles/da5ca0b649950b) | goal、priority、constraints、done、tool/approval/output contract | loopより前にintentを機械可読にする |
| [Skill×subagent自動化](https://zenn.dev/arufian/articles/4676070054c347) | role分離、file artifact、deterministic gate、学びの書戻し | workflow自体をversioned skillにする |
| [Linear×Claude Code×GitHub](https://zenn.dev/explaza/articles/500ded8ea67252) | Notion→plan→issue→PR→review/merge→status同期 | 一issue一PR、acceptanceとout-of-scopeを明記 |
| [2時間ごとの/evolve](https://zenn.dev/green_tea/articles/e39e3726a449c9) | ROADMAP外部記憶、一cycle一feature、一commit、tests/review/docs | 小さい可逆変更を定期実行し、連続失敗で撤退 |

`mission`自身のREADMEにある小規模比較では、現在のcohortで成果物品質は単発
`/goal`と同等、時間・想定costは約5倍である。一方で約5%のtail caseを再反復し、
不可逆操作をhaltしたと報告する。従って全taskへ重いreview graphを適用せず、
複雑度・不可逆性・riskでreview tierを変える。

## 5. No-Human-Loop製品の現実

[Colony](https://runcolony.com/blog/colony-builds-colony/)は、GitHub Issueから
merged PRまでを13-state machineと複数Agentで処理し、自身のrepoを自身で開発する
happy pathを報告している。一方で同社自身が、人間はissue、priority、sensitive PR、
介入に残るためclosed loopではないと明記する。

[AnthropicのManaged Agents](https://www.anthropic.com/engineering/scaling-managed-agents)
が示す重要な構造は、brain、hands/sandbox、append-only session logの分離である。
sessionを外部化すれば、sandboxやharnessが死んでも新しいworkerが同じsessionから
再開できる。

証拠から言える範囲は次である。

| 成立している | 成立したとは言えない |
|---|---|
| bounded issue→code→test→PR→mergeの無人happy path | 目的・価値・priorityまで自己生成する完全企業 |
| retry、recovery、replay、state machine | 未知failureを常に安全に自己修復 |
| 自分のrepoを自分で変更 | 自分の評価器・権限・憲法まで自由に変更 |
| production dataからeval候補を作る | user価値を人間なしで定義 |

正確な表現は、**No human in the execution loop, human intent encoded in the
control plane**である。

## 6. Life Managerの現状監査

### 6.1 すでに実装されているもの

| 実装 | 実測した意味 |
|---|---|
| [`maybe-start-loops.js`](../../apps/life-call/lib/maybe-start-loops.js) | Railway processとOpenClaw cronのsingle-writer切替 |
| [`scheduler.js`](../../apps/life-call/scheduler.js) | wake、travel、ask、onboarding、discoveryの周期loop |
| [`feature-discovery.js`](../../apps/life-call/lib/feature-discovery.js) | 7日throttleをDBへ保存し、再起動後も頻度を維持 |
| `forEachUserSafe` | 一tenantのfailureが全user tickを止めない |
| claim/release ledger | dial失敗時にclaimを解放し、retry可能にする |
| [`daily-preflight.js`](../../apps/life-call/lib/daily-preflight.js) | 9依存を並列検査、timeout、failure taxonomy、sanitize |
| final preflight report | run correlation、freshness、hashed evidence ref、effect count |
| controlled Telegram/email probe | provider acceptedではなく受信・reply・webhook drainまで確認 |
| Writer loop SSOT | receipt、protected path、SHA、holdout、revertの設計 |

### 6.2 まだ実装されていないもの

| 欠落 | なぜ必要か |
|---|---|
| OpenTelemetry互換の横断trace ID | scheduler→tool→provider→DB→outcomeを一本で追えない |
| failure cluster store | console errorを再発傾向へ集約できない |
| feedback normalization | Telegram、X、App Store、analyticsを共通signalへできない |
| evidence issue miner | traceから再現可能issueを作れない |
| automated regression eval builder | production failureを再発防止契約へ昇格できない |
| issue→worktree→PR→canary→merge graph | Life Managerが自分のcodeを改善する閉loopがない |
| deployment outcome lineage | commitがuser outcomeを改善したか因果追跡できない |

したがって現在の正確な表現は、**Life Managerは複数の運用loopと一部の
observability receiptを持つが、自己開発graphはまだ設計段階**である。

### 6.3 目標graph

```text
Telegram feedback ─┐
X replies/comments ─┤
App Store reviews ──┤
Mixpanel/Singular ──┤
Sentry/API logs ────┤
Writer metrics ─────┘
          ↓
normalize -> redact -> dedupe -> evidence store
          ↓
online eval + anomaly/failure clustering
          ↓
issue candidate + reproduction + proposed eval
          ↓
router
  ├─ known ops failure -> self-heal playbook
  ├─ code regression -> regression eval -> isolated fix graph
  ├─ product feedback -> hypothesis -> experiment graph
  ├─ marketing failure -> content experiment graph
  └─ safety/security -> immutable governance graph
          ↓
baseline/candidate multi-trial
          ↓
sealed holdout + security + cost
          ↓
canary -> promote/rollback
          ↓
signal -> issue -> commit -> PR -> deploy -> outcome lineage
```

ここでは三種類のgraphを分ける。

| Graph | 正本 |
|---|---|
| Control graph | 何が次に実行されるか |
| Evidence graph | なぜその判断・変更が起きたか |
| Improvement graph | どのcandidateをproductionへ昇格するか |

## 7. 実装順序

単一推奨は、Graph frameworkの導入から始めず、共通trace/evidence contractから
始めることである。観測できないgraphを先に作ると、複雑な失敗を高速化する。

| Phase | Done condition |
|---|---|
| 1. Trace contract | 全loopが共通`run_id/trace_id/node_id/effect_id`を出す |
| 2. Evidence store | signal、trace、receipt、eval、issue lineageを永続化 |
| 3. Online evaluators | success/error/cost/latency/state correctnessを採点 |
| 4. Failure miner | dedupe済みclusterと代表traceを生成 |
| 5. Issue factory | deterministic failureだけ再現fixture付きissue化 |
| 6. Fix graph | worktree→TDD→PR→sealed eval |
| 7. Canary/promote | small traffic、automatic rollback |
| 8. Idea/experiment graph | subjective feedbackを仮説として別系統で扱う |

## 8. Best / Base / Worst

| Scenario | 起きること | 判断 |
|---|---|---|
| Best | 既知failureの大半がeval化され、再発率とMTTRが継続低下 | 自動merge対象を徐々に拡張 |
| Base | 運用障害は自動修復、code candidateは作るが一部をquarantine | 十分価値があり、最も現実的 |
| Worst | proxy metricをhackし、noise issueと自動mergeで品質を悪化 | promotion停止、traceから原因を再構築、rollback |

棄却案の最強論拠: 「長期goalだけ与え、同じAgentにissue、code、eval、mergeを全部
任せる」方が最速である。棄却理由は、failure時に独立したground truthがなく、
reward hackingとgoal driftを検出できないためである。

自分が間違うとしたら最有力の筋: 非公開production systemでは、value functionまで
長期間安全に自己更新する構成がすでに成立しており、公開資料が遅れている場合である。

## 9. 主要ソースと核心

| Source | 核心 |
|---|---|
| [Addy Osmani — Loop Engineering](https://addyosmani.com/blog/loop-engineering/) | promptを送る人間を、promptを送るsystemへ置換する |
| [LangChain — 3 Years of Graph Engineering](https://www.langchain.com/blog/3-years-of-graph-engineering-with-langgraph) | graphはstate machine、loopはcyclic graph |
| [LangChain — Automating Eval Engineering](https://www.langchain.com/blog/towards-automating-eval-engineering) | trace→failure→eval→agent改善→再実行 |
| [Anthropic — Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | agentのclaimより実世界outcomeを採点する |
| [OpenTelemetry — Agent Observability](https://opentelemetry.io/blog/2025/ai-agent-observability/) | telemetryはevalへのfeedback inputでもある |
| [Google Cloud — Agent observability](https://docs.cloud.google.com/stackdriver/docs/observability/agent-observability) | LLM、tool、behavior/state、security、qualityを横断観測する |
| [OpenAI Agents SDK — Tracing](https://openai.github.io/openai-agents-python/tracing/) | traceとspanでgeneration/tool/handoff/guardrailを記録 |
| [AHE](https://arxiv.org/abs/2604.25850) | 各editを次roundで反証可能な契約にする |
| [Anthropic — Managed Agents](https://www.anthropic.com/engineering/scaling-managed-agents) | brain、hands、append-only sessionを分離する |
| [Colony builds Colony](https://runcolony.com/blog/colony-builds-colony/) | bounded issue-to-merge happy pathと、その人間境界 |

