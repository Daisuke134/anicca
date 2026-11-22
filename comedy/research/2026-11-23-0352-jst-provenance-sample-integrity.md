# Comedy AI内部研究：同じ欠測が2モデルに起きても誤って比較可になる問題を修正（2026-11-23 03:52 JST）

## 正本・モード・使用権限

- ベース：GitHub `Daisuke134/anicca` の `main`、起点commit `530b49d9ae5a766d4b2181189aa48f54c8dc2d54`。
- 作業ブランチ：`comedy/provenance-sample-audit-20261123-0352`。内部研究 `RESEARCH/EVAL` のみ。
- 読込資料：`comedy/AGENTS.md`、`skills/comedy-agent/SKILL.md`、`comedy/COMEDY-AGENT-LOOP.md`、`comedy/benchmarks/README.md`、`comedy/IMPROV-PLAYBOOK.md`、`comedy/feedback/KANEKO-2026-11-15.md`、`validate_stage_dialogue.py`、`sagi-injury-help-2min-live.md`、前回出自監査記録。
- Skill：v0.2.1、blob SHA `fe21da855d08d5d01feff89be7244176087d4044`。この回はSkill変更なし。
- `publish_enabled=false`、`auto_reply_enabled=false`。X・大喜利サイト・第三者サイトへの自動投稿/応募/返信なし。外部APIの規約外クロールなし。

## 1. 具体的なバグ（レッド→グリーンで検証）

前回追加した`audit_comparison_provenance.py`は「モデル間で `(task_id, sample_index)` の組が一致するか」を見ていた。しかし、**2モデルが同じタスクの2回目を両方欠測した場合**、両者は同じ組を持つため `COMPARISON_INPUTS_AUDITED` と誤判定された。さらに両モデルが試行番号1と3だけを保持し2を欠測したケースも比較可と誤判定された。

今回、モデル**ごと・タスクごと**の試行数が一定であり、番号が1から連続することを確認するよう修正。`temperature=true`（Python boolの誤混入）と `max_output_tokens=0`（無効予算）も、比較条件メタデータとして不正な設定とする。これは「同じ条件」を満たすかの監査であり、プロバイダの実行証跡の真正性は証明しない。

| 人工的な負例 | 修正前の誤判定 | 修正後 |
|---|---|---|
| 両モデルとも task2/sample2 を欠損 | 比較可 | `uneven_task_sample_counts` |
| 両モデルとも sample1と3だけ存在 | 比較可 | `noncontiguous_sample_indices` |
| 両モデルの temperature に true | 比較可 | `invalid_generation_setting` |
| 両モデルの max_output_tokens が0 | 比較可 | `invalid_generation_setting` |

**Mac mini実行結果**：テスト追加直後 `Ran 14 tests / FAILED (failures=4)`。修正後、同じ新旧14件を `python3 -m unittest -v test_audit_comparison_provenance` で再実行し `Ran 14 tests / OK`。既存の正規メタデータ肯定例もPASS。人工的な2モデルの組を使ったユニットテストであり、Grok/Museの実行ではない。

## 2. 新規オリジナル開発題と実際のChatGPT候補

- 今回は**固定ベンチ不使用**。ゼロから作ったオリジナル開発題8題（大喜利4、電話先AI即興4）を新規作成、各2候補の合計16回答をチャット内で生成。第三者の大喜利回答の複製なし。
- ファイル：`comedy/benchmarks/runs/2026-11-23-0352-integrity-tasks.jsonl`、`2026-11-23-0352-integrity-responses.jsonl`。
- モデル：ChatGPT GPT-6（この会話のコンシューマーセッション）、**独立APIの複数試行ではない**。正確なデプロイビルド、temperature、effort、max_output_tokens、プロバイダレシートはいずれも制御・取得不可。出力16件を `invocation_source=chat_session` と記録。
- 各出力には`sample_index`を持たせて候補を分離したが、それは独立サンプルの保証ではない。
- 舞台題では「おもち34号の招待状」「右折田にバックを要求」「会田の代理受診」「玄関だけ来た病院」の既出人物/車両を**具体的な誤手配・結果**につなげる練習をした。登場人物名の文字列出現だけで本当のコールバックの質は測れない。

## 3. 実際に実行した検証と結果

macOS Mac miniにてPython標準ライブラリスクリプトを取得して実行：

```bash
python3 -m unittest -v test_audit_comparison_provenance
python3 benchmarks/validate_run.py --tasks 2026-11-23-0352-integrity-tasks.jsonl --responses 2026-11-23-0352-integrity-responses.jsonl --output 2026-11-23-0352-format-report.json --strict
python3 benchmarks/audit_comparison_provenance.py --tasks 2026-11-23-0352-integrity-tasks.jsonl --responses 2026-11-23-0352-integrity-responses.jsonl --output 2026-11-23-0352-provenance-report.json
python3 benchmarks/check_injury_2min.py
```

- Python単体テスト：**14/14 PASS**。新規4テストが修正前には想定どおりFAILすることを確認。
- 新規8題×2：形式ゲート**16/16 PASS、欠測0、strict終了コード0**。これは長さ/疑問符/字面のアンカー等の検査で、面白さの点数ではない。
- 出自監査：**NOT_COMPARABLE**。理由：`fewer_than_two_models`、`invalid_generation_setting`、`missing_generation_setting`、`missing_provider_receipt`、`missing_version_or_skill_sha`、`no_verified_independent_invocation`。精確なモデルビルド取得不可、1モデルのみ、独立API試行0。
- 台本静的検査：**PASS、22発話、発話714文字**。第一・第二声の原文、交互応答、質問増殖防止、既出人物の包含。実機Voiceの再現実績ではない。
- 実行結果JSON：`comedy/benchmarks/runs/2026-11-23-0352-format-report.json` と `2026-11-23-0352-provenance-report.json`。これらはMac miniで**実行して得たファイルそのもの**をGitHubへ保存。
- Reason Networkは DAISUKE 接続で `list_team` を実行したが HTTP 409 `agent_network_offline`。他2リンクは今回再接続テストなし。Grok/Museの実行・比較は **NOT_RUN**。

## 4. 金子さん指摘・台本の保全・未計測

- 金子さん指摘に対する舞台設計の要点：**ダイスの一声だけで開演**、電話先にいるのは人間でなく「AI救急指令員」、AI第一・第二声の厳密一致、問診ループ禁止、短い返答から既出人物を回収しダイスに演技の間を渡す。観客の声には演技上反応しない。ただし現実の危険は安全上の例外。
- 今回のオリジナル候補は稽古用テキストであり、確定台本への挿入はしていない。**長尺『痛い痛い！』v8** blob `099ab68381e23f838299a9706c64f82bfc2dce1d`、**9/6確定稿** blob `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`、**2分稿** blob `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`。いずれも未変更。
- **NOT_MEASURED**：本物のVoiceの台詞遵守/遅延/発話の被り/音量/客席後方の可聴性、観客の「電話先AI」理解率、笑いの実測、ダイスの身体演技と即興の相乗効果、20回の再演再現性。形式PASSと実演成功を混同しない。

## 5. 残課題

接続できる2モデル以上の独立した実行レシートと完全な`task × sample_index`行列を用いた同条件比較。録音・映像が許諾済みなら、別の音声/人間評価系で「間」「聞き取り」「笑い」を測る。メタデータ監査を通過しても、そのままモデルの質や面白さの優劣としない。
