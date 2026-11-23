# Comedy AI研究: コールバックが「名前を再登場させただけ」にならないための複数ターン監査

日時: 2026-11-23 14:55〜15:02 JST / モード: RESEARCH + EVAL / 正本: GitHub `Daisuke134/anicca` main (開始時確認: `83403814b0efef7f932d4acc95739f6770e78d0c`)

## 今回の問いと結果

前回までの `audit_adlib_anchors.py` は、**ダイスの直前の発話**をAIが人物名と行動語で拾ったか、否定・予定・質問を実行済みと取り違えないかを調べる。しかし、**数ターン前に仕込んだ「おもち34号は式場に行った」が後半で「新婚旅行の荷物になった」に発展したか、途中で突然ダイスの場所へ到着していないか、ダイスがリアクションする発話を挟んだか**は測れなかった。

新規 `audit_callback_continuity.py` を追加。完結したテキスト発話列と人手で明示的に注釈した `setup_ai_event` / `callback_ai_event` / `entity` / `setup_any` / `payoff_any` / `forbidden_after_setup` を照合する。これにより、仕込み→ダイスのリアクション→後半の回収の**語句・発話順の代理ゲート**を設けた。

自動検査: 前振り／後半で同じ人物・車両が存在するか、後半で新しい結末語があるか、間にダイスの発話があるか、事前注釈した特定の矛盾表現が後続のAI発話に現れるか、AIがダイスを挟まず連続発話しないか、開始合図前と終幕後に発話しないか。どの項目も文脈理解・コメディ評価ではなく**字面と発話順**だけの検査。

## 再現済みのテスト（Python 3.14.7 / Mac mini）

- 新規 `test_audit_callback_continuity.py`: **19/19 PASS**。入力の不正や注釈なしのケースも「合格」にしない。
- 既存 `test_audit_adlib_anchors.py`: **26/26 PASS**。合計**45/45**。前回の即時アドリブ回収検査への影響は観測されなかった。
- 明示的な `source_type=synthetic` の**人工8ケース**: **8/8 期待判定と一致**。正常2ケース、意図的な失敗6ケース。失敗例は「後半で名前を忘れる」「後半に結末語がない」「救急車が突然到着する」「ダイスのリアクションがない」「AI連続独演」「終幕後に勝手に喋る」。正常例は「式場→新婚旅行へ展開」「観客の笑いが間に入るがダイスの発話は維持」。
- 最初の人工8例では観客の笑いをダイスの発話と**置換**したため7/8一致になった。これは設計上正しいFAILだった。人工入力を修正して笑いを別イベントとして**挿入**し、ダイスのリアクションを保持して再実行したところ8/8一致。入力修正履歴を隠していない。
- **新規オリジナル開発題8題**（一般大喜利4題・電話先AI即興4題）に各2案、計**16テキスト候補**を同じChatGPT製品セッションで作成。**固定ベンチは未使用**。`validate_run.py --strict`: **16/16形式PASS、未提出0**。文字制限、禁止句、人物名などのハードゲートだけの成績。
- `audit_comparison_provenance.py`: **`NOT_COMPARABLE`**、理由 `fewer_than_two_models`, `invalid_generation_setting`, `missing_generation_setting`, `missing_provider_receipt`, `no_verified_independent_invocation`。この単一のチャット生成を外部独立API比較とは呼ばない。
- `check_injury_2min.py`: **PASS**、22発話・714文字（静的台本チェック）。実際の上演時間が2分になったことは未測定。

## モデル出自・権利・使用制限

- 生成元: このChatGPT製品に表示された **GPT-6**。正確なビルドID、temperature、effort、token上限、provider receiptは**未取得／NOT_CONTROLLED**。`model_version=product_label_only_exact_build_not_exposed`。
- Skill: v0.2.1、Git **blob SHA** `fe21da855d08d5d01feff89be7244176087d4044`。生成ベースの `main` コミットを `skill_commit` として併記し、blob SHAとは区別した。
- Reason Networkの接続3件を今回直接呼び出したが、すべてHTTP 409 `agent_network_offline`。Grok・Museは**未実行**。勝敗もスコアも作らない。
- 題材は今回作成した合法な**オリジナル内部開発題**。外部サイトから回答を転載・再投稿していない。結果は公開コンテスト応募ではなくリポジトリ内研究データ。
- `publish_enabled=false`、`auto_reply_enabled=false`。Xへの投稿、無差別自動返信、第三者大喜利サイトへの応募は**未実施**。権限・規約・専用アカウントが未確認なのでDRAFT_ONLY。

## 金子さんのフィードバックと舞台への関係

- **設定の明示:** ダイスが電話し、AIは電話先の「AI救急指令センター」の役。Alexa風置物にしない。これはキャラ設定・視覚的演出設計であり、観客の設定理解度は未測定。
- **開始合図:** ダイスの「痛い！」より前にAIは喋らず、第一声 `はい、救急指令センターです。火事ですか、救急ですか？` と第二声は現行2分稿に完全一致。今回の新評価器は合図の前後の発声順も検査するが、**実機話者識別を実装したわけではない**。
- **アドリブ回収:** 即時の名前・行動ゲートと、複数ターンを跨ぐ「おもち34号：式場→新婚旅行」のコールバックゲートを分離。車両がダイスのところへ到着したという設定破綻は特定の文字列表現としてのみ検出する。
- **人間の存在感:** ダイスの発話が回収の間に入ったかを確認。**本当の間の秒数、身体演技、表情、観客の笑いに対する効果は未測定**。長いAI独演を避けるためのテキストレベルの補助。
- **音声の再現性:** 実録音がないため、マイク、音量、遅延、話者識別、客席後方可聴性、同条件の反復成功率、観客笑い、意味理解はすべて `NOT_MEASURED`。今回の人工8/8を実機成功率と誤称しない。

## 不変確認と成果物

開始時の保護ファイル Git blob SHA:
- `comedy/sagi-injury-help.md` (v8): `099ab68381e23f838299a9706c64f82bfc2dce1d`
- `comedy/sagi-denwa-2026-09-06-live.md` (9/6): `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`
- `comedy/sagi-injury-help-2min-live.md`: `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`
- `skills/comedy-agent/SKILL.md`: `fe21da855d08d5d01feff89be7244176087d4044`

これらは変更しない。PRマージ後に再取得したmainでハッシュを照合し、再実行する。PRを開いただけでは完了としない。

- コード: [`audit_callback_continuity.py`](../benchmarks/audit_callback_continuity.py)
- 回帰テスト: [`test_audit_callback_continuity.py`](../benchmarks/test_audit_callback_continuity.py)
- [新規題8件](../benchmarks/runs/2026-11-23-1455-continuity-tasks.jsonl)、[16候補全文](../benchmarks/runs/2026-11-23-1455-continuity-responses.jsonl)
- [人工入力](../benchmarks/runs/2026-11-23-1455-callback-synthetic-input.json)、[実行済み人工監査](../benchmarks/runs/2026-11-23-1455-callback-synthetic-report.json)
- [形式検査](../benchmarks/runs/2026-11-23-1455-continuity-format-report.json)、[モデル出自監査](../benchmarks/runs/2026-11-23-1455-continuity-provenance-report.json)

## 未解決と次回の研究

現在の語句一致は「おもち34号が到着しました」以外の言い換えや、否定の範囲、引用表現を確実には認識できない。真の物語状態を人間評価するなら、**別の注釈者が独立に「場面の状態・矛盾・前振り回収・リアクション余白」を確認**する必要がある。実機Voiceと観客の録音が揃うまで、測っていない音声／笑いの数値は埋めない。
