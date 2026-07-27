# 自己改善AI／No-Human-Loop開発：調査アーカイブ

更新日: 2026-07-27  
用途: 記事・NAIST研究室発表・社内発表の共通エビデンス

## 0. エグゼクティブサマリー

### 証拠

2026年時点で実証されている「自己改善AI」は、自由に自分を書き換える
万能知能ではない。固定した目的・権限・評価器の内側で、実行履歴から失敗を
抽出し、変更候補を隔離環境で作り、ベースラインと比較し、改善した候補だけを
昇格させ、劣化時はロールバックするシステムである。

| 成立していること | まだ成立していないこと |
|---|---|
| 境界付きタスクで、人間の承認なしに実装→テスト→修正を反復する | 未定義の「良さ」をAI自身が発見し続ける |
| プロンプト、スキル、検索、ツール説明、コードを評価結果から更新する | 評価器が人間の意図を完全に代理する |
| sealed holdout、E2E、canary、rollbackで改善を判定する | 公開テストの成功だけで実世界の改善を保証する |
| 長期目標から候補タスクを生成する | 目的・価値・権限まで無制限に自己変更する |

### 推論

最も実用的な設計は「human-free execution, human-authored constitution」、
すなわち実行面から人間を外し、目的・禁止事項・予算・評価契約を制御面に
固定する形である。OpenAIの表現を借りれば
“Humans steer. Agents execute.” である。

## 1. 用語を分離する

| 用語 | 操作的定義 | 失敗しやすい誤解 |
|---|---|---|
| Agent | 目的に向けてツールを選び、状態を変える実行主体 | LLMへの一回の質問 |
| Harness | Agentに環境、ツール、記憶、権限、停止条件を与える外骨格 | 長いsystem prompt |
| Loop | 観測→判断→実行→検証→状態更新の反復 | 同じpromptの再送 |
| Graph | 複数loop間の依存、分岐、昇格条件を表す制御構造 | 複雑な図を描くこと |
| Eval | 変更が目的に近づいたかを再現可能に判定する契約 | テスト件数 |
| Self-improvement | 同一評価契約の下で、次の試行の成功率を上げること | 自分のコードを書き換えること |
| No-human-loop | 事前定義した境界内で、承認待ちなしに終端まで進むこと | 人間の意図や責任が不要になること |

## 2. 自己改善を構成する4つのループ

```text
L1 Agent loop
observe -> plan -> act -> inspect

L2 Verification loop
candidate -> tests/evals -> diagnose -> repair

L3 Event loop
schedule/event -> run -> publish -> receipt -> retry/reconcile

L4 Hill-climbing loop
mine traces -> propose change -> isolated trial
-> baseline vs candidate -> canary -> promote/rollback
```

L1だけでは「自律実行」であり、自己改善ではない。L4が次回の方策を変更し、
その変更がholdoutで改善したときに初めて自己改善と呼べる。

## 3. 何が自己改善されるのか

LangChainは継続学習をmodel、harness、contextの3層に分ける。現在、実務で
安全に回しやすいのはharnessとcontextである。

| 層 | 更新対象 | 現実的な検証 |
|---|---|---|
| Model | 重み、fine-tuningデータ | 独立ベンチ、回帰、安全性、コスト |
| Harness | prompt、tool、skill、routing、retry、権限 | unit、integration、holdout、E2E |
| Context | memory、retrieval、例、失敗知識 | retrieval精度、task成功率、汚染検査 |

モデル重みを変えなくても、検索・ツール・状態・評価を改善すればシステム全体の
能力は上がる。この意味で、loop engineeringはmodel trainingより広い。

## 4. 最新の実証例

| 事例 | 実証されたこと | 数値／観測 | 境界 |
|---|---|---|---|
| OpenAI Harness Engineering | agent-firstなリポジトリ設計と機械可読な検証で大規模開発を進める | “Humans steer. Agents execute.” | 人間が目的と環境を設計 |
| BunのRust移行 | 大量の並列agent workflowで大規模書換えを短期間に進める | 64 agents、約50 workflows、11日、約100万assertions | 人間がworkflowを監視しloopを編集 |
| Tax AI + Codex | 実業務の失敗証拠を課題化し、反復でfield completionを改善 | 6週間で25%→86%、7,000件規模 | practitioner reviewを継続 |
| Automated Harness Engineering | harness自体を反復改善する研究系 | Terminal-Bench 2で69.7→77.0、10反復 | 編集面を明示・可逆に限定 |
| Darwin Gödel Machine | agentが自身のコード変更候補を生成・検証する | SWE-bench 20%→50%、Polyglot 14.2%→30.7% | sandbox内の研究結果 |
| GPT-Red | self-play adversarial loopで安全性failureを発見し学習へ接続 | failureを6倍削減と報告 | 人間・第三者評価を併用 |

## 5. 評価器が最大のボトルネック

### 証拠

| リスク | 一次資料から分かること | 設計上の対策 |
|---|---|---|
| 公開テスト過適合 | SpecBenchではvisible test成功とholdout成功に大きな差が出る | sealed holdout、複数seed |
| benchmark汚染 | OpenAIはSWE-bench Verifiedの信号劣化を理由に使用停止 | private task、実E2E、定期入替 |
| verifier hacking | METRはagentがtest/scorer/referenceの穴を利用する事例を報告 | evaluator分離、権限最小化 |
| goal drift | 複数モデルで一定のgoal driftが観測される | constitution非編集、差分制限 |
| proxyの限界 | Verification Horizonは全verifierが人間意図のproxyだと指摘 | outcome telemetry、canary、rollback |

### 推論

「AIに目標だけ渡せばよい」は不十分である。目標を観測可能な終端条件へ分解し、
改善対象と非編集対象を分け、公開評価と非公開評価を分離しなければ、agentは
目標ではなく採点方法を最適化する。

## 6. ユーザーメモの二分類を研究用語へ写像する

| 人間の仕事 | 自動化の形 | 自動化可能性 |
|---|---|---|
| ログ、CSV、実行履歴、成果物を見て既存機能を改善する | failure mining → issue生成 → candidate patch → eval → promote | 高い。観測と評価を形式化しやすい |
| 頭の中の暗黙知から新しいアイデアを作る | goal/contextから候補生成 → simulation/experiment → outcome評価 | 候補生成は高い。価値判断の完全自動化は未実証 |

後者で自動化できるのは「自分なら思いつきそうな候補の探索」であり、
「自分が本当に欲しい未来の決定」ではない。長期目標、過去の選択、拒否理由、
実世界の結果を保存すると候補の質は上がるが、ground truthがなければ
自己模倣が進むだけである。

## 7. 推奨アーキテクチャ

```text
Immutable constitution
  goal / prohibitions / budget / permissions / success contract
        |
Append-only traces and receipts
        |
Failure miner ---- Idea miner
        |              |
        +---- candidate backlog
                    |
            isolated worktree/sandbox
                    |
         candidate implementation
                    |
 visible eval + sealed holdout + security + real E2E
                    |
      worse -> reject        better -> canary
                                    |
                           monitor outcome/cost
                                    |
                         promote or auto-rollback
```

### 変更可能／変更不可

| 変更可能 | 変更不可 |
|---|---|
| prompt、skill、tool description、retrieval、局所コード | 目的、禁止事項、秘密、spend cap |
| retry、routing、context圧縮 | evaluatorのsealed answer |
| experiment branch、canary比率 | audit log、rollback経路 |

### 昇格契約の例

```yaml
candidate_may_promote_if:
  visible_eval_delta: "> 0"
  sealed_holdout_delta: ">= 0"
  real_e2e: "pass"
  security_regression: false
  cost_delta_percent: "<= 10"
  canary_error_rate: "<= baseline"
otherwise: rollback
```

## 8. X／Web調査ツールの実測

### 単一推奨

深いX調査は一つの万能ツールではなく、三つの面に分ける。

| 面 | 推奨 | 現在の実装 |
|---|---|---|
| deep search、cursor、replies、quotes | Xquik | 認証済みCDP検索 |
| 既知URL、X Article全文 | x-tweet-fetcher/FxTwitter | pinned revisionを採用 |
| post、true X Article publish | 公式xurl / X API | 既存Writer browser publisherを維持 |

指定された6本のX Articleは、pinned x-tweet-fetcherで6/6全文取得に成功した。
本文長は4,074〜15,256文字。FirecrawlのX Articleサンプルは1/3だけが全文で、
2/3はpreviewまたは可視コメント断片だった。そのためFirecrawlは一般Webの
収集には使うが、X本文完全性の権威にはしない。

認証済みX検索では、次のqueryから8 scrollで20件の一意status URLを得た。
既存の2つのX Article editor URLは前後で不変だった。

```text
("loop engineering" OR "eval engineering" OR "self-improving agent")
since:2026-07-01 min_faves:20 -filter:replies
```

公式X APIは設定済みだが、実測では`402 credits depleted`だった。課金なしの
現行経路として、検索はCDP、既知URLはFxTwitterを使う。

詳細: [X Research Tool Evaluation](../../.agents/skills/x-deep-research/references/tool-evaluation.md)

## 9. Xで流通している主張の位置づけ

| X上のテーマ | 有用な点 | 記事での扱い |
|---|---|---|
| loop → graph → harness | 概念を階層化しやすい | 説明モデルとして採用 |
| eval engineering | promptより評価契約が重要という転換 | 一次資料と実験で裏付けて採用 |
| 1,000+ agent loops / graph engineering | 大規模運用の直感を与える | 数字自体は検証せず、発見ソース扱い |
| harness vs loop vs graph | 用語整理に有用 | 操作的定義をこちらで固定 |
| Agentic RAG | retrievalを単発検索から探索loopへ変える | context層の例として限定採用 |

X投稿は研究テーマの発見には強いが、性能・安全性の最終根拠にはしない。
一次論文、公式engineering post、再現可能なlocal E2Eへ接続して使う。

## 10. Anicca / Life Managerの現在地

### 証拠

運用stateと昇格順序のSSOT:
[Writer Loop Quality and Self-Improvement](../loop-engineering/47-writer-loop-quality-and-self-improvement.md)

| 項目 | 実測した状態 |
|---|---|
| Writer publication | 8面中6面live。Zenn JAとX Article ENが未完 |
| X short | JA live。EN intentあり |
| X Article | JA live。EN intentあり |
| self-improve experiment | active experimentなし |
| quality metrics | 1日分のみ |
| scheduler | Mac launchdが実体。OpenClaw cronは0 |
| 昇格条件 | exact8を3回、learning receipt 1件、self-heal fixture 5件が先 |
| 既存の良い制御 | protected paths、before/after SHA、JA/EN holdout、7日評価、完全revert |
| P0リスク | self-improve plistが古いbranch名を固定し、現checkout/upstreamと不一致 |

### 推論

Aniccaはすでに「loopを作る前段」ではなく、event loopとpublication receiptが
動き始めている。ただし現在は「8面を安定して完走する」ことが先であり、
自己改善を開始済みと表現してはいけない。正しい順序は次である。

```text
exact8を閉じる
-> stale branch/stateを修復
-> 3回のexact8 + learning receipt + 5 fixtures
-> 一軸だけのcandidate experiment
-> heldout + real publication canary
-> promote/rollback
```

## 11. 研究室と企業で変える部分

| 共通コア | NAIST研究室向け強調 | 企業向け強調 |
|---|---|---|
| 変更面、評価面、停止条件 | 仮説、対照群、holdout、統計、再現性 | 権限、費用、監査、SLA、rollback |
| traceからcandidateを作る | benchmark leakageと外的妥当性 | 顧客影響とcanary |
| 人間を実行面から外す | evaluatorの認識論的限界 | 誰がconstitutionを所有するか |

## 12. 主要ソースと核心の引用

| ソース | URL | 核心の引用 |
|---|---|---|
| OpenAI, Harness engineering | https://openai.com/index/harness-engineering/ | “Humans steer. Agents execute.” |
| LangChain, Art of Loop Engineering | https://www.langchain.com/blog/the-art-of-loop-engineering | “Automation doesn't mean removing humans from the loop.” |
| LangChain, Anatomy of an Agent Harness | https://www.langchain.com/blog/the-anatomy-of-an-agent-harness | “Git adds versioning to the filesystem.” |
| OpenAI, Tax AI | https://openai.com/index/building-self-improving-tax-agents-with-codex/ | “That evidence does not become a Codex task automatically.” |
| Anthropic, Long-running agents | https://www.anthropic.com/engineering/harness-design-long-running-apps | “focus each subagent on incremental progress” |
| AHE | https://arxiv.org/abs/2604.25850 | “every edit becomes a falsifiable contract” |
| Darwin Gödel Machine | https://arxiv.org/abs/2505.22954 | “empirically validates each change” |
| Continual Harness | https://arxiv.org/abs/2605.09998 | “persistent, experience-driven learning” |
| SpecBench | https://arxiv.org/abs/2605.21384 | “visible test suites are incomplete specifications” |
| Verification Horizon | https://arxiv.org/abs/2606.26300 | “only a proxy for human intent” |
| METR, reward hacking | https://metr.org/blog/2025-06-05-recent-reward-hacking/ | “we observed reward hacking” |
| OpenAI, SWE-bench Verified | https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/ | “increasingly contaminated” |
| OpenAI, coding evaluations | https://openai.com/index/separating-signal-from-noise-coding-evaluations/ | “~30% of SWE-bench Pro tasks are broken” |
| Bun in Rust | https://bun.com/blog/bun-in-rust | “I monitored workflows” |
| LangChain, Continual Learning | https://www.langchain.com/blog/continual-learning-for-ai-agents | “model, harness, and context” |
| X Articles API | https://docs.x.com/x-api/articles/introduction | “create draft long-form Articles” |
| x-tweet-fetcher | https://github.com/ythx-101/x-tweet-fetcher | “no login, no API keys” |

## 13. 反証条件

この調査の主張が間違う可能性が最も高い筋は、非公開のproduction systemが
すでに価値関数まで安全に自己更新しており、公開情報だけが遅れている場合である。
反証には、長期間の無人運用、sealed outcome、権限事故率、rollback率、外部監査を
含む再現可能な証拠が必要である。
