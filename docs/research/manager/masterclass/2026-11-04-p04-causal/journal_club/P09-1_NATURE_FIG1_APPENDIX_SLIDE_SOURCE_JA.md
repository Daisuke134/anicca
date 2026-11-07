# P09-1 Nature 2026：研究補足4枚のスライド原稿
2026-11-07。既存34枚本番・118枚保存版は未変更。新規4枚は教材原稿のみ、PPTX/PDFへの組込みは未実施。

## Slide 1｜何を未知として残すか
Person / Study / Time / Domain の四種類。研究IDや同じネタ系列がtrain/testをまたがないこと。話者ノート：同じ人や類似刺激をランダム分割しても未知研究への汎化にならない。

## Slide 2｜Nature Figure 1：公開データを別実装で再計算
70 studies, 3356 directed contrasts, 1678 reverse pairs。全行等重みr=0.8051、RMSE=11.83pp。話者ノート：著者の正式panelB raw r=.8508, adjusted r=.9151とは解析対象が違う。独立参加者3356人と呼ばない。

## Slide 3｜Leave-One-Study-Out
69研究train / 1研究test ×70回。探索的な線形校正でmicro RMSE 11.83→8.15pp。56研究改善/14悪化。話者ノート：モデルの事前学習データの汚染を解消した証拠ではない。公開された効果を用いる後付けの校正実験。

## Slide 4｜何を実行したか・していないか
PASS：Source Fig1取得、Pythonによる独立計算、研究クラスタbootstrap、9件のテスト。NOT_DONE：元の個人RDSダウンロード、元Rによる完全再現、調整済み推定の独立再計算、新モデル推論、人間対象試験。話者ノート：Code Oceanの個別データエクスポートは認証が必要。次P09-2ではゼロショット/少数例適応を学ぶ。
