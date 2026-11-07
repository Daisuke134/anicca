# AI企業の最も重要なアルゴリズムは、モデルではなく資金配分かもしれない

*Anicca Manager Research / Phase 10-2 / 2026年11月7日。研究記事ドラフト・未公開。*

AI企業を作るとき、最も刺激的な投資対象は最新のモデルかもしれない。しかし企業にとって必要なのは「世界最高のモデル」だけではない。限られた現金で、そのモデルが本当に顧客へ価値を届けられるかを検証することだ。

## 探索と活用は経営の数学である
Machine LearningにはExploreとExploitという有名なトレードオフがある。新しいモデルを調べるのは探索。すでに検証できた製品を顧客に届けるのは活用だ。Bandits with Knapsacksの研究は、報酬の不確実性に加えて予算制約を扱う。実務ではさらに、許可範囲・キャッシュリザーブ・安全性・データ権利という制約がある。

たとえば、行動モデル学習に資金を使う前に、オープンな小型モデルや既存Qwenで同じ未見データを評価する。その結果「追加学習は不要」とわかれば、GPU支出を防げる。むしろこの「不要と判明する情報」自体が価値を持つ。

## 情報の価値を評価する
Value of Information（VOI）の基本は、追加実験によって将来の選択がどれだけ改善するかを測ること。期待完全情報価値EVPIは上限、実際の研究設計にはEVSI（期待サンプル情報価値）を使う。ENBS＝EVSI−実験費用で、研究が合理的か検討する。ただし、正確な分布・効果・資金効果を推定するデータがなければ、計算値を本当のROIと呼べない。

FinOps Foundationの2026年のAI向け実務ガイドも、AI費用をモデルAPI・GPU・SaaS・運用へ配賦し、1トークンではなく成功した業務1件の費用を見よと提案する。利用件数が伸びても、失敗と再試行で利益が減れば拡大すべきではない。

## Managerの提案
私たちは、予測器と予算配分を独立のソフトウェア層として設計する。モデルは提案を出す。資金上限・許可・収益証拠・停止条件を評価する制御層はモデル出力に影響されない。権利のないモデルの期待スコアが高くても除外する。

Phase 10-2で行ったのは完全合成プロトタイプの予算制約テストである。実際のAniccaの投資成績や顧客利益を測定したわけではない。次は、既存の正本へ読み取り専用で接続し、支出と価値を確かめることだ。

### Sources
- FinOps for AI (2026): https://www.finops.org/wg/finops-for-ai-overview/
- Bandits with Knapsacks: https://arxiv.org/abs/1305.2545
- Resourceful Contextual Bandits: https://proceedings.mlr.press/v35/badanidiyuru14.html
- Value of Information methods: https://pmc.ncbi.nlm.nih.gov/articles/PMC7373630/
- FinOps Budgeting: https://www.finops.org/framework/capabilities/budgeting/

*公開前に経済数値・比較対象・ライセンス・出典・実測と推測の区別を再点検する。*