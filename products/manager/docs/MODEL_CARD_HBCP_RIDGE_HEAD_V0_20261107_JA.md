# HBCP Ridge Head v0 — 実人間由来の研究介入群アウトカム予測モデル

## モデルの実体と用途
2026年11月7日に、公開のHuman Behaviour-Change Project禁煙介入RCTの介入群単位集約データ（405研究・971群）で**実際に学習した93特徴のRidge回帰モデル**。出力は研究の禁煙成功率（0〜100%、百分率ポイント）。独自の大規模Behavior Foundation Model、特定個人の禁煙確率、治療、心理診断、個人への介入効果ではない。開発用G2モデルであり、**実ユーザーへの推論や製品介入は承認されていない**。

- 重み：docs/research/manager/verification/HBCP_TRAINED_HEAD_V0_20261107.json （モデル重みと訓練済み変換パラメータ、個票はなし）
- trainer/predictor：products/manager/evals/hbcp_train_v0.py
- 元データ：https://raw.githubusercontent.com/HumanBehaviourChangeProject/semantic-prediction/main/data/hbcp_gen.csv
- 元データSHA256：eec4ba6ffc51961fda1308f690a97a60111d93858fa67ca19ffd4392fd49679b
- 権利：HBCPの関連論文が元DataをCC0 1.0として公開（https://pmc.ncbi.nlm.nih.gov/articles/PMC12603517/）。この実装は公開集約データを使用し、元データ行をGitへ再配布していない。
- head SHA256：a555054355038b8dc0072cb3f1999829ad8bd7a81128322d0ad68f0dfd1c36a7
- 観測単位：study-arm aggregates。機械学習の93特徴は原著RuleNNの82 ontology特徴と完全には一致しない。
- テスト対象：283研究train / 40研究calibration / 82研究test（対象群数689 / 85 / 197）。SHA256で分割固定。前処理・係数はTrainだけで学習。calibrationは別セットの残差にだけ使用。
- 未使用82研究197群：訓練平均MAE **10.12781pp** / Ridge **10.71865pp**。Ridge改善 **-0.59083pp**（悪化）。研究単位500回Bootstrap区間 [-1.4121, +0.3459]。より複雑なモデルの優位性は未実証。
- 推論だけなら保存JSONをロードして可能。ただし製品用の有効性・公平性・安全性・権限・人間便益は不明。

## 製品採用の判断
**NOT PROMOTED — research only**。平均だけを返すベースラインより未知研究で悪かったため、採用を拒否。臨床的行為・禁煙治療・人間の同意不要な推論・通知・経済行為に使用しない。

## 次のモデル実装
複数行動領域の合法なデータと独立holdoutを用いた共有Encoder/各領域Headを学習し、専門モデルより実際に改善するか検証する。外部人物・文化・時点・研究に対する汎化、校正、NO_ACTION/害に加え、推論費用を比較する。
