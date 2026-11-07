# Phase 8: P08-3〜P08-5 研究補足スライド原稿（2026-11-06）
**状態：スライド原稿と日本語発表者ノートのみ作成。118枚の研究保存版PPTX/PDFへは未組込、既存34枚の本番版は変更しない。** 実PPTX/PDFの更新はCodex側のレンダリング・検証工程。根拠は P08-3_JA.md、P08-4_JA.md、P08-5_JA.md に詳述。

## Slide 1｜Phase 8: Learn to act, learn to abstain
表示：Prediction ≠ Causal Effect ≠ Policy Value。P08-1 Safety → P08-2 MRT → P08-3 Bandit → P08-4 MDP/POMDP → P08-5 Clinical/Research Gate。注：BFMとPolicy、Executor、Evaluatorを分ける。真の人間便益は未測定。

## Slide 2｜Explore versus exploit
表示：3 arms, unknown reward rates; epsilon greedy / UCB / Thompson Sampling。注：学習者には分かりやすい成功率の玩具例。成功率20/50/70%は説明用で、人間データではない。探索する権限と安全な行動選択は別。

## Slide 3｜Contextual bandits
表示：context x_t → A_safe(x_t) → π(a|x_t) → observed reward。注：停止・撤回はBandit armではなくhard gate。遅延と欠測のログを保つ。LinUCB/Linear TSはMABWiser既存実装で比較。Source: https://fidelity.github.io/mabwiser/

## Slide 4｜Offline policy evaluation
表示：IPS = Σ[π_e(a|x)/π_b(a|x)]r/n; DR=DM+weighted residual; ESS。注：元割付確率とsupportが不可欠。配信状態を無作為割付と混同しない。Source: https://www.microsoft.com/en-us/research/publication/doubly-robust-policy-evaluation-and-learning-2/

## Slide 5｜From bandits to sequential decisions
表示：Today action → Tomorrow state → Future reward。注：短期の成果だけを最大化すると通知疲れを見逃す。数値例 +5 today / -8 future は人工。MDPの導入。Source: https://mitpress.mit.edu/9780262039246/reinforcement-learning/

## Slide 6｜MDP state, policy and Bellman equation
表示：MDP=(S,A,P,R,γ)、V*(s)=max_a E[R+γV*(S')]。注：StateのMarkov性は仮定。将来の結果は実証しない限り推測。割引率は価値観の正しさを認定しない。

## Slide 7｜POMDP: do not pretend to read minds
表示：Hidden S → Consented O → Belief b(s) → Safe choice; b'=ηZΣTb。注：推定状態は真実や診断ではない。観測不足ならNO_ACTION。Source: https://search.r-project.org/CRAN/refmans/pomdp/html/update_belief.html

## Slide 8｜Which complexity is justified?
表示：NO_ACTION / fixed / rules JITAI / LinTS / finite MDP / POMDP。注：同じ分割・アウトカム・評価条件で比較。シミュレータでの勝利は人間での便益を証明しない。

## Slide 9｜Oralytics: deployed algorithm, not blanket efficacy
表示：2 decision points/day, 70 days, 79 enrolled, 72 analyzable (7 data issue), weekly update。注：2025設計論文と2026監視論文を区別。単群では無介入比較の因果効果は証明できない。Sources: https://pmc.ncbi.nlm.nih.gov/articles/PMC12122013/ ; https://www.nature.com/articles/s41746-026-02669-4

## Slide 10｜Consent, withdraw, harm
表示：Goal consent / data permission / notification permission / research consent ≠ each other。注：日本の2026-08改正倫理指針の施行は12月1日、現時点は未施行。EU GDPR/AI Act、US Common Ruleは適用法域と用途を見て判定。Sources: https://www.mhlw.go.jp/stf/newpage_75864.html ; https://www.hhs.gov/ohrp/regulations-and-policy/guidance/faq/informed-consent/index.html

## Slide 11｜Monitor and fallback
表示：Green normal; Yellow freeze learning/no action; Red stop/refer + incident reporting。注：2026年npj Digital MedicineのOralytics/MiWaves事例を再利用。ソフトの監視自動化は倫理審査・研究責任者の代替にならない。Source: https://www.nature.com/articles/s41746-026-02669-4

## Slide 12｜ManagerBench acceptance ladder
表示：B0 synthetic scorer → B1 real public study → B2 model comparison → B3 policy OPE (if identified) → B4 approval+limited research → B5 independent welfare outcome。注：P08-3/4/5は講義・設計完了、実装・人間の効果は未測定。NO_ACTION is an outcome of sound decision making, not a failure.

## 次のCodex作業（ここでは未実行）
118枚研究版の既存ソース、全スライドのspeaker notes、PDFとの整合を確認。既存内容を壊さず末尾に12枚追加し、日本語ノート・引用を反映。PPTX/PDFを再生成して全頁を検査し、実ページ数とハッシュを報告。**34枚の本番版は変更しない。** メタデータや証拠の数値を、研究計画の数字と取り違えない。
