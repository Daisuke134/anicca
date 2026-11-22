# 2026-11-23 04:55 JST — 空回答・沈黙課題を誤って比較可能とする出自監査の修正

## 正本と目的
GitHub `Daisuke134/anicca` の `main` `d2db141ff69986fc23d1fe654c4c72c1b3b148c6` を開始点とし、`comedy/AGENTS.md`、`skills/comedy-agent/SKILL.md`、`comedy/COMEDY-AGENT-LOOP.md`、`comedy/benchmarks/README.md`、`comedy/IMPROV-PLAYBOOK.md`、`comedy/feedback/KANEKO-2026-11-15.md` を確認した。研究対象は比較入力の検証力であって、実際の笑いの増加ではない。

### 問題と修正
`audit_comparison_provenance.py` の従来判定は、同一タスク・試行・モデル版・Skill SHA・生成条件・レシートの形式が揃えば、**非沈黙タスクの空文字回答**でも `COMPARISON_INPUTS_AUDITED` とできた。一方、観客の声への無応答を要求する `kind=silence` で発話しても検出できなかった。

タスク辞書から `kind` を参照し、①非沈黙課題の `response.strip()==""` を `empty_non_silence_response`、②沈黙課題の非空回答を `unexpected_silence_response` として出自監査に追加。沈黙タスクで本当に空回答なら許容する。スキーマと既存の正常系は保持した。**プロバイダのレシート文字列の真正性を認証する仕組みではない。**

### 実行したテスト
- Mac miniでテスト追加直後、ユニットテスト18件中3件FAIL（期待どおりのRed）。修正後18/18 PASS、`python3 -m py_compile` PASS。
- 新規の合成4ケース：通常タスクの空文字（FAIL検知）、空白のみ（FAIL検知）、沈黙タスクの空文字（許容）、沈黙タスクの発話（FAIL検知）。
- 2分台本 `check_injury_2min.py` の静的検査 PASS。これはAIの第一・第二声と舞台進行の文字列検査であり、Voiceの発話成功ではない。

### 新規オリジナル開発題の実験（固定ベンチ未使用）
- `comedy/benchmarks/runs/2026-11-23-0455-tasks.jsonl`：合法な社内オリジナル8題（一般大喜利4、ダイスと電話先AIの即興4）。既存サイトからの複製・第三者ネタの投稿なし。
- `...-responses.jsonl`：同一チャット内ChatGPT GPT-6による各2候補、全16回答全文。推論パラメータ・正確なデプロイビルド・provider receipt は未取得。独立API試行ではない。モデル表示は `ChatGPT GPT-6`、正確なbuildは `NOT_AVAILABLE`。
- `validate_run.py --strict`：16/16文字数・形式・禁止語ゲートPASS。
- `audit_comparison_provenance.py`：`NOT_COMPARABLE`。`fewer_than_two_models`, `no_verified_independent_invocation`, `missing_provider_receipt`, `missing_version_or_skill_sha`, `missing_generation_setting`, `invalid_generation_setting`。
- `audit_response_repetition.py`：2026-11-23 04:02の過去16回答と比較、最大3-gram Jaccard **0.135135**、閾値0.70で内部・過去の近重複フラグ0。これは表記上の要確認判定だけで意味的独創性の保証ではない。
- Skill blob SHA：`fe21da855d08d5d01feff89be7244176087d4044`、Skillの参照元mainコミット：`d2db141ff69986fc23d1fe654c4c72c1b3b148c6`。Skill本文は編集しない。

### 金子さんフィードバックと舞台の保護
電話先AI救急指令センターという設定、ダイスの声が最初の合図であること、ダイス以外の声に反応しないこと、第二声で即架空病名を出すこと、既出人物へのアドリブ回収、ダイスの身体演技・間、終幕後の沈黙、後方可聴性・Voice再現性を引き続き別々に評価する。今回の監査修正は、第三者音声に対する無応答を**文字ベースの入力**として検証できる方向の前進だが、実機の話者分離を保証しない。

保護対象の開始時点のGit blob SHA：
- 長尺『痛い痛い！』v8 `comedy/sagi-injury-help.md`：`099ab68381e23f838299a9706c64f82bfc2dce1d`
- 9/6確定上演稿 `comedy/sagi-denwa-2026-09-06-live.md`：`036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`
- 現行2分稿 `comedy/sagi-injury-help-2min-live.md`：`892ce8db0cc84eece3a64ecf661a7fdc90cc5784`
- 共通Skill `skills/comedy-agent/SKILL.md`：`fe21da855d08d5d01feff89be7244176087d4044`

### 未実行・禁止操作
Reason NetworkをPrimary / DAISUKE / MKの3接続で再確認したが、いずれもHTTP 409 `agent_network_offline`。そのためGrokとMuseの出力は一つも生成しておらず、横比較も順位付けも行わなかった。観客の笑い、ライブ音声の反応速度・明瞭度・再現性、第三者音声の認識、金子さんの指摘に対する舞台改善効果、AIとダイスの身体動作による笑いはすべて `NOT_MEASURED`。外部X、大喜利サイト、返信、応募は実行せず、`publish_enabled=false` と `auto_reply_enabled=false`。

**結論：** 実行済み合成回帰テストにおける比較入力監査の偽陽性を改善した。Comedy AIの基盤モデルが学習・改善された証拠や、舞台で笑いが増えた証拠ではない。
