# 2026-11-24 01:00 JST — 独立モデル比較の資格監査：部分的なメタデータを順位に変えない

## 要旨と結論

- **実際に比較できた独立モデルは0組**。ChatGPT（製品ラベル GPT-6）の単一チャットで**新規オリジナル開発題8題×2候補＝16回答**を作成した。独立API呼び出しの証拠はなく、正確なモデルビルドとtemperature/effortは未取得。
- 新たな \`comedy/benchmarks/audit_run_comparability.py\` は、**2モデル以上、タスクと候補の網羅一致、Skill blob SHA、モダリティ、生成設定、モデル版、独立実行の申告とレシート**を機械的に点検する。結果は \`NOT_COMPARABLE\` または \`CONDITIONALLY_COMPARABLE_RECEIPTS_UNVERIFIED\`。後者も**独立プロバイダによるレシート真正性の検証はしていない**ことを明記。
- 既存 \`validate_run.py\` の静的形式ゲートは16/16 PASS。新規テスト12件を含む \`python3 -m unittest discover -p 'test_*.py' -q\` は**309/309 PASS**（macOS Python 3.14.7、元コミット \`545331aad8fe5d6a7388003856e787aac43cbca5\`）。
- Grok/Muse：Reason Networkの3接続すべて **HTTP 409 \`agent_network_offline\`**。Mac miniの \`reason network doctor\` はローカルデーモン稼働と表示したが、**Reason relayはReason CLI未ログイン**と出た。モデルへの評価リクエストは送信していない。ChatGPT自体も独立API評価ではない。
- Voice音声録音、笑い、設定理解、後方可聴性、アドリブ回収の実演、2分間の再現性はすべて **NOT_MEASURED**。publish/auto-reply/応募は OFF・実施0。

## 正本と保護対象

2026-11-24の作業前に \`main\` の6文書を確認：
\`comedy/AGENTS.md\`、\`skills/comedy-agent/SKILL.md\`、\`comedy/COMEDY-AGENT-LOOP.md\`、\`comedy/benchmarks/README.md\`、\`comedy/IMPROV-PLAYBOOK.md\`、\`comedy/feedback/KANEKO-2026-11-15.md\`。

保護対象の開始時Git blob SHA：
- 長尺v8 \`comedy/sagi-injury-help.md\`: \`099ab68381e23f838299a9706c64f82bfc2dce1d\`
- 9/6確定上演稿 \`comedy/sagi-denwa-2026-09-06-live.md\`: \`036a10a7a0cd103663c48b56b9ab5137b3f2c4b9\`
- 2分舞台稿 \`comedy/sagi-injury-help-2min-live.md\`: \`892ce8db0cc84eece3a64ecf661a7fdc90cc5784\`
- 共通Skill \`skills/comedy-agent/SKILL.md\`: \`fe21da855d08d5d01feff89be7244176087d4044\`

いずれも編集せず、金子さんの「電話先AI」「ダイスの合図が先」「人間の身体演技」「声の後方可聴性」を今後の舞台評価対象として保持。舞台での冒頭第一声・第二声の固定も変更しない。

## 開発セット（固定ベンチではない）

今回の8題はすべて本サイクル独自の **\`NEW_ORIGINAL_INTERNAL_DEV\`**。他者のネタを転記せず、公開サイト題を流用しない。**固定ベンチ \`taskset-v1.jsonl\` は使用していない**。

- 一般大喜利4題：「行列のレンタル」「昨日の影の回収」「ハサミ面接官」「タクシーの通訳」。
- 電話先AIアドリブ4題：「右ひざの婚姻届」「おもち34号の帰還」「右折田まっすぐと左出口」「会田アイタロウの席次表」。
- 各題A/Bの2テキスト候補。全16出力をそのまま保存。形式チェックは文字列の必須アンカー、文字数、禁止語等のゲートのみ。A/Bの優劣・笑いは未判定。

入力と全文：
- [8題・権利とカテゴリ](../benchmarks/runs/2026-11-24-0055-original-tasks.jsonl)
- [16回答・生成出自とモデル表記](../benchmarks/runs/2026-11-24-0055-chat-responses.jsonl)
- [形式ハードゲート結果](../benchmarks/runs/2026-11-24-0055-formal-gates.json)
- [独立比較の資格監査](../benchmarks/runs/2026-11-24-0055-comparability.json)

## 新規コード・回帰テスト

\`audit_run_comparability.py\` はオフラインの入力記録だけを審査し、以下を区別：

1. **自己申告が不完全**：ChatGPTのチャット内生成を「独立プロバイダ呼出し」とみなさない。Model product label \`EXACT_BUILD_UNKNOWN\` は正確なbuildとみなさない。\`provider_receipt=null\` は証明不能。
2. **モデル数・タスク数・候補数**：片方だけ欠けた問題／候補を均衡した比較とみなさない。
3. **前提条件**：別Skill blob、音声vsテキスト、異なるtemperature/effortを同条件とみなさない。不明値も比較不能。
4. **保守的な限界**：架空のレシート文字列を入力する人工正例でも \`CONDITIONALLY_COMPARABLE_RECEIPTS_UNVERIFIED\` としか返さない。実際にそのモデルを接続した証明でも、面白さのランキングでもない。

実行テスト：新規12/12 PASS。例：非独立生成、build未知、レシート欠落、モデル数不足、候補欠落、Skill不一致、設定不一致、重複回答、モダリティ不一致、publish=trueの検出など。全既存テストと合わせ309/309 PASS。

**実出力結果**：\`comparison_eligibility=NOT_COMPARABLE\`、\`response_count=16\`、\`task_count=8\`、\`model_count=1\`、独立呼出しレシート検証なし。独立モデル勝敗・精度・人間評価・笑いはどれも測っていない。

## 金子さんのフィードバック／舞台品質への位置づけ

今回の変更は生成能力や音声品質の向上ではなく、**比較が成立したと誤認しないための計測上の改善**。舞台実装を壊さないよう台本・Skill本文・上演制御を変更していない。今後実機の20試行を行うなら、録音と端点注釈によって開始合図→AI第一声→固定第二声の厳守、第三者非反応、電話先AIの観客認識、固有名詞の後方明瞭性、ダイスの身体反応とAI発話それぞれによる笑い、既出人物の回収を別軸で記録する必要がある。

参考：Stanford CRFMのHELMが共通シナリオ・条件・出力開示を重視すること（https://doi.org/10.1111/nyas.15007）。本研究はその思想を参考にした**内部の独自監査**でありHELMの成果を再現したものではない。

## 残課題・禁止事項

- Reason Network relayのCLIログイン不備でGrok/Muse未実行。独立したChatGPT APIレシートもなし。
- レシートが存在しても真偽を外部検証する実装はない。推論設定の等価性、レイテンシ、コストも未評価。
- 観客の笑いとモデルの面白さの自己採点は行わない。
- 外部X投稿・自動リプ・大喜利サイト応募・大量応募・外部サイト規約外アクセスは実施しない。 \`publish_enabled=false\`、\`auto_reply_enabled=false\` を維持。

## 再現コマンド

\`\`\`bash
cd comedy/benchmarks
python3 -m unittest discover -p 'test_*.py' -q
python3 validate_run.py --tasks runs/2026-11-24-0055-original-tasks.jsonl --responses runs/2026-11-24-0055-chat-responses.jsonl --output /tmp/comedy-formal-gates.json --strict
python3 audit_run_comparability.py --tasks runs/2026-11-24-0055-original-tasks.jsonl --responses runs/2026-11-24-0055-chat-responses.jsonl --output /tmp/comedy-comparability.json
\`\`\`
