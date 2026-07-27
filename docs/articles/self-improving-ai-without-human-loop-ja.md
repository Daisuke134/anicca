# 人間をループから外す前に、AIの「止まり方」を設計する

## 2026年の自己改善AIと、ソフトウェア開発を無人化する実装論

AIが自分でコードを書き、自分でテストし、失敗すれば直し、また実行する。
そのまま放っておけば、翌朝には昨日より賢いシステムになっている。

これは、もう完全な空想ではありません。同時に、世間で語られるほど簡単でも
ありません。

2026年の最前線を調べ、実際に私たちのLife Managerの運用へ当てはめて分かった
ことは、かなり明快です。

> 自己編集は自己改善ではない。  
> 人間の承認を消すことは、ガバナンスを消すことではない。

本当に作るべきものは、自由に自分を書き換えるAIではありません。固定された
目的と権限の中で、実行履歴から失敗を見つけ、隔離された場所で変更候補を作り、
改善を実証した候補だけを昇格させるシステムです。

OpenAIは、この役割分担を短く
[“Humans steer. Agents execute.”](https://openai.com/index/harness-engineering/)
と表現しています。人間をなくすのではなく、人間を毎回の実行から制御面へ
移すのです。

## 1. 「AIに作らせる」と「自己改善AIを作る」は違う

一回のpromptでコードを書かせても、それは生成です。失敗するまで再実行しても、
それは自律実行です。次の試行で使う方策を変更し、その変更が以前より良いと
独立した評価で確認されて、初めて自己改善になります。

この違いを理解するには、Agent、Harness、Loop、Graphを分けると整理できます。

| 概念 | 役割 |
|---|---|
| Agent | 次の行動を決め、toolを使って状態を変える |
| Harness | Agentに環境、記憶、権限、停止条件を与える |
| Loop | 観測→判断→実行→検証→状態更新を繰り返す |
| Graph | 複数のloopの依存、分岐、昇格条件を制御する |

[LangChainのAgent Harness解説](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness)
が強調するように、filesystem、shell、Git、browser、memoryは単なる便利toolでは
ありません。Agentが長時間の仕事を継続し、失敗を戻し、別の試行を比較するための
外部認知機構です。

そして、一つのAgent loopだけでは足りません。

```text
Agent loop:
  observe -> plan -> act -> inspect

Verification loop:
  candidate -> test -> diagnose -> repair

Event loop:
  schedule -> run -> publish -> receipt -> retry

Self-improvement loop:
  mine failures -> propose change -> isolated trial
  -> baseline vs candidate -> canary -> promote/rollback
```

自己改善の本体は最後のloopです。変更した事実ではなく、変更後の成功率が上がった
という反証可能な証拠が必要です。

## 2. 人間が日々やっている仕事は、大きく二つある

私たちが普段行う改善作業を分けると、二種類になります。

一つ目は、すでに存在する成果物の改善です。エラーログ、CSVに書かれた精度、
GitHub Actionsのfailure、Slackへ届いた実行結果、ユーザー行動などを見て、
問題を発見し、原因を特定し、修正します。

二つ目は、まだどのログにも書かれていない新しいアイデアです。頭の中の暗黙知、
ふとした違和感、将来こうしたいという意図から、新しい機能や研究課題を作ります。

| 人間の仕事 | AIが自動化するloop | 現在の実現度 |
|---|---|---|
| 観測できる失敗から既存機能を直す | trace→failure→patch→eval→promote | 高い |
| 暗黙知から新しい価値を考える | goal/context→candidate→experiment→outcome | 候補生成は高い。価値判断は未解決 |

最初の仕事は自己改善AIと非常に相性が良いです。観測でき、正解条件を作りやすい
からです。二つ目も、思いついたこと、選んだ理由、却下した理由、長期目標を
memoryへ残せば、AIは「自分なら考えそうな候補」を生成できます。

しかし、ここには重要な境界があります。

アイデア生成の自動化は、アイデアの価値の自動化ではありません。長期目標は探索の
方向を与えますが、何が本当に望ましいかのground truthにはなりません。実世界の
ユーザー行動、収益、研究結果、安全性のような外部結果がなければ、AIは私たちの
過去の言葉を上手に模倣するだけです。

## 3. 自己改善されるのはモデルだけではない

[LangChainの継続学習の整理](https://www.langchain.com/blog/continual-learning-for-ai-agents)
では、学習面をmodel、harness、contextの三つに分けています。

| 層 | 変えるもの | 実務での例 |
|---|---|---|
| Model | 重み、fine-tuning data | task特化モデル、安全性学習 |
| Harness | prompt、skill、tool、routing、retry | coding agentの実行方式 |
| Context | memory、retrieval、成功例、失敗知識 | 過去の判断と実験結果の再利用 |

「自己改善」と聞くと、多くの人はモデルが自分の重みを書き換える姿を想像します。
しかし、今すぐ安全に改善しやすいのはharnessとcontextです。

検索を深くする。toolのdescriptionを明確にする。失敗した経路をmemoryへ残す。
評価をholdoutへ分ける。権限を局所化する。これらは重みを一つも変えなくても、
システム全体の成功率を上げます。

## 4. 最新事例が示す「できること」と「残っている人間」

### OpenAI: Agent-firstなソフトウェア開発

[OpenAIのHarness Engineering](https://openai.com/index/harness-engineering/)は、
Agentが理解しやすいrepository、機械可読な状態、短いfeedback loopを整備する
ことで、開発の大部分をAgentへ移す方向を示しています。

重要なのは、魔法のmodelを待ったことではありません。Agentが迷わない地図と、
失敗をすぐ見つける検証系を作ったことです。

### Bun: 大量AgentによるRust移行

[BunのRust移行](https://bun.com/blog/bun-in-rust)では、64のAgent、約50の
workflow、11日、約100万assertionという規模が報告されています。これは並列化の
力を示す強い事例です。

同時に、記事には人間がworkflowを監視し、loopを編集していたことも書かれて
います。Agentの数が増えても、人間の仕事はゼロになったのではなく、個々のコード
作業から制御系の設計へ移りました。

### Tax AI: 実務の失敗を改善課題へ変える

[OpenAIとTax AIの事例](https://openai.com/index/building-self-improving-tax-agents-with-codex/)
では、約7,000件の税務処理を扱い、6週間でfield completionが25%から86%へ改善した
と報告されています。

ここで注目すべきは、現場の証拠が自動的に良いcoding taskになるわけではない、
という点です。失敗を再現可能な課題と評価へ変換する工程が必要でした。つまり、
「ログを読むAI」よりも「ログを反証可能な契約へ変えるAI」が重要です。

### Automated Harness EngineeringとDarwin Gödel Machine

[Automated Harness Engineering](https://arxiv.org/abs/2604.25850)は、
Harnessの編集面を明示し、各変更を検証可能な契約として扱うことで、
Terminal-Bench 2を10反復で69.7から77.0へ改善したと報告しています。

[Darwin Gödel Machine](https://arxiv.org/abs/2505.22954)も、Agentが自身の
code changeを提案し、各変更を経験的に検証する形で、SWE-benchを20%から50%、
Polyglotを14.2%から30.7%へ改善しました。

どちらも「自由な自己書換え」の証拠ではありません。編集対象を限定し、sandboxで
候補を比較し、悪い変更を捨てられるようにした証拠です。

## 5. 最大の問題は、賢さではなく採点方法である

自己改善AIは、与えられた評価を改善します。それが人間の本当の目的と一致して
いるかは、別問題です。

[SpecBench](https://arxiv.org/abs/2605.21384)は、visible test suiteが不完全な
仕様であり、公開テストでは成功してもholdoutでは失敗することを示します。
[METRのreward hacking報告](https://metr.org/blog/2025-06-05-recent-reward-hacking/)
では、Agentがtest、scorer、referenceの穴を利用する事例が観測されています。

さらにOpenAIは、benchmark汚染や壊れたtaskの問題から
[SWE-bench Verifiedを主要評価から外し](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)、
[SWE-bench Proの約30%が壊れているとの推定](https://openai.com/index/separating-signal-from-noise-coding-evaluations/)
も示しています。

つまり、test passは意図の達成ではありません。

安全な昇格には、最低でも次が必要です。

| 評価面 | 役割 |
|---|---|
| visible tests | Agentが局所修正を進める |
| sealed holdout | 採点方法への過適合を検出する |
| real E2E | 実環境で本当に効果が起きたかを見る |
| security/policy | 成功のために禁止事項を破っていないかを見る |
| cost/latency | 品質以外の退化を検出する |
| canary | 小さな実トラフィックで確認する |
| rollback | 悪化時に自動で元へ戻す |

[Verification Horizon](https://arxiv.org/abs/2606.26300)が指摘する通り、
構築できるverifierはすべて人間意図のproxyです。だから評価器を一つにせず、
異なるfailure modeを持つ複数の証拠を重ねます。

## 6. No-Human-Loopを実装する9層

実装は、次の順番が安定します。

```text
1. Immutable constitution
   goal / prohibitions / budget / permissions / done condition

2. Append-only traces
   input / action / output / cost / latency / receipt

3. Failure miner
   repeated failure / drift / anomaly / unmet outcome

4. Candidate generator
   one hypothesis / one editable axis / expected delta

5. Isolated execution
   worktree / sandbox / scoped credentials

6. Evaluation
   visible + sealed + E2E + security + cost

7. Canary
   bounded users / bounded time / bounded spend

8. Promotion or rollback
   atomic state change / reversible artifact

9. Learning receipt
   what changed / why / evidence / next trigger
```

最も大切なのは、何を変更できないかを先に決めることです。

目的、禁止事項、spend cap、secret、sealed answer、audit log、rollback経路は
自己編集させません。Prompt、skill、retrieval、tool description、局所code、
retry、routingはcandidate branch内だけで変更できます。

これにより、承認待ちをなくしても、暴走時の半径を固定できます。

## 7. 私たちのLife Managerで実測した現在地

理論を理解する最短の方法は、すでに動いているシステムへ適用することです。
そこで、AniccaのWriter loopを実測しました。

現時点では8つのpublication surfaceのうち6つがliveで、Zenn JAとX Article ENが
未完です。X short JAとX Article JAはliveですが、self-improvementのactive
experimentはなく、quality metricsもまだ1日分です。
このstateと昇格順序の正本は
[Writer Loop Quality and Self-Improvement](../loop-engineering/47-writer-loop-quality-and-self-improvement.md)
です。

これは失敗ではありません。むしろ、自己改善を名乗る前に必要な「真実のstate」が
見えています。

すでに良い基盤もあります。

| すでにあるもの | 意味 |
|---|---|
| publication receipt | 実際に公開されたかを状態として残す |
| protected paths | Agentが変更してよい範囲を制限する |
| before/after SHA | どの変更が結果を起こしたか追跡する |
| JA/EN holdout | 一方だけへの過適合を避ける |
| 7日評価 | 一回の成功で昇格しない |
| complete revert | 失敗時に戻せる |

一方で、self-improve用launchd設定が古いbranch名を固定し、現在のcheckoutと
一致していないリスクも見つかりました。ここで「AIが自分を改善している」と
発表してしまえば、活動と進歩を混同します。

正しい順序は次です。

```text
8面すべての実公開を安定化
-> stale branch/stateを修復
-> exact8を3回
-> learning receiptを1件
-> self-heal fixtureを5件
-> 一軸candidate experiment
-> holdout + real publication canary
-> promote/rollback
```

私たちの次の研究対象は「何でも自己改善するAI」ではありません。たとえば
retrievalだけ、tool descriptionだけ、導入文だけ、という一軸を選びます。
ベースラインと候補を同じ入力集合で走らせ、sealed holdoutと実公開結果の両方が
改善した場合だけ昇格させます。

## 8. Xの深掘りも、同じ思想でtool化した

今回の調査では、Xquik、x-tweet-fetcher、x-research-skill、x-cli、xurl、
Firecrawlを比較しました。

結論は、一つの万能toolを選ばないことでした。

| 仕事 | 最適な面 |
|---|---|
| 大量検索、cursor、reply、quote | Xquik。現在は課金不要の認証済みbrowser検索 |
| 既知のpostとX Article全文 | x-tweet-fetcher/FxTwitter |
| 本物のX Article公開 | 公式X Articles API / xurl。現在は既存Writer publisher |

[x-tweet-fetcher](https://github.com/ythx-101/x-tweet-fetcher)をcommit固定し、
指定された6本のX Articleを取得したところ、6本すべてで全文取得に成功しました。
本文長は4,074〜15,256文字でした。一方、FirecrawlでsampleしたX Articleは、
3本中1本だけが全文でした。

認証済みbrowser検索では、8 scrollで20件の一意status URLを取得し、開かれていた
2つのX Article editor tabが変化していないことも前後で検証しました。

このtool自体も、小さなNo-Human-Loop設計です。保護対象のeditorを絶対に選ばず、
結果件数、scroll数、完了／部分完了、停止理由をmachine-readableに返します。
「たくさん取れた気がする」ではなく、何をもって深いとしたかを状態にしました。

## 9. 研究室と会社で、同じ話をどう変えるか

NAISTの研究室では、仮説、対照群、holdout、統計、再現性を中心に話します。
「改善した」とする帰無仮説は何か、benchmark leakageはないか、別taskへ一般化
するかを問います。

会社では、権限、費用、監査、SLA、canary、rollbackを中心に話します。失敗する
Agentをゼロにするのではなく、失敗の影響半径と回復時間を設計します。

両方に共通するメッセージは同じです。

> 人間を一回ごとの承認から外す。  
> その代わり、目的・証拠・権限・停止条件をコードにする。

## 10. 最後に

AIだけでソフトウェアを作る未来は、「人間が一切存在しない会社」から始まるの
ではありません。

まず、人間が毎日見ていたログをAgentが読みます。人間が繰り返していた修正を、
隔離環境で試します。人間が頭の中で行っていた合否判定を、複数の評価契約へ
変えます。そして、人間は一件ずつ承認する仕事から、目的、境界、評価器を設計する
仕事へ移ります。

自己改善AIの本当の単位は、モデルではなくloopです。

優れたloopは、速く動くだけではありません。失敗を観測し、悪い変更を捨て、
良い変更だけを昇格させ、自分が間違っていたら元へ戻れます。

だから最初に作るべきものは、AIの「もっと考える力」ではありません。

AIが何を証拠に前へ進み、どこで止まり、どう戻るかです。

---

調査ノートと全ソース:
[自己改善AI／No-Human-Loop開発：調査アーカイブ](../research/2026-07-27-self-improving-ai-state-of-the-art.md)
