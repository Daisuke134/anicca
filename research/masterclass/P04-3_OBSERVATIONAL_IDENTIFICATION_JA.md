# P04-3｜観察データから因果効果を推定する

最終更新: 2026-11-04。教育用の数値例。実在ユーザーへの通知は送信していない。講義の完了と、実世界でのManagerの介入効果の実証は別。

## 0. 今回の問い
予測は P(Y|A)、介入効果は P(Y|do(A))。RCTが行えない場合、観察された処置AとアウトカムYの関係から、どの仮定によって E[Y(1)-Y(0)] を識別できるか。

## 1. 識別が推定に先行する
対象集団、処置A、対照A=0、アウトカムY、介入時点、観測期間、処置前共変量X、推定対象（ATE/ATT/CATE）を事前定義。DAGにより調整集合を選ぶ。consistency / conditional exchangeability (Y(0),Y(1)) ⟂ A | X / positivity 0<P(A=1|X)<1 等を吟味する。処置後の媒介因子やコライダーを不用意に調整しない。未測定交絡が残れば統計モデルを高度化しても識別できないことがある。

## 2. 完全架空のSimpson's paradox例
対象者2,000人。購買意欲が高い1,000人、低い1,000人。通知ありA=1と通知なしA=0。

| 意欲 X | 通知あり人数 | 通知あり購入率 | 通知なし人数 | 通知なし購入率 |
| --- | ---: | ---: | ---: | ---: |
| 高 | 900 | 40% | 100 | 50% |
| 低 | 100 | 10% | 900 | 20% |

単純比較: 介入群=(900*0.40+100*0.10)/1000=37%、対照群=(100*0.50+900*0.20)/1000=23%。観察上の差は +14ポイント。
しかし同じX内の差は高意欲40−50=−10ポイント、低意欲10−20=−10ポイント。全対象集団の高/低割合は50%ずつなので、適切な調整後の差は −10ポイント。これは例で設定した潜在的結果モデルと識別仮定が正しい場合の因果効果である。
逆転の原因: 購買意欲Xが通知割当Aと購入Yの双方に影響する交絡。

## 3. G-formula / Outcome regression
m_a(x)=E[Y|A=a,X=x] を推定し、E[Y(a)]=E_X[m_a(X)] と標準化する。
ATE_hat=平均_i[m_1(X_i)-m_0(X_i)]。
架空例: E[Y(1)]=0.5*0.40+0.5*0.10=0.25。E[Y(0)]=0.5*0.50+0.5*0.20=0.35。ATE=-0.10。
線形回帰・ロジスティック回帰・ニューラルネットなどを使えるが、交絡調整とモデル適合は別問題。

## 4. 傾向スコア・IPW
e(x)=P(A=1|X=x)。例では e(高)=0.9、e(低)=0.1。
ATE_hat_IPW = (1/N) Σ[A_iY_i/e(X_i) − (1−A_i)Y_i/(1−e(X_i))]。
架空例: 通知ありの重み付け成功数=(900*0.40/0.9)+(100*0.10/0.1)=500。通知なし=(100*0.50/0.1)+(900*0.20/0.9)=700。N=2000なので差=(500−700)/2000=−0.10。
傾向スコアが0や1に近い場合は極端な重み・分散増大・実質的なoverlap欠如に注意する。重みの分布や有効サンプルサイズを確認する。

## 5. Matching
処置前のXまたはpropensity scoreが近い者を比較する。Balance診断（standardized mean differences, SMD）、マッチできなかった人数、ATE/ATTの変更可能性を明示。未測定交絡は解決できない。

## 6. AIPW（Augmented Inverse Probability Weighting）
ATE_hat_AIPW=(1/N)Σ[m_1(X_i)−m_0(X_i)+A_i(Y_i−m_1(X_i))/e(X_i)−(1−A_i)(Y_i−m_0(X_i))/(1−e(X_i))]。
条件付き交換可能性・positivity等の仮定に加え、通常の正則性条件下で、propensity modelまたはoutcome modelのどちらかが正しく指定されれば一致性がある。未測定交絡は救済しない。機械学習を使う場合はcross-fittingを推奨。

## 7. Difference-in-Differences (DiD)
DiD=(処置群の事後−事前)−(比較群の事後−事前)。
架空例: 処置群20%→35%、比較群15%→20%なら (35−20)−(20−15)=+10ポイント。
条件は、処置がなかった場合の平行トレンドなど。事前トレンド、先取り行動、同時介入、時点の異なる処置導入、構成変化も検討する。

## 8. 現実のManagerへの研究プロトコル
- [ ] 対象・時間窓・処置・比較・アウトカム・estimand・ガードレールを定義。
- [ ] DAGと必要な処置前交絡因子を記録。
- [ ] データ利用権・欠測・時系列分割・リークを確認。
- [ ] Positivity、SMD、重みの分布、予測性能の診断。
- [ ] G-formula / IPW / AIPWを同じ対象estimandで比較。
- [ ] 信頼区間、感度分析、負の影響、前向き検証を記録。
- [ ] 高精度の行動予測と、因果推定の正しさを区別。
- [ ] Manager選択施策と強いベースライン選択施策の意思決定価値を別途比較。

## 学習確認
1. 観察比較は+14ポイント、因果効果は−10ポイントとなった理由は？
2. IPWは何を重み付けし、e(X)=0.001では何が起こる？
3. AIPWのdouble robustnessが救わないものは？
4. DiDの平行トレンド仮定を破る例を挙げる。
5. ATE, ATT, CATEはそれぞれどの集団・条件への効果か？

## 参考
- Hernán & Robins, Causal Inference: What If, https://www.hsph.harvard.edu/miguel-hernan/causal-inference-book/
- Rosenbaum & Rubin (1983), The central role of the propensity score
- Augmented Inverse Probability Weighting and the Double Robustness Property, https://pmc.ncbi.nlm.nih.gov/articles/PMC8793316/

関連資料: P00_P12_FULL_ROADMAP_AND_STATUS.md, P04_SLIDES_APPENDIX_JA.md
