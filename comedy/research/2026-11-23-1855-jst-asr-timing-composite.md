# Comedy AI研究 2026-11-23 18:55 JST：ASR復元後の時間的舞台違反を見落とさない

## 対象・根拠

正本 GitHub `Daisuke134/anicca` `main` の実行前コミット `6e852740b817830e76f3f7335c4dbe3eb7f89a84` を取得した。
`comedy/AGENTS.md`、`skills/comedy-agent/SKILL.md`、`comedy/COMEDY-AGENT-LOOP.md`、`comedy/benchmarks/README.md`、`comedy/IMPROV-PLAYBOOK.md`、`comedy/feedback/KANEKO-2026-11-15.md` に従う。Skill v0.2.1 の Git blob SHA は `fe21da855d08d5d01feff89be7244176087d4044`。

前回の `normalize_asr_turns.py` は、時刻注釈付きASRチャンクを完全ターンへ復元して `validate_stage_dialogue.validate` で判定していた。しかしこのテキストゲートは、**AIの発話開始がダイスの開演合図より早い時刻だった**、または**AIの音声終了が終幕合図より遅れた**という状態を検査しなかった。文字起こしが完全一致でも、舞台の「ダイスが最初」「終幕後は無言」を保証できない。

Stivers et al. (2009), *PNAS*, https://doi.org/10.1073/pnas.0903616106 は自然会話のターン交代で重複や沈黙が重要であると示す。自然会話の研究からAI舞台向けの許容秒数を導出したわけではない。本研究では**ゼロを境にする明示的な舞台契約**だけを静的に検査する。

## 変更

- `normalize_asr_turns.evaluate` は従来どおり `turn_id`・話者・時刻から連続するASR断片を結合し、第一声/第二声/開始合図の文字列ゲートを保持する。
- **復元後**の時刻注釈を既存 `measure_stage_timing.measure` へ渡し、`ai_overlaps_dais_speech`、`ai_audio_after_end_cue` などの時刻違反を評価。新しい恣意的な時間閾値は導入しない。
- `stage_gate` と `timing_gate` を独立出力に残し、総合 `gate` は両方PASSの場合に限りPASSとする。`timing_audit` で再現できる。
- 音声の取得、ASR品質、実機遅延、話者認証、笑いは一切検証しない。`audio_annotated` の申告だけでは実測証明にならない。

## 実行した合成反例（同じ台詞内容、手動時刻のみ変更）

| ケース | 旧gate | 新テキストgate | 新時間gate | 新総合gate | 説明 |
|---|---|---|---|---|---|
| 通常ASR断片 | PASS | PASS | PASS | PASS | 11断片→7イベント |
| 開演合図が500msまで、AIが450msから発話 | **誤PASS** | PASS | FAIL | FAIL | `ai_overlaps_dais_speech`、50ms |
| AI発話が終幕合図3450msを超えて3500msまで残る | **誤PASS** | PASS | FAIL | FAIL | `ai_audio_after_end_cue`、50ms |
| AI開始が合図終了500msちょうど | PASS | PASS | PASS | PASS | 境界一致は重複ではない |

`comedy/benchmarks/runs/2026-11-23-1855-asr-timing-regression.json` に旧mainと修正ソースで**実際に実行した**判定を保存。いずれも**合成入力**で、本番音声に成功したことを意味しない。

## 回帰・生成・出自監査

macOS / Python 3.14.7 で、固定main `6e852...` の公開ソースをローカル隔離ディレクトリへ取得し、変更ソース・新規4テストを差し替えて `python3 -m unittest discover -s . -p 'test_*.py' -q` を実行：**267/267 PASS**。2分稿 `check_injury_2min.py` は**22発話、714文字、静的PASS**。元の各舞台台本は変更していない。

**固定ベンチは今回未使用。新規オリジナル内部開発題8題**（一般大喜利4、電話先AI即興4）の各2候補、計16テキスト。題と回答全文は `runs/2026-11-23-1855-original-tasks.jsonl` と `runs/2026-11-23-1855-chat-responses.jsonl`。第三者サイトのお題・回答は収集していない。権利欄は self-authored。形式 `validate_run.py --strict` は **16/16 PASS**。形式だけの結果で、人間評価、音声の面白さ、候補の勝敗は `NOT_MEASURED`。

- 利用できた生成系：このChatGPTチャット内の**GPT-6製品ラベル**によるテキスト16候補。正確なモデルビルド、温度、推論量、独立呼び出しレシートなし。単一チャット内で2候補を作ったので独立したAPI比較とは呼ばない。
- Grok / Muse：Reason Network の対象接続がHTTP **409 agent_network_offline**。今回の生成は **NOT_RUN**。公平なモデル間比較は **NOT_COMPARABLE**。比較出自監査でも `fewer_than_two_models`, `no_verified_independent_invocation`, `missing_provider_receipt` 等を検出。
- `runs/2026-11-23-1855-format-report.json`、`runs/2026-11-23-1855-provenance-report.json` が機械生成された実行結果。プロバイダ・人間による成功を主張しない。

## 金子さんの講評と未解決事項

「電話先のAI救急窓口」という役の位置付け、ダイス先行の合図、AIに独演させないテンポ、固有名詞回収、後方可聴性を引き続き遵守。今回の時間的ゲートで、合図途中にAIがかぶる・終幕後に音声が残るという失敗を、**時刻が適切に注釈されている場合に限り**検出可能になった。

**未測定**：実際のVoice録音、音声認識の誤字/重なり、マイク、通話先AIの観客理解率、金子さん指摘の声量、ダイスの身体演技・リアクション、観客の笑い、複数モデル比較の性能、会場での再現性。合成タイムコードを実機Voiceのミリ秒実測値として扱わない。

『痛い痛い！』長尺v8、2026-09-06確定上演稿、現行2分稿、Skill本文は無変更。舞台外の一般医療誘導は追加しない。ただし現実に危険が明白な場合は安全優先の既存ルールを維持。

`publish_enabled=false`, `auto_reply_enabled=false`。X・大喜利サイトへの投稿、第三者への自動返信、サイト規約外アクセスは **実施なし**。

## 限界

時刻注釈の正確さやモデル出力と録音の対応は認証されていない。既存 `measure_stage_timing` の挙動を再利用しているため、今後のTiming Gateの変更はASR総合判定にも影響し得る。Voice運用への適用には独立した収録・正確なタイムアライメント・端末と会場の再現試験が必要。
