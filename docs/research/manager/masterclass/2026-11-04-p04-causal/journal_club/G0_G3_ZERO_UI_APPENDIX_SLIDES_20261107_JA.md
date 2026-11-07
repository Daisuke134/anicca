# 研究発表追加5枚｜Manager Zero-UI G0〜G3（2026-11-07）

これは発表用の原稿と日本語Speaker Notes。既存の34枚講演本編と134枚研究アーカイブPPTXは書き換えない。配信用スライドの更新は独立したPPTXビルド受入が必要。

## Slide 1. UIがないことと秘密の監視は違う
**表示：** Zero UI, zero repeated prompts, no covert personal surveillance.
**読み上げ：** Managerの製品設計は「利用者が追加アプリを開かない」であり「知らない人の履歴を無断で集める」ではない。既存の合法なホスト権限・データ目的・撤回を尊重する。Public aggregateの初期Shadowだけなら個人識別は不要。実介入は未許可なのでNO_ACTION。
出典：Apple App Review 5.1.1, NIST AI RMF1.0。

## Slide 2. 4種類の人間由来評価を一つの契約で実行
**表示：** Nature RMSE .12008→.08026 (exploratory); MaMe-Re .18460→.18469 (worse); HBCP MAE9.9868→9.9247 (CI crosses zero); Qwen text-only 10/18 vs historical 11/18.
**読み上げ：** 4種類の異なる単位を統一スコアにしない。実データとモデルforward passを分ける。Study/Context Holdoutが必要。成功と失敗を両方残す。
出典：正式Manager P09 source, GitHub Actions 42379471598, HBCP.

## Slide 3. 実データで重みを学習して、正しく不採用にした
**表示：** HBCP StudyArm Ridge v0, 405 studies, 971 arms, 283 train/40 calibrate/82 test studies, weights=93. Test MAE mean=10.128, Ridge=10.719, difference=-0.591pp.
**読み上げ：** 実学習したモデルは重みと前処理を再ロードして推論できる。しかしモデルを訓練するだけでは本番出荷にならない。単純ベースラインに負けたため研究用のまま留保した。
出典：G2 weight/metrics pinned real source.

## Slide 4. Zero UI P0 Shadow: dry-runだけ
**表示：** Public aggregate → archived trained model → verified offline fixture gate → NO_ACTION receipt. Notifications=0, Writes=0, Personal profiles=0.
**読み上げ：** 正式なホスト権限・モデル・アウトカム監査がないと新しい介入はできない。現在のP0は公開介入群の資料で計算だけを行う。不可視の人間監視にしない。
出典：manager_core.zero_ui_shadow_v0, AuthorityVerifier.

## Slide 5. Model × Eval × Product の次のゲート
**表示：** G1 eval regression → G2 actual shared encoder/head with superior heldout score → G3 authorized host read-only connection → G4 bounded opt-in intervention → G5 human benefit/harm RCT → G6 deploy+cost+external replication.
**読み上げ：** 会社側には人間の繰り返し操作が不要でも、元データへの正当な権限、説明責任、停止・撤回が必要。究極の目標は「AIの魔法」ではなく、外部証拠のある社会への便益。
出典：Manager Product Contract v0.1; ROADMAP_STATUS_JA.
