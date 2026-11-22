# Comedy AI内部研究 — 2026-11-22 15:57 JST — 第三者発話と笑い声の誤認リスク

## 正本・参照情報
正本：GitHub Daisuke134/anicca main（読み取り時 commit e15ac5b4763c056b55fb8f628cef00196c89325a）。

必須6資料（comedy/AGENTS.md、skills/comedy-agent/SKILL.md、comedy/COMEDY-AGENT-LOOP.md、comedy/benchmarks/README.md、comedy/IMPROV-PLAYBOOK.md、comedy/feedback/KANEKO-2026-11-15.md）を確認した。既存対話ゲート、単体テスト、直近の報告書も確認した。

Skill版 v0.2.0、Skill blob SHA 79df70969f92223aed9746fe63cf0f919bfe6c2a（参照mainのcommit SHAとは別）。
保護対象の長尺『痛い痛い！』v8 blob 099ab68381e23f838299a9706c64f82bfc2dce1d、9/6確定上演稿 blob 036a10a7a0cd103663c48b56b9ab5137b3f2c4b9、現行2分稿 blob 892ce8db0cc84eece3a64ecf661a7fdc90cc5784。**3稿とも改変しない**。

## バグと今回の修正
従来の validate_stage_dialogue.py は「直前イベントが観客・スタッフ」かつ「すでにダイスに回答済み」の場合だけ第三者への誤反応らしさを検出した。しかしダイスが発話した直後は last_replied_to_dais がFalseになるため、ダイス→観客の割り込み→AIの並びを見逃していた。

1. 最後のダイスの発話以降に観客・スタッフの speech が介在すると、AIの次の発話に ambiguous_third_party_speech_between_dais_and_ai を付ける。ダイスが再度発話すれば介在フラグは消える。
2. 任意のイベント属性 kind=speech/laughter/noise を導入。笑い声と雑音は第三者の speech に数えない。未指定は従来と互換の speech、未知のkindやAI/ダイスへの不適切なkindは入力エラー。
3. 開始合図、第一・第二声の全文一致、質問ループ、終幕後沈黙の検査は維持。

**このフラグは「AIが観客に応答した」との因果確定ではない。** あくまで話者アノテーション付きテキストの保守的な要レビュー警告であり、笑い声の誤ラベルは偽陽性を起こし得る。実機の話者識別・ASR・音声再現性を示さない。

## 実行した評価
実行場所：接続済みMac miniの既存作業ツリーを触らない独立clone。Python 3.14.7。

- Python unittest discover（comedy/benchmarks/test_*.py）：**38件中38件PASS**。対話ゲート単独は22/22（今回追加7テスト）。
- Python validate_run.py --strict：今回の独自開発題6問×2候補、**12/12形式ゲートPASS、欠損0、exit 0**。
- Python validate_stage_dialogue.py --strict：合成の「ダイス→観客speech→AI」は**FAIL／1違反／exit 1**、合成の「ダイス→観客laughter→AI」は**PASS／0違反／exit 0**。正常例と異常例をそれぞれ保存。
- これらはPythonで実際に実行した**コード・合成テキストの検証**。音声モデルでの上演実験ではない。

データ： [新規6題](../benchmarks/runs/1557-original-tasks.jsonl) ／ [生成12件の全文](../benchmarks/runs/1557-original-responses.jsonl) ／ [ゲート結果](../benchmarks/runs/1557-original-gate-report.json) ／ [第三者speech負例](../benchmarks/runs/1557-audience-interposition-report.json) ／ [laughter正例](../benchmarks/runs/1557-audience-laughter-report.json)。

## 大喜利・即興の候補生成と比較境界
**固定ベンチ taskset-v1 と公開Oogiri-Masterは今回モデルに流していない**。内部で新規に創作した開発題6問（大喜利4、電話先AIの初見アドリブ2）から、それぞれ2候補、合計12候補をChatGPT GPT-6の**このテキスト会話文脈**で生成し、回答全文を保存。外部サイトから転載していない。第三者サイトの投稿・大量応募は行っていない。

例：ダイス「財布から救急車のサイレンが聞こえる！」→「おもち34号が財布に駐車しました。右折田まっすぐが免許証を式場まで運んでいます。」。既出の車と職員を回収する候補。台本には追加していない。笑いが生じたという測定はない。

| 対象 | 実施状況 |
|---|---|
| ChatGPT GPT-6 | テキストで6題×2候補。serving build/temperature/effort/latency未取得。**独立APIの2反復ではない** |
| Grok / Muse | NOT_RUN。モデル応答未取得 |
| Reason Network | list_team: 409 agent_network_offline、モデル応答未取得 |
| Ollama | CLIのみ確認、serverに接続できず、モデル生成なし |

複数のモデルを同条件で実行していないため**公平なモデル間ランキング・勝率はNOT_MEASURED**。出力の文字数などの形式合格と面白さは別指標。

## 金子さん講評／舞台の改善対象
- **開始合図**：ダイスの声の前にAI発声0、第一声は「はい、救急指令センターです。火事ですか、救急ですか？」。2分稿の第二声も原文で維持。実機成功率 NOT_MEASURED。
- **電話先AI役**：観客には「ダイスが電話先のAI救急指令センターへ掛けている」と伝わる必要がある。観客の設定理解率 NOT_MEASURED。
- **音量**：後方客席で「田中ピーポー太郎」「おもち34号」が聞き取れるか、電話音声の音量・明瞭度・遅延、音声の開始・終了再現率 NOT_MEASURED。
- **アドリブとダイスの身体演技**：既出人物を行動で回収するテキスト候補を開発。実際の笑い・演技による笑い・事故的な笑いはそれぞれ NOT_MEASURED。
- **第三者の声と笑い**：今回追加した静的リスクゲートを実音声由来の話者・発話種別・時刻付きログへ拡張する必要がある。現時点でリアルタイム防止機構ではない。
- 現実の重大な緊急事態は舞台より安全を優先。この評価コードは緊急性判別器ではない。

publish_enabled=false、auto_reply_enabled=false。X・大喜利サイトへの投稿、第三者サイトへの規約外自動アクセス、無差別返信、公開GitHubへの客席録音アップロードはなし。今後は20試行の開始合図、観客割り込み、終幕、後方音量、設定理解率を現場で計測する。**モデルの重みが学習されたという主張はしない**。
