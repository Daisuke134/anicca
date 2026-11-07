# P12-1全16枚・日本語発表ノート

## Slide 01｜P12-1の研究目的

P12-1の研究目的

Phase9-11ではモデルの予測/選択/社会/協調/転移を学習。P12-1で第三者が評価できる証拠へ。CI成功は科学的追試ではない。

参考：ACM/NeurIPS artifact evaluation
実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。

## Slide 02｜3つの異なる再現性

3つの異なる再現性

ACMのバッジは論文審査等で評価されるものであり、著者が単独で自称しない。分野間の用語差にも注意。

参考：ACM Artifact Badging 2026
実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。

## Slide 03｜論文の『SOTA』をClaim Cardにする

論文の『SOTA』をClaim Cardにする

claim_id、data SHA、model SHA、code SHA、評価時点、分母、欠測、権利、baselineを最低限保存。

参考：NeurIPS Checklist; Model Cards
実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。

## Slide 04｜行動予測はAccuracyだけではない

行動予測はAccuracyだけではない

尺度の違う予測スコア・心理尺度・収益を一つの世界共通Accuracyへ合算しない。

参考：BehaviorBench; Causal inference
実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。

## Slide 05｜Data Leakageを可視化

Data Leakageを可視化

行数nが多くても独立人が少数なら信頼区間を過小評価することがある。人物ID・研究IDを分割前に固定。

参考：scikit-learn GroupKFold
実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。

## Slide 06｜未知の何を検証したいのか

未知の何を検証したいのか

同一人物の繰返し測定を分割またぎにしない。翻訳/派生研究のリークも防止する。

参考：GroupKFold / LeaveOneGroupOut
実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。

## Slide 07｜クラスタ依存を考慮した不確実性

クラスタ依存を考慮した不確実性

150人×10 trialは1500の独立人ではない。confidence intervalの単位を事前定義。

参考：NeurIPS Checklist
実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。

## Slide 08｜既存Benchmarksを再利用する

既存Benchmarksを再利用する

Centaur testはgated。Be.FMのライセンスの曖昧さは商用接続前に解決すべき。

参考：Nature 2025; BehaviorBench official evaluator
実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。

## Slide 09｜OPEを元評価関数とは別に検算

OPEを元評価関数とは別に検算

Doubly Robust元実装と別実装の最大数値差4.32×10^-14。これは同一チームの内部検算。

参考：P11 synthetic research code; P12-1 evidence
実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。

## Slide 10｜負の転移を別の推定器で検算

負の転移を別の推定器で検算

共通モデルの負の転移を人工的に作った演習。実BFM/LoRA学習を行ったわけではない。

参考：P11-4; P12-1 alternate estimator
実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。

## Slide 11｜1つのSeedだけで結論しない

1つのSeedだけで結論しない

複数seedの変動は人工生成器に関する分散であり、個人Bootstrap・実心理的便益の不確実性とは別。

参考：P12-1 synthetic JSON
実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。

## Slide 12｜再現性の4段階

再現性の4段階

これはAniccaが自作した教材図。ACMの公式バッジを模倣・授与したものではない。人物がtrainとtestに混ざるリーク例も表示。

参考：ACM; original Anicca artwork
実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。

## Slide 13｜第三者へ渡すべき資料

第三者へ渡すべき資料

SHA256はバイト同一性を検証するだけ。論文の科学的正しさ・著作権/規約の正当性は別。

参考：Hugging Face Cards; GitHub Attestations
実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。

## Slide 14｜本当に第三者に検証してもらう手順

本当に第三者に検証してもらう手順

GitHub Actions成功をthird party results replicatedと呼ばない。査読の再現証拠を追加する。

参考：ACM Reproduced/Replicated distinctions
実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。

## Slide 15｜P12-1の完了と、未完了を分ける

P12-1の完了と、未完了を分ける

学習の終了は実証の終了ではない。実人間・実企業価値は別のRCT/財務証拠が必要。

参考：P12-1 research artifact
実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。

## Slide 16｜P12-1からP12-2へ

P12-1からP12-2へ

P12-1では再現可能なアーティファクトと公正なBenchmarkを理解した。P12-2は長期的な人の便益・害・社会影響。独立再現は未完。

参考：ACM/NeurIPS/BehaviorBench
実際の第三者による独立追試は未実施。今回の数値はすべて完全合成の教育例。
