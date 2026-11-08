# 行動AIの最大の問題：予測が当たるほど、世界が変わる

*Anicca Research / Manager Masterclass P12-4 / 2026年11月8日。研究記事ドラフト・未公開。*

あるAIが「午前9時に通知すると、多くの人が行動する」と予測する。その判断に従って大勢に通知すると、数週間後には人々が通知に慣れ、反応しなくなるかもしれない。

モデルが世界を予測し、その予測で世界に介入すると、**予測対象の世界そのものが変わる**。

この問題を、2020年のPerdomoらはPerformative Predictionと呼び、予測器を運用した結果生まれる新しいデータ分布を考える理論を示した。

## 過去の評価セットでは見えないこと

通常の機械学習は、固定した分布の中で誤差を最小化する。しかしAIが推薦・通知・価格・行動方策を変えると、その行動によって利用者が適応する。

入力の割合が変わるCovariate Drift、反応規則自体が変わるConcept Drift、モデルの更新やパーサー変更による計測Driftは異なる現象だ。

入力が変わっても予測性能は変わらないかもしれない。逆に入力分布が同じでも、結果が変わって予測が外れることがある。

## 分布変化はJensen–Shannon Divergenceで検査できる

例えば2選択の元の割合を50%・50%、新しい割合を90%・10%とする。2つの分布を比べる指標の一つがJensen–Shannon Divergence（JSD）だ。同じ分布ならゼロ、異なれば正となる。

ただし小さなサンプルや季節変動だけでもJSDが揺れる。分布の変化を見つけることと、モデルが悪くなったことを証明すること、介入が原因で変わったと特定することは、どれも別だ。

## 自動再学習ではなく、継続的な反証

Managerが新しい候補モデルを作ったら、以前の単純なBaselineや稼働モデルと、人物・研究・文化・時期を分けた未見データで比較する。新モデルが一部で改善しても、別領域の負の転移や確率校正の悪化、負担・害の増加があれば採用しない。

さらに、ラベルがまだ取得できない時点では「実性能は不明」と表示すべきだ。ユーザーの反応が未計測なのに「成功0」や「成功100%」に置き換えてはいけない。

安全で必要な権限・同意・費用上限を満たした範囲でのみShadow比較や限定リリースを行い、結果は外部の情報で独立確認する。

## 研究の終わりはどこにあるか

新しい言語・文化・社会制度・生活環境が出現する限り、人間行動の予測・介入に関する研究は終わらない。

Phase 12はカリキュラムの最終章だが、真に重要なのは、**新しい証拠が出たときに自分たちの主張を更新し、間違いを認め、より良い方法を検証できる研究体制**を作ることだ。

### 一次資料
- [Perdomo et al., Performative Prediction (ICML 2020)](https://proceedings.mlr.press/v119/perdomo20a.html)
- [Google Cloud, Model Monitoring](https://docs.cloud.google.com/gemini-enterprise-agent-platform/machine-learning/model-monitoring/overview)
- [NeurIPS Paper Checklist](https://neurips.cc/public/guides/PaperChecklist)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [CONSORT 2025](https://www.bmj.com/content/389/bmj-2024-081123)

*本稿の例は概念上のシナリオ。Managerの実際のドリフトや人間への便益・害を測定したという主張ではない。AI執筆支援を利用した未公開ドラフト。*
