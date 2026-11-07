# P09-1〜P09-5：実データ評価研究アーカイブ補足16枚（119〜134）
更新2026-11-07 JST。今回Mac上で既存118枚PPTXを読み、**元118枚の文章とノートが変わらないことを検証しつつ、新しい16枚のPowerPointと日本語発表者ノートを実生成・検査**した。ただしMacの共有ディスク満杯によりGitへのバイナリ保存が未達。再生成元ソースはbuild_p09_2_5_real_research_slides.pyへ、データはevidence/P09-2_TO_P09-5_REAL_TWO_DOMAIN_EVAL_20261107.jsonへ保存済み。既存34枚の短縮発表用は変更しない。著者の元RDS完全再現やBFM学習を完了済みと記さない。

| slide | 表示すべき中心 | 根拠 |
|---:|---|---|
| 119 | Holdout: person, study, time, domain | P09-1 |
| 120 | Nature Fig1: 70 studies / 3356 directional contrasts / 1678 reverse pairs | Source Data Fig1 / P09-1 |
| 121 | Zero-shot + Few-shot + partial pooling | MAML/Centaur/P09-2 |
| 122 | Real few-shot RMSE chart: 0.12008 / 0.08154 / 0.08026 / 0.08478 | P09-2 actual evidence |
| 123 | 36 studies: 19 improved / 17 worsened; exploratory interval | P09-2 actual evidence |
| 124 | Conformal interval and assumptions | JMLR2024/P09-3 |
| 125 | Target90 coverage: 100% / 98.54%; interval halfwidth24.25pp | P09-3 actual evidence |
| 126 | Selective risk-coverage: retained RMSE 4.81pp / 7.49pp | P09-3 actual evidence |
| 127 | Continual learning: EWC / LwF / Replay / PCGrad | P09-4 literature |
| 128 | Negative transfer: Nature RMSE 4.54→8.45pp; balanced replay6.02pp | P09-4 actual scalar probe |
| 129 | Regression tests before accepting model updates | P09-4 design |
| 130 | Two real response datasets: Nature / MaMe-Re | P09-5 sources |
| 131 | Meme test 20k pairs: historical mean0.184605 vs text ridge0.184694 | P09-5 actual evidence |
| 132 | Shared encoder only after specialist baseline evidence | HBA/OmniSapiens |
| 133 | Verified / Not verified; model-specific caveats | all evidence |
| 134 | Phase10 curriculum and existing BFM-01/INT-02 product cursor | ONE ROADMAP |

英語のスライド本体・日本語ノートの各ページ全文は実際の再生成スクリプト内で固定。CodeOceanの元の人間個票や新しいLLM forward passは未実行。既存の134枚版PPTX/PDFを配布する際は、ソースの出典・日付・研究の単位の間違いを視覚QAし、一般公開の証拠は実際の公開URLと版ハッシュに限定する。
