# P04-3｜観察データから因果効果を推定する
更新: 2026-11-04。講義用。実データでの検証結果ではない。

## 1. 識別が先
処置A、結果Y、処置前共変量X、対象集団、時間窓、estimandを定義。条件付き交換可能性・positivity・consistencyを検討。未測定交絡はモデルの高度化だけでは解決しない。

## 2. Outcome regression / g-formula
m_a(x)=E[Y|A=a,X=x]。E[Y(a)]=E_X[m_a(X)]、ATE=E_X[m_1(X)-m_0(X)]。結果モデルの誤指定に注意。

## 3. Propensity score / IPW
e(x)=P(A=1|X=x)。ATEのHorvitz–Thompson型推定値は平均[A Y/e(X) -(1-A)Y/(1-e(X))]。極端な重みは不安定。重みの分布とoverlapを点検し、正規化推定も検討する。

## 4. Matching
処置前属性が近い群を比較。標準化平均差（SMD）、重複領域、マッチ除外数、ATE/ATTの違いを記録。未測定交絡は残る。

## 5. AIPW / Doubly robust
平均[m1(X)-m0(X)+A(Y-m1(X))/e(X)-(1-A)(Y-m0(X))/(1-e(X))]。標準的条件下で結果モデルと処置モデルのどちらか一方が正しく指定されれば一致性を得られるが、未測定交絡やpositivity違反は解消しない。柔軟なML推定ではcross-fittingを検討する。

## 6. Difference-in-Differences
DiD=(処置群の事後-事前)-(対照群の事後-事前)。反実仮想の平行トレンド仮定、事前トレンド、anticipation、同時介入、処置時期の異質性を確認する。

## 7. 架空例
高意欲層では通知あり40%、なし50%。低意欲層では通知あり10%、なし20%。どちらの層も差は-10ポイント。群の意欲構成が異なれば粗比較は逆符号になり得る。正しく測定した処置前意欲で標準化すると-10ポイント。

## 8. Manager実装チェック
EstimandとDAGを事前定義→時系列分割→overlapとbalance→g-formula/IPW/AIPW→区間推定と未測定交絡感度分析→外部検証→可能なら前向きRCT。推定効果と意思決定価値を分ける。

参考: Hernán & Robins, Causal Inference: What If; Rosenbaum & Rubin (1983); Sant'Anna & Zhao (2020).
