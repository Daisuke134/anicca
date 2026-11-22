# Comedy AI研究 2026-11-22 14:51 JST — 対話の系列ゲート

## 正本・SHA・未改変
main読み取り時 commit `eef9c012eded18b6ee7913e4d459dbdd188c3535`。確認：`comedy/AGENTS.md`、`skills/comedy-agent/SKILL.md`、`comedy/COMEDY-AGENT-LOOP.md`、`comedy/benchmarks/README.md`、`comedy/IMPROV-PLAYBOOK.md`、`comedy/feedback/KANEKO-2026-11-15.md`、直近2分舞台稿、失敗講評、回帰9題、評価コード。
Skill v0.2.0、参照commit `eef9c012eded18b6ee7913e4d459dbdd188c3535`、Skill blob SHA `79df70969f92223aed9746fe63cf0f919bfe6c2a`（両者は異なる）。保存対象の原典 `sagi-injury-help.md` v8 blob `099ab68381e23f838299a9706c64f82bfc2dce1d`、9/6上演稿 `sagi-denwa-2026-09-06-live.md` blob `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9` は変更していない。

## 新しい研究課題
既存 `validate_run.py` の `expected_prefix` は、第一声が正しい全文に「住所は？」を付加した出力を見逃しうる。疑問符カウントだけでは「今どこにいますか。」を見逃しうる。個別回答だけではダイスの開始合図・各ターンの応答関係・終演後の沈黙を同時に評価できない。

そこで**新しい** `comedy/benchmarks/validate_stage_dialogue.py` とテスト15件を追加。話者ラベル・start/endキューが付いたテキストについて、合図前AI発声、第一声と第二声の**全文一致**、新たなダイス発話なしの連投、終演後の発声、疑問符やよくある場所問診の定型文、4文以上の独演リスクを検査する。これは前回の「疑問符数」から**系列構造を測る**進展である。

**ローカル実行で得た実測**：`python3 -m unittest discover -s ... -p test_validate_stage_dialogue.py -v` に相当する実行が **15/15 PASS**。別途CLI `--strict` の正常合成フィクスチャは **PASS/0違反/exit 0**、異常合成フィクスチャは **FAIL/4違反/exit 1**。異常は第一声不一致、第二声不一致、疑問符ありと疑問符なしの問診。これらは**合成テキストと実際のPython実行**の証拠であり、音声AIの本番性能ではない。

- [正常合成会話](../benchmarks/runs/1451-stage-valid-synthetic.json) ・ [正常報告](../benchmarks/runs/1451-stage-valid-report.json)
- [異常合成会話](../benchmarks/runs/1451-stage-fail-synthetic.json) ・ [異常報告](../benchmarks/runs/1451-stage-fail-report.json)

## オリジナル開発題と12回答
**固定ベンチは今回モデルに流していない**。新規オリジナル開発題6題（大喜利4題：議事録の退職・時計の時間外労働・卒業証書の留年・静けさ専門の仲居。舞台即興2題：電波が震える・サイレンが逆方向）を新規作成。外部サイトから転載せず、外部へ投稿もしていない。各題2候補、計12件を **ChatGPT GPT-6 のこの会話のテキスト文脈内**で生成。生成全文・タスク・メタデータを保存した。

- [新作6題](../benchmarks/runs/1451-original-tasks.jsonl) ・ [12回答](../benchmarks/runs/1451-original-responses.jsonl) ・ [文字列ゲート](../benchmarks/runs/1451-original-gate-report.json)
- ローカルのリテラル制約（文字数、疑問符、禁止語、アンカー）チェック **12/12 PASS**。**既存GitHub `validate_run.py` をこの回で実行したと主張しない**。回答のユーモア、人間評価、実際の観客の笑いは未測定。

例：「電波まで震えてる！」→「おもち34号が電波を迎えに出発し、右折田まっすぐの四回右折でアンテナだけ基地局に戻しました。」。台本には追加していない。

## モデル条件と未実行
| 名称 | 実行状況 | 証拠・限界 |
|---|---|---|
| GPT-6（ChatGPT製品内のこの実行文脈） | 6題×2候補、テキスト12件 | `model_version=serving_build_NOT_EXPOSED`、temperature/effort/latency未取得。同一文脈での2候補で独立API・ブラインド比較ではない |
| Grok | NOT_RUN | 実モデルの返答未取得 |
| Muse | NOT_RUN | 実モデルの返答未取得 |

Reason Networkの3接続はいずれも `409 agent_network_offline`、relay最終到達の表示は2026-11-07 23:48 UTC。モデル間勝者の判定はできない。コードテスト結果とモデルベンチ結果を混ぜない。

## 金子さん講評と再現性の検証境界
開演合図、電話先AI役の固定第一・第二声、場所質問の反復、アドリブによる既出人物の回収、ダイスの身体演技の余白を**次に測るべき対象**として保持。本サイクルは合成テキストの系列評価のみ。会場後方の音量・聞き取り、音声遅延、話者誤認、実際の2分の尺、笑い、観客の「電話先AI」の理解率は **NOT_MEASURED**。実際の危険が明らかな場合は安全優先（このオフライン検査は緊急事態判別器ではない）。

**表記上の不整合**：2分実演稿の第二声の病名は `「急性ひざの里帰りスペシャル」`、AGENTS/Skillの一部抜粋は `『急性ひざの里帰りスペシャル』`。全文一致は選択済み**2分実演稿の「」**に準拠。音声では引用符の差を測れない。原典は改変していない。

判定器の入力は正しい話者ラベル付きテキストが前提。会話順だけでは観客発言への因果的応答を確証できない。疑問の言い換えや句読点揺れは検出しきれない。音声モデルの重みを訓練・改善した証拠ではない。

`publish_enabled=false`、`auto_reply_enabled=false`。X・コンテスト・大喜利サイトへの投稿、無差別返信、規約外スクレイピング、応募は行わず、内部下書きのみ。
