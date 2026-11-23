# Comedy AI内部研究 2026-11-24 03:00 JST: お題の同一性フィンガープリント

## 結論

**モデル間の比較前に、同じ `task_id` に紐づく実際の問題文が同一かを検査する仕組みを追加した。** 旧版はモデルA・Bが同じ候補ID・Skill SHA・推論設定を申告していても、モデルBへ別のお題が渡された場合を見逃した。今回の新規7件の回帰テストを含め、Python全322件がPASSした。

この改善は比較資格の*オフライン検査能力*である。モデルの実力、創造性、面白さ、実際のVoiceの改善を実証したものではない。

## 正本・権利・保護対象

- 正本: `Daisuke134/anicca` の `main`。作業開始時のmain SHA: `04867960992be85e9dba3cc126e6967b3c6d7e6a`。
- 確認した規範: `comedy/AGENTS.md`, `skills/comedy-agent/SKILL.md`, `comedy/COMEDY-AGENT-LOOP.md`, `comedy/benchmarks/README.md`, `comedy/IMPROV-PLAYBOOK.md`, `comedy/feedback/KANEKO-2026-11-15.md`。
- Skill v0.2.1 blob SHA: `fe21da855d08d5d01feff89be7244176087d4044`。Skill自体は変更しない。
- 長尺『痛い痛い！』v8 `comedy/sagi-injury-help.md`: blob `099ab68381e23f838299a9706c64f82bfc2dce1d`。
- 9/6確定上演稿 `comedy/sagi-denwa-2026-09-06-live.md`: blob `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`。
- 選択中2分舞台稿 `comedy/sagi-injury-help-2min-live.md`: blob `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`。
- 上記3台本と共通Skill本文は**編集対象外**。PRで変更しない。
- 今回の8題は全て新規オリジナルの内部開発題。固定ベンチは**使用していない**。他者の大喜利作品の転載、外部サイトへの無許可アクセス・投稿はなし。

## 発見と改修

`comedy/benchmarks/audit_run_comparability.py` に、問題文の厳密なUTF-8バイト列のSHA-256を導入する。各タスクには `prompt`、各回答には `task_prompt_sha256` を記録する。監査器は、タスクの `prompt` から自ら計算した値と回答に申告された値を照合する。

- task IDだけを同一にした問題すり替え: `TASK_PROMPT_SHA256_MISMATCH`。
- 回答側のハッシュ欠測、64桁未満、形式不正: `MISSING_TASK_PROMPT_SHA256`。
- 正本タスク側に実際の問題文がない: `MISSING_CANONICAL_TASK_PROMPT`。
- 問題文が一致する人工正例でも従来通り `CONDITIONALLY_COMPARABLE_RECEIPTS_UNVERIFIED`。ハッシュは**実際のプロバイダへ送信された文字列**の保証ではなく、申告メタデータの整合のみ保証する。

SHA入力にUnicode正規化や空白除去は**しない**。見た目が近くても一文字異なる問題は別ハッシュとなる。モデルが見た全文脈の保証には、Skill SHAに加えて独立送信ログ・レシートを別途要する。

## 実行した評価

検証場所: 許可済みMac mini上、GitHub `origin/main` のGitオブジェクトから、`comedy/benchmarks` と必須舞台契約ファイルを一時展開。Python 3.14.7。実行コードと入力はこのサイクルで実在し、テスト出力を確認した。

| 試験 | 旧版 | 修正後 |
| --- | --- | --- |
| 人工的に同条件を申告した2モデル | CONDITIONAL | CONDITIONAL |
| タスクIDは同じ、Bだけ問題文SHAを交換 | 誤ってCONDITIONAL | NOT_COMPARABLE |
| Bに問題文SHAが存在しない | 誤ってCONDITIONAL | NOT_COMPARABLE |
| 両モデルが同じ誤ったSHAを申告 | 誤ってCONDITIONAL | NOT_COMPARABLE |

出典: [旧新版の合成回帰JSON](../benchmarks/runs/2026-11-24-0300-prompt-fingerprint-regression.json)。ここに登場するA/Bモデルとレシートは**人工フィクスチャ**であり、実際のモデルAPI呼び出しはしていない。

- 比較資格テスト: **25/25 PASS** (既存18件、新規7件)。
- Python全単体テスト: **322/322 PASS**。
- 新規の大喜利4題、電話先AI即興4題: 各2回答で計**16テキスト候補**。 `validate_run.py --strict` で **16/16 PASS**、未回答題0。これは文字列・形式検査である。
- 現行2分舞台稿の静的検査: **PASS、22発話、714文字**。録音した2分の時間測定ではない。
- 実際のモデル間比較: **NOT_COMPARABLE**、理由は単一チャットのテキスト候補のみ、独立APIレシート不在、exact build・temperature・effort不明。
- 実録Voice、観客の笑い、客席後方の固有名詞可聴性、電話先のAI設定を観客が理解した率: **NOT_MEASURED**。

## 実際のモデル接続

| モデル | 実行事実 | ビルドと条件 |
| --- | --- | --- |
| ChatGPT GPT-6 | このチャット内で8題×2のテキスト案を生成、回答全文を保存 | 製品名GPT-6、exact build非公開、temperature・effort取得不可、独立APIレシートなし |
| Grok | Reason Networkの接続を試行しHTTP 409 `agent_network_offline`、今回生成なし | NOT_EXECUTED |
| Muse | 同上、今回生成なし | NOT_EXECUTED |

3つのReason接続アカウントで `list_team` がHTTP409。接続復旧や生成成功と解釈しない。

## 舞台へどう効くか

金子さんの講評および`IMPROV-PLAYBOOK.md`に従い、4つの舞台開発題は「電話先のAI救急指令センター」「固定の人物と車両の回収」「ダイスがリアクションする余白」「一手の具体的な手配と失敗」の枠内に置いた。例えばダイスの「会田アイタロウに今すぐ会わせて」への即興には、会田の面会手配と婚礼世界の悪化を回答した。候補がこの枠を**本番音声で**再現できたかは未測定。

実演上の契約は、ダイスの合図まで無言、電話先のAI役、台本第一声・第二声厳密一致、繰り返し住所質問をしない、第三者に演技として答えない、終幕後は無言、現実の緊急事態だけ安全優先。これらの改善・違反は実録で別途評価すべきであり、文字列の形式PASSと混同しない。

参照した発想法: [Improv Archive, Heightening](https://improvarchive.org/learn-improv/concepts/heightening)。既出の中心的な異常を繰り返し強める考え方を参考にしたが、今回の研究から笑いの効果は推定していない。

## 成果物

- `comedy/benchmarks/audit_run_comparability.py`: 問題文SHA照合と欠測検出。
- `comedy/benchmarks/test_audit_run_comparability.py`: 新規7ケースと既存18件。
- `comedy/benchmarks/runs/2026-11-24-0300-original-tasks.jsonl`: 新規オリジナル8題。
- `comedy/benchmarks/runs/2026-11-24-0300-chat-responses.jsonl`: テキスト16案、モデル版とSkill SHA、各問題文SHA、未測定情報。
- `comedy/benchmarks/runs/2026-11-24-0300-format-report.json`: 実行済み形式検査。
- `comedy/benchmarks/runs/2026-11-24-0300-comparability.json`: `NOT_COMPARABLE`の実行済み監査。
- `comedy/benchmarks/runs/2026-11-24-0300-prompt-fingerprint-regression.json`: 合成4比較の旧新版回帰。
- 本研究報告および `comedy/benchmarks/README.md` の追記。

## 未解決

独立プロバイダの署名済み／信頼できる送信レシートがないため、同じ入力を実際に各モデルへ送ったことまで実証できない。正確なモデルビルドと推論予算の同条件検証も未解決。Voiceの舞台実測と観客の笑いは収録・計測していない。

**publish=false、auto_reply=false、DRAFT_ONLY。** X／大喜利サイトへの投稿、無差別返信、大量応募、非公式な規約外アクセスはいっさい行っていない。
