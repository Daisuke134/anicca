# Comedy AI研究 2026-11-23 21:55 JST：Voice録音の証拠整合性を測る

## 結論：改善したのは評価基盤。Voice本体の能力は未測定

今回、録音のSHA-256、PCM WAVの音声長・RMS dBFS・sample peak dBFS・クリップ率、試行間の録音重複と設定不一致を監査できるPythonツールを追加。実録音の再現性、舞台での笑い、後方可聴性は依然 **NOT_MEASURED**。

- Pythonの新規回帰テスト **12/12 PASS**。人工データのみ。
- 独立の合成音声2本を実測し、ファイル整合性 **2/2 PASS**。人間の声でもAI音声でもない。
- 既存2分稿の静的検査 **PASS（22発話・714文字）**。実機Voiceの成功ではない。
- 新作オリジナル8題、チャット内候補16案。機械的形式検査 **16/16 PASS**、面白さは未測定。
- 比較出自監査 **NOT_COMPARABLE**。Grok・Muse未実行、モデルランキングなし。
- 外部のX・大喜利サイトへの投稿・自動返信 **一切なし**。publish/auto_replyはfalse。

## 正本と保護

GitHub Daisuke134/aniccaのmainを開始時に再取得したcommit：49419bb6131a1524edb03c7850d37a9dae0dd91b。
必須6資料をGitHub mainから参照済み：comedy/AGENTS.md、skills/comedy-agent/SKILL.md、comedy/COMEDY-AGENT-LOOP.md、comedy/benchmarks/README.md、comedy/IMPROV-PLAYBOOK.md、comedy/feedback/KANEKO-2026-11-15.md。

Skill v0.2.1 blob SHA：fe21da855d08d5d01feff89be7244176087d4044。
保護対象の開始時blob SHA：痛い痛い！v8＝099ab68381e23f838299a9706c64f82bfc2dce1d、9/6確定稿＝036a10a7a0cd103663c48b56b9ab5137b3f2c4b9、2分稿＝892ce8db0cc84eece3a64ecf661a7fdc90cc5784。
これらの台本とSkill本文を編集しない。

## 新規監査器

実装：comedy/benchmarks/audit_voice_wav_evidence.py
テスト：comedy/benchmarks/test_audit_voice_wav_evidence.py

入力はローカルJSONL manifest。各行に trial_id、録音ディレクトリ相対のwav_path、sha256、source_kind、model_version、skill_blob_sha、script_blob_sha、voice_mode、mic_setup_id、speaker_output_idを指定する。プライベートな録音そのものを公開GitHubへアップロードしない。

1. WAVのバイトをストリーミングSHA256で確認。異なる試行IDへ同一バイト列を再利用した場合はFAIL。
2. PCM16bitモノラル／ステレオを解析し、サンプル数、再生秒数、レート、チャンネル数、RMS dBFS、sample peak dBFS、クリップ比率、完全無音を算出。
3. 名目の収録設定だけでなく、実WAVヘッダーのサンプルレート／チャンネル数の不一致も検出。条件不一致を同条件の再現試行と誤認しない。
4. 不正WAV、欠けた設定、パストラバーサルを拒否。
5. ファイルに「実録」と書いても収録元の真正性を検証できないため audio_origin_authenticity は NOT_VERIFIED とする。

RMS dBFSは、客席の音圧(SPL)、LUFS、true-peak、ASRの正確さ、固有名詞の聞き取り率、笑いの測定ではない。放送ラウドネスの別アルゴリズムについてはITU-R BS.1770-5とAudio Engineering Societyを参照：
https://www.itu.int/rec/R-REC-BS.1770-5-202311-I
https://aes.org/resources/audio-topics/loudness-project/loudness-basics/

## 実際の実行

Mac miniはディスク容量が極めて少ないため、既存作業木を変更せず16MiBの一時RAMディスク /Volumes/ComedyRAM でGitHubブランチのPython 3.14ソースを実行した。

- 新規unittest 12/12 PASS。正常WAV、無manifest、SHA不一致、同一音源再利用、完全無音、クリップ、マイク設定不一致、**実サンプリングレート不一致**、パス越境、必須属性欠落、不正WAV、実録と称する偽装可能性を検査。
- 別途8kHz/16bit/monoの人工WAVを2本生成して1秒ずつ解析。RMS dBFSは -28.03 / -23.46、クリップ率ともに0、音源は異なる。wav_byte_integrity=PASS、repeated_config_consistency=CONSISTENT、voice_reproducibility=NOT_MEASURED、audio_origin_authenticity=NOT_VERIFIED。
- 報告JSON：comedy/benchmarks/runs/2026-11-23-2155-synthetic-wav-audit.json。
- main由来の既存check_injury_2min.pyによる現行台本検査：PASS、22発話、714文字。Voice実演は0試行。

## 新規オリジナル開発題とモデルの出自

固定ベンチは未使用。今回の内部オリジナル題8題（一般大喜利4、電話先AI即興4）から各2案。第三者サイトからの転載・無断データ取得はなし。

問題全文：comedy/benchmarks/runs/2026-11-23-2155-original-tasks.jsonl
回答全文：comedy/benchmarks/runs/2026-11-23-2155-chat-responses.jsonl
形式結果：comedy/benchmarks/runs/2026-11-23-2155-format-report.json
出自監査：comedy/benchmarks/runs/2026-11-23-2155-provenance-report.json

生成はChatGPT製品ラベルGPT-6の一チャット内テキストのみ。正確なモデルビルド、temperature、effort、プロバイダAPI実行レシートは未取得。各回答にSkill SHA、基点main commit、生成形式、候補番号と出自を記録した。16/16の形式PASSは面白さのスコアではない。

Reason Networkの3接続はいずれもHTTP 409 agent_network_offline。GrokとMuseはNOT_RUN。同条件の独立モデル比較はNOT_COMPARABLE。人間・観客による独立した6軸採点、笑い、モデル勝率はNOT_MEASURED。

## 金子さんのフィードバックと次の実測

開始合図はダイスから。AI第一声は固定の救急指令センター、電話先のAI役として応じる。リアルな緊急事態なら演技を中断し安全優先。アドリブでは「会いたい→会田」「救急車どこ→右折田／おもち」「絹ごし3号」の既出設定を回収し、相方の身体反応の余白を残す。既存の舞台ルールは変更しない。

現場で検証すべきもの：20反復の開幕フライング、第一・第二声一致、音声のリアル遅延と被り、ダイスの反応、客席後方での固有名詞の聞こえ方、観客が電話先AIと理解した割合、演者別・掛け合い別の笑い。実録WAVを権利のある環境で保全し、検査器でハッシュと条件を確認した後、時刻・話者・観客の人手注釈を別途採る。**今回この実録を実施した事実はない**。