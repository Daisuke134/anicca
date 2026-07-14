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

## 第2調査（別 subagent、trading ドメイン一致重視）— 結論は整合、統合案が具体化

`paperswithbacktest/pwb-alphaevolve`(124★, 10ファイル程度)= AlphaEvolve を **backtrader 戦略×KPI gate** に応用。
ドメインが我々(trade × on-chain P&L gate)と1:1一致。Controller の parent選択(elite/exploit/explore)
と KPI evaluator パターンを copy。小さく copy+tweak しやすい。汎用 archive が要るとき OpenEvolve(6706★)の
database.py/controller.py(MAP-Elites+islands)を横に見る、で両調査は同じ結論。

**既存 evolve.mjs を捨てず evaluator として温存する統合案（実読ベース）**:
1. 評価器 = 現行 `evolve.mjs::summarizeByGenome`（on-chain 実現益 gate、無改造でそのまま使う）
2. archive 化 = `genome-override.json` を単一 genome → **候補配列**にし、DGM の score_child_prop
   (score × 1/(1+children)) で親選択（今は「baseline vs 1 mutant」の単一系統 = 最大の弱点）
3. 変異 = `mutate()` の random walk を、履歴(genome_id, realized_usdc)を meta-prompt に埋めて
   **LLM に次の値を選ばせる**(OPRO 型)に置換。clamp 範囲は既存 MUTATION_SPEC のまま
4. code 自己改変 = pick.py / PRODUCTS 表への LLM patch を、**同一の evaluatePromotion バー
   (絶対 net-positive + baseline 超え)** を課した別 promotion 経路として追加（既存 gate を壊さない）

DGM archive 設計と OPRO 変異と pwb の Controller = 3つを既存 gate の上に足す = 最小改修で SOTA に寄せる。

## TODO 化
- [ ] pwb-alphaevolve の Controller + KPI evaluator を copy、evaluator に evolve.mjs::summarizeByGenome を差す
- [ ] 最初の適用先 = 最も安全な x402 seller（evaluator = sales.jsonl × on-chain settle）→ 次に PM/SOL trade
- [ ] genome を単一→候補配列(archive)化 + mutate を OPRO 型に置換。既存 evaluatePromotion gate は無改造で温存
- [ ] 動いてる PM trade を壊さない（新経路を並行で立ててから切替判断）
