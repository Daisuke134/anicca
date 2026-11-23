# Comedy AI 内部研究 2026-11-23 20:00 JST：ASR時刻注釈の物理的整合性

## 正本と対象

開始時 GitHub `Daisuke134/anicca` `main`: `1eebb9246a2cb6599360e062f1787df70095a07e`。
確認した規範：`comedy/AGENTS.md`、`skills/comedy-agent/SKILL.md`、`comedy/COMEDY-AGENT-LOOP.md`、`comedy/benchmarks/README.md`、`comedy/IMPROV-PLAYBOOK.md`、`comedy/feedback/KANEKO-2026-11-15.md`。
Skill v0.2.1 blob SHA：`fe21da855d08d5d01feff89be7244176087d4044`。上演正本は`sagi-injury-help-2min-live.md`、長尺v8と9/6確定稿は変更しない。

## 仮説と修正

`normalize_asr_turns.py` は、同一 `turn_id` のチャンク重複と断片間の負のギャップを拒否していた。しかし `turn_id` が違う場合、同じ話者の二つの独立発話が同じ時刻範囲を占めても受理していた。また、文字が存在するのに発話長が0msのチャンクも受理していた。これらはASRの重複仮説／不正な注釈の可能性があり、テキストが正しいだけで音声の正常性を報告すべきではない。

変更：
1. ダイス・AIの非空speechチャンクに `end_ms > start_ms` を要求し、0msは `ValueError` で拒否。
2. 同じ話者の**異なる** `turn_id` の時間区間が重複する場合、`overlapping distinct <speaker> turns` で拒否。結合後の終了時刻を追跡する。
3. 境界がちょうど一致する二つの発話は許容。ダイスとAIの別話者間の重なりは入力エラーで消さず、従来の `measure_stage_timing` の違反として報告する。
4. この拒否は**注釈データの整合性チェック**であり、実録音声を解析した結果ではない。出力で `INPUT_REJECTED` と `gate=FAIL` を混同しない。

## 実行証跡

既存mainへ新規テスト6件を先に追加：ASRモジュール計27件で **4件FAIL**（ゼロ長2、同一話者の異ID重複2）。修正後：27/27 PASS。全 `test_*.py` で **273/273 PASS**。Python 3.14.7 (macOS) で実行。初回は依存する舞台プロンプトファイルのローカル取得漏れによる1件のFileNotFoundErrorが出たが、正本から取得後に273件を再実行しPASSした。この環境準備ミスを製品のコード不具合としない。

旧mainコードと新コードを同じ合成7ケースに実際に適用した `runs/2026-11-23-2000-asr-annotation-regression.json`：
- 正常例1件：旧・新ともPASS。
- ゼロ長ダイス断片とゼロ長AI断片：旧版は両方PASS、新版は両方入力拒否。
- 同一話者で異なるturn_idの重複：AI側は旧版PASS、新版入力拒否。ダイス側は旧版の総合判定FAILだが不正注釈そのものは受理、新版は入力拒否。
- 同一話者の境界接触：旧・新とも入力受理。別話者の発話かぶり：旧・新とも `timing_gate=FAIL`、入力は保持。
- **3件の旧総合PASSを入力拒否へ変更**した。これは誤った注釈の受理を防いだ数であり、モデルの舞台成功率ではない。

## オリジナル開発題と生成結果

固定ベンチ **未使用**。権利問題のある第三者サイトへアクセスせず、新しい自作開発題8題（一般大喜利4、電話先AI即興4）を作成。各2候補、テキスト16回答。詳細：`runs/2026-11-23-2000-original-tasks.jsonl` と `runs/2026-11-23-2000-chat-responses.jsonl`。両候補は独立APIサンプルではない。

`validate_run.py --strict`：**16/16形式PASS**。これは人物名、長さ、質問・禁止語等の静的ハードゲートであり、面白さや話者理解の採点ではない。`audit_comparison_provenance.py`：**NOT_COMPARABLE**（モデル1種のみ、APIレシートなし、生成設定非公開）。

- ChatGPT：GPT-6製品ラベルで単一チャット内テキスト生成。モデルの厳密なビルド、temperature、effort、provider receiptは取得不能。
- Grok / Muse：Reason Networkの独立3接続はいずれも409 `agent_network_offline`。**NOT_RUN**。モデル間ランキングや優劣は提示しない。
- 人間の笑い評価・独立盲検・外部応募：なし。

## 金子さんのフィードバックと音声運用

導入は電話先のAI救急指令センターのまま、ダイス本人の開演合図まで無言、上演第一声・第二声は台本どおり。AIが観客やスタッフに応答しないこと、会田アイタロウ、おもち34号、右折田まっすぐ、右ひざのアドリブ回収を維持。今回は台本に追加台詞を挿入していない。

今回の新たな入力整合性チェックは、音声認識や話者分離自体を改善せず、舞台の途中でエラー処理を行う機能でもない。**実機Voiceの再現率、開始合図の正認識、電話先AI設定の観客理解、後方可聴性、ダイスの身体演技、観客の笑いはすべてNOT_MEASURED。** 実際の収録と話者・時刻の第三者注釈が必要。

参考研究：TagSpeech (2026), https://arxiv.org/abs/2601.06896 。話者と時間の対応が重要という関連研究であり、このコード・日本語舞台・実機で効果を測ったわけではない。

## 保護対象・公開制限

長尺`comedy/sagi-injury-help.md` v8、`comedy/sagi-denwa-2026-09-06-live.md`、`comedy/sagi-injury-help-2min-live.md`、`skills/comedy-agent/SKILL.md`はすべて無変更。

`publish_enabled=false`, `auto_reply_enabled=false`。X投稿、大喜利サイトへの公開・応募、第三者サイトへの規約外アクセスは実行していない。外部公開、モデル学習、舞台笑いの向上は主張しない。
