# Comedy AI 研究サイクル：AIの累積発話占有率（2026-11-22 23:57 JST）

## 対象・入力の出典と保護
- SSOT: `Daisuke134/anicca` `main`、基準コミット `8d2c894b4e46f5996277dafcc8ac53a3370bf883`。
- 必須資料を確認：`comedy/AGENTS.md` (blob `aa5b798ccb38cb2c3c6dd045e7a26f7adac44b09`)、`skills/comedy-agent/SKILL.md` (blob `fe21da855d08d5d01feff89be7244176087d4044`)、`comedy/COMEDY-AGENT-LOOP.md`、`comedy/benchmarks/README.md`、`comedy/IMPROV-PLAYBOOK.md`、`comedy/feedback/KANEKO-2026-11-15.md`。
- 保存・非改変対象：`comedy/sagi-injury-help.md` (v8; blob `099ab68381e23f838299a9706c64f82bfc2dce1d`)、`comedy/sagi-denwa-2026-09-06-live.md` (9/6確定稿; `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`)、`comedy/sagi-injury-help-2min-live.md` (`892ce8db0cc84eece3a64ecf661a7fdc90cc5784`)。Skill本文にも変更を加えない。

## 問題と仮説
前回までの `max_ai_turn_duration_ms` は「AIの各発話は短いが累積するとAIがほぼ独演している」ケースを判別しない。金子さんの講評ではダイスの身体・ツッコミの存在感が重要。即興の Give and Take（他の演者へ焦点を譲ること）という考え方を参考に、*誰がどれだけ発声したか*を注釈から測る。出典: https://improvarchive.org/learn-improv/glossary/give-and-take 。これは着想であり、特定の発話時間比率を先行研究が推奨したという意味ではない。

## 実装（台本には無変更）
`comedy/benchmarks/measure_stage_timing.py` に `--max-ai-talk-share-percent`（0～100整数、**任意**）を追加。
- `start`～`end` の手動注釈時刻にクリップ。AI/Daisごとに重複発話ラベルを区間の和集合で集計。
- `ai_stage_speaking_ms` と `dais_stage_speaking_ms` を生成。`ai_talk_share_percent = 100 × AI発声ms / (AI発声ms + Dais発声ms)` を小数3桁で報告。
- 閾値判定は丸め前の整数比で行い、超過で `ai_dominates_speaking_time`。指定がなければ計測のみ。欠損した開始/終幕や分母0は比率を `null` とし、数値を捏造しない。
- 無音のリアクション・身体演技・笑い・明瞭さ・音声データそのものは、この指標の対象外。閾値60%も今回の**合成試験用**であり、上演の最適値ではない。

## 実行結果（Mac mini / Python 3.14.7）
- `python3 -m unittest -q test_measure_stage_timing`：**43/43 PASS**（既存38件+新規5件）。
- 新たな合成入力（`test_measure_stage_timing.good()`）：AI **6100ms**、ダイス **3400ms**、AI発声占有率 **64.211%**。最大単発発話 **4000ms** なので従来の `max_ai_turn_duration_ms=5000` は PASS。
- 新ゲート `--max-ai-talk-share-percent 64 --strict` は **FAIL（exit 1）**、65 は **PASS（exit 0）**。境界・不正引数・終幕外クリップ・CLIまで自動テスト。
- 以上は**人工的な手動時刻注釈**。実際の舞台音声・ダイスの演技・笑いを計測していない。

## オリジナル開発課題・回答
- この研究サイクルで新規制作したオリジナル開発8題：大喜利4題と『痛い痛い！』の電話先AI即興4題。**固定ベンチ（taskset-v1、Oogiri-Master等）は今回未使用**。
- ChatGPT GPT-6 が現会話で各題2候補、計16回答をテキスト生成。公開サイトの設問や第三者のネタをコピーしない。再利用権限は作成者の内部草稿であり外部投稿を許諾するものではない。
- 評価 `python3 validate_run.py --tasks original-tasks.jsonl --responses original-responses.jsonl --output original-report.json --strict`：**16/16形式PASS**、欠損0、ただし笑いの点数は `NOT_MEASURED`。
- 比較可能な外部API/音声モデル実行は成立せず：Grok/Muse **NOT_RUN**。GPT-6候補も同一ChatGPT会話内で同時生成したため独立API反復とは扱わない。公平なクロスモデル比較／勝敗は `NOT_MEASURED`。
- モデル情報: `model=ChatGPT`、`model_version=GPT-6 (chat session)`、Skill v0.2.1・blob SHA `fe21da855d08d5d01feff89be7244176087d4044`、基準コミット `8d2c894...`。API receiptなし、temperature/effortは制御できず `NOT_CONTROLLED`。入力・全16回答・機械評価を個別JSONL/JSONに保存。

## 金子さんの指摘と次の検証
- 電話先AIの説明：2分現行稿の冒頭を変更せず、観客への一言説明とスマホ表示の**認識率は未測定**。
- ダイスの開始合図・AI第一声・第二声・第三者の声・終幕後無言：既存の静的/合成ゲートを維持。**実機Voice再現性未測定**。
- アドリブの回収：今回の電話先AI題4つで既出人物（おもち34号・右折田まっすぐ・会田アイタロウ）を再利用。**構造評価のみ／面白さは未測定**。
- 声量・客席後方の固有名詞理解率、観客笑い、ダイスの身体演技への反応：**未測定**。発声比率で笑いを代用しない。

## 公開・安全
`publish_enabled=false` / `auto_reply_enabled=false`。Xや大喜利サイトへの投稿・自動返信・大量応募は行っていない。専用アカウント／プラットフォーム規約／利用権限を確認できない限り今後も `DRAFT_ONLY`。現実の救急事態では安全の例外を優先。

## 成果の解釈
**実測済み**：Python合成テスト、全16回答の長さ・形式・既出名キーワード検査、GitHub変更の有無。
**未実測**：実機モデルの声、遅延、客席笑い・理解率、持続的なユーモア能力向上、外部モデルの優劣。今回改善したのは計測器の再現性と検出範囲であって、舞台での笑いの増大ではない。
