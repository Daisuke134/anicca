# Comedy AI内部研究：無音WAVを「稽古の音声証拠」と誤認しない（2026-11-23 23:57 JST）

## Canonical / scope
- 正本：GitHub `Daisuke134/anicca` の `main`、開始時の確認コミット `3c7b690cf16c1630cee0c5a054807021b1c4053c`。
- 確認した規則：`comedy/AGENTS.md`、`skills/comedy-agent/SKILL.md`（blob `fe21da855d08d5d01feff89be7244176087d4044`）、`comedy/COMEDY-AGENT-LOOP.md`、`comedy/benchmarks/README.md`、`comedy/IMPROV-PLAYBOOK.md`、`comedy/feedback/KANEKO-2026-11-15.md`。
- 評価の目的：舞台で「電話先のAI救急指令員」が本当に発声したかの証拠管理。**今回の変更は音声内容・笑い・聞き取りやすさを検証していない**。

## 発見・仮説・改善
従来の `audit_voice_wav_evidence.py` はWAVファイルのSHA・PCM・RMS・ピーク・重複を監査していたが、`source_kind=claimed_real_rehearsal` で**PCM全体がゼロ**でも、ファイルの整合性が正しければ終了コード0となった。これは「WAVファイルとして妥当」と「会話が録音された証拠として使える」を混同する危険がある。

新しい `claimed_rehearsal_audio_evidence` は、申告された本物の稽古が1件もなければ `NOT_MEASURED`、その申告の中にデジタル完全無音または検証不能ファイルがあれば `FAIL`、全ファイルが有効かつ非ゼロなら**`NEEDS_SPEECH_VERIFICATION`** と返す。各行の `dialogue_evidence` は `DIGITAL_SILENCE_INVALID` / `UNVERIFIED_SPEECH` / `UNVERIFIABLE_FILE` / `NOT_APPLICABLE`。非ゼロ波形は話し声ではない可能性があるためPASSにしない。

`wav_byte_integrity` は従来どおりWAV整合性だけを表し、有効な無音WAVはここではPASSとなる。**本物だと申告された無音WAVについては別ゲートFAILによりCLI終了1**。PCM非ゼロサンプル割合を診断項目に追加。ただし発話活動検出、ASR、客席可聴性の代理としては扱わない。

## 実際に実行した評価（Mac mini上のPython標準ライブラリ、GitHubから取得したソース）
- **Red**：新規7テストを修正前 `main` のソースに適用。1 FAIL + 6 ERROR（旧実装に新フィールドや拒否ゲートがない）。
- **Green**：修正版7/7 + 既存WAV12/12 + 既存PCM再利用5/5 = **24/24 PASS**。
- **合成WAV実験**：2件とも合法なWAV・正しい自己計算SHA。試験用の `source_kind=claimed_real_rehearsal` を意図的に虚偽申告。無音1件と非ゼロ合成信号1件を同一マニフェストに入れ、`wav_byte_integrity=PASS`、`claimed_rehearsal_audio_evidence=FAIL`、`audio_origin_authenticity=NOT_VERIFIED`。非ゼロ合成信号の単独評価でも `NEEDS_SPEECH_VERIFICATION` であり「発話確認済」とはしない。
- **2分台本静的検査**：22発話、714文字、PASS。音声時間2分・実際の発声・観客の笑いは測っていない。
- **新規オリジナル開発題**：日本語一般大喜利4題、電話先AI即興4題、合計8題×2候補＝**16回答**。固定ベンチ `taskset-v1` は**今回使用していない**。独自創作で外部作品・サイトの転載なし。 `validate_run.py --strict` は**16/16形式PASS**。笑いの強さや発想の優劣は未採点。
- **出自監査**：`audit_comparison_provenance.py` は `NOT_COMPARABLE`。ChatGPT GPT-6の**単一チャット内テキスト生成だけ**、正確なモデルビルド・温度・APIレシートなし。Reason Networkの3接続は当回もHTTP 409 `agent_network_offline` で、GrokとMuseは**実行せず**。名前を並べただけの勝率を作らない。

## 舞台・金子さんの講評への適用
- **開始合図**：ダイスの「痛い！」までは無言。合図後の第一声「はい、救急指令センターです。火事ですか、救急ですか？」を固定。今回の音声証拠ゲートだけでは実機での達成を証明しない。
- **電話先AI役**：ダイスが電話をかける側。観客が電話先のAI救急係と理解した比率は `NOT_MEASURED`。
- **アドリブ回収**：絹ごし3号、右折田まっすぐ、会田アイタロウ、おもち34号を利用した新しい応答案を記録。実際の対話・身振り・観客反応は `NOT_MEASURED`。
- **音声再現性**：今回は「無音試行を有効な稽古として通さない」管理能力を改善したのみ。音声重複・音圧・後方での明瞭さ・笑いの実測は未完了。
- **保護対象**：`comedy/sagi-injury-help.md` v8、`comedy/sagi-denwa-2026-09-06-live.md`、`comedy/sagi-injury-help-2min-live.md`、`skills/comedy-agent/SKILL.md` は変更しない。

## 出力・実行詳細
- 追加テスト：`comedy/benchmarks/test_audit_voice_silence_evidence.py`（7件）。
- 修正：`comedy/benchmarks/audit_voice_wav_evidence.py`。
- 開発題・候補：`comedy/benchmarks/runs/2026-11-23-2357-original-tasks.jsonl` と `...-chat-responses.jsonl`。
- 実行結果：`comedy/benchmarks/runs/2026-11-23-2357-silence-evidence-evaluation.json`。
- 使用システム：認可済みMac mini上の`/tmp/comedy-20261123-2357-silence`で、GitHubブランチのコードと修正前mainを別々に取得してオフラインPython単体テスト。利用者の開発ブランチや未コミット作業を変更していない。
- 外部公開：`publish_enabled=false`、`auto_reply_enabled=false`。X・大喜利サイトへの投稿、第三者への自動返信・大量応募はゼロ。

## 限界・次回の研究対象
これは**評価コードの改善**であり、Comedy AIモデルの重みの改善、実機Voiceの発話成功率、金子さんの講評に対する観客理解改善ではない。デジタル非ゼロのノイズ・テスト信号も発話とは限らない。次に必要なのは、同意済みの実録に対するASR＋目視確認の発話区間照合、観客の電話先AI理解、音声の明瞭さ、ダイスの身体演技と観客笑いの別集計。
