# Comedy AI内部研究：16/16形式PASSでもモデル比較は成立しない（2026-11-23 02:55 JST）

## 0. 実行範囲と正本
- 正本：GitHub `Daisuke134/anicca` `main` 起点コミット `ce2a57e8be3b3ee1acd71222a5adbf16d70f685d`。
- 専用ブランチ：`comedy/provenance-audit-20261123-0255`。
- 確認した必須資料：`comedy/AGENTS.md`、`skills/comedy-agent/SKILL.md`、`comedy/COMEDY-AGENT-LOOP.md`、`comedy/benchmarks/README.md`、`comedy/IMPROV-PLAYBOOK.md`、`comedy/feedback/KANEKO-2026-11-15.md`。そのほか `validate_run.py`、`check_injury_2min.py`、`sagi-injury-help-2min-live.md`、前回研究報告を読み取った。
- 研究モード：内部RESEARCH/EVAL。外部のX・大喜利サイトへの投稿・返信・大量応募なし。`publish_enabled=false`、`auto_reply_enabled=false`。

## 1. 仮説と発見
従来の8題×2候補で `validate_run.py --strict` が全件PASSしても、それは短さ・疑問符・既存人物といった**文字列条件**のみを表す。同一ChatGPTセッションの16案を独立したAPI呼び出しや複数モデル比較と誤認すると、能力改善を測ったつもりになる危険がある。

`audit_comparison_provenance.py` を新設して、別の検証軸として「比較条件が再現可能で揃っているか」を監査した。ソースとモデルの真正性はプロバイダ署名などで検証していないため、監査PASSでもモデルの勝敗や出力の真正性を証明しない。公開研究ではLLM Judgeの順位・位置・文体などのバイアスも指摘されており、今後の盲検採点で別途検証する。
- https://aclanthology.org/2025.ijcnlp-long.18/
- https://arxiv.org/abs/2606.19544

## 2. 今回のコードとチェック内容
- 新規 `comedy/benchmarks/audit_comparison_provenance.py`：JSONLタスクIDの一意性、モデル×タスク×候補番号の重複、タスク×候補カバレッジ、モデル版とSkill commit/blob SHAの整合、生成設定4項目、provider_apiという呼び出し種別、証跡文字列の存在と重複を監査。タスクファイル SHA-256 を出力。
- 新規 `comedy/benchmarks/test_audit_comparison_provenance.py`：適切な人工的な2モデルのメタデータを `COMPARISON_INPUTS_AUDITED` とする肯定例、単一チャット、Skill不一致、試行漏れ、重複、レシート重複、生成パラメータ不一致、未知タスク、不正候補番号、未制御パラメータの合計10件。**すべて合成データ**。
- `COMPARISON_INPUTS_AUDITED` はメタデータ条件の整合を表すだけ。provider_receiptは単なる文字列で、出所の真正性は `NOT_VERIFIED`。厳密な外部モデル比較に追加の実行記録が必要。

## 3. 新規オリジナル開発題と回答
- **固定ベンチは使用せず**、新たに書き下ろした内部オリジナル開発題8題（大喜利4、電話先AI即興4）を作成。各2候補、16全文をGitHubに保存。他人の大喜利作品は再利用していない。
- 問題と回答：`comedy/benchmarks/runs/2026-11-23-0255-provenance-tasks.jsonl`、`...-responses.jsonl`。同じチャットで作成した案を `sample_index=1/2` として識別。
- 生成元はChatGPTの **GPT-6**（コンシューマーセッション）。正確なデプロイビルド、temperature、effort、max_output_tokens、API呼び出しIDは**制御・取得できていない**。`invocation_source=chat_session`、`provider_receipt=null` と記録した。
- Skill v0.2.1、blob SHA `fe21da855d08d5d01feff89be7244176087d4044`、生成時のmainコミット `ce2a57e8be3b3ee1acd71222a5adbf16d70f685d`。Skill本文は今回変更していない。

## 4. 実行した評価
macOS Mac miniのPythonにて（ネット送信を伴わない標準ライブラリ検査）：
1. `python3 test_audit_comparison_provenance.py -q` → **10/10 PASS**。
2. `python3 validate_run.py --tasks tasks.jsonl --responses responses.jsonl --output formats.json --strict` → **16/16 PASS、各8題に欠損0、exit code 0**。これは形式・文字列条件の成績で、面白さではない。
3. `python3 audit_comparison_provenance.py --tasks tasks.jsonl --responses responses.jsonl --output provenance-report.json` → **NOT_COMPARABLE**。理由 `fewer_than_two_models`、`missing_generation_setting`、`missing_provider_receipt`、`missing_version_or_skill_sha`（正確なモデルビルドが取得できない）、`no_verified_independent_invocation`。レポートJSONを保存。
4. 正本の2分上演稿に対して `python3 comedy/benchmarks/check_injury_2min.py` → **PASS**（22発話、714文字、第一・第二声の原文と交互発話を静的検査）。Voiceの実測成功ではない。

## 5. 接続確認とモデル比較の限界
- Reason Networkの3アカウントに `list_team` を実際に試みたが、**全3接続がHTTP 409 `agent_network_offline`**。Grok・Museへの独立モデル実行は行っていない。
- 比較モデルは一種類のみ、独立の推論試行ゼロ。Grok/Museの結果やプロバイダ費用・レイテンシ・モデル間勝敗は **NOT_RUN / NOT_MEASURED**。
- 「16/16 PASS」を「コメディの腕前16/16」とは報告しない。人間による6軸盲検評価、観客の笑い、ダイスの身体演技、音声遅延・音量・後方可聴性、設定理解、20回の音声再演再現性はすべて **NOT_MEASURED**。

## 6. 台本と金子さん指摘の保護
- 電話先のAI救急指令センターという役割、ダイス先行の開演合図、第一声・第二声の厳密性、既出車両・人物のアドリブ回収、人間側の間、観客への誤応答を評価軸に保持。
- 2分稿に触れずに静的検査した。長尺v8、9/6確定上演稿も変更しない。
- 保護すべきGit blob SHA：v8 `099ab68381e23f838299a9706c64f82bfc2dce1d`、9/6 `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`、2分稿 `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`、Skill `fe21da855d08d5d01feff89be7244176087d4044`。

## 7. 次の検証
実際に接続できるモデルが2つ以上になったら、**同じ初見題・Skill SHA・サンプル数・デコード条件・音声/テキストモード**で独立実行し、元出力と実行証跡を保存。モデル名を伏せた評価と順番入替えで判断し、上演時の実録は別指標で評価する。出自監査器自体は音声・笑いを評価しない。
