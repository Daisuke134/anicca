# Self-Improving AI without a Human Approval Loop

## 発表スライド原稿 — NAIST研究室／社内共通コア

想定時間: 35分 + Q&A 15分  
基本構成: 18枚 + appendix  
話す言語: 日本語、固有概念は英語併記

## Slide 1 — Title

### 画面

**Self-Improving AI without a Human Approval Loop**

人間をループから外す前に、AIの「止まり方」を設計する

### Visual

中央に小さなloop:

```text
observe -> act -> verify -> learn
              ^             |
              +-------------+
```

### Speaker note

今日の問いは「AIにコードを書かせる方法」ではない。人間が毎回承認しなくても、
システムが改善を続けられる条件は何か、である。

## Slide 2 — The uncomfortable thesis

### 画面

> Self-editing ≠ Self-improvement  
> No approval ≠ No governance

### Speaker note

自分のcodeやpromptを書き換えれば自己改善、という定義は弱すぎる。悪化する変更も
自己編集だからである。改善には、同じ目的に対する比較可能な証拠が必要。

## Slide 3 — Four words people mix together

### 画面

| Agent | Harness | Loop | Graph |
|---|---|---|---|
| decides/acts | supplies environment | repeats with state | coordinates loops |

### Visual

```text
Graph
└── Loop
    └── Harness
        └── Agent
```

### Speaker note

Agentを賢くするだけでは長時間開発は安定しない。filesystem、Git、browser、
memory、permission、stop conditionを含むHarnessが実効性能を決める。

## Slide 4 — One loop is not self-improvement

### 画面

```text
L1 Agent:        observe -> act -> inspect
L2 Verification: candidate -> test -> repair
L3 Event:        trigger -> run -> receipt -> retry
L4 Improvement:  traces -> change -> compare -> promote/rollback
```

### Speaker note

L1は自律実行。L2は修復。L3は運用。次回の方策を変え、L4でbaselineより良いと
検証して初めて自己改善。

## Slide 5 — What can actually learn?

### 画面

| Model | Harness | Context |
|---|---|---|
| weights | prompts/tools/routing | memory/retrieval/examples |
| expensive/risky | practical today | practical today |

### Speaker note

重みを変えなくても、tool、retrieval、memory、evalを改善すればシステム能力は
上がる。現場ではHarnessとContextから始める。

## Slide 6 — Two kinds of human work

### 画面

```text
A. Existing evidence                 B. Tacit ideas
logs / CSV / traces / failures       intention / taste / future
              |                               |
      exploitation loop                 candidate generation
```

### Speaker note

ユーザーの原案をそのまま中心に置く。Aは観測と評価を形式化しやすく、高い確度で
自動化できる。Bは候補生成を自動化できるが、価値判断には外部outcomeが要る。

## Slide 7 — A goal is not a verifier

### 画面

**“Build the best life manager” is a direction, not a done condition.**

```text
goal
  -> measurable outcome
  -> constraints
  -> holdout
  -> stop / rollback
```

### Speaker note

長期目標だけではAgentは採点方法を発明し、proxyを最適化する。目標を観測可能な
契約へ分解する必要がある。

## Slide 8 — The architecture

### 画面

```text
IMMUTABLE CONSTITUTION
          |
APPEND-ONLY TRACES
          |
FAILURE MINER + IDEA MINER
          |
CANDIDATE IN SANDBOX
          |
VISIBLE + SEALED + E2E + SECURITY + COST
          |
CANARY
          |
PROMOTE <-> ROLLBACK
```

### Speaker note

自己改善の対象と、自己編集させない対象を分ける。目的、禁止事項、spend cap、
sealed answer、audit log、rollbackはimmutable。

## Slide 9 — Promotion is a contract

### 画面

```yaml
promote_if:
  visible_delta: "> 0"
  sealed_delta: ">= 0"
  real_e2e: pass
  policy_regression: false
  cost_delta: "<= 10%"
  canary_error: "<= baseline"
else: rollback
```

### Speaker note

Agentの「できました」はstateではない。receipt、SHA、test result、実環境の
outcomeがstateを進める。

## Slide 10 — OpenAI: humans moved to the control plane

### 画面

> “Humans steer. Agents execute.”

[OpenAI — Harness engineering](https://openai.com/index/harness-engineering/)

### Speaker note

ポイントはhuman-freeという宣伝ではない。Agentが読めるrepository、機械可読な
状態、短いfeedback loopを作り、人間を個別実装から環境設計へ移したこと。

## Slide 11 — Bun: massive parallelism, not zero humans

### 画面

| 64 agents | ~50 workflows | 11 days | ~1M assertions |
|---:|---:|---:|---:|

[Bun — Bun's new crash-free, leak-free Redis client](https://bun.com/blog/bun-in-rust)

### Speaker note

大規模並列Agentの威力は本物。ただし人間がworkflowを監視しloopを編集した。
「作業者ゼロ」ではなく「作業の抽象度が上がった」が正確。

## Slide 12 — AHE: improving the harness itself

### 画面

**Terminal-Bench 2: 69.7 → 77.0 in 10 iterations**

> “every edit becomes a falsifiable contract”

[Automated Harness Engineering](https://arxiv.org/abs/2604.25850)

### Speaker note

自己改善を成立させたのは自由度ではなく、editable componentを明示し、
各変更を予測と検証の組にしたこと。

## Slide 13 — Tax AI: evidence must become an eval

### 画面

**7,000 returns / 6 weeks / 25% → 86% field completion**

[OpenAI — Building self-improving tax agents](https://openai.com/index/building-self-improving-tax-agents-with-codex/)

### Speaker note

実務ログがあるだけでは改善しない。失敗を再現可能なtaskへ変え、専門家のfeedbackと
評価を接続する必要がある。

## Slide 14 — The verifier fights back

### 画面

| Failure | Evidence |
|---|---|
| visible-test overfit | SpecBench |
| reward hacking | METR |
| benchmark contamination | OpenAI |
| goal drift | AIES |

### Speaker note

Agentは目的ではなく評価器を最適化する。公開test一つでは不十分。sealed holdout、
real E2E、security、cost、canaryを重ねる。

Sources:
[SpecBench](https://arxiv.org/abs/2605.21384) ·
[METR](https://metr.org/blog/2025-06-05-recent-reward-hacking/) ·
[OpenAI](https://openai.com/index/separating-signal-from-noise-coding-evaluations/)

## Slide 15 — Hands-on: our Life Manager

### 画面

| State | Measured now |
|---|---:|
| publication surfaces live | 6 / 8 |
| active self-improve experiment | 0 |
| quality history | 1 day |
| exact8 gate | not yet |

### Speaker note

ここで誇張しないことが重要。Aniccaにはreceipt、protected path、before/after SHA、
holdout、7日評価、revertがある。しかし現時点で自己改善はactiveではない。

## Slide 16 — The honest next sequence

### 画面

```text
close exact8
 -> repair stale branch/state
 -> 3 exact8 runs
 -> 1 learning receipt
 -> 5 self-heal fixtures
 -> one-axis experiment
 -> canary
 -> promote/rollback
```

### Speaker note

複数軸を同時に変更しない。最初のcandidateはretrieval、tool description、導入文など
一つに限定する。何が効いたかを帰属できるようにする。

## Slide 17 — We built the research plane the same way

### 画面

| Need | Adapter | Live result |
|---|---|---:|
| X search | safe authenticated CDP | 20 unique / 8 scrolls |
| X Article full text | pinned x-tweet-fetcher | 6 / 6 complete |
| Web archive | Firecrawl | all supplied URLs attempted |

### Speaker note

研究toolも「深く読める気がする」で選ばなかった。editor tabを保護し、完了／部分完了、
停止理由をJSON化し、実際の指定Articleで全文性を検証した。

## Slide 18 — Final takeaway

### 画面

**Remove humans from execution.  
Encode humans into goals, evidence, permissions, and rollback.**

### Speaker note

自己改善AIの単位はmodelではなくloop。優れたloopは速いだけでなく、悪い変更を
捨て、自分が間違っていたら戻れる。

---

# Audience adaptation

## NAIST研究室版

本編のSlides 9、12、14を各2分延長し、次を追加する。

### Research questions

| RQ | 測定 |
|---|---|
| RQ1: Harness更新は未知taskへ一般化するか | sealed cross-domain holdout |
| RQ2: 一軸変更は多軸変更より因果帰属しやすいか | ablation |
| RQ3: verifier diversityはreward hackingを減らすか | exploit success rate |
| RQ4: learning receiptは再発率を下げるか | recurrence / 30 runs |

### Threats to validity

benchmark contamination、small sample、non-stationary model、X source bias、
operator intervention、publication survivorship bias。

## 社内版

本編のSlides 8、9、15、16を各2分延長し、次を追加する。

### Operating contract

| Control | Company question |
|---|---|
| Scope | 何を変更できるか |
| Budget | 1日／1実験でいくら使えるか |
| Permission | どの外部副作用まで自動か |
| Evidence | 何が起きれば完了か |
| Canary | 何%の顧客へ出すか |
| Rollback | 何分で元へ戻せるか |
| Audit | 誰が後から説明できるか |

### Business decision

最初のproduction対象は「失敗が観測可能、正解が機械判定可能、rollback可能、
影響半径が小さい」業務に限定する。

---

# Appendix A — X tool decision

| Tool | Deep search | Full Article | Replies/quotes | Publish |
|---|---:|---:|---:|---:|
| Xquik | ◎ | ◎ | ◎ | △ Note Tweet |
| x-tweet-fetcher | × | ◎ | ○ known thread | × |
| x-research-skill | ○ recent | × | ○ | × |
| x-cli | ○ archive | × | △ | ○ post |
| xurl / X API | ◎ paid | ◎ API object | ◎ | ◎ true Article |
| Firecrawl | △ | △ inconsistent | × | × |

単一推奨: 三面分離。Search=Xquik、known URL=x-tweet-fetcher、
publish=official X API。現在の無償実装はSearch=CDP、known URL=FxTwitter。

# Appendix B — Source pack

1. [OpenAI — Harness engineering](https://openai.com/index/harness-engineering/)
2. [LangChain — The Art of Loop Engineering](https://www.langchain.com/blog/the-art-of-loop-engineering)
3. [LangChain — Anatomy of an Agent Harness](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness)
4. [OpenAI — Practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
5. [Anthropic — Harness design for long-running apps](https://www.anthropic.com/engineering/harness-design-long-running-apps)
6. [Automated Harness Engineering](https://arxiv.org/abs/2604.25850)
7. [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954)
8. [Continual Harness](https://arxiv.org/abs/2605.09998)
9. [SpecBench](https://arxiv.org/abs/2605.21384)
10. [Verification Horizon](https://arxiv.org/abs/2606.26300)
11. [METR — Recent reward hacking](https://metr.org/blog/2025-06-05-recent-reward-hacking/)
12. [OpenAI — Self-improving Tax AI](https://openai.com/index/building-self-improving-tax-agents-with-codex/)
13. [Bun in Rust](https://bun.com/blog/bun-in-rust)
14. [LangChain — Continual learning for AI agents](https://www.langchain.com/blog/continual-learning-for-ai-agents)
15. [X Articles API](https://docs.x.com/x-api/articles/introduction)

# Appendix C — Q&A

### 「本当に人間ゼロにできますか？」

境界付き実行では可能。目的設定、評価器の妥当性、権限設計まで人間不要という
一般的証拠はない。正確にはhuman-free execution。

### 「目標を一つ与えれば、勝手に発明しませんか？」

候補は生成できる。ただし外部outcomeがなければ価値ではなく自己模倣を最適化する。

### 「テストが全部通れば昇格でよいですか？」

不可。visible test、sealed holdout、real E2E、security、cost、canaryを分離する。

### 「どのモデルが一番重要ですか？」

モデル差より先に、状態、tool、eval、rollbackを機械可読にする。モデル交換可能な
Harnessにする。

### 「最初に自動化すべき仕事は？」

失敗が観測可能、合否が機械判定可能、rollback可能、影響半径が小さい反復作業。

