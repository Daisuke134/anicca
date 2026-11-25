# 自然言語の反応を確率分布に変換するとき、曖昧さを隠さない

2026-11-25 | Anicca Manager research note | preliminary / not fully validated

**TL;DR.** 合成5次元の応答と単位アンカー、公式関数本体の転記を実行。epsilon=0で等類似度とゼロベクトルはNaN、.001で等類似度は先頭に偏る。5件のguardテストが成功。

## 問題
未定義の反応を中立やゼロとして集計すると、存在しない根拠が生まれる。

対象読者：行動モデルと介入評価を実装する研究者・開発者。Pythonと基礎統計を前提とする。

## 方法・再現
合成5次元の応答と単位アンカー、公式関数本体の転記を実行。epsilon=0で等類似度とゼロベクトルはNaN、.001で等類似度は先頭に偏る。5件のguardテストが成功。

```bash
python -m unittest discover -s files/eval/managerbench -p test_ssr_guard.py -v
```

[出典・既存実行レシート](https://github.com/Daisuke134/anicca-ops/blob/main/files/eval/managerbench/ssr-upstream-boundary-audit-2026-11-25.md)。Concordia以外は過去の保存結果の再確認で、今回の新規再実行ではない。

## 結果
![測定図](./02-ssr-chart.svg)

図1：ローカルテスト件数、2026-11-25の実験。分母・範囲は上記方法を参照。

| 条件 | 値 |
|---|---:|
| 成功 | 5 |
| 失敗 | 0 |

## 接続の設計
![接続図](./02-ssr-pipeline.svg)

図2：既存Managerへの接続候補。概念図であり、本番実装を示さない。

## 限界・トレードオフ
公式パッケージ、埋め込みモデル、実人間評定は未実行。ライセンス記述差を要確認。保存済みテストは当時の実行ファイルと同一ではない。 低コストな部品テストで問題を絞れるが、E2Eの代わりにはならない。

## 次の実験
公式環境と人間の独立評定を通し、分布・信頼性を評価する。

[公式資産](https://github.com/pymc-labs/semantic-similarity-rating) · [実装・レシート](https://github.com/Daisuke134/anicca-ops/blob/main/files/eval/managerbench/ssr-upstream-boundary-audit-2026-11-25.md) · [Master TODO](https://github.com/Daisuke134/anicca-ops/blob/main/files/master-todo-2026-11-24.md)

公開研究原稿。公式ブログのライブ公開・査読・SNS投稿は別途確認する。
