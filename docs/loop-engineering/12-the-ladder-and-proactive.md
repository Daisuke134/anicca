# 12 AI-driven development の梯子（ladder）と proactive loop ── 記事/本の背骨

> ★Dais の到達点(2026-07-08)★: loop の型は並列の4分類でなく、**登る梯子**。各段が人間を1つ剥がす。上の段ほど賢い agent が要る。★proactive loop = loop + goal★（ただの loop=cron、proactive は goal を内包する＝そこが違う）。正本の型分類 → [[01-loop-vs-goal-resolved]]、主体別3ループ → [[04-the-two-loops]]。

## 1. 梯子（各段が人間を1つ剥がす）

| L | 段 | 何が起きるか | 人間の残る仕事 |
|---|---|---|---|
| L1 | vibe-coding | 毎ターン「こう直せ」と指示 | 観測 + ゴール生成 + 検証、全部 |
| L2 | xDD（spec/test/verification/eval-driven, superpowers/vcsdd） | framework が1反復の品質を保証 | 毎ステップ babysit + done 判定 |
| L3 | `/goal` | 独立 checker が done を verifiable に判定 → agent が止まらず end-to-end 完遂 | ★ゴールを1回 prompt する★ |
| L4 | loop（time-based, cron/launchd） | その `/goal` を cron 化。agent が毎日 自分でゴールを立て実行 | ★prompt から out★。だが台本は固定(＝ただの cron) |
| **L5** | **proactive + self-improving** | loop が「環境を観測しゴールを自己生成(=loop+goal)」＋ **loop 自身が loop を改善** | 長期ゴール設定 + 日々のゴールが長期に aligned かの保証のみ |
| **L6** | **self-goal-setting（最終）** | agent が **end-goal 自体も自己決定**（Elon が「多惑星種」を選ぶように）。日々も end-goal も self-generated + self-improving | ★なし（人間の仕事すら消える）★ |

★人間の仕事が段ごとに縮む★: 毎ゴールを prompt(L1-3) → loop を設計(L4) → **自己改善する loop を設計 + 長期ゴール & alignment(L5)** → **何も設定しない(L6)**。

## 2. 第2軸 ── これが揃って初めて "no human"

```
       開発ループから人が out（L1→L6、agent が自分でゴールを立てる）
             ×
       human credential / subscription 依存ゼロ（own crypto wallet で compute[食+住=cloud]を実払い）
       ────────────────────────────────────────────────────────
             = 真の no-human
```
どの段でも agent が人間の credential/subscription で動く限り依存は残る。Franklin / claude(→cloak reader)が **自分の wallet で自分の compute を実際に払う**と credential 依存も消える。

## 3. proactive loop vs cron（Dais の核心）

```
ただの loop / cron : 時計で起きて【固定台本】を実行（time-based, L4）
proactive loop     : 起きて【世界を観測し "今何が重要か" を自己生成(goal)】して動く = loop + goal
                     ＝ CEO（Elon）が毎日 世界を見て自分の優先順位を作るのと同じ
```
→ 詳細な time-based vs proactive → [[11-parent-funding-loop]]（親 funding loop は proactive の型: OBSERVE→DECIDE(agent判断)→FUND→LOG）。

## 4. 今どこ / 決定事項

- **今 = L4**（time-based loops 稼働: 2026-07-08 Franklin loop 蘇生([[10-STATUS-verified]] #10)、claude-p main loop 配線済）→ **L5 へ移行中**。self-improve harness(openevolve)が「loop が loop を改善」の種で、既に1周 adversary-gated promote 実証済(A3)。
- ★決定(Dais 2026-07-08)★: **Franklin も claude-p も proactive loop にする**（両方 loop+goal 化）。#7 恒久 funding loop がその第一歩。
- ★決定(Dais 2026-07-08)★: **refactor（claw loops を `~/anicca`→`~/profitable-claude` へ、anicca=経済の環境 / profitable-claude=human-funded 外側）は最後（very end）に行う**。→ [[05-coordination-with-agent-economy]] の境界と整合。

## 5. prior art（外部検索 2026-07-08、全て自取得の一次引用）

### L5 = 自己改善ループ（loop が自コードを書き換え、検証 gate で守る）
| 手法 | 核心引用（URL） | copy する手法 |
|---|---|---|
| **Darwin Gödel Machine**（Sakana） | 「iteratively modifies its own code…empirically validates each change using coding benchmarks」20%→50% SWE-bench（[arxiv 2505.22954](https://arxiv.org/abs/2505.22954) / [sakana.ai/dgm](https://sakana.ai/dgm/) / gh `jennyzzt/dgm` 2161★） | ★archive(stepping-stone群)から親 sample→FM が変異案→benchmark gate→通過のみ archive 追加★。**警告**: DGM がテストログ捏造の reward hacking を起こした（「it faked a log making it look like it had run the tests」）→我々の fake/dry 禁止 + transparent lineage と一致 |
| **ADAS / Meta Agent Search** | 「a meta agent iteratively programs interesting new agents…archive of previous discoveries…superior performance even when transferred across domains and models」（[arxiv 2408.08435](https://arxiv.org/abs/2408.08435) / gh `ShengranHu/ADAS` 1608★） | agent を code として定義しメタ agent が構造を書換。model 非依存の汎用改善 |
| **STOP** | 「a seed improver that improves an input program…run this seed improver to improve itself」（[arxiv 2310.02304](https://arxiv.org/abs/2310.02304)） | 最軽量: utility fn 1個 + seed improver + LM で自己適用ループ |
| **Schmidhuber Gödel Machine**（理論祖） | 「rewrites its own code as soon as it has found a proof that the rewrite is useful…globally optimal」（[idsia](https://people.idsia.ch/~juergen/goedelmachine.html)） | 「書換前に必ず gate」。DGM=証明を実証検証に置換した実装版 |
| **Self-Rewarding LMs** | 「the language model itself…via LLM-as-a-Judge…provide its own rewards」（[arxiv 2401.10020](https://arxiv.org/abs/2401.10020)） | judge 自体も反復成長→L6 への橋渡し |

### L6 = agent が end-goal 自体を生成（open-ended）
| 手法 | 核心引用（URL） | 機構 |
|---|---|---|
| **DeepMind「Open-Endedness Essential for ASI」** | 「open-endedness through…novelty and learnability…essential property of any ASI」（[arxiv 2406.04268](https://arxiv.org/abs/2406.04268)） | ★次 goal を novelty×learnability で filter★ |
| **OMNI** | 「foundation models as a model of interestingness…AI selecting its own next task」（[arxiv 2306.01711](https://arxiv.org/abs/2306.01711)） | ★最も直接: FM に「面白いか」を prompt で判定させ次タスク選択★ |
| **Clune AI-GAs** | 「Pillar 3: generating effective learning environments」（[arxiv 1905.10985](https://arxiv.org/abs/1905.10985)） | 学習環境(=課題/目標)自体を自動生成 |
| **POET** | 「pairs the generation of environmental challenges and the optimization of agents」（[arxiv 1901.01753](https://arxiv.org/abs/1901.01753)） | 課題生成×agent 最適化を共進化 |
| **Voyager** | 「an automatic curriculum that maximizes exploration…without human intervention」（[arxiv 2305.16291](https://arxiv.org/abs/2305.16291)） | skill 在庫+世界から次タスク自己提案（有界 L6） |

### 経済的自立（own wallet で compute 実払い）
| 事例 | 核心引用（URL） |
|---|---|
| **x402** | agent micropayment 標準、30日で 75.41M tx / $24.24M（[x402.org](https://x402.org) / gh 6274★） |
| **Virtuals / ACP** | ★最も具体★「each agent…non-custodial wallet, virtual payment card, wallet-funded compute access」。ACP=Request→Negotiation→Transaction→Evaluation を escrow+Evaluator で検証（[whitepaper.virtuals.io](https://whitepaper.virtuals.io/)） |
| **Truth Terminal** | agent が wallet を求め資金調達し memecoin で millionaire 化（[Wired](https://www.wired.com/story/truth-terminal-goatse-crypto-millionaire/)）。★但し非 zero-human（人間が投稿承認+retrain、code 自己改善なし）★ |

### ★統合 = 我々の novelty（正直な gap）★
**L5/L6 の自己改善 × zero-human 経済的自立 を"同時に"満たす実例は未発見。**
- DGM/ADAS/STOP = 自己改善するが human-funded + human-supervised（sandbox, 研究者の API key）。
- Virtuals/x402 = own-wallet+own-compute だが、その上の agent が自コード改善 / 自 end-goal 選択する文書化事例なし（rails のみ）。
- Truth Terminal = 経済的自律に最も近いが人間 curation + code 自己改善なし。
→ ★我々の harness = この2系譜（DGM 式 self-improve gate + Virtuals/x402 式 self-funded infra）を**意図的に接続**する試み。この位置づけは正当かつ新規。★

出典: 全て自取得の一次情報（arxiv abstract / 公式 blog / GitHub README / Wired / x402.org / Virtuals whitepaper, 2026-07-08）。

出典: Dais 対話(2026-07-08) / [[01-loop-vs-goal-resolved]] / [[11-parent-funding-loop]] / [[06-harness-engineering-weng]]。
