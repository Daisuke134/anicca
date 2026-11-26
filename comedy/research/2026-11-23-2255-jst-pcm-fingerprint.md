# Comedy AI internal research: WAV headerを変えた同一音声の再利用検出

実行: 2026-11-23 22:55 JST開始 / Source of truth: `Daisuke134/anicca` `main` at `98ace4c5de2e55c8aa22b91b87cd5d9e5e4810ae`

## 研究課題と仮説
前回の `audit_voice_wav_evidence.py` はWAVファイル全体のSHA-256が異なれば、同じPCMサンプル列を違うRIFFヘッダ・メタデータに包み直した場合に同一録音と検出できない。将来の「20回稽古」記録が見せかけの独立試行になり得る。**ファイルハッシュに加え、PCM実サンプルのストリームハッシュを比較する**とこの誤受理を防げると予測した。

## 事前に確認した正本
- `comedy/AGENTS.md` (`aa5b798ccb38cb2c3c6dd045e7a26f7adac44b09`)
- `skills/comedy-agent/SKILL.md` (v0.2.1, blob `fe21da855d08d5d01feff89be7244176087d4044`)
- `comedy/COMEDY-AGENT-LOOP.md` (`a3325b5851155311a09805d443ea352a239347e6`)
- `comedy/benchmarks/README.md` (`7ab13f9c36f095a093e4dd001bf6cc832ecf3480`)
- `comedy/IMPROV-PLAYBOOK.md` (`5f494c648ac6a630fe932342b53c575f4349e3db`)
- `comedy/feedback/KANEKO-2026-11-15.md` (`6c26deba72a978b29da3cfb1975a96d6993451ca`)

金子さんの講評は発話者分離が曖昧な記録を含むので逐語引用にしない。電話先にいるAI救急担当・ダイス主導の開始合図・第三者に応答しないこと・短い具体的な配車ボケ・アドリブ回収・後方可聴性・身体演技が重要。音声の再現性を検証できる**録音証拠の独立性**だけを今回の直接対象とする。これを笑いの改善や実機音声の再現性とは混同しない。

## 赤→緑の実行結果
- 正本の旧監査器と新規5回帰テストをMac mini上のPython 3で実行。**旧版は5件中1件PASS、2件FAIL、2件ERROR**。特に有効な `LIST` チャンクを追加しただけの別WAV（全体SHAは異なるがdecoded PCMは同一）を `wav_byte_integrity=PASS` と誤受理した。
- 同じテストを修正版で実行。**新規5/5 PASS、既存12/12 PASS、合計17/17 PASS**。2つのWAVに同じPCMが格納された場合、ファイル全体SHAの一致/不一致にかかわらず `duplicate_decoded_pcm` としてFAIL。中身が異なる場合はPASS。sample-rateだけ変更して同じPCMを流用した試験も検出。
- 実装は `wave.readframes(32768)` の生PCMバイトを逐次SHA-256し、同じチャンネル数とPCM SHAのペアを重複監査する。メモリへ音声全体を読み込まない。**波形の似ている別テイクや意味的な同一演技を検出するものではない**。逆に短い同一無音サンプルも重複と判定し得る。
- GitHubから取得した修正版のローカル `git hash-object` は `7fa1be4270bbbf71e34bf9607b74a5867fe9b359` で、GitHub blob SHAと一致。新テストも `75eebda873013f63fe3a54a0ece11a46c3d4e1b7` で一致。
- 2分稿 `check_injury_2min.py` の静的チェックは **PASS、22発話・714文字**。上演音声を録音したわけではない。

実行データ: [合成PCM回帰](../benchmarks/runs/2026-11-23-2255-pcm-regression.json)。実機録音は**0件**。

## 新規オリジナル開発題（固定ベンチは使用していない）
独自に新作8題（一般大喜利4題・「痛い痛い！」の電話先AI即興4題）を作成し、各2つのテキスト候補、計16回答を同一ChatGPTチャット内で作成。例：
- 「市役所が『なくした言い訳』を再発行する窓口を始めた。初日の混乱は？」 → A:「番号札をなくした人に『番号札をなくした言い訳』を発行し、行列が二重になった。」 / B:「『寝坊した理由』を再発行したら、申請者の時計が先に遅刻届を出した。」
- ダイス「右折田まっすぐ、今、病院の前を通り過ぎたよね？」 → A:「右折田まっすぐは病院を確認しました。入口を右折できず、救急車のほうを病院の駐車場に改名しました。」 / B:「右折田まっすぐに停止を指示しました。止まるのも右折だと思い、駐車場でハンドルだけ回しています。」

`validate_run.py --strict` の**形式ゲート16/16 PASS**（1題96文字以内、stageは指定アンカー含む、追加質問なし）。これは形式の機械検査であり、ボケの面白さ・行動語の意味的妥当性・観客の笑いを測るものではない。正本の固定ベンチは未使用なので汚染させない。

全題: [タスク](../benchmarks/runs/2026-11-23-2255-original-tasks.jsonl) / [回答全文](../benchmarks/runs/2026-11-23-2255-chat-responses.jsonl) / [形式評価](../benchmarks/runs/2026-11-23-2255-format-gate.json)。

## モデルと比較可能性
- ChatGPTの製品ラベル: `GPT-6`。**正確なモデルビルド・temperature・effort・独立API実行レシートは未取得**。このチャットで作った2案は独立ランダム試行でも独立モデル比較でもない。
- Grok、Muse: このサイクルでは**未接続・未実行**。過去回の接続失敗を今回の接続検証結果として流用しない。
- Skill v0.2.1、blob SHA `fe21da855d08d5d01feff89be7244176087d4044`、実験開始main `98ace4c5de2e55c8aa22b91b87cd5d9e5e4810ae`。
- 出自監査 `audit_comparison_provenance.py`: **`NOT_COMPARABLE`**。独立APIレシート0件、比較対象モデル1種類。人間評価・Judge評価のいずれも**NOT_MEASURED**。モデルランキングなし。

[出自監査実行JSON](../benchmarks/runs/2026-11-23-2255-provenance-report.json)。

## 舞台・音声・権限の限界
- 『痛い痛い！』v8 (`099ab68381e23f838299a9706c64f82bfc2dce1d`)、9/6確定上演稿 (`036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`)、現行2分稿 (`892ce8db0cc84eece3a64ecf661a7fdc90cc5784`) は**未変更**。Skill本文も未変更。
- 開始合図の実機応答、電話先AIという観客の認識、ダイスのアドリブ回収率、実際の声の再現性、音量と客席後方の聞き取り、二人の掛け合い・観客の笑いは**すべてNOT_MEASURED**。合成WAVは現実の収録証拠ではない。
- Xへの公開・自動リプ、大喜利サイトへの投稿、コンテストへの大量応募、第三者サイトへの規約外アクセスは**行わない**。 `publish_enabled=false`、`auto_reply_enabled=false`。権限/規約/専用アカウント未確認のため公開しない。
- 次の研究は実録音を権利・同意の範囲で取得できた時点で、このPCM監査を先行させ、信号独立性、台詞一致、開始合図、AI音声の明瞭度、観客評価をそれぞれ分けて測定すること。監査器の修正だけではComedy AI基盤モデルが上達した証拠にならない。

