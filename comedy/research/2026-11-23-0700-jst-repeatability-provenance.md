# Comedy AI 内部研究：反復稽古の「同条件」監査と音声証拠の分離

- 実施日：2026-11-23 07:00 JST頃
- 種別：**新規オリジナル開発8題**（一般大喜利4・電話先AI即興4）、各2案。固定の公開／非公開ベンチは今回の生成に使用していない
- 正本：GitHub `Daisuke134/anicca` の `main`、研究開始時のコミット `a3a85b11ec004c58719ec06d26591dee84f5006c`
- 作業：内部研究とオフライン検証のみ。外部SNS・大喜利サイト `publish_enabled=false`、`auto_reply_enabled=false`

## 読み込んだ指示の出自

| 正本ファイル | 読み込み時のGit blob SHA |
|---|---|
| `comedy/AGENTS.md` | `aa5b798ccb38cb2c3c6dd045e7a26f7adac44b09` |
| `skills/comedy-agent/SKILL.md` | `fe21da855d08d5d01feff89be7244176087d4044` |
| `comedy/COMEDY-AGENT-LOOP.md` | `a3325b5851155311a09805d443ea352a239347e6` |
| `comedy/benchmarks/README.md` | `14c305f22e4247c696b5183b83bf3825116a6613` |
| `comedy/IMPROV-PLAYBOOK.md` | `5f494c648ac6a630fe932342b53c575f4349e3db` |
| `comedy/feedback/KANEKO-2026-11-15.md` | `6c26deba72a978b29da3cfb1975a96d6993451ca` |

舞台の保護対象：長尺 `sagi-injury-help.md` v8 = `099ab68381e23f838299a9706c64f82bfc2dce1d`、9/6確定上演稿 `sagi-denwa-2026-09-06-live.md` = `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`、2分実演稿 = `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`。**いずれも今回編集しない**。

## 問題設定と実装

これまでは一つの舞台テキストのPASSと、発話の長さ・被り・間隔を個別に調べられた。しかし「20回の稽古で何回再現できたか」と報告するときに、モデルビルド・Skill・台本・マイクや入力方式が違う試行を足すと再現性の根拠が崩れる。さらに、合成台詞を実機音声と誤認する危険がある。

新規 `comedy/benchmarks/audit_stage_repeatability.py`：
1. 各runの `events` を既存 `validate_stage_dialogue.validate` で文字列・話者・第一声／第二声・開始／終幕・第三者介在のハードゲートに通す。
2. `stage_id`、`model_id`、`model_version`、`skill_blob_sha`、`script_blob_sha`、`input_profile`、`audio_profile`、`source_type` の**申告値**で条件ごとに分ける。異なる条件を合算しない。1回のみ・複数条件では全体 `NOT_COMPARABLE`。
3. `synthetic` と `audio_annotated` を混ぜない。後者には録音参照と注釈者IDが必要。しかし参照先を開いて音声を検証する機能はないため、両者とも**実機Voiceの客観的再現率と呼ばない**。
4. AI発話前のダイス合図、電話先のAIとしての第一・第二声、ダイスが反応できる交互発話、第三者声による介入危険を監査する。音量、電話設定の観客理解、アドリブの面白さ、身体演技、笑いの再現性は `NOT_MEASURED`。
5. `--strict` は1つでもFAILか同条件の反復が成立しなければ非ゼロ終了。

### 実行した合成反復（**モデルの実発話ではない**）

| run_id | 人工的な入力 | テキストゲート |
|---|---|---|
| synthetic-good-01 | ダイス合図→台本の第一・第二声→終了 | PASS |
| synthetic-noise-control-02 | 機材ノイズを挿入、第三者による発話ではない | PASS |
| synthetic-extra-triage-03 | 第一声の後ろに「住所を教えてください。」を追加 | FAIL：`opening_not_exact` |
| synthetic-audience-interruption-04 | ダイス発話とAI返答の間に観客発話を挿入 | FAIL：`ambiguous_third_party_speech_between_dais_and_ai` |

**2/4は人工的に用意した正負対照の結果であり、Voiceの成功率50%、モデルの欠陥率、観客の笑いの数値ではない。** AIらしい文言も手動で組み立てた合成イベントであり、実在モデル出力とは表示しない。`SAME_DECLARED_CONDITIONS_ONLY` も自己申告メタデータが揃った意味に限る。

- 単体テスト：新規14/14 PASS ＋ 既存舞台対話22/22 PASS ＝ **36/36 PASS**（Python標準ライブラリ、Mac miniで実行）。
- 合成レポート：`benchmarks/runs/2026-11-23-0700-repeatability-report.json`。
- 厳格モードは、意図的なFAILを含む合成データで**期待どおり終了コード1**。
- 音声認識・話者分離・音声生成・本番再演はいずれも**未実行**。

## オリジナル大喜利・即興の生成と検査

- 8題：町内会回覧板の推理小説、寿司ネタの労働組合、宇宙土産、消しゴム警備員（一般4件）、救急車の面接、膝だけ呼ぶ病院、右折田の方向音痴、豆腐の花束（電話先AIの4件）。
- 各2候補：**16案**。全候補を `benchmarks/runs/2026-11-23-0700-gpt6-chat-responses.jsonl` に全文記録。`benchmarks/runs/2026-11-23-0700-new-development-tasks.jsonl` が題と権利・公開OFF・文字数等の条件を記録。
- **ChatGPT GPT-6（製品ラベル）**の同一チャット内で生成。正確な基盤ビルド番号、独立したAPI実行証跡、厳密に同じtemperature/effortは取得できない。2案は独立サンプル／統制した複数推論とは扱わない。
- `validate_run.py --strict` の**客観的形式テスト16/16 PASS**（各グループ8/8、欠測0）。禁句・長さ・疑問符等での検査であり、**面白さは未測定**。`benchmarks/runs/2026-11-23-0700-format-report.json`。
- Grok・MuseについてReason Networkの3接続へ `list_team` を直接試したが、いずれも HTTP 409 `agent_network_offline`。他モデルの出力は得ていない。**公平な複数モデル比較は未成立（NOT_COMPARABLE）**。

## 金子さんのフィードバックへの適用と残課題

- **電話先AIの役割**：ダイスがスマホからAI救急指令員にかける設定を維持。第一声・第二声は完全一致を監査対象とした。観客がその役割を理解する割合は**未測定**。
- **開演と第三者声**：ダイスの「痛い！」合図以前の沈黙、第三者の介在の要確認、終幕後の無音を既存の対話ゲートで保持。実機話者分離の成功率は**未測定**。
- **アドリブ**：「会いたい」「救急車どこ」系は既出人物と具体的な行動の回収を新規開発題で検討した。ただし人間による意味的評価は**未実施**。
- **音声再現性**：音声モード・入力経路・マイク・会場後方での重要語句の聞き取りやすさは本ツールでは検証できない。実録の繰り返しでのみ効果を判定できる。
- **笑い・身体演技**：観客笑いの量やダイスの身体反応の寄与を数字で報告しない。
- **外部投稿**：X・大喜利サイトへの公開、返信、大量応募は一切実行しない。投稿IDもない。

## 再現コマンド

```bash
python3 -m unittest comedy/benchmarks/test_audit_stage_repeatability.py comedy/benchmarks/test_validate_stage_dialogue.py
python3 comedy/benchmarks/validate_run.py --tasks comedy/benchmarks/runs/2026-11-23-0700-new-development-tasks.jsonl --responses comedy/benchmarks/runs/2026-11-23-0700-gpt6-chat-responses.jsonl --output /tmp/comedy-format-report.json --strict
python3 comedy/benchmarks/audit_stage_repeatability.py --input comedy/benchmarks/runs/2026-11-23-0700-stage-repeatability-synthetic.json --output /tmp/comedy-repeatability-report.json
```

上記テストはMac miniの専用一時ディレクトリにGitHubの当該ブランチから取得した実ファイルで実行した。リポジトリ全CIの完了や本番舞台の再演は主張しない。

**外部研究の扱い**：NIST AI RMF Metrology Center (https://airc.nist.gov/metrology/) にあるTEVVの目的と整合する形で測定出自を区別した。ただしこのレポートの具体的なテスト結果はすべて上記の自作合成入力・コードによるもので、NISTの測定結果ではない。
