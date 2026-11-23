# Comedy AI研究 2026-11-23 17:55 JST：ASR断片から舞台ターンを安全に復元

研究開始時のGitHub main: 247cbb843862fac6c3593d4602655d1c2864ebad
Skill v0.2.1、Git blob SHA: fe21da855d08d5d01feff89be7244176087d4044
モード: RESEARCH / EVAL（音声本番ではない）
publish_enabled=false / auto_reply_enabled=false

## 問題と新しい改善

既存の舞台対話評価器は完全な発話列を想定している。ASRで「はい、救急指令」と「センターです。火事ですか、救急ですか？」が別イベントに分断されると、正しい第一声でも誤FAILになり得る。一方、無条件に結合すればダイス以外の人の発言やアドリブの割り込みを消しかねない。

新設した comedy/benchmarks/normalize_asr_turns.py は明示的なturn_idが同じ、話者が同じ、時間順に連続するASRテキスト断片だけを厳格に連結する。最大250msの断片間ギャップは今回の人工入力用パラメータであり、実際の応答速度の合格値ではない。

第三者の発話・笑い・雑音は独立イベントとして保存。turn_id欠損、再利用、異なる話者への流用、逆転時刻、重複時刻などは不正入力として扱い、恣意的な復元をしない。正規化後は既存のvalidate_stage_dialogueを使い、開始合図、電話先AIの正本第一声・第二声、観客割込、終幕後の沈黙を検査する。

この処理は文字列の復元であり、ASR認識精度・話者分離・マイク音量・観客理解・実際の音声再現性を測定しない。原文を言い換えたり訂正したりしない。

## コードと人工ケースの実行結果

- 正本の冒頭二発話を細かく分けた合成11イベントは従来の完全発話評価器ではFAIL。
- 新規正規化後は7イベント・4連結となり、第一声と第二声を完全一致させた上で静的舞台ゲートPASS。
- 第一声に追加の住所質問がある人工負例は依然FAIL。
- 観客の発言がダイスとAIの間に挿入された人工負例は曖昧な第三者割込としてFAIL。
- 同じAI turn_idの断片の間にスタッフ発言が入った場合は、不正な非連続turn_idとして停止し、スタッフ発言を削らない。
- 新規回帰テスト17/17 PASS。GitHub main由来の従来テストを含めて263/263 PASS（ローカルMac miniの一時領域で実行、人工入力のみ）。
- CLIを実際に実行し、合成11 chunksから7 events、gate PASSを確認。入力、コード、出力JSONをGitHubへ記録する。
- これらは監査器に対するテスト結果で、Voiceが17回成功した等を意味しない。

## 新規問題・回答（外部の固定ベンチは未使用）

この研究回で一般大喜利4題（昨日の窓口、海底郵便局、転職する改札機、校長になった時計）と電話先AI即興4題（おもち34号、豆腐田プル男、会田アイタロウ、病院玄関）を独自制作。各2候補、計16テキストをChatGPT GPT-6のこの単一チャット内で作った。第三者作品の文面は流用していない。

既存のvalidate_runをローカルで実行した形式検査は16/16 PASS。回答A/Bは独立API試行ではなく、面白さの人間評価もない。モデルの勝敗は判断しない。

## 実際のモデル接続と測定範囲

| 項目 | 状態 |
|---|---|
| ChatGPT | GPT-6の製品ラベル、チャット内の16テキスト候補。正確なビルドID、temperature、effort、独立API receiptは未取得 |
| Grok・Muse | Reason Networkの3接続はHTTP 409 agent_network_offline。未実行 |
| 同条件での独立モデル比較 | NOT_COMPARABLE |
| Skill | v0.2.1、Git blob SHA fe21da855d08d5d01feff89be7244176087d4044 |
| 合図前AI音声、Voice遅延、発話秒数、再現性 | NOT_MEASURED |
| 金子さん指摘の電話先AIという設定の観客理解・後方可聴性 | NOT_MEASURED |
| 身体演技・観客の実際の笑い | NOT_MEASURED |
| X投稿、大喜利応募、外部自動返信 | OFF、実行なし |

## 保護する台本・Skillの開始時点Git blob SHA

- 長尺v8 comedy/sagi-injury-help.md: 099ab68381e23f838299a9706c64f82bfc2dce1d
- 9月6日確定稿 comedy/sagi-denwa-2026-09-06-live.md: 036a10a7a0cd103663c48b56b9ab5137b3f2c4b9
- 選択中2分稿 comedy/sagi-injury-help-2min-live.md: 892ce8db0cc84eece3a64ecf661a7fdc90cc5784
- Comedy Skill: fe21da855d08d5d01feff89be7244176087d4044

以上4ファイルは改変しない。

## 研究上の制限と参照

ASR断片のturn_idは外部注釈者・ASRによる自己申告であり、ここでは話者本人かどうかの認証をしていない。250msという値の適切さも実録で検証が必要。録音そのものを公開GitHubへ置かず、権利確認済みの音声の非公開検証で境界誤差・話者誤認・台本一致率を独立に測る必要がある。

関連研究: He et al. (2026年10月2日), An automated pipeline for standardised speech-unit annotation in spontaneous dialogue, https://arxiv.org/abs/2610.03078 。発話境界や相づちの識別には限界があり、自動処理は人間の再確認のための一次注釈として扱うべきと論じる。同論文の性能値は今回の実測ではない。
