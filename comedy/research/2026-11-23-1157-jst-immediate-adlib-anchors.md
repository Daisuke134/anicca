# Comedy AI内部研究 2026-11-23 11:57 JST：応答しただけで「アドリブ回収」と誤認しない

## 正本・権利・変更境界

- 開始時の正本：GitHub `Daisuke134/anicca` `main` = `30400e4708785c610cceb757b700e334df90f989`。
- 確認資料：`comedy/AGENTS.md`（blob `aa5b798ccb38cb2c3c6dd045e7a26f7adac44b09`）、`skills/comedy-agent/SKILL.md`（v0.2.1、blob `fe21da855d08d5d01feff89be7244176087d4044`）、`comedy/COMEDY-AGENT-LOOP.md`、`comedy/benchmarks/README.md`、`comedy/IMPROV-PLAYBOOK.md`、`comedy/feedback/KANEKO-2026-11-15.md`。
- 長尺『痛い痛い！』v8 `comedy/sagi-injury-help.md`（blob `099ab68381e23f838299a9706c64f82bfc2dce1d`）、9/6確定上演稿 `comedy/sagi-denwa-2026-09-06-live.md`（`036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`）、2分稿 `comedy/sagi-injury-help-2min-live.md`（`892ce8db0cc84eece3a64ecf661a7fdc90cc5784`）は**変更しない**。
- 題材は今回新作の**オリジナル開発題8題**（大喜利4、電話先AI即興4）。固定ベンチ15題は**未使用**。外部サイトからの題・投稿作品を転用しない。権利は内部オリジナル案で、外部への公開・自動投稿とは別。

## 発見した計測上の盲点

前サイクルの `validate_stage_dialogue.py --require-turn-coverage` は、ダイスの完全な台詞のあとAIの発話が1つあれば「応答あり」と数える。しかしAIが「承知しました」や「別件の手配です」と返しただけでは、ダイスの「会いたい」「誰が運転」への**具体的回収**を判定できない。

新しい `benchmarks/audit_adlib_anchors.py` は、**人手で完全な一発話単位に注釈した** `dais` イベントだけに `anchor_any`（回収すべき人物や問題）と `action_any`（手配・出動などの行動を示す複数候補）を明示し、**次のダイス発話より前の最初の非空AI回答**に少なくとも各1語が現れるか検査する。次のダイス発話の後で遅れて回収しても加点しない。観客の笑いは発話に数えず、観客の言葉が割り込んだらレビュー対象にする。注釈が一件もない入力は合格にせず FAIL、メタデータ不正は入力エラー。

これは文字列を照合する**弱い代理指標**。役柄の意味理解、ジョークの独創性、モデルの内部処理、笑い、音声を保証しない。別表現の自然な回収が誤FAILになり得るし、単語だけ並べた回答が誤PASSになり得る。独立した `validate_stage_dialogue.py` の起動、第一・第二声、終幕、第三者のハードゲートも別途併用すべきで、実機Voiceの評価に昇格させない。

## 実行済み測定

Mac mini `/tmp/comedy-20261123-1157` に少量のコード・タスク・回答とGitHub main由来の実コードを配置し、Python 3で以下を実行した（フルリポジトリのcheckoutや外部投稿なし）。

- 新規 `test_audit_adlib_anchors.py` 14/14 PASS、既存 `test_validate_stage_dialogue.py` と `test_stage_turn_coverage.py` の28/28 PASS。計 **42/42** のPython単体テストPASS。
- `validate_run.py` を実際に実行：8題×2候補=16件の**形式ゲート16/16 PASS**。大喜利と舞台の別カテゴリで既存ルールを維持。
- 今回の舞台4題×2候補=8件を、冒頭2声が正しい**合成された注釈テキスト**へ組み込んで新監査器で実行：**7/8 PASS、1/8 FAIL**。FAILは `st02-2`（右折田まっすぐに言及したが、「再手配／出動／回る」等の行動語を含まず `immediate_reply_missing_action`）。元回答を改変せず保存。期待PASS/FAILの合成fixture8件も8/8期待どおりの判定。
- 比較出自監査 `audit_comparison_provenance.py` の実行結果は **`NOT_COMPARABLE`**。理由：単一モデル、独立API呼び出し証跡なし、生成温度・努力量など未制御、レシートなし。
- 16件の生成主体は**ChatGPT製品ラベル GPT-6 の単一会話**。正確なモデルbuild、確定した生成パラメータ、個別API実行レシートはなし。別候補は独立実験試行ではない。
- Reason NetworkのPrimary/DAISUKE/MKに今回再接続を試行、いずれも `HTTP 409 agent_network_offline`。Grok / Muse は**未実行**、比較対象に含めない。

## データと再現コマンド

- 新規開発8題：`comedy/benchmarks/runs/2026-11-23-1157-original-development-tasks.jsonl`
- GPT-6チャット内案16件・モデル出自・Skill SHA：`comedy/benchmarks/runs/2026-11-23-1157-chat-product-responses.jsonl`
- 合成舞台8ケース：`comedy/benchmarks/runs/2026-11-23-1157-anchor-synthetic-cases.json`
- 実行レポート：`...-anchor-audit.json`、`...-format-report.json`、`...-provenance-audit.json`（同じrunsディレクトリ）。
- 実行：`python3 -m unittest test_audit_adlib_anchors.py test_validate_stage_dialogue.py test_stage_turn_coverage.py`、`python3 audit_adlib_anchors.py --input runs/2026-11-23-1157-anchor-synthetic-cases.json --output /tmp/anchor-audit.json --strict`、`python3 validate_run.py --tasks runs/2026-11-23-1157-original-development-tasks.jsonl --responses runs/2026-11-23-1157-chat-product-responses.jsonl --output /tmp/format.json`。
- すべて**同じSkill本文**を参照、ただしAI基盤モデルに学習が反映されたという証拠ではない。

## 金子さんの指摘と今後の評価

- **開始合図**：最初はダイス、AIは「痛い」まで待機するハードゲートを維持。今回の合成舞台は冒頭2声を固定しているが、実際の開演成功率は測定なし。
- **電話先AI**：田中ピーポー太郎が電話越しに不合理な手配を進める設定を保持。観客が設定を理解した率は未測定。
- **アドリブの回収**：直近1ターンの人物・行動の語句の取り込みを明示的に計測。形式16/16でも回収代理指標7/8となり、形式だけでは見落とす失敗を区別。
- **ダイスの間、音声再現性、後方可聴性、笑い**：舞台映像・音声・観客データなし。すべて **NOT_MEASURED**。特に7/8を音声の成功率・笑い率と扱わない。
- **安全境界**：現実の明確な緊急事態は安全対応を優先。上演中の第三者への応答禁止。X、大喜利サイト、外部プラットフォームへの投稿、無差別返信、自動応募は**0件**。`publish_enabled=false`、`auto_reply_enabled=false`。

## 次の独立検証

「同じ回答でも `anchor_any/action_any` 注釈次第で判定が変わる」ため、評価語を回答を見る前に固定するか、独立注釈者の一致率を計測すること。録音・原音声への照合、ダイスが身体表現できる間、会場後方での可聴性、観客による電話先AI認識率を別々に実測するまで能力改善は**未実証**。
