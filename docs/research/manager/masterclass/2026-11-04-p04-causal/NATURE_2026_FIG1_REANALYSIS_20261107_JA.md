# Nature 2026 Figure1 公開データの独立再解析 — 実行レシート
2026-11-07 JST。User-requested Stage 7.1. **部分達成：公開Source Data Fig.1を取得して独立Python解析を実行。元RDS個人回答と元Rの全実行は未達**。

## 実際に何を実行したか
1. 論文の公式Source Data Fig. 1、MediaObjects/41586_2026_10742_MOESM4_ESM.xlsxのpanelAを取得・抽出。panelBに著者側のモデル別集約値があることも確認。
2. 表の7列（study、reference_condition、outcome.name、condition.name、estimate、prediction、group）を正規化してMac miniの隔離一時フォルダにCSV保存。個人単位の原記録ではなく公開図表の**集約効果行**。公開GitHubへCSV個票・図表原表は再配布しない。
3. Mac mini上のPython標準ライブラリにより相関、RMSE、MAE、校正傾き、研究単位bootstrap、1研究除外、研究holdout校正を**実際に再実行**。入力CSVのSHA256はJSONで固定。
4. 人工fixtureの9ユニットテストを実行。9/9成功。ネットワーク認証のある個人データ取得や、新しいAI推論・実験対象者への介入は行っていない。

## 結果
| 対象と指標 | 今回の計算 |
|---|---:|
| 集約データの研究数 | 70 |
| 方向付き比較行 | 3,356 |
| 逆向きペア（重複の対） | 1,678 |
| 全比較行での単純Pearson | 0.8051489 |
| 全比較行でのRMSE | 0.1183468（割合単位） |
| MAE | 0.0817313 |
| 実際の効果をモデル予測値で回帰した傾き | 0.5512409 |
| 研究クラスタbootstrapのPearson 95%区間（2,000回・固定seed） | [0.5973, 0.9093] |
| 1研究除外のPearsonの範囲 | [0.7048, 0.8326] |
| 69研究で校正して1研究を評価するLOSOのmicro RMSE | 0.1183468 → 0.0814526 |
| LOSOで改善・悪化した研究数 | 56改善・14悪化 |
| 研究等重みのmacro RMSE | 0.0780281 → 0.0503598 |

百分率ポイントとして表示する場合は各結果を100倍する。**この探索的な統計は、著者のRで再現した正式な推定結果ではない。**

## なぜNature公式数字と異なるか
- Fig1 panelAには各研究の複数条件の方向付き比較（向きを反転した重複を含む）が3,356行存在。これは論文の469効果と同じ独立観測単位ではない。
- 原著のFigure1 panelBはGPT-4についてraw correlation=0.8507895、adjusted estimate=0.9151266を示す。
- 我々の0.8051はpanelA全行等重みの記述的Pearson。著者の正規化・研究単位の重み付け、調整済み相関推定方法とは同一ではない。
- だから「0.8051が再現できた＝Nature原著の相関0.85を再現した」とは宣伝しない。

## 標本・方法上の制約
同じ研究から複数の比較を作ることで行数は増えるが、独立した研究数は増えない。各ペアの逆向きはほぼ数値が符号反転したもの。研究単位で再標本化した区間は、研究間変動を確認する簡易評価であり、正式な潜在変数モデル/測定誤差調整ではない。

LOSOの改善は「元LLMの未知研究予測に新しい因果能力が生じた」という主張ではない。**古い公開予測の線形補正器だけを、研究を分けて後付け評価した**もの。元のGPT-4の事前学習で実験が既知だった可能性は、今回の分割では除去できない。

## 残るブロッカーを実地で確認
Code Ocean v1の/public browserで、data/rct_responses.RDS、data/llm_responses.RDS、code/0_minimal_example.Rの名前とサイズは確認できるが、元の個別ファイルのダウンロードとエクスポートにはログインが必要。TinyFishブラウザーで確認したが公開匿名の正規ダウンロードリンクは見つからず、認証の迂回をしていない。
接続Mac上にRscriptはなく、元Rの最小スクリプト・全解析実行は未実施。アーカイブREADMEによると最小例は数分、全解析は数時間規模だが、これは著者の目安であり実行した時間ではない。
既存のRDSを合法に取得できる正規アクセスが整うまでは、完全な元結果・新しいLLM個人応答を再現済みと主張しない。

## 参照・再現
- 論文 DOI: https://doi.org/10.1038/s41586-026-10742-x
- 元の公開データ・解析: https://codeocean.com/capsule/9843791/tree/v1
- Source Fig1: https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41586-026-10742-x/MediaObjects/41586_2026_10742_MOESM4_ESM.xlsx
- 実行ソース: experiments/p09_1_nature_fig1_reanalysis.py
- テスト: experiments/test_p09_1_nature_fig1_reanalysis.py
- 独立計測レシート: evidence/P09-1_NATURE_FIG1_RESULT_20261107.json
- 実行例（入力は公式panelAを上記列名のCSVへ変換し、同一データ行を保つこと）：

    python3 experiments/p09_1_nature_fig1_reanalysis.py --input /private/path/figure1_panelA_effects.csv --output /private/path/result.json --seed 20261107 --reps 2000

データ再配布・商用派生についてはファイル別の使用条件を点検する。コードと科学論文本文の著作権は別。

## P09-1への教訓
初見の研究を正しく評価したいなら「研究の全行」をholdoutする。個人・ネタ・時期・文化の異なる汎化を同じスコアにまとめない。単純な相関だけでなく、効果の大きさ・不確実性・研究間の依存・時刻のリークを検査する。実際の人間への介入の便益は、さらに別の無作為化や同意/安全性が必要。
