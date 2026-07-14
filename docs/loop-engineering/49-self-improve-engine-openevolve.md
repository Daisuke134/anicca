# self-improve engine — ゼロから再検索した結論（2026-07-14）

指示: 自作 evolve/genome を疑い、既存 repo を総ざらいして copy 対象を選べ。
調査 = selfimprove-repos subagent、gh + raw.githubusercontent 実測。関連: [[48-x402-growth-levers-and-improve-loop]]

## 結論: OpenEvolve を丸ごと copy（自作より上）

- repo: `algorithmicsuperintelligence/openevolve`（6,706★, Apache-2.0, PyPI, 活発）
- 核: "The most advanced open-source evolutionary coding agent — Turn your LLMs into autonomous code optimizers"
- 仕組み: `initial_program.py` + 自作 `evaluator.py`（任意のスコア関数）+ `config.yaml` → LLM がコードを変異 → evaluator のスコアで淘汰 → island 並列進化。
  **evaluator の score に「realized PnL / x402 売上」を差すだけで「収益を測って戦略コードを進化」エンジンになる**。`pip install` 一発、`from openevolve import run_evolution` でライブラリ呼び出し可。
- 実証フォーク: `tarsyang/quantevolve`（46★）= OpenEvolve を trading 戦略進化に応用済み。Market Data → LLM Strategy Generator → Backtester(PnL/Sharpe/MaxDD) → Strategy DB。**evaluator の書き方の設計図として写す**。

方針（[[feedback_never_combine_copy_one_winner_whole]]）: 勝者 = OpenEvolve 本体を丸ごと採用、QuantEvolve は evaluator 設計だけ写す。

## 不採用（理由つき）

| 候補 | ★ | 不採用理由 |
|---|---|---|
| Darwin Gödel Machine (jennyzzt/dgm) | 2,178 | 自己コード書き換えの本家だが eval が SWE-bench 等コーディングベンチで**収益でない**。Docker 重い。将来「engine 自体を自己書換」段階の参照に温存 |
| TradingAgents (TauricResearch) | 92,929 | マルチ agent 討論の意思決定 fw。過去収益で戦略を進化させる loop は無い。BASE 戦略の部品にはなる |
| freqtrade+FreqAI | 52,324 | LLM 不使用だが実運用最豊富。backtest/hyperopt で収益自己最適化が成熟。OpenEvolve の evaluator を freqtrade backtest に繋ぐハイブリッドも現実的 |
| FunSearch (deepmind) | 1,091 | 数式発見特化、trading 応用例まだ無し |

## 自作 evolve/genome の弱点（正直）

- 変異が **random 方向のコイン投げ**（genome.mjs の mutate）。OpenEvolve/OPRO は **LLM が feedback から次の値を推論**（OPRO 型）— こちらが上
- 変異対象が**数値 knob のみ**。OpenEvolve は**コードそのもの**を変異できる（route 追加・ロジック改良まで届く）
- ただし自作の強み = **on-chain 検証済み実現益だけを gate**（money-safety。HARD 0.24）— OpenEvolve の evaluator にこの gate を移植すれば両取り

## 採用アーキテクチャ（file レベル）

```
OpenEvolve(pip) を engine に据える:
  initial_program = 現行 BASE 戦略（x402: PRODUCTS+価格表 / trade: pick.py）
  evaluator.py    = 「直近N回の on-chain 実現益」を返す（自作 evolve.mjs の
                     summarizeByGenome + HARD 0.24 gate をここに移植）
  config.yaml     = island 並列・iteration 数
  → ベスト戦略を live/paper に反映するループ
横展開: Franklin(SOL) / claude-p(PM) / HL / x402 seller の evaluator を差し替えるだけ
```

次段階(温存): Darwin Gödel Machine = engine 自体を自己書換する層。

## TODO 化
- [ ] OpenEvolve を pip 導入 → x402 seller 用 evaluator(sales.jsonl × on-chain settle) を書く（最初の適用先 = 最も安全な x402、次に trade）
- [ ] 自作 evolve/genome は当面 PM trade で温存（動いてる物を壊さない）、OpenEvolve が回り出したら統合判断
