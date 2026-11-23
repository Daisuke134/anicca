# Comedy AI研究 2026-11-24 02:00 JST：対称欠測と沈黙の比較資格監査

- 種類：**内部研究・合成回帰・新規オリジナル開発題**。固定ベンチは使用していない。
- 正本：`Daisuke134/anicca` の開始時 `main=39eb770202790472a09a185852d8e31933c32f07`。
- 比較対象：`audit_run_comparability.py` 旧main 対 今回の修正。**実モデル間の性能比較ではない**。
- Comedy Skill：v0.2.1、Git blob SHA `fe21da855d08d5d01feff89be7244176087d4044`。本文は変更しない。
- モデル：ChatGPTの**製品ラベルGPT-6**で、この会話内のテキスト16候補を制作。正確なbuild、temperature/effort、独立APIレシートは取得できない。Grok・MuseはReason Networkの3接続が409 `agent_network_offline` で**未実行**。

## 確認した正本と保護対象

`comedy/AGENTS.md`（`aa5b798ccb38cb2c3c6dd045e7a26f7adac44b09`）、`skills/comedy-agent/SKILL.md`、`comedy/COMEDY-AGENT-LOOP.md`（`a3325b5851155311a09805d443ea352a239347e6`）、`comedy/benchmarks/README.md`（`870c36fd8e920124a543d5256ac4ed70911d189a`）、`comedy/IMPROV-PLAYBOOK.md`（`5f494c648ac6a630fe932342b53c575f4349e3db`）、`comedy/feedback/KANEKO-2026-11-15.md`（`6c26deba72a978b29da3cfb1975a96d6993451ca`）をmainから読み込んだ。

保護対象の開始時Git blob SHA：`sagi-injury-help.md` v8 `099ab68381e23f838299a9706c64f82bfc2dce1d`、`sagi-denwa-2026-09-06-live.md` `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`、`sagi-injury-help-2min-live.md` `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`。今回、台本・Skillは**編集対象外**。

## 発見した実際のバグ

1. 2モデルの両方が「同じ題のB回答」を欠測した場合、旧監査器はモデル間の`(task_id,candidate)`集合が一致するだけで、`CONDITIONALLY_COMPARABLE_RECEIPTS_UNVERIFIED`を返す。両モデルが同じミスをしていても、**各題2案以上**を満たすか検査していなかった。
2. 普通のお題に空白だけを回答しても、「文字列ではある」として通した。
3. 「舞台で沈黙する」課題に実際には発話文字列が含まれても、比較資格の段階では拒否していなかった。

修正では **各題ごとの候補件数** と **課題kindに応じた空回答** を監査し、`LESS_THAN_TWO_CANDIDATES_PER_TASK`、`UNEQUAL_CANDIDATES_PER_TASK`、`EMPTY_NON_SILENCE_RESPONSE`、`UNEXPECTED_RESPONSE_TO_SILENCE` を追加した。正しい沈黙課題の空文字は許容する。出力に各モデルの `candidates_per_task` を加えた。既存の証拠の限界は維持し、APIレシートの真正性を推認しない。

## 実行結果

| 実験 | 旧main | 修正後 |
|---|---|---|
| 新規6テストを含む比較監査単体18テスト | **14/18 PASS、4 FAIL** | **18/18 PASS** |
| Python全回帰（隔離配置、選択2分稿・Skill・stage prompt同梱） | 未実行 | **315/315 PASS** |
| 新作8題×2回答、`validate_run.py --strict` | 該当なし | **16/16 形式PASS** |
| `audit_run_comparability.py` の実回答出自監査 | 該当なし | **NOT_COMPARABLE** |

関連データ：
- [新規オリジナル題8件](../benchmarks/runs/2026-11-24-0200-original-tasks.jsonl)
- [16テキスト候補全文](../benchmarks/runs/2026-11-24-0200-chat-responses.jsonl)
- [回答形式検査結果](../benchmarks/runs/2026-11-24-0200-format-report.json)
- [出自監査](../benchmarks/runs/2026-11-24-0200-comparability-report.json)
- [旧新版合成回帰](../benchmarks/runs/2026-11-24-0200-eligibility-regression.json)

`16/16` は文字数・アンカー・禁止表現等の**静的ハードゲート**に過ぎない。人間による優劣評価、爆笑した割合、観客反応、真のモデル生成パラメータ、音声遅延、Voice実機での第一声／第二声・終幕の再現率は**NOT_MEASURED**。見かけ上の空白回答も本物の無音音声の証拠ではない。

## 金子さんのフィードバックへの接続

次の稽古は **ダイスの開始合図 → 電話先のAI救急係の正確な第一声・第二声 → アドリブを既出人物の行動で回収 → ダイスの身体反応の間 → 終幕後無言**。電話先のAIという観客理解、客席後方の聞き取り、声の再現性を映像と録音で別に計測する。今回の変更は、これらの成績を測ったものではなく、**無言と欠測を混同しない比較基盤**に限定される。

参考研究：Himmi et al., *Towards More Robust NLP System Evaluation: Handling Missing Scores in Benchmarks*, Findings of EMNLP 2024, https://aclanthology.org/2024.findings-emnlp.688/ 。同論文の欠測に対する警告を動機としたが、論文のランキング手法を実装・使用したものではない。

**公開設定**：`publish_enabled=false`、`auto_reply_enabled=false`。X投稿、大喜利サイト投稿、自動返信、大量応募、第三者サイトの規約外アクセスは実施していない。外部利用規約・権限・専用アカウントは未確認のまま。
