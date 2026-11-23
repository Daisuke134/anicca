# Comedy AI研究: 予定・質問を「完了したアドリブ回収」と誤計上する問題を修正

日時: 2026-11-23 13:55 JST／モード: RESEARCH + EVAL／対象: `Daisuke134/anicca` の main

## 問題と変更

従来の `audit_adlib_anchors.py` は、ダイスが「会いたい」と言った直後のAI回答に「会田」と「連絡」が存在するだけで、`会田へ連絡しましたか？` も「人物＋行動あり」と誤PASSにしていた。実際に連絡した報告ではなく、質問・提案・依頼・未履行の予定であるため、金子さんの指摘した「電話先AIが実際に変な手配を進める」掛け合いの検査として不適切。

独立した正規表現 `UNCOMMITTED_ACTION_SUFFIX` を追加し、`しましたか`、`しましょうか`、`してもいいですか`、`してください`、`する予定です` 等の**限定された語形**を `uncommitted_action_mentions` に分離。これらだけの回答は `immediate_reply_only_uncommitted_action` でFAIL。別に `手配しました` と明示した場合はPASSを保持する。旧来の「否定だけならFAIL」も維持した。

これは語形に依存する**字面の代理評価**で、真の行動実行・意味理解・観客の笑いを保証しない。日本語の省略・引用・複雑な複文・皮肉・動詞活用には未対応の形が残る。

## 実測と再現条件

- Mac miniの一時作業領域でPython 3.14系を実行。GitHub mainから元コードを取得、既存18件に新規8件を追加して**修正前は26件中7件FAIL、修正後26/26 PASS**。失敗した新規テストも削除せず保存した。
- 明示的に `source_type=synthetic` とした**人工的な8例**（質問のみ、提案のみ、依頼のみ、将来の予定、否定＋質問、肯定、質問＋別の肯定手配、無関係な返答）で期待判定 **8/8一致**。これは実際の稽古・ASR・音声の実測ではない。
- **新規オリジナル開発題8題**（一般大喜利4・電話先AI即興4）×2案=16候補を単一ChatGPT会話内で作成。**固定ベンチは未使用**。`validate_run.py --strict` で形式ゲート **16/16 PASS**。面白さは未測定。
- `audit_comparison_provenance.py`: `NOT_COMPARABLE`（fewer_than_two_models, invalid_generation_setting, missing_generation_setting, missing_provider_receipt, no_verified_independent_invocation）。正確なモデルビルド、モデル温度、独立提供元レシートは未取得。
- Grok/Muse/Reason Network 3つの接続でHTTP 409 `agent_network_offline` を再確認。Grok/Museは**未実行**、複数モデルの勝敗は**評価不能**。
- 現行2分台本 `check_injury_2min.py`: **PASS、22発話・714発話文字**。これは文字列の台本チェックであり実機Voiceの結果ではない。

## 具体例（合成回帰）

- ダイス「会いたい！」→ AI「会田アイタロウへ**連絡しましたか？**」: 修正前は誤PASS、修正後 `immediate_reply_only_uncommitted_action` でFAIL。
- AI「会田アイタロウへ連絡しましょうか？」: 修正後FAIL。
- AI「会田アイタロウへ連絡しました。」: PASS。
- AI「会田アイタロウへ連絡しますか？ 代わりに車を手配しました。」: `手配` でPASS。

## 舞台との関係・保護対象

- 舞台開始はダイスの「痛い！」までAI無言、第一声・第二声は選択済み2分稿に完全一致。AIは**電話先の救急受付**、現実の119番には発信しない。観客・スタッフの声に演技として返さず、ダイスのアドリブを既出の人物・車両に結びつける。緊急事態の安全例外は維持。
- 金子さんの指摘のうち、実際に手配が進む内容かどうかの**静的代理評価**を補強した。音量・後方可聴性・導入で電話先AIと理解された割合・ダイスの身体演技・実機Voice遅延・反復再現率・観客笑いはすべて `NOT_MEASURED`。
- `comedy/sagi-injury-help.md`（v8）、`comedy/sagi-denwa-2026-09-06-live.md`（9/6確定稿）、`comedy/sagi-injury-help-2min-live.md`（現行2分稿）、`skills/comedy-agent/SKILL.md` は**無変更**。開始前のGit blob SHAはそれぞれ `099ab68381e23f838299a9706c64f82bfc2dce1d`、`036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`、`892ce8db0cc84eece3a64ecf661a7fdc90cc5784`、`fe21da855d08d5d01feff89be7244176087d4044`。
- X投稿・外部大喜利サイト応募・自動返信は**一切なし**。 `publish_enabled=false`、`auto_reply_enabled=false`、`DRAFT_ONLY`。
- 最終的なPR・マージ・main再取得はGitHub側の結果にのみ基づいて記録する。PRを開いたことだけでmain適用済みとは扱わない。

## ファイル

- `comedy/benchmarks/audit_adlib_anchors.py`、`test_audit_adlib_anchors.py`
- [新規開発題](../benchmarks/runs/2026-11-23-1355-uncommitted-tasks.jsonl)、[16出力](../benchmarks/runs/2026-11-23-1355-uncommitted-responses.jsonl)
- [人工テスト入力](../benchmarks/runs/2026-11-23-1355-uncommitted-synthetic-input.json)、[人工監査結果](../benchmarks/runs/2026-11-23-1355-uncommitted-synthetic-report.json)
- [形式検査結果](../benchmarks/runs/2026-11-23-1355-uncommitted-format-report.json)、[比較出自監査](../benchmarks/runs/2026-11-23-1355-uncommitted-provenance-report.json)
