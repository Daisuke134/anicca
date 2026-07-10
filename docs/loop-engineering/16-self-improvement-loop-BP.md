# 16 — Self-Improvement Loop: how to actually make an agent improve itself (research corpus)

> 2026-07-10。Loop Engineering 記事①の「self-improvement をどう本当に効かせるか」章の evidence 正本。
> LayerX Zenn 2記事 + 実装 repo 群の deep-research を集約（それまで chat のみだった分をここに永続化）。
> crypto ゼロ = 一般の agent 構築論。関連 [[14-cold-start-escape-BP]]（我々の trap 診断）。

## 中心命題

単一 agent を1本の loop で「自己反省」させるだけでは局所最適で止まる。効くのは
**population（複数候補）+ archive（捨てない）+ 非貪欲な親選択 + 強制探索**。
＝「1体を賢くする」ではなく「群れで探索し、良い変異を残す」。

## 局所最適の失敗モード（LayerX Zenn の整理軸）

- **PACEevolve**: Context Pollution（文脈汚染）/ Mode Collapse（多様性崩壊）/ Weak Collaboration。
- **Controlled Self-Evolution (CSE)**: Initialization Bias / Uncontrolled Stochastic Operations /
  Insufficient Experience Utilization。
- **Degeneration-of-Thought**（Multi-Agent Debate, Liang et al.）: 単一 self-refine/Reflexion は
  「自信を持つと初期の誤りから抜けられない」。→ meta-loop が単一 sub-loop の自己評価だけに頼るのは危険。

## 効く機構（実装 repo・file レベル）

| 機構 | repo / file | 何をする | 我々への適用 |
|---|---|---|---|
| **3階層の親サンプリング** | `openevolve/database.py::_sample_parent()` (star 6.7k) | exploration / exploitation / weighted-random の3確率で親選択。空 island には最良個体を注入（`_sample_exploration_parent`） | cold-start 個体を淘汰せず探索側に配分 |
| **island migration** | `openevolve::migrate_programs()` | ring topology で勝者を島間伝播（重複検出付き） | 勝った genome を Franklin 群で交配 |
| **非貪欲な親選択** | `dgm/DGM_outer.py::choose_selfimproves()` (star 2.2k) | `score_prop`＝sigmoid 確率選択。低スコア個体も非ゼロ確率で選ぶ → 多様性が枯れない。SWE-bench 20%→50% を自己改善で実証 | 「まだ稼げない Franklin」も改善対象に残す |
| **Archive = population** | `ShengranHu/ADAS/search.py` (ICLR2025) | `get_init_archive → get_prompt(archive, mutation指示) → 生成 → score>0 なら append`。archive 自体が群 | 全 genome 変異体を archive に蓄積 |
| **多様性軸で照らす** | MAP-Elites「Diverse Prompts」(Santos et al.) | 単一性能スコアでなく多様性グリッド上に個体配置 | genome 多様性指標の定義 |
| **Score Matrix + Reflective Mutation** | GEPA (genetic-pareto) | 入力タイプ別性能を保持する Score Matrix + 自然言語 reflection で prompt 進化 | 単一 redeem 実績だけの promotion gate の代替（多次元評価） |
| **Archive + 親再利用** | HGM（Huxley-Gödel Machine, CMP指標, Wang et al.） | 過去候補を archive し親選択で再利用 | 実績ゼロ個体を即淘汰しない |
| **経験共有** | Group-Evolving Agents (GEA) | 複数 loop 間で経験共有 | Franklin 群の相互学習 |

## 我々の cold-start への copy+tweak（ランク付き、詳細は [[14-cold-start-escape-BP]]）

1. **【最優先】backtest-bootstrap**（PolyEvolve 型）: 歴史 corpus を offline 再生し、同じ
   `decideEngagement` で would-engage 数を出し、rubric（非退化・多様性）を通った genome を
   **exploration seed** に昇格（**baseline には触れない** = money-safety）。
   ※ simulated-P&L は使わない（tautological と判明、削除済）。
2. **【次】非対称強制探索**（openevolve `_sample_parent` + DGM `score_prop`）: 飢餓検知（N 連続 skip）で
   mutation を bottleneck knob の loosen 方向に強制、最初の1 trade で自己リセット。決定論的 bookkeeping。
3. **【安価】near-miss trace を population data に**（OpenEvolve の「0点 attempt も population 化」）。

## 正直（hype vs real、[[14-cold-start-escape-BP]] と [[15-agent-economy-landscape]] より）

- OpenEvolve/AlphaEvolve/DGM は**安価・決定論的な evaluator を持つ領域**（backtest Sharpe、code の test）で
  genuine な改善を出す。**live trading（実 fill・実時間・rare reward）で戦略が自己改善した repo は皆無**
  （Numerai は人間クラウドソース、FinRL/FreqAI は retraining あるが live-money 実証なし）。
  = **我々の self-fix harness が既存事例より一歩先を狙う world-frontier**。だから難しい。

## 出典
openevolve(algorithmicsuperintelligence/openevolve), dgm(jennyzzt/dgm), ADAS(ShengranHu/ADAS),
GEPA, Reflexion/Self-Refine, HGM(Huxley-Gödel Machine), MAP-Elites Diverse Prompts(Santos et al.),
Multi-Agent Debate(Liang et al.), LayerX Zenn: https://zenn.dev/layerx/articles/b36ceffe6b5e20 +
https://zenn.dev/layerx/articles/9f25ec86a31730。
