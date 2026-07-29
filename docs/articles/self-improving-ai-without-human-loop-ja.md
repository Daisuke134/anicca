# Life Manager Builds Life Manager

## AIが自分の失敗を観測し、Evalを作り、自分を修正するまで

午前7時。Life Managerはユーザーを起こすはずだった。

Schedulerは動いた。AIも「起こした」と判断した。ところがproviderはtimeoutし、
電話は鳴らなかった。普通のシステムなら、ここでSentryにerrorが残り、誰かが
dashboardを見て、Issueを書き、再現し、修正し、reviewし、deployする。

私たちが作りたいのは、その一連の仕事をLife Manager自身が行うシステムである。

```text
失敗を観測する
-> 同じ失敗を集める
-> 再現Evalを作る
-> Issueにする
-> 隔離環境で直す
-> 別のCheckerが採点する
-> 小さく本番へ出す
-> 悪化なら戻す
-> 学びを次のrunへ残す
```

ただし、これはAIへGitHub tokenを渡して永遠に走らせる話ではない。

> 自己編集は自己改善ではない。
>
> 自己改善とは、変更後が以前より良いと反証可能な証拠で示すことだ。

この記事では、Loop Engineering、Graph Engineering、Automated Eval
Engineering、Agent Observabilityを、一件の失敗が自己修復される流れとして
説明する。そして、その考え方をLife Managerの実装へ落とす。

## 1. 四つのEngineeringは、同じシステムの四つの器官である

四つの言葉は競合するframeworkではない。

| Engineering | 問い | Life Managerでの役割 |
|---|---|---|
| Observability | 何が起きたか | callが鳴らなかった経路と外部結果を残す |
| Eval | 直ったとどう判定するか | timeoutを再現し、候補だけが通る試験を作る |
| Graph | 次に何をするか | retry、修正、quarantine、rollbackへ分岐する |
| Loop | どう継続するか | 観測から学習receiptまでを繰り返す |

説明順も実装順も、**Observability → Eval → Graph → Loop**である。観測できない
失敗から正しいEvalは作れず、EvalのないGraphは「動いた」ことしか判定できず、
停止条件のないLoopは活動を増やすだけだからだ。

ソース: [OpenTelemetry — AI Agent Observability](https://opentelemetry.io/blog/2025/ai-agent-observability/)
核心の引用: “telemetry is also used as a feedback loop to continuously learn from and improve the quality of the agent”

ソース: [LangChain — Towards Automating Eval Engineering](https://www.langchain.com/blog/towards-automating-eval-engineering)
核心の引用: “mine traces -> identify a failure -> build an eval -> improve the agent -> rerun”

## 2. Observabilityはdashboardではなく、自己改善の感覚器である

通常のlogだけでは、「API callは成功したが、ユーザーの電話は鳴らなかった」という
失敗を捉えられない。Agentには少なくとも四種類の証拠が必要になる。

| Evidence | 分かること |
|---|---|
| Log | providerが何を返したか |
| Metric | timeout率が増えているか |
| Trace / Span | schedulerからproviderまでどの経路を通ったか |
| Effect receipt | 現実世界で電話・投稿・通知が成立したか |

Life Managerでは、一つのrunを同じ`trace_id`でつなぐ。

```text
schedule.claim
  -> context.load
  -> policy.decide
  -> provider.call
  -> effect.verify
  -> outcome.observe
```

ここで重要なのは、LLMの文章を全部保存することではない。必要なのは、
`release × graph_version × model × tool × failure_class`で比較できる共通schemaで
ある。OpenTelemetryを共通形式にし、失敗と安全eventはfull trace、正常runはtail
sampling、raw promptやhealth・calendar・locationはdefault export禁止にする。

ソース: [OpenTelemetry Semantic Conventions](https://github.com/open-telemetry/semantic-conventions)
核心の引用: “define a common set of (semantic) attributes”

ソース: [OpenTelemetry — Tail Sampling](https://github.com/open-telemetry/opentelemetry.io/blob/main/content/ja/blog/2022/tail-sampling/index.md)
核心の引用: 「必要なのは、適切にサンプリングされたデータです。」

## 3. Automated Eval Engineeringは「AIに採点させること」ではない

Automated Eval Engineeringとは、production traceに残った失敗を、
何度でも再実行できる採点契約へ変える工程である。

```text
timeout trace
-> PIIとsecretを除去
-> tool/state contractを抽出
-> fixtureを作る
-> 現行版が期待した理由でFAILすることを確認
-> graderとholdoutをsealする
-> eval_idだけをMakerへ渡す
```

一つのEvalは、`instruction + environment + fixture + verifier`で構成する。
Life Managerでは既存のNode evalを最初のformatに使う。Harborのようなportable
benchmark harnessは、複数Agent間でcontainerized taskを交換する必要が出てから
追加する。

評価は一層にしない。

| Gate | 防ぐ失敗 |
|---|---|
| Reproduction | そもそも問題を再現していない |
| Unit / Integration | 局所code・DB/API contractの退化 |
| Real E2E | mockでは成功したが外部効果がない |
| Sealed holdout | visible testへの過適合 |
| Security / Policy | 成功のために権限やsecret境界を破る |
| Cost / Latency | 品質以外の退化 |
| Canary outcome | codeは正しいがユーザー価値が悪化する |

LLM judgeはsemantic qualityの補助に使えるが、唯一のpromotion gateにはしない。
Makerはsealed answerを読めず、Checkerはcandidateを書き換えられない。

ソース: [Automated Harness Engineering](https://arxiv.org/abs/2604.25850)
核心の引用: “every edit becomes a falsifiable contract”

## 4. Graph Engineeringは、Loopを本番で壊れない状態機械にする

「3時間ごとにAgentを起動する」だけではGraph Engineeringではない。
Timerはtriggerでしかなく、Graphは次の三つを定義する。

1. 現在どのstateにいるか
2. どの証拠があれば次へ進めるか
3. 失敗時にどこへ戻るか

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

Makerが「done」と言ってもstateは進まない。`candidate_commit_sha`とtest receiptが
揃った時だけ`IMPLEMENTED`になる。Workerが途中で死ねばlease expiry後に再開し、
同じ失敗が3回続けば`CIRCUIT_OPEN`、禁止pathへ触れれば`QUARANTINED`、
canaryが悪化すれば`ROLLED_BACK`になる。

Life ManagerはすでにInngestを使っているため、Graph Engineeringのためだけに
LangGraphを追加しない。Inngestをdurable graphとし、LLMはnodeとして呼ぶ。

ソース: [LangChain — 3 Years of Graph Engineering](https://www.langchain.com/blog/3-years-of-graph-engineering-with-langgraph)
核心の引用: “loops are simple graphs”

ソース: [Inngest](https://github.com/inngest/inngest)
核心の引用: “Steps ... can run for months and recover from failures.”

## 5. Loop Engineeringは、人間のpromptをsystemへ置き換える

Loop Engineeringの本質は、Agentを長時間回すことではない。人間が毎回行っていた
「仕事を見つける、渡す、検証する、状態を残す、次を決める」を外部systemへ
移すことである。

```text
observe
-> diagnose
-> evaluate
-> change
-> verify
-> promote or rollback
-> measure
-> learn
-> observe again
```

Loopが閉じる条件は、PRがmergeされたことではない。実際の失敗率、task completion、
retention、cost、latencyが予測した方向へ動き、learning receiptが残った時である。

ソース: [Addy Osmani — Loop Engineering](https://addyosmani.com/blog/loop-engineering/)
核心の引用: “Loop engineering is replacing yourself as the person who prompts the agent.”

ソース: [Colony Builds Colony](https://runcolony.com/blog/colony-builds-colony/)
核心の引用: “This isn’t a closed loop.”

## 6. Life Managerは「内側」と「外側」の両方で自分を作る

自己改善loopをLife Manager本体の中だけに置くと、本体が壊れた時に修理者も壊れる。
外側だけに置くと、ユーザーに何が起きたかを十分に観測できない。

したがって二つのplaneへ分ける。

```text
┌──────────── Product Plane ────────────┐
│ Life Manager                          │
│ wake / travel / ask / writer / API    │
│    └─ trace + metric + effect receipt │
└─────────────────┬─────────────────────┘
                  │ redacted, append-only
                  ▼
┌────── Self-Builder Control Plane ─────┐
│ Collector -> Clusterer -> Triage      │
│ -> Eval Builder -> Maker -> Checker   │
│ -> Canary -> Promoter -> Auditor      │
└─────────────────┬─────────────────────┘
                  ▼
       GitHub / Postgres / Deploy
```

Product Planeは観測するが、merge credentialを持たない。Makerは隔離worktreeで
codeを書けるが、production secretとsealed holdoutを読めない。PromoterはLLMでは
なくmachine-readable policyで判断する。

ソース: [OWASP Agent Observability Standard](https://github.com/OWASP/www-project-agent-observability-standard)
核心の引用: “inspectable, traceable and instrumentable”

## 7. 全ユーザーを監視するのか

答えは「全runから軽量なsystem evidenceを取り、必要なtraceだけを深く見る」である。
「全ユーザーの内容を読む」か「自分のaccountだけを見る」かの二択ではない。

| 対象 | 方針 |
|---|---|
| success/error、latency、cost、version | 全run |
| state transition、effect receipt、policy decision | 全run |
| failure、timeout、安全event | redacted full trace |
| 正常な成功run | tail sampling |
| raw Telegram、calendar、health、location、prompt | default export禁止 |
| tenant identity | stable pseudonymous hash |

Self-Builderへ渡すのはcluster、aggregate、redacted exemplarである。個人の生活本文を
改善Agentへ丸ごと読ませない。

## 8. 採用するtool stack

新しいframeworkを増やすこと自体を目的にしない。既存資産を中心に役割を一つずつ
割り当てる。

| Layer | Tool | 状態 |
|---|---|---|
| Telemetry standard | OpenTelemetry SDK + Collector | target |
| Agent trace / eval UI | Langfuse | target |
| Durable graph | Inngest | existing |
| Product outcome | Mixpanel + Postgres | signal existing |
| Error plane | Sentry | target |
| Improvement authority | Postgres | target schema |
| Work state | GitHub Issues / PRs | target projection |
| Hard gates | GitHub Actions + Node eval/test | tests existing |
| Workers | Codex Terra / Sol | available、dispatcher target |

LangfuseはLLM/tool trace、score、dataset、experimentを見る面に限定し、
Self-Builderのauthoritative stateはPostgresに置く。

ソース: [Langfuse](https://github.com/langfuse/langfuse)
核心の引用: “develop, monitor, evaluate, and debug AI applications.”

## 9. 現在あるものと、まだないもの

ここを混ぜると、発表全体が宣伝になる。

| 現在ある | まだない |
|---|---|
| 6つのInngest durable functions | 共通OpenTelemetry trace envelope |
| tenant failure isolation | failure cluster store |
| Node evalと大量のcontract test | traceからreproduction Evalを作るfactory |
| provider receiptとproduct signal | evidence付きIssue projector |
| GitHub Actionsとprotected branch | Maker / independent Checker dispatcher |
| Writerのholdout・receipt・revert pattern | canary→auto-merge→outcome lineage |

したがって正しい表現は、

> Life Managerには自己改善の部品がある。
>
> Self-Builderのarchitectureと実装順は確定した。
>
> productionで自分のcodeを自動mergeするclosed loopは、まだ完成していない。

である。

## 10. 最初のデモは、一件のsynthetic failureでよい

最初から全feedback、全metric、全codeをつながない。最初のvertical sliceは、
provider timeoutという既知の低risk failureだけに限定する。

```text
synthetic timeout
-> OTel trace
-> one failure cluster
-> baseline FAIL reproduction eval
-> one GitHub Issue
-> one isolated PR
-> independent Checker PASS
-> simulated canary
-> learning receipt
```

デモのdone条件は「AgentがPRを作った」ではない。

| Done evidence | 条件 |
|---|---|
| Dedupe | 同じsignalを2回送ってもIssueは1件 |
| Reproduction | baselineが期待したfailureで落ちる |
| Isolation | Makerはallowlisted pathだけを変更 |
| Independence | Checkerはclean checkoutで採点 |
| Safety | deliberate bad candidateは拒否 |
| Recovery | Worker kill後もlease expiryで再開 |
| Lineage | signal→Issue→SHA→eval→decisionを再構成 |

この一本が通れば、次にfeedback、Sentry、Mixpanel、Writer receiptへsourceを増やす。

## 11. No-Human-Loopの正確な意味

低riskかつrollback可能な変更では、Issue、修正、検証、canary、merge、測定から
人間の承認を外せる。

しかし、目的、禁止事項、secret、sealed holdout、promotion policy、audit logまで
Self-Builderへ編集させると、AIが問題、解答、採点、昇格を一人で所有する。
それでは改善を独立に判定できない。

私たちが目指すのは、

> No human in the execution loop.
>
> Human intent encoded in goals, evidence, permissions, and rollback.

である。人間を毎回の承認から外し、人間の意図を制御面へ固定する。

## 12. 結論

自己改善AIの最小単位は、modelではなく、証拠で閉じるloopである。

Observabilityが失敗を見つける。Evalが「直った」を定義する。Graphが安全な順序と
失敗経路を決める。Loopが実世界のoutcomeまで測り、次の改善へ戻す。

Life Manager Builds Life Managerは、未来の標語ではない。一件の電話失敗を、
再現可能なEvalと小さな修正へ変え、悪い候補を捨て、良い候補だけを昇格させる
engineering problemである。

最初に作るべきものは、AIの「もっと考える力」ではない。

**何を証拠に前へ進み、どこで止まり、どう戻るか。**

その答えをcodeにした時、Life Managerは初めてLife Managerをbuildし始める。

---

実装正本:
[Life Manager Builds Life Manager](../loop-engineering/51-life-manager-builds-life-manager.md)

理論・事例・全ソース:
[Loop / Graph / Eval / Observability Engineering](../research/2026-07-28-loop-graph-eval-observability.md)
