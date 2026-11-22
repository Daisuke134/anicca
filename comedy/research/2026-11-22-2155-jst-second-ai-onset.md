# Comedy AI研究 — 第二声の開始時刻を測る静的タイミングゲート（2026-11-22 21:55 JST）

## 正本・研究課題
- 正本: GitHub `Daisuke134/anicca` main (`465681b3d5f6008fc0f86f85d0bae0f9498d7e61`)。
- 確認: `comedy/AGENTS.md`, `skills/comedy-agent/SKILL.md`, `comedy/COMEDY-AGENT-LOOP.md`, `comedy/benchmarks/README.md`, `comedy/IMPROV-PLAYBOOK.md`, `comedy/feedback/KANEKO-2026-11-15.md`, 2分上演稿、直近の再演失敗レビュー、評価コード。
- 金子さん関連の講評と再演失敗からの課題: **2往復目で具体的なボケに進む／初期30秒のボケ到達を検証できること**。既存のタイミング評価器は返答間隔は測るが、第二声の開始時刻を開演から直接測る項目がなかった。
- 変更対象は `comedy/benchmarks/measure_stage_timing.py` とその単体テスト、README、および新規研究データに限定。『痛い痛い！』v8・9/6確定上演稿・現行2分稿・Comedy Skill 本文は変更しない。

## 実装
- 明示された開始合図（Daisの `cue=start`）の `start_ms` から **2番目のAI音声イベント開始** `start_ms` までの差を `second_ai_onset_ms` として返す。
- `--max-second-ai-onset-ms N` を**任意**の評価条件として追加。 `second_ai_onset_ms > N` の場合に `second_ai_onset_exceeds_target` でFAIL。**未指定は観測値のみ**。境界ちょうどはPASS。
- 最初のジョークの実際の発声タイミングや観客の笑いを直接測るわけではない。現行2分稿では第2AI発話が意図された最初の架空病名のボケなので、**第二声の開始をボケ到達の代理指標（proxy）**として扱う。音声区間における病名そのものの開始、理解率、笑いの発生は `NOT_MEASURED`。
- 第二声欠損時は数値を捏造せず `null`。対話ハードゲートが欠損でFAILする既存仕様を維持。

## 実行済み（Mac mini / Python 3.14.7 / ローカル一時コピー）
- `python3 -m unittest -q test_measure_stage_timing.py`: **33/33 PASS**（既存28 + 新規5）。**リポジトリ全テストではない**。
- 合成の正常対話では `second_ai_onset_ms=3900`。 `max_second_ai_onset_ms=3899` で **FAIL**、`3900` で **PASS**、未指定で **PASS**。
- CLIの `--strict` を使う閾値の FAIL/ PASS (exit 1 / 0) を追加回帰テストで確認。すべて手作りの時刻注釈であり、実際の録音・音声認識ではない。

## オリジナル内部開発題・候補
- 固定ベンチ: **使用せず**。
- 本サイクルの合法な**新規オリジナル開発題8題**: 大喜利4 + 電話先AI即興4。2候補ずつ **16回答**。外部作品の転載・第三者サイトへのアクセス・外部投稿なし。
- 問題定義: [tasks](../benchmarks/runs/2026-11-22-2155-second-onset-tasks.jsonl)。候補全文と入力条件: [responses](../benchmarks/runs/2026-11-22-2155-second-onset-responses.jsonl)。
- 実際にローカルで実行: `validate_run.py --strict` は **16/16 形式ゲートPASS、未回答0、終了コード0**。 [機械レポート](../benchmarks/runs/2026-11-22-2155-second-onset-report.json)。文字数・禁止語・既出人物などのみのチェックであり**面白さは評価しない**。
- モデル: このChatGPTセッション内の GPT-6 による草案（A/B）。**独立したAPI呼び出し、同条件の確率的サンプリング、provider receipt、blind judge は存在しない**。候補A/Bは別モデル比較ではなく、同一セッション内の案。temperature、effort、API latency は `NOT_AVAILABLE`。
- Grok / Muse: **実行せず**。Reason Networkの一覧取得はリンク認証エラー `link_id must identify an eligible linked account`。ほかのモデルの稼働・出力を偽装せず、**モデル間優劣は比較不能**。
- Skill v0.2.1、Git blob SHA `fe21da855d08d5d01feff89be7244176087d4044`、開始時 main commit `465681b3d5f6008fc0f86f85d0bae0f9498d7e61`。

## リスクと次の検証
- 30秒以内という目標に対し `--max-second-ai-onset-ms 30000` を固定して録音注釈に適用すれば、少なくとも第二声の開始の遅れを検知できる。しかし**病名が観客に届いたか・初笑い発生時刻**は別個に音声の実測が必要。
- 開始合図・第一声/第二声完全一致・質問ループ・第三者の声・終幕後沈黙は従来ゲートのまま。電話先AIという役の理解、ダイスの身体演技、音声出力の後方可聴性・遅延・複数試行の再現性、観客笑い、金子さんの指摘に対する実演上の改善は**未実測**。
- `publish_enabled=false`, `auto_reply_enabled=false`。X・大喜利サイト投稿、応募、外部自動返信なし。
