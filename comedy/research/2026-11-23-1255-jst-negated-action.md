# Comedy AI内部研究：アドリブ回収の「否定された行動」を誤PASSしない

- 実施日：2026-11-23 12:55 JST（内部研究）
- GitHub SSOT：`Daisuke134/anicca` の `main`。作業開始時commit `ae7e0d0d44ce0066d5b33c6219276c7bdfde548e`
- 対象Skill：`skills/comedy-agent/SKILL.md` v0.2.1、Git blob SHA `fe21da855d08d5d01feff89be7244176087d4044`
- 評価対象：**新規オリジナル開発題8題**（一般大喜利4、電話先AI即興4）、各2候補。**固定ベンチは未使用**。
- 出版：`publish_enabled=false`、`auto_reply_enabled=false`。X・大喜利サイト・第三者サイトには何も投稿していない。

## 問題と仮説

前回の `audit_adlib_anchors.py` は、ダイスの人物名（`anchor_any`）と動作語（`action_any`）が次のAI発話に含まれればPASSになった。しかし、例えば「**会田アイタロウへ連絡しません**」は「会田」「連絡」の両方を含むが、手配したことにはならない。舞台の電話先AIが**手配を進める**という金子さんの指摘・キャラクター設計の代理評価にとって、これは具体的な誤PASSである。

改善仮説：明示的な否定形 `連絡しません／連絡はできません／手配できない` などを、実施済み行動の字面の根拠から除外する。文章全体の意味を読めるとは主張せず、限定した日本語の否定パターンのみ補助的に識別する。

## 実装

`audit_adlib_anchors.py` に `action_mentions()` と `NEGATED_ACTION_SUFFIX` を追加。行動キーワードの各出現位置の直後に限定的な日本語否定語が続く場合、その出現を肯定的行動マッチとして数えない。否定のみの時は `immediate_reply_only_negated_action` でFAILとし、未出現（`immediate_reply_missing_action`）とは分ける。同じ発話で「連絡はできません。車を**手配しました**」なら、手配の肯定的マッチは残す。監査出力に `negated_action_mentions` を追加。

検査は文字列ヒューリスティクスのみ。否定の二重否定、婉曲表現、引用、別の行動主体、語句の分割などは解決しない。PASSを意味理解や電話先AI役の実力と同一視しない。

## 実測：ローカルPythonでのコード検証

Mac mini上でGitHub `main` の監査器・単体テストを取得し、先に4件の追加テストを書いて修正前後を比較した。

| 検証 | 実行結果 | 解釈 |
|---|---:|---|
| 修正前：元14件＋新4件 | **15/18 PASS、3件FAIL** | 意図した否定誤PASS・否定後の肯定誤集計を再現 |
| 修正後：同じ18件 | **18/18 PASS** | 指定した合成負例が正しくFAIL |
| 舞台対話の既存6件も含む `unittest discover` | **24/24 PASS** | 回帰テスト |
| 新規8題×2回答の形式ハードゲート | **16/16 PASS** | 字数・禁止表現・必要語の検査。面白さではない |
| 人工舞台会話12ケース | **12/12 期待判定と一致** | うちチャット候補8件PASS、合成の否定2件FAIL／肯定混在・肯定2件PASS |
| 同じ12ケースの舞台対話静的検査 | **12/12 PASS** | 冒頭2声の完全一致、開始合図、終幕、ダイス発話のカバレッジ |
| 2分上演稿の静的検査 | **PASS：22発話、714文字** | 音声・尺の実測ではない |

失敗ケースは修正せず記録した。音声録音・観客の笑いは**0件、NOT_MEASURED**である。

## モデル生成と比較可能性

- ChatGPT **GPT-6製品ラベル**の同一チャット内で新規オリジナル題8件について16候補を書いた。モデルの正確なAPIビルドID、温度、推論予算、独立したprovider receiptは取得できない。生成内容は `*-responses.jsonl` に全文保存。
- Reason Networkの3リンクで `list_team` を実行したが、すべてHTTP **409 `agent_network_offline`**。よってGrokとMuseは**今回も未実行**。以前の失敗に基づく推測ではなく、今回の接続試行。
- `audit_comparison_provenance.py` は **NOT_COMPARABLE**、理由：`fewer_than_two_models`, `invalid_generation_setting`, `missing_generation_setting`, `missing_provider_receipt`, `no_verified_independent_invocation`。モデル間勝敗は出さない。

## 金子さん・本番への適用範囲

- **開始合図：** 先にダイスが「痛い！」と発し、固定第一声と第二声が正確なことを人工舞台会話と静的検査で確認。実録Voiceは未検証。
- **電話先AI役：** 返答が「連絡しません」なのに「手配した」扱いする静的な誤認を減らした。役の理解度、観客がAI電話と認識する率は未測定。
- **アドリブ回収：** 登場人物・行動の字面を第一応答で検査。人間の身体演技の余白、発想の意外性、客席の笑いは未評価。
- **音声の再現性：** 音声実録がなく、後方音量、遅延、話者識別、開始前の沈黙、観客の声への反応、同条件反復稽古はすべて未測定。
- **保護された史料：** 長尺 `comedy/sagi-injury-help.md` v8（blob `099ab68381e23f838299a9706c64f82bfc2dce1d`）、9/6確定稿 `comedy/sagi-denwa-2026-09-06-live.md`（blob `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`）、2分稿（blob `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`）は**一切変更しない**。
- 金子さんの発言は不完全な音声書き起こしに由来するため逐語引用しない。

## 再現コマンド

```bash
cd comedy/benchmarks
python3 -m unittest test_audit_adlib_anchors test_stage_turn_coverage -q
python3 validate_run.py --tasks runs/2026-11-23-1255-negation-tasks.jsonl --responses runs/2026-11-23-1255-negation-responses.jsonl --output /tmp/comedy-1255-format.json --strict
python3 audit_comparison_provenance.py --tasks runs/2026-11-23-1255-negation-tasks.jsonl --responses runs/2026-11-23-1255-negation-responses.jsonl --output /tmp/comedy-1255-comparison.json
python3 audit_adlib_anchors.py --input runs/2026-11-23-1255-negation-synthetic-fixture.json --output /tmp/comedy-1255-anchor.json --strict
python3 check_injury_2min.py
```

実行結果の保存先：`comedy/benchmarks/runs/2026-11-23-1255-negation-{tasks.jsonl,responses.jsonl,format.json,comparison.json,synthetic-fixture.json,anchor-audit.json}`（実際のファイル名は下記README/ディレクトリ参照）。

**次の優先事項：** 語彙に依存しない匿名化人間評価、実機Voice録音からの第一声／第二声再現率・電話先AI認識率・客席後方の明瞭度。これらを測る前に「面白くなった」「Voiceが改善した」とは報告しない。
