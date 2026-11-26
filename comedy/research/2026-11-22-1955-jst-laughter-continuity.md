# Comedy AI 内部研究 — 2026-11-22 19:55 JST / laughter-continuity boundary bug

## 結論（実行と未測定の分離）
実行確認：人工的な時刻注釈で、複数の観客笑いラベルが途切れず続く場合のAI発話開始時の重複時間の過小計算を再現・修正し、回帰テストに追加した。音声認識や観客の反応を測定したわけではない。

新規のオリジナル開発題8題（大喜利4・電話先AI舞台即興4）をChatGPT GPT-6の同一テキストセッションで各2案作り、計16回答の全文をJSONL保存した。既存固定ベンチは今回未使用。人間評価、笑い、ライブ音声、多モデル比較は NOT_MEASURED。

## 参照したGitHub正本
Repository: Daisuke134/anicca main、開始時HEAD 21603ce3e9b948aebadffde7514346ca3ed9d7e6。
- comedy/AGENTS.md blob aa5b798ccb38cb2c3c6dd045e7a26f7adac44b09
- skills/comedy-agent/SKILL.md v0.2.1 blob fe21da855d08d5d01feff89be7244176087d4044
- comedy/COMEDY-AGENT-LOOP.md blob a3325b5851155311a09805d443ea352a239347e6
- comedy/benchmarks/README.md 修正前blob 8d92ea96a09b2794c0bb65b9e0bee28921ae7ddc
- comedy/IMPROV-PLAYBOOK.md blob 5f494c648ac6a630fe932342b53c575f4349e3db
- comedy/feedback/KANEKO-2026-11-15.md blob 6c26deba72a978b29da3cfb1975a96d6993451ca

次の舞台は2分実演稿を選択する。金子さん指摘の「電話先AI救急係」設定、ダイス先行合図、第一・第二声の一字一句一致、観客への不応答、既出キャラ回収、ダイスのリアクション余白を維持。
保護対象のGit blob SHAは変更しない：
- 『痛い痛い！』長尺v8 comedy/sagi-injury-help.md = 099ab68381e23f838299a9706c64f82bfc2dce1d
- 9/6確定稿 comedy/sagi-denwa-2026-09-06-live.md = 036a10a7a0cd103663c48b56b9ab5137b3f2c4b9
- 現行2分稿 comedy/sagi-injury-help-2min-live.md = 892ce8db0cc84eece3a64ecf661a7fdc90cc5784
- Comedy Skill本文 = fe21da855d08d5d01feff89be7244176087d4044

## Before / After：実際に再現した境界バグ
時刻はすべて人工的な合成注釈、録音や観客の実際の発話ではない。
観客の笑いA [3750,3950) ms、笑いB [3925,4100) ms、AI第二声 [3900,7900) ms。

旧版の実行結果：総重複200ms、AI発声開始時点の既存笑い継続50ms。BはAI開始後の3925msに始まるので旧コードから除外されたが、実際にはAと重なって笑いは途切れていない。閾値100msなら誤PASSだった。

修正版：笑い注釈の重なり・隣接を和集合へマージし、AI開始時点を含む連続区間がAI発話の中にどれだけ続くかを計測。その結果、entry継続200ms、総重複200ms、閾値100msでFAIL（strict終了コード1）、閾値200msでPASS（終了コード0、超過だけFAIL）。

対照例：笑いBを [3970,4100) ms に変えてAと20ms離すと、開始時の継続は50msのままで、後続Bは開始時違反に含まれない。ラベルが端点で接する場合は連続と判定。ここで同じ観客がずっと笑っていたとは主張せず、ラベル区間の接続性だけを測る。100ms/200msは合成テスト用であり、舞台上の推奨閾値ではない。

## 再現コマンドと結果
Python標準ライブラリのみ。macOSの専用スパースクローン上で実行。
- python3 -m unittest discover -s comedy/benchmarks -p 'test_*.py' -q → 67 tests OK（以前64、連続・分離・接触の3件追加）。
- python3 comedy/benchmarks/check_injury_2min.py → PASS：第一声、第二声、場所質問の増殖防止、キャラ回収、会話交代。尺と音声はNOT_MEASURED。
- python3 comedy/benchmarks/validate_run.py --tasks comedy/benchmarks/runs/2026-11-22-1955-continuity-tasks.jsonl --responses comedy/benchmarks/runs/2026-11-22-1955-continuity-responses.jsonl --output comedy/benchmarks/runs/2026-11-22-1955-continuity-report.json --strict → 16/16形式PASS、各runの欠損0。
- python3 comedy/benchmarks/measure_stage_timing.py --input comedy/benchmarks/runs/2026-11-22-1955-continuity-synthetic.json --output comedy/benchmarks/runs/2026-11-22-1955-continuity-timing-report.json --max-ai-entry-laughter-ms 100 --strict → text PASS、timing FAIL、期待どおり終了コード1。

## 生成とモデル比較の正確な範囲
- 開発題は完全新規の日本語オリジナル8題。タスクには原著明示、権利、最大100文字、電話先AIの既出キャラクターのアンカー、禁止句を記載。公開大喜利データや他者の回答は一切転載していない。
- 生成済みモデル：このChatGPT GPT-6のテキストセッションで執筆した各2案。独立API反復サンプリングではない（independent_api_sample=false）。serving build、実temperature、実effortは NOT_EXPOSED。モデルID・Skill blob SHA・出力全文を各JSONL行に保存。
- Grok・MuseはMODEL_NOT_RUN。Reason NetworkのPrimary、DAISUKE、MKをこのサイクルでlist_teamして、すべて409 agent_network_offline。多モデルの同条件性能比較・勝者は NOT_COMPARABLE。
- 自動の文字制約と禁止句判定は面白さの点数ではない。LLM-judge・人間のblind評価・観客の笑い・統計的な優劣は NOT_MEASURED。

## 本番適用・金子さんのフィードバックと公開境界
金子さんの講評は話者分離が不完全な文字起こしを逐語引用せず、電話先AIという設定の理解、後方での声量・明瞭性、ダイスの身体表現、AIに話を奪われない間、偶発的なアドリブの回収と再現性を独立に検証する。今回追加したのは「手動ラベルの時間計算が正しいか」のみ。Voiceライブの話者識別、発話開始遅延、実際の笑い、本番での笑いの増加は未測定。現実の重大な危険では安全例外を維持。

公開GitHubに個人音声・観客の私的映像は置かない。X投稿・自動返信・大喜利サイト応募・無差別リプ・規約外の自動アクセスを行わない。publish_enabled=false、auto_reply_enabled=false。GitHubの内部研究PRだけが今回の公開操作。
