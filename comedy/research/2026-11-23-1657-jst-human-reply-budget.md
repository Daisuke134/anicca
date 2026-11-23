# Comedy AI 1-cycle: 人間の返しを奪う長文AIターンの検出

- 実行: 2026-11-23 17:04 JST（研究開始16:57 JST）
- Source of truth: `Daisuke134/anicca` `main`（実験開始時点）
- モード: **RESEARCH / EVAL（テキスト）**。STAGE/Voiceは実行していない。
- 問題セット: **新しいオリジナル内部開発題8題**（一般大喜利4、電話先AI即興4）。公開固定ベンチは今回**未使用**。
- 権利: この回に独自作成したお題・回答。第三者サイトや既存作品の文面は取得・転用していない。
- 公開設定: `publish_enabled=false`, `auto_reply_enabled=false`。X投稿・コンテスト投稿・外部返信はゼロ。

## 観察した評価上の欠陥

`validate_stage_dialogue.py` の既存 `long_ai_turn_proxy` は、AIの句点 `。` が **4個以上**のときに発火する。しかし**句点1個で122文字**という長い台詞は従来PASSし得ていた。この場合ダイスが反応する舞台上の余白が失われる可能性がある。金子さんの「人間の演技を笑いの柱に」「AIの声が小さく聞き取りづらい」という指摘を踏まえ、速度と聞き取りやすさを独立に測る必要がある。

## 変更（台本は変更せず）

1. `validate_stage_dialogue.validate(..., max_ai_turn_chars=None)` に **任意の文字数ゲート**を追加。未指定なら従来動作を保持し、真偽値・負値・0・非整数は拒否。
2. `audit_stage_composite.evaluate` は冒頭の正本第一声・第二声**以降のAI発話だけ**に **96 Unicode文字**上限を適用。超過は `ai_turn_exceeds_char_budget_proxy` でFAIL。台本固定の冒頭二発話は検査対象外。
3. 各AI発話の `ai_turn_char_counts` と設定した予算を出力。**文字数は秒数、TTS発話速度、笑いの間、後方可聴性の測定ではない**。

96という値は初期の保守的なレビュー閾値で、最適な芸のテンポを実測して決めた数値ではない。選定された2分稿ではAI発話の最大が**68文字**で、現行台本に過敏にFAILを出さない値である。今後、人間のリアクションを遮らないかはVoiceと稽古を録音して検証する。

## 実行した検査

- 旧ゲート相当 `validate(events, require_turn_coverage=True)`: 一文122文字の人工ケースを **PASS**。
- 新総合 `evaluate(events, chains, require_adlib=True)`: 同じ人工ケースを **FAIL** (`ai_turn_exceeds_char_budget_proxy`)。コールバック・アドリブ回収の字面ゲートはどちらもPASSで、**舞台ゲートだけが失敗を発見**。
- 通常の人工舞台対話は総合PASSのまま。
- `python3 -m unittest discover -p 'test_*.py' -q`: **100/100 PASS**（既存94、新規6）。これは監査器の単体テストでありモデル性能の100%ではない。
- `check_injury_2min.check`: **0件問題**。原稿22発話、計714文字。AI発話最大68文字。**音声の2分達成は未測定**。
- 新規オリジナル内部開発題 **8題×2候補=16回答**。 `validate_run.run` による形式/文字数/質問記号/必須固有名詞チェック **16/16 PASS**。人間による面白さ評価は **0件**。
- 正規化されたレポート: [回答形式判定](../benchmarks/runs/2026-11-23-1657-original-format-report.json)、[お題](../benchmarks/runs/2026-11-23-1657-original-tasks.jsonl)、[全回答](../benchmarks/runs/2026-11-23-1657-original-responses.jsonl)。

## 比較出自と未測定

| 事項 | 状態 |
|---|---|
| ChatGPT | このチャットのGPT-6製品ラベルで16テキスト案を作成。正確なビルドIDは取得不可。temperature/effortをAPIで固定した独立実行ではない |
| Grok / Muse | Reason Networkの3接続でHTTP 409 `agent_network_offline`。**未実行** |
| モデルの同条件ランキング | `NOT_COMPARABLE`（独立モデル呼出しはゼロ） |
| Skill | v0.2.1、Git blob SHA `fe21da855d08d5d01feff89be7244176087d4044` |
| 合図前の発声、電話先AI認識、実音声応答速度 | `NOT_MEASURED` |
| 客席後方の可聴性、実際のタイミング、笑い、身体演技 | `NOT_MEASURED` |
| 舞台上での再現性、複数回の音声一致率 | `NOT_MEASURED` |
| 外部投稿・自動返信 | `OFF`、未実行 |

## 保護対象

変更しないことを前提として参照したGit blob SHA:
- `comedy/sagi-injury-help.md`（v8）: `099ab68381e23f838299a9706c64f82bfc2dce1d`
- `comedy/sagi-denwa-2026-09-06-live.md`（9/6確定上演稿）: `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`
- `comedy/sagi-injury-help-2min-live.md`: `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`
- `skills/comedy-agent/SKILL.md`: `fe21da855d08d5d01feff89be7244176087d4044`

## 参考研究と次の検証

Levinson & Torreira (2015) は自然会話におけるターン交代時間の短さと予測的な発話準備の重要性を論じる（[研究全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC4464110/)）。**200ms前後の自然会話ターン間隔をAI音声の実測値とみなさない。** UCBの[Improv 201](https://ucbcomedy.com/course/improv-201/) はGameの発展とsecond beatsを扱い、ダイスの反応を間に置く設計に参考となる。

今回のAI出力は新しい創作案だが、**モデルの重みを学習・更新したわけではない**。次回の重要課題は録音の開始/終了タイムスタンプ、AI発話秒数、ダイスの反応までの間、観客の設定理解、後方での聞き取りを、録音・録画から別々に実測すること。音声を公開リポへ無断保存しない。
