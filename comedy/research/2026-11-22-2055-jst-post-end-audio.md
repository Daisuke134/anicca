# Comedy AI研究 2026-11-22 20:55 JST — 終幕後に残るAI音声の誤PASS修正

- **モード**：内部研究/評価のみ、`publish_enabled=false`、`auto_reply_enabled=false`。X・大喜利サイト・無差別リプ・外部投稿は未実行。
- **ベースの正本**：`Daisuke134/anicca` `main` commit `a3b026552fc23ba24f24c37d2f5fc23587014532`。本研究開始時に6指定ファイルと2分実演稿を確認。
- **使用したComedy Skill**：v0.2.1、Git blob SHA `fe21da855d08d5d01feff89be7244176087d4044`（`skill_commit` は上記mainのコミット）。最終版はマージ後に再確認する。
- **研究の目的**：金子さんの講評に沿って電話先AIの終幕無言・開始合図・ダイスがリアクションできる余白を守る。本文は改変せず、評価器だけ改善する。

## バグを実際に再現した証拠

`test_measure_stage_timing.good()` 合成注釈を使い、最後のAI発話（index 5）を `9300–11500ms` に延長、ダイスの終幕合図（index 6）を `11000–11200ms` に維持した。

| 比較 | text_gate | timing_gate | 総合gate | 終幕後に残ったAI音声 |
|---|---|---|---|---|
| main修正前・同じ合成入力を実行 | PASS | **PASS（誤判定）** | PASS | 300ms（旧実装は未計算） |
| 修正後・同じ合成入力を実行 | PASS | **FAIL** | FAIL | **300ms** |
| 修正後・AIが11200msちょうどで終了 | PASS | PASS | PASS | 0ms |

修正前にPython `measure(e)` で `gate=PASS`, `timing_violations=[]` を実行確認。修正後にPythonテストとCLI `--strict` で、終幕後の音声残留に終了コード1、境界一致でPASSを確認する。これは**手動構成された時刻注釈**であり音源・ASR・リアルタイム発声ではない。

## 新しいオリジナル開発セット（固定ベンチではない）

- `comedy/benchmarks/runs/2026-11-22-2055-end-cue-tasks.jsonl`：8題（オリジナル大喜利4、舞台アドリブ4）。
- `comedy/benchmarks/runs/2026-11-22-2055-end-cue-responses.jsonl`：8題×2候補の回答全文16件。1セッション内で書いた原案であり、**独立APIサンプルでも同条件の他モデル比較でもない**。テキストの具体性、既出の人物・車両の回収、役の継続を狙ったが、面白さの改善は未検証。
- `comedy/benchmarks/runs/2026-11-22-2055-end-cue-report.json`：`validate_run.py --strict` による文字数/キャラ名アンカー/禁止語/疑問符チェックの結果。これは客観的な**形式**ゲートのみ。
- 固定 `taskset-v1.jsonl` と外部Oogiri-Masterは今回の生成比較には使用していない。題材・回答は本サイクルで原案化したもので第三者のネタを転載していない。

## 実際に接続したモデル・未接続モデル

| 対象 | 実際の状態 |
|---|---|
| ChatGPT GPT-6 | **当セッションで16個のテキスト候補を原案作成**。serving build / temperature / effortはNOT_EXPOSED。API receiptなし。独立反復・ブラインドJudgeは未実施。 |
| Grok | 利用可能な直接モデルAPIが確認できず、**未実行**。 |
| Muse | 利用可能な直接モデルAPIが確認できず、**未実行**。 |
| Reason Network | 3接続への`list_team`がいずれもHTTP 409 `agent_network_offline`、メッセージ送信・生成は未実行。 |

各モデルの独立出力と比較可能な推論条件が揃っていないため**優劣は判定しない**。他モデルの存在だけで比較結果を捏造しない。

## 既存舞台の保護と演出要件

- v8 `comedy/sagi-injury-help.md` blob SHA `099ab68381e23f838299a9706c64f82bfc2dce1d`。
- 9/6確定上演稿 `comedy/sagi-denwa-2026-09-06-live.md` blob SHA `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`。
- 現行2分上演稿 `comedy/sagi-injury-help-2min-live.md` blob SHA `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`。すべて今回変更しない。
- 金子さんの「電話先AIを明確に」「人間側のリアクション」「後方で聞き取れる声」「偶発アドリブを回収」の指摘は引き続き課題。実測による設定理解率、声量、モデルの発話内容、応答遅延、観客笑いとダイスの身体の間はすべて **NOT_MEASURED**。

## 参考研究（設計上の注意）

- Nakanishi et al. (2026), [Real-Time Turn-End and Interruption Estimation Using Linguistic Cues for Turn-Taking](https://doi.org/10.7210/jrsj.44.413)：自然な対話ではターン終了と割り込みの判断が別問題。
- Shamsaie & Modarressi (2026), [Neither Silence nor Overlap Is Failure](https://arxiv.org/abs/2609.27372)：一般対話で全ての重なりを失敗扱いしない。今回の判定は**台本の明示した終幕合図後の無言**だけに限定し、任意の通常会話用閾値を勝手に発明しない。

## 次の評価

同じ実機構成で録音したDais/AIの発話境界を注釈してから `measure_stage_timing.py` に入力し、開始合図と終幕後の無言、第三者発話、笑いの直前の間、後方可聴性を別々に検証する。認識誤差と注釈誤差、音源の利用同意を記録する。実録なしに「音声改善済み」「爆笑」とは報告しない。
