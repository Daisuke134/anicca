# Comedy AI 内部研究：AI単独発話の尺を測る・制限する（2026-11-22 23:01 JST）

## 正本・実行条件
- GitHub `Daisuke134/anicca` `main` 基点：`5ea3222c3280c5a96172e9eedb1b733e3576ca73`。
- 読込：`comedy/AGENTS.md`, `skills/comedy-agent/SKILL.md`, `comedy/COMEDY-AGENT-LOOP.md`, `comedy/benchmarks/README.md`, `comedy/IMPROV-PLAYBOOK.md`, `comedy/feedback/KANEKO-2026-11-15.md`。
- Skill v0.2.1 blob SHA：`fe21da855d08d5d01feff89be7244176087d4044`。Skill本文・v8・9/6確定上演稿・2分実演稿は未改変。
- 発想生成：このChatGPT会話のGPT-6テキスト出力。APIによるモデルの独立呼び出し・反復サンプリングではない。プロバイダ内部build ID・temperature・effortは利用不能（NOT_EXPOSED）。Grok/Muse/Reasonは未実行、比較勝者なし。
- 開発題：**完全新規オリジナル8題（大喜利4＋電話先AI即興4）、固定ベンチ未使用**。作品権利は今回生成のオリジナル内部研究、外部の第三者ネタ未取得。

## 課題：二人の掛け合いの余白をAIが占有する
金子さんの「AIばかりが面白くならない／人間側の身体反応を生かす」「後ろまで聞き取れること」、開始合図の遵守、電話先AI役、アドリブの既出人物回収を評価対象とする。以前の評価では `ai_turns > 2 && 句点数 > 3` を長い発言の近似としていたが、短い単文でも長時間かけて話すケースは文字数では発見できない。舞台用には時間軸の直接監査が必要。

`measure_stage_timing.py` に**任意指定**の `--max-ai-turn-duration-ms` と `ai_turn_duration_ms`（イベントごとの継続時間）、`ai_turn_duration_max_ms` を追加した。`end_ms-start_ms` に基づき、閾値を**超えた場合のみ** `ai_turn_exceeds_duration_target` とする（等号はPASS）。未指定時は計測だけで従来の合否に影響なし。値は非負整数だけ（真偽値や浮動小数はエラー）。ラベルの手動時刻のみであり、**実際の音声を解析・補正したわけではない**。

## 実際に行った検査
- Python 3.14.7, macOS。標準ライブラリ `python3 -m unittest discover -s comedy/benchmarks -p 'test_*.py' -q`: **81/81 PASS**（このサイクルで5件追加）。CLI strict の終了コードも境界（3999ms FAIL / 4000ms PASS）で確認。
- `python3 comedy/benchmarks/check_injury_2min.py`: **PASS**、22ターン・台本文字数714。これは**静的台本検査**であり音声の合否ではない。
- 合成時刻入力 `runs/2026-11-22-2255-jst-ai-turn-synthetic-input.json`：第2AI発話4000ms、第3AI発話6000ms、第三声は1文。**閾値未指定**では text=PASS / timing=PASS / strict exit=0。**試験用閾値5000ms** では text=PASS / timing=FAIL / strict exit=1。検出は `event=5, duration_ms=6000`。5000msは本番の推奨上限・人間の笑いに基づく閾値ではない。
- 新作8題×2候補=16件を `validate_run.py --strict` でオフライン形式評価：**16/16 PASS・未提出0**。内容の面白さ・新奇性・音声出力の質は採点していない。候補1と候補2を異なるrun_idに分け、`run_id/model/task_id`重複の偽PASSを防止した。
- 観客の笑い、音量・明瞭性、電話先AI設定の理解、Daisの身体表現、実機Voiceの遅延・上演再現性：すべて **NOT_MEASURED**。

## 保存したデータ
- `comedy/benchmarks/runs/2026-11-22-2255-jst-turn-budget-original-tasks.jsonl`: 新規開発8題。固定ベンチとは別。
- `comedy/benchmarks/runs/2026-11-22-2255-jst-turn-budget-original-responses.jsonl`: 16候補の全文、生成元・モデル版・Skill blob SHA・未測定。
- `comedy/benchmarks/runs/2026-11-22-2255-jst-turn-budget-original-report.json`: 実行した形式ゲートの結果。
- `comedy/benchmarks/runs/2026-11-22-2255-jst-ai-turn-synthetic-input.json`: 合成データ（録音ではない）。
- `comedy/benchmarks/runs/2026-11-22-2255-jst-ai-turn-baseline-report.json`、`...-optin-report.json`: 同一合成入力で閾値の有無のみ変更した機械評価。

## 未解決・研究上の限界
- 現時点では実録音に手動で区間を付けたものがなく、`max_ai_turn_duration_ms` を最適化する根拠はない。場面や台詞の種類（第一声・長めの病名・通常の短い回収）による上限の違いも未検証。
- 句読点や形式のPASSは「面白い」ことを意味しない。候補A/Bを同じ会話が作成しているので、独立実験・無作為化・ブラインド人間評価の代わりにはならない。
- 舞台での合図前の無言、AI役の維持、他者の音声への無反応、終幕後の無音、現実の安全例外は既存ゲートを維持。追加ルールで置き換えない。
- 公開／応募／自動返信の実行は一切なし。`publish_enabled=false`、`auto_reply_enabled=false`、`DRAFT_ONLY`。権利・規約・専用アカウント・用途の許可未確認のため変更しない。
- 台本『痛い痛い！』v8 = `099ab68381e23f838299a9706c64f82bfc2dce1d`、9/6確定上演稿 = `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`、現行2分稿 = `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`。これらのblob SHAが変わらないことをmerge後に再確認する。
