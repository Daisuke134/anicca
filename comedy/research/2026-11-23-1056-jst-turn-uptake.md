# Comedy AI研究 2026-11-23 10:56 JST: ダイスのアドリブ未回収を検出する厳格モード

## 研究対象と正本
- GitHub `Daisuke134/anicca` の `main` コミット `4408279a2c3629d114c966c4257abd0aa73668db` を開始時の正本とした。
- 確認対象：`comedy/AGENTS.md`、`skills/comedy-agent/SKILL.md`、`comedy/COMEDY-AGENT-LOOP.md`、`comedy/benchmarks/README.md`、`comedy/IMPROV-PLAYBOOK.md`、`comedy/feedback/KANEKO-2026-11-15.md`。
- `skills/comedy-agent/SKILL.md` v0.2.1、Git blob SHA `fe21da855d08d5d01feff89be7244176087d4044`。これは**使用した指示の版**であり、基盤モデルの学習版ではない。
- 9月6日確定上演稿 `comedy/sagi-denwa-2026-09-06-live.md`（Git blob SHA `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`）と長尺『痛い痛い！』v8 `comedy/sagi-injury-help.md`（`099ab68381e23f838299a9706c64f82bfc2dce1d`）を改変しない。2分実演稿 `comedy/sagi-injury-help-2min-live.md`（`892ce8db0cc84eece3a64ecf661a7fdc90cc5784`）も無変更。

## 発見した評価上の穴
従来の `validate_stage_dialogue.validate` では、ダイスが1つの完全なアドリブを言い、AIが応答しないままダイスが次の台詞を言っても、最初の2声と以後の発話順だけ満たせば `PASS` になり得た。開始前の沈黙やAIの余計な台詞は検査しても、**ダイスの個別アドリブに1回ずつ応答したか**を検査していなかった。

例（合成テキスト）：開演→固定AI第一声→ダイス「救急！」→固定AI第二声→ダイス「会いたい！」→ダイス「もう無理、誰か来て！」→AIが会田アイタロウに応答→終幕。
- **修正前の既定検査：PASS、違反0**（実際に旧ソースをPythonで実行）。
- **新しい厳格検査：FAIL、`unanswered_dais_turn`**（同じ合成入力をPythonで実行）。
- 最終発話をAIが返さず終幕した場合は `unanswered_dais_before_end`。
- `--require-turn-coverage` は**オプトイン**。旧CLIや既存試験の既定の挙動は変えない。分割ASRセグメントを「別々の完全なダイスの台詞」と誤認しないよう、完全発話単位に人手で注釈されたテキストに限って使う。単にAIの返答が存在するかを検査するもので、返答の意味的な適切さや面白さを証明しない。

## 実行した検証
- GitHubブランチのPythonソースとテストをMac miniに**メモリ内で直接読み込んで実行**。ディスク残量不足につきローカルcheckoutや一時ファイル保存を使用しない。
- 旧単体テスト **22/22 PASS**、追加した合成テキスト回帰テスト **6/6 PASS**、合計 **28/28 PASS**。追加テストは未回収アドリブ、終幕時未回収、空のAI発話、観客笑いの割り込み、既定モード互換、正常な掛け合い。
- 新規オリジナル開発8題（一般大喜利4、電話先AI即興4）、各2候補、ChatGPT GPT-6製品ラベルの同一チャット内で生成した**16テキスト**を、GitHubの `validate_run.score` 関数の実ソースで検証。**16/16 形式PASS**。これは独立APIでの16呼び出しを意味しない。
- 生成途中の事前検査で、一般大喜利の「窓の外に引っ越す」まで、救急問診対策の禁止句「窓の外」によって弾いてしまう**検査範囲の誤設定**を発見。新しいオリジナル開発題4件だけで、この舞台専用の禁止句を除いてから正式に形式評価した。回答そのものは書き換えず保存した。既存固定ベンチ・舞台タスク規則は変更していない。
- 同じく既存の `audit_comparison_provenance.audit` を実ソースから実行し、`NOT_COMPARABLE` を確認。単一モデル、独立プロバイダ呼び出しレシートなし、生成設定未制御、正確なモデルビルド未取得。出自監査の結果は[JSON](../benchmarks/runs/2026-11-23-1056-provenance-audit.json)に保存。

## 研究データ
- [今回の新しいオリジナル開発題8題](../benchmarks/runs/2026-11-23-1056-original-development-tasks.jsonl)（固定15題 `taskset-v1.jsonl` は未使用）
- [GPT-6のチャット内で生成した16候補の全文](../benchmarks/runs/2026-11-23-1056-gpt6-chat-responses.jsonl)。モデルビルド：`product_label_only_exact_build_not_exposed`、`invocation_source=chat_session`、provider receiptなし、temperature/effort未制御。モデル間優劣の資料としては不適格。
- 同じ8題の2案は新規作成した独自の短文。公開大喜利サイトの回答の複製、外部サイトへの自動アクセス、X投稿・自動返信・応募は実施していない。外部publishはOFF。

## 金子さんのフィードバックへの寄与
- **開始合図**：ダイスが「痛い！」または電話をかける台詞を言うまでAIは無言。既存の開始ゲートは維持。
- **電話先AI役**：受付係・田中ピーポー太郎が、自分の判断で手配を進めるコントという立場を維持。電話先のAIだと観客が理解した割合は未測定。
- **アドリブの回収**：「会いたい！」など、ダイスの完全な一手を飛ばして次に進んだ回を新しいオプトイン監査で検出する。コールバックの内容の質は人間の確認が必要。
- **人間のリアクション・音声再現性**：本改善は台詞単位の受け答え確認のみ。実機Voiceの開始遅延、録音、音量、客席後方可聴性、話者識別、笑い、身体演技はすべて `NOT_MEASURED`。
- **安全**：舞台外の現実の危険が明らかな場合の安全例外は変更せず、第三者の声への応答を禁止する上位ルールも維持。

## 接続状況・制限
- Reason NetworkのPrimary / DAISUKE / MKの3接続で `list_team` を実際に試行し、いずれもHTTP 409 `agent_network_offline`。**Grok・Muse未実行**。モデル間の公平比較や勝敗宣言なし。
- 本番Voice、後方可聴性、観客の笑い、金子さんの指摘の解消は **未実測**。
- 全て内部研究用。**`publish_enabled=false`、`auto_reply_enabled=false`**。権限・専用アカウント・利用規約確認が済むまで外部投稿しない。

## 再現コマンド（コードをローカルに置ける環境向け、今回のMac上では未使用）
```bash
python3 -m unittest comedy/benchmarks/test_validate_stage_dialogue.py comedy/benchmarks/test_stage_turn_coverage.py
python3 comedy/benchmarks/validate_stage_dialogue.py --input path/to/complete-turn-events.json --output path/to/coverage.json --require-turn-coverage --strict
```
`--require-turn-coverage` のない既定の評価と区別して記録すること。入力は話者ラベル付きで「完全な台詞ごと」に区切られた**注釈済みデータ**が必要。
