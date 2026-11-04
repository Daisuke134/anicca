# Manager Masterclass | P04-1–P04-5 Causal Inference

- **更新日：** 2026-11-04（Asia/Tokyo）
- **学習現在地：** P04-1～P04-4は講義・架空演習が完了。P04-5は講義と合成研究ベンチマークが完了、ただし**実際の公開RCTの未見予測は未実施**。次の講義はP04-6。
- **科学的検証状態：** 今回の数字は**すべて人工・合成データ**に由来する。Manager Behavior Foundation Model 1.0の実人間での優位性、介入効果、心理的・事業的な便益を示していない。
- **P00-3：** 本番実証対象・同意・権限・停止条件は未確定。
- **講義／現在地の唯一の正本：** `ROADMAP_STATUS_JA.md`。このREADMEやJSONは進捗の代替正本ではない。

## 成果物

| パス | 内容 |
| --- | --- |
| `ROADMAP_STATUS_JA.md` | P00～P12全講義の唯一の進捗・ロードマップ |
| `P04-1_JA.md` | 観察と介入、DAG、潜在的結果 |
| `P04-2_JA.md` | RCT、ATE、ITT、区間推定 |
| `P04-3_JA.md` | 観察データの識別、g-formula、IPW、AIPW、DiD |
| `P04-4_JA.md` | CATE、効果修飾、方策価値、媒介分析 |
| `P04-5_JA.md` | 研究単位Holdout、予測凍結、ベンチマーク、OOD |
| `exercises/P04-3_SIMPSON_2000_JA.md` | 追加のSimpson手計算教材 |
| `experiments/p04_*.py` | P04-1～P04-5の教育用シミュレーション |
| `experiments/test_p04_*.py` | 全80件の単体テスト |
| `evidence/TEST_RESULTS_P04_1_TO_P04_5.txt` | 全80件成功の新規実行記録 |
| `evidence/P04-4_SYNTHETIC_DATA.csv` | 完全架空24,000人分の生データ |
| `evidence/P04-4_SYNTHETIC_RESULTS.json` | CATE・方策・媒介の結果 |
| `evidence/P04-5_*_SYNTHETIC.csv` | 人工180研究のデータ分割、Holdout、凍結予測 |
| `evidence/P04-5_FREEZE_RECEIPT.json` | 予測CSVのSHA256 |
| `evidence/P04-5_SYNTHETIC_BENCHMARK_RESULTS.json` | 人工ベンチマークの採点結果 |
| `journal_club/AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx` | **82枚**の編集可能PowerPoint（従来の74枚＋付録8枚） |
| `journal_club/AI_BEHAVIOR_JOURNAL_CLUB_JA.pdf` | **82ページ**の閲覧用PDF |
| `journal_club/SPEAKER_NOTES_JA.md` | **全82枚**の日本語発表ノート |
| `journal_club/RUN_OF_SHOW_JA.md` | 45分講演＋15分質疑、元の本編を維持 |
| `journal_club/build_p04_45_appendix.py` | 74枚版からP04-4/P04-5の8枚を追加 |
| `journal_club/export_p04_45_pdf.py` | 既存74ページPDFを保持し追加8ページを生成して統合 |
| `journal_club/sync_pptx_speaker_notes.py` | PowerPoint内部の全82枚に日本語発表者ノートを同期 |
| `evidence/P04-4_P04-5_QA.json` | 旧74枚本文の保全・ノート・PDFページ数・ハッシュの検証 |
| `MANIFEST.json` | ファイル一覧・SHA256・サイズの照合 |

## 主要結果（人工世界）

**P04-3**：架空30,000人、単純観察差+26.12ポイント、g-formula/IPW/AIPW約−10ポイント。因果仮定の成立を完全に人工世界で設定。

**P04-4**：架空24,000人、理論ATE+2.924ポイント、RCT推定ATE+2.684ポイント。4群のCATEは理論+16/+10/−4/−10ポイント。学習外9,619人で個別化方策をIPW評価し、通知なし方策に対し+6.279ポイント（近似95%区間+4.842〜+7.717）。別の連続値を用いた人工20,000人で線形媒介の総効果0.24を再現。

**P04-5**：架空180研究を90学習／30検証／同領域未見30／新領域未見30に分割。Ridgeの平均絶対誤差は同領域1.55ポイント、新領域3.99ポイント。ゼロ予測・学習平均と比較。**実在の公開RCTへの予測は0件**。

## 再現実行

Python 3.11+ / NumPy を使用。実験ディレクトリに移動して次を実行：

```bash
python3 -m unittest discover -p 'test_p04_*.py' -v
python3 p04_4_heterogeneous_effects.py
python3 p04_5_effect_forecasting.py
```

テストは2026-11-04に**80/80件成功**。内訳：P04-1 14件、P04-2 17件、P04-3 26件、P04-4 12件、P04-5 11件。単体テストの成功は研究コードの動作確認であって、現実の人間に対する因果効果を保証するものではない。

### 発表資料再生成

元の74枚版PowerPointと74ページPDFを別途保管した状態で、`journal_club`で`python3 build_p04_45_appendix.py`を実行（入力が74枚でない場合は追加しない）。追加8枚は79～82にP04-5、75～78にP04-4が収録されている。旧スライドの本文は維持し、ページ数表記だけ変更。

PDF変換環境のLibreOfficeが利用できなかったため、`export_p04_45_pdf.py`では**既存74ページを保持し追加8ページを高解像度画像としてレンダリングして結合**した。結果は82ページ。PDFは閲覧用、元のPPTXは編集可能。両者のページ構成と主要表示内容を検査した。

## 今後の必須研究

1. **P04-5の本当の公開RCT Holdout：未完了。** J-PAL/IPA DataverseやMany Labs 2等を候補として評価する。権利、尺度、標準誤差、汚染、予測時点を検査し、可能なら結果公開前に予測を第三者へ登録する。
2. **P04-6：** 事前登録・予測凍結・意思決定価値の評価を学ぶ。
3. **P00-3：** 実世界の対象・許可・害・停止条件を確定する。
4. **P05～P06：** 他のエージェントや実事業へ接続する前に、シャドー運用で結果を独立に検証する。

研究以外の本番運用や資金調達・事業収益の更新を示したものではない。
