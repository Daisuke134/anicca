# Comedy AI 内部研究 — 舞台固定発話の完全一致ゲート（2026-11-23 05:55 JST）

## 正本・対象・仮説
- Source of truth: GitHub `Daisuke134/anicca` の `main`、作業開始時 `595a7e3cbc3a62f2754c73ae6cf82d377eafea4a`。専用ブランチ `comedy/2026-11-23-0555-exact-stage-turn-gate`。
- 読込対象: `comedy/AGENTS.md`、`skills/comedy-agent/SKILL.md`、`comedy/COMEDY-AGENT-LOOP.md`、`comedy/benchmarks/README.md`、`comedy/IMPROV-PLAYBOOK.md`、`comedy/feedback/KANEKO-2026-11-15.md`。追加で2026-11-22再演失敗記録、9題の舞台回帰セット、2分舞台版も確認。
- Comedy Skill: v0.2.1、blob SHA `fe21da855d08d5d01feff89be7244176087d4044`。`main`のSkillと台本は変更しない。
- 仮説: `validate_run.py` の `expected_prefix` は固定第一声の後に別台詞・現実の住所質問が続いても先頭一致で合格するため、金子さんフィードバックの重要な失敗（受付の質問が連続し、二声目にボケが出ない）を過小検出しうる。

## 修正内容
- `comedy/benchmarks/validate_run.py` に**任意の `expected_exact`**を追加。指定があれば文字列完全一致のみをPASSとし、不一致は `script_exact_response_mismatch`。無効な空文字・非文字列の期待値は例外。指定していない従来タスクの動作は変更しない。
- `comedy/benchmarks/test_validate_run.py` に追加5件：第一声への余計な住所質問、二声目の末尾欠落、完全一致の正常系、無効な期待値、旧先頭一致との互換。
- 新規**舞台固定回帰** `comedy/benchmarks/injury-stage-exact-2026-11-23.jsonl` は固定された第一声・第二声・観客が叫んだ場合の沈黙の3件。既存固定ベンチと2026-11-22舞台回帰セットは改変していない。
- 台本の原文改変はゼロ。現実の重大な緊急事態では役を解いて安全を優先するルールも維持。

## Before / After：合成テキスト実行
- 合成positive 3件：第一声・第二声が台本と完全一致、開演前の沈黙。変更後 `3/3 PASS`、`--strict` exit 0。
- 合成negative 3件：①正しい第一声に「住所を教えてください。」を追加、②第二声の末尾文字を欠落、③第三者だけが話したのにAIが発声。**変更前の `main`** の旧評価器では①②が誤PASSで③のみFAIL。**変更後**は3件とも期待どおりFAIL、`--strict` exit 1。
- Mac mini からリポジトリブランチのコードをHTTP readbackし実行。`python3 -m unittest discover -s comedy/benchmarks -p 'test_*.py'`（今回取得した2テストファイルに限定）：**32/32 PASS**（うち新規5）。初回に誤ったunittestモジュール指定をしたため1件のコマンド実行はImportErrorだったが、正しいdiscoverコマンドで再実行し全32件PASS。これはコード不具合の修正とは区別。
- `check_injury_2min.py` による既存2分台本の静的検査は **PASS**、22発話・714文字。ただし上演の長さ・初ボケの時刻・後方可聴性・音声遅延は未測定。
- 実行生レポート: `runs/2026-11-23-0555-positive-report.json`、`negative-report.json`、`original-report.json`、`provenance-report.json`。synthetic positive/negativeの**台詞データも保存**し、実際の録音とは絶対に混同しない。

## 新作オリジナル開発題：固定ベンチではない
- 今回の開発題は独自作成8題（大喜利4、電話先AI即興4）。各2候補、合計**16テキスト候補**。題と回答全文は `runs/2026-11-23-0555-tasks.jsonl` と `runs/2026-11-23-0555-responses.jsonl` に保存。
- 同じ題、`max_chars` / `max_questions` / `any_of` 条件で文字数・世界観アンカー・質問数を検査し、**16/16形式PASS**。これは面白さ・声のタイミング・独創性の評価ではない。
- 例：ダイス「AI救急に電話したのに救急車が電話に出た！」→「おもち34号本人です。運転手が結婚式へ行ったので、ただいま受話器だけ出動しています。」。電話先の役割、固有キャラの行動、その結果を一手で返して人間側の間を残す設計。別候補はJSONL参照。
- 創作の参考原則：Upright Citizens Brigade `Improv 201` の一つのGame、反復・heightening、second beats（https://ucbcomedy.com/course/improv-201/586/）。表現の転載や他者の大喜利回答の流用はしていない。

## 実際に走ったモデル・比較条件
- ChatGPT GPT-6（現チャットのテキスト生成）のみ16候補。正確なデプロイビルド、temperature、effort、max_output_tokens、API実行レシートは取得不能。記録上 `invocation_source=chat_session`、`model_version=GPT-6 ChatGPT UI; exact deployment build NOT_AVAILABLE`、Skill commitとblobを各行に記録。**独立API反復ではなく、同じチャット内で候補を作成**。
- Grok / Muse：今回、同条件で独立に呼び出すプロバイダ経路を確認・実行できず **NOT_RUN**（過去のReason Networkの409ログを今回の生接続試験として再利用しない）。
- `audit_comparison_provenance.py` の実行結果は **`NOT_COMPARABLE`**（`fewer_than_two_models`、`no_verified_independent_invocation`、`missing_provider_receipt`、`missing_version_or_skill_sha`、`missing_generation_setting`、`invalid_generation_setting`）。モデル順位・Skill改善効果は出さない。
- Model performance: `NOT_MEASURED`、実際の客席の笑い `NOT_MEASURED`、音声モデルの再現性 `NOT_MEASURED`、金子さんの導入設計の実舞台効果 `NOT_MEASURED`。

## 不変の舞台資料（開始時Git blob SHA）
- 長尺『痛い痛い！』v8 `comedy/sagi-injury-help.md`: `099ab68381e23f838299a9706c64f82bfc2dce1d`。
- 2026-09-06確定上演稿 `comedy/sagi-denwa-2026-09-06-live.md`: `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`。
- 現行2分実演稿 `comedy/sagi-injury-help-2min-live.md`: `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`。
- Skill `skills/comedy-agent/SKILL.md`: `fe21da855d08d5d01feff89be7244176087d4044`。
- マージ後にも新しいmainをfetchしSHAを比較すること。PR作成時の修正差分に上記ファイルを含めない。

## 安全・publish境界と残課題
- `publish_enabled=false`、`auto_reply_enabled=false`。X・大喜利サイトへの投稿・自動リプ・大量応募・第三者サイトの自動操作は**実施していない**。
- 舞台の電話先AIと観客の声の区別はテキスト上のフィクスチャであり、話者識別／ミュート／会場の音量の実装保証ではない。
- 次の検証課題：ダイス実声の合図20試行・第一／第二声の逐語一致・第三者音声での沈黙・ダイスの身体反応・後方客席での固有名詞聞き取り・コールバック回収・音声出力の複数回再現性。実録の入力、モデル版、マイク位置、時刻を揃える必要がある。
