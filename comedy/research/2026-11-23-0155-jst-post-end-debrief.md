# Comedy AI 内部研究：終幕後の稽古講評を「舞台の間」に混ぜない（2026-11-23 01:55 JST）

## 0. 研究モード・正本・権限
- 対象：GitHub `Daisuke134/anicca` の `main`、起点コミット `a0b9bf5205bce5966e9afb1d1af72a8ed9277a6b`。専用ブランチ `comedy/reentry-stage-boundary-20261123-0155`。
- 実読込：`comedy/AGENTS.md`（blob `aa5b798ccb38cb2c3c6dd045e7a26f7adac44b09`）、`skills/comedy-agent/SKILL.md`（blob `fe21da855d08d5d01feff89be7244176087d4044`、v0.2.1）、`comedy/COMEDY-AGENT-LOOP.md`、`comedy/benchmarks/README.md`、`comedy/IMPROV-PLAYBOOK.md`、`comedy/feedback/KANEKO-2026-11-15.md`。
- モード：内部RESEARCH/EVAL。外部サイトへの投稿・自動返信・大量応募を行わない。設定 `publish_enabled=false`、`auto_reply_enabled=false`。第三者の作品を転載しない。

## 1. 発見した問題と仮説
従来のタイミング評価器 `measure_stage_timing.py` は、最後のAI発話を記録した後、ダイスの「もういい、終わり！」（`cue=end`）を処理しても、`ai_waiting_for_dais` が残ったままだった。このため**終幕後のダイスによる録音確認・講評**が、新たな舞台上のツッコミ再発話として算入され得た。

これでは `dais_reentry_gap_ms` の標本数・中央値が変わり、任意閾値を設定した場合は存在しない舞台内違反も加わる。舞台上の間と稽古後の会話は分ける必要がある。これは音声モデルの不具合ではなく、**注釈評価器のスコープの誤り**。

## 2. 差分と実装
`comedy/benchmarks/measure_stage_timing.py` のダイス通常発話→再発話ギャップ抽出条件に `active` を加えた。`active` は正しい開演合図以後・終幕合図前のアノテーションを示す。舞台後の講評やデブリーフを含めない一方で、既存の `ai_audio_after_end_cue`（AI音声残留を検知するハードゲート）は変更しない。既存の時間閾値は既定値未指定のまま維持。

`comedy/benchmarks/test_measure_stage_timing.py` に回帰3件：
1. 終幕後のダイス発話を追加しても、再発話ギャップは100ms・200msの2件のまま。
2. `--min-dais-reentry-gap-ms` を明示しても、講評が余分な違反を作らない。閾値1200msでは舞台中2件のみ違反。
3. 終幕後に講評があり、AI音声が終幕を300ms越える場合は、講評は数えず従来の音声残留FAILを維持。

## 3. 実行証拠（合成データ／コード動作）
- **テストを先に追加した赤フェーズ**：`python3 comedy/benchmarks/test_measure_stage_timing.py -q` → 53件中3件FAIL。終幕後のデブリーフが3番目のギャップ（1100ms）に誤算入された。
- **修正後の緑フェーズ**：同じテスト **53/53 PASS**、`python3 comedy/benchmarks/test_validate_stage_dialogue.py -q` **22/22 PASS**、`python3 comedy/benchmarks/check_injury_2min.py` **PASS**。
- 合成 `runs/2026-11-23-0155-boundary-synthetic-input.json` を `measure_stage_timing.py --strict` で実行→ `timing=PASS`、`text=PASS`、`dais_reentry_gap_ms=[100,200]`、中央値 `150` ms。出力は `...-synthetic-report.json`。
- これは**人工的なタイムコードによるコード試験**。実録音を解析した結果でも、音声Voiceのタイミングや実際の笑いを改善した証拠でもない。

## 4. オリジナル開発題・複数候補（固定ベンチは未使用）
- 同じこの実行で書き下ろした内部オリジナル題8件：一般大喜利4件、田中ピーポー太郎の電話先AI即興4件。出典／利用権：`original_internal_draft_created_in_this_run`、他人の投稿は使わない。
- `runs/2026-11-23-0155-boundary-tasks.jsonl` に全文、`...-responses.jsonl` に各2案、計16回答全文とメタデータ、`...-formats.json` にハードゲート検査結果を保存。
- **実行**：`python3 comedy/benchmarks/validate_run.py --tasks ...-tasks.jsonl --responses ...-responses.jsonl --output ...-formats.json --strict` → **16/16 PASS、欠損0、終了コード0**。文字数・疑問符・既存人物アンカー等の**形式検査のみ**。人間による面白さ評価は未実施。
- 生成モデル：このChatGPTテキストセッションの **GPT-6**。モデルAPIの厳密なビルド番号・temperature・effort・token usage・提供元レシートは `NOT_CONTROLLED`／`NOT_AVAILABLE`。A/Bの候補は独立モデルAPIの反復試行ではなく、同一会話で生成した別案。Skill v0.2.1、起点commit `a0b9bf5205bce5966e9afb1d1af72a8ed9277a6b`、Skill blob SHA `fe21da855d08d5d01feff89be7244176087d4044` を各回答に記録。
- Grok/Museの独立モデル実行は **NOT_RUN**。Reason Networkの接続を今回確認したが、`link_id must identify an eligible linked account` で一覧取得に失敗。これをモデルの実行・409エラーと混同しない。同条件のモデル間比較は **NOT_ESTABLISHED**。

## 5. 金子さんフィードバック・舞台への意味
- 電話先のAI救急係という観客に伝えるべき設定と開始合図（ダイスの「痛い！」先行）、第一声・第二声の原文一致、アドリブのキャラクター回収、ダイスの身体演技への余白を維持。稽古後の講評を舞台の演技量に混ぜないことで評価データの解釈を改善。
- 声の後方可聴性／設定理解率／実機Voiceによる20回反復／舞台の笑い・身体演技／ダイス以外の声への誤反応／初回ボケの本当の発声時刻は**NOT_MEASURED**。本番で良くなったという結論を出さない。
- 確定台本『痛い痛い！』v8 `comedy/sagi-injury-help.md`、9/6確定稿 `comedy/sagi-denwa-2026-09-06-live.md`、現行2分稿 `comedy/sagi-injury-help-2min-live.md`、Skill本文は今回無変更。

## 6. 保護するGit blob SHA（起点）
- v8: `099ab68381e23f838299a9706c64f82bfc2dce1d`
- 9/6確定稿: `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`
- 現行2分稿: `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`
- Skill: `fe21da855d08d5d01feff89be7244176087d4044`

次の必要作業は、適切な同意・権限で集めた実際の録音／動画に時刻注釈を付け、台本外の講評がない統一した記録単位で反復評価すること。機械的PASSと観客の笑いは別管理する。
