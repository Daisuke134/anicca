# Comedy AI 内部研究：AIのボケ後、ダイスが再び話すまでの余白（2026-11-23 JST）

## 正本と研究モード
- 正本: `Daisuke134/anicca` `main` の `ac1593181ad98b5ac397ab86a547924cb8d065c1` を基準としてブランチ作成。
- 読込: `comedy/AGENTS.md`、`skills/comedy-agent/SKILL.md`、`comedy/COMEDY-AGENT-LOOP.md`、`comedy/benchmarks/README.md`、`comedy/IMPROV-PLAYBOOK.md`、`comedy/feedback/KANEKO-2026-11-15.md`。
- Skill v0.2.1 blob SHA: `fe21da855d08d5d01feff89be7244176087d4044`。台本／Skillの原文は変更しない。
- モード: 内部RESEARCH/EVALのみ。外部公開・自動返信とも `publish_enabled=false`, `auto_reply_enabled=false`。

## 仮説と根拠
金子さんのフィードバックでは、AI音声だけでなくダイスのリアクション・身体演技の笑いを重視する。以前のAI発話占有率は声量のバランスを測る一方、AIのボケ後にダイスの発話開始までどれほど空間があるかは計測していなかった。
自然会話のターン交代に関する研究（Stivers et al., 2009, PNAS, https://doi.org/10.1073/pnas.0903616106）とライブコメディのタイミング分析（Pope, Stewart & Chew, 2026, PNAS Nexus, https://visualize.jove.com/41567929-timing-structures-in-live-comedy-a-matched-sequence-approach-to-mapping-performance-dynamics）を発想の参考にした。ただし日常会話での高速な応答は舞台コメディの「適切な間」の閾値を正当化しない。

## 実装
`comedy/benchmarks/measure_stage_timing.py`に以下を追加。
- `dais_reentry_gap_ms`: AIの発話が終了してから次のダイスの**通常発話が始まるまで**を記録。正は無音の可能性がある時間差、負は発話重なり。話者イベント番号を併記。
- `dais_reentry_gap_median_ms`: 上記ギャップの中央値。該当発話なしならnull。
- `--min-dais-reentry-gap-ms N`: **オプトイン**でNミリ秒未満を `dais_reentry_below_opt_in_target` としてFAIL。NぴったりはPASS。未指定なら従来の合否に影響しない。負値・真偽値・小数は拒否。
- 開演・終幕の合図、観客の笑いラベルをダイスの通常の返答として数えない。ひとつのAI発話に対する最初のダイス返答を記録。
- `dais_reentry_is_physical_acting=NOT_MEASURED`: 時間差は**身体演技・客席の笑い・音声の聞き取り・舞台の好適性そのものではない**。

## 実行した合成テスト
`2026-11-23-0051-reentry-synthetic-input.json`（人工時刻の7イベント）を使い、AI終了→ダイス開始の差分は **100ms, 200ms**、中央値 **150ms**。
- デフォルト: タイミングPASS / CLI `--strict` 終了コード0。
- 任意の最小閾値100ms: PASS（境界一致）。
- 任意の最小閾値101ms: タイミングFAIL / CLI `--strict` 終了コード1。違反1件。
- AIの話にダイスが400ms被せたケースは報告値 -400ms、閾値未設定なら別途タイミングFAILにしない（演劇上の意図的な被せもありうる）。
- 新規7単体テストを追加、`test_measure_stage_timing.py` **50/50 PASS**、`test_validate_stage_dialogue.py` **22/22 PASS**、`check_injury_2min.py` PASS。**実行したPythonのみを成功と記録**。
- これらは録音やVoiceモデルの観測ではなく**人工注釈に対するコードの動作試験**。101msも舞台の推奨閾値ではない。

## 新作オリジナル題と生成（固定ベンチは未使用）
新規権利確保済みの内部オリジナル題を8件（一般大喜利4件・電話先AI即興4件）独自作成し、各2候補、合計16件のテキストをChatGPT GPT-6**このチャット内**で生成した。`...reentry-tasks.jsonl`に全文、`...reentry-responses.jsonl`に全16回答・原文・version・Skill SHAを保存。
`validate_run.py --strict`で形式・長さ・非質問・既出人物アンカーのハードゲート **16/16 PASS**。これは面白さの評価でも同条件のモデル間比較でもない。生成努力・temperatureは統制していない。第三者の人間評価と実際の笑いを採点していない。
Grok/Museは実行していない。Reason Networkの3接続は本実行時 `409 agent_network_offline`、よって**外部モデル比較は未成立**。接続されていないモデルの出力、遅延、採点は作らない。

## 金子さん指摘との対応・未解決
1. 開始合図はダイスの「痛い！」先行、AI第一声と第二声は現行2分稿の完全一致契約を維持。今回はテキスト正本未変更で静的台本検査PASS。
2. 電話先のAI救急指令員という設定、キャラ回収、「救急車は来ない」の因果を短い即興候補で設計。実際に観客が理解したかは未測定。
3. AIが喋りすぎない・ダイスが反応できる間は今回のギャップ報告で補足。ただし無言の身体演技は動画で別注釈が必要。
4. 音声の後方可聴性、再演のばらつき、観客の笑い、第三者の声で誤起動しない率、実機Voiceの遅延は全て **NOT_MEASURED**。
5. 20試行の開始合図再現・冒頭の完全一致・聞き取り調査・台本外アドリブの独立試行は未実施。

## 不変条件・公開境界
Git blobを基準SHAと変更後で比較する:
- 原典 `comedy/sagi-injury-help.md`: `099ab68381e23f838299a9706c64f82bfc2dce1d`
- 9/6確定稿 `comedy/sagi-denwa-2026-09-06-live.md`: `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`
- 2分稿 `comedy/sagi-injury-help-2min-live.md`: `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`
- Skill: `fe21da855d08d5d01feff89be7244176087d4044`。

外部X・大喜利サイトへの投稿／自動返信／応募は実行なし。音声や個人情報は公開リポジトリへ保存していない。タイムスタンプ注釈の有効性は映像・音声を用いた将来の独立検証を要する。
