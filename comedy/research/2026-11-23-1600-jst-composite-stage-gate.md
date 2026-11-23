# Comedy AI research — 2026-11-23 16:00 JST: 舞台の個別PASSを総合PASSと誤認しない

## 正本・スコープ
- GitHub main 入力コミット: `94ac12c27de7ff932034248ab639b7d60d253ed8`。
- 必須確認: `comedy/AGENTS.md`、`skills/comedy-agent/SKILL.md`、`comedy/COMEDY-AGENT-LOOP.md`、`comedy/benchmarks/README.md`、`comedy/IMPROV-PLAYBOOK.md`、`comedy/feedback/KANEKO-2026-11-15.md`。
- 目的: 現行2分稿における①ダイス開演合図とAIの第一・第二声完全一致・第三者割込・終幕、②人物の仕込み→ダイスのリアクション→後半回収、③事前注釈されたアドリブに対する直後の具体的な行動、という**異なる静的ゲートのAND合成**。
- 金子さんの指摘：電話先のAI救急指令センターとして認識されること、ダイスの身体反応の余白、後方可聴性、舞台再現性。このうち今回テストしたのは*文字列と完全発話の順序だけ*。音声・観客理解・笑い・身体演技は `NOT_MEASURED`。

## 新規実装
- `comedy/benchmarks/audit_stage_composite.py`: 既存の `validate_stage_dialogue.validate(..., require_turn_coverage=True)`、`audit_callback_continuity.audit`、注釈のある場合だけ `audit_adlib_anchors.audit` を**実際に呼び出し**、全要求ゲートがPASSの時だけ総合PASS。省略したアドリブは `NOT_REQUESTED` と明示。注釈が必須なのに欠落したケースは拒否。
- `source_type=synthetic` 以外を拒否する入力契約。実際の録音が存在するか・話者認識・意味理解・人間の笑いは検証しない。合成音声としての実測も行っていない。
- 新規 `test_audit_stage_composite.py`: 13件の回帰テスト。既存の2評価器のテスト45件と合わせて**58/58 PASS**。
- 合成8シナリオの期待判定 **8/8一致**：正常な会話と笑い声だけの割込はPASS、第一声破損・第二声破損・後半回収欠落・手配が「予定」のみ・観客の発話割込・終幕欠落はFAIL。これは**事前に設計した人工入力**であってモデルへの実API実行でも本番の成功率でもない。
- 個別ゲートの実例：第一声が誤っていてもコールバックゲート単体はPASSになる。逆に前振り回収を欠いても台本・開始のゲート単体はPASSになる。総合ゲートでは両者をFAILにし、評価の抜け道を塞ぐ。

## 新しい大喜利・即興開発データ
- **固定ベンチは使用しない**。自作の権利明示済みオリジナル開発題8題（一般大喜利4・電話先AI即興4）×2案=**16テキスト候補**。回答全文は `runs/2026-11-23-1600-chat-responses.jsonl`。外部作品の逐語的な複製・再投稿なし。
- 新規題例：「駅の忘れ物センターに『来週の月曜日』が届いた。持ち主は？」「ダイス『右ひざが実家から帰らない！』電話先AI係として短い手配を一手」。
- `validate_run.py` を実行：**16/16形式ゲートPASS**。これは字数・既出人物・禁止表現・質問記号の機械的確認であり「16個とも面白い」ことを意味しない。
- **実際の生成主体はこのChatGPTチャットのGPT-6製品ラベル**。同じチャット内で2案を作ったもので、独立APIの2反復ではない。正確なモデルビルド、temperature、effort、レシートは取得できず、独立性も実証できない。`skill_version=0.2.1`、Skill Git **blob SHA** `fe21da855d08d5d01feff89be7244176087d4044`（コミットSHAと混同しない）。
- `audit_comparison_provenance.py` 実行：`NOT_COMPARABLE`。一つのモデルだけ、未制御の生成設定、独立プロバイダ実行レシートなし。**Grok・Museは未実行**。Reason Networkの接続3系統は全て HTTP 409 `agent_network_offline`（今回再確認）。
- ChatGPT内の2案に優劣や勝者をつけていない。実際の評価者0件。観客笑い・人間演技・Voice再現性・後方の聞こえ方・電話先AI認識率はすべて `NOT_MEASURED`。

## 実行証跡
```bash
python3 -m unittest -v test_audit_stage_composite.py test_audit_callback_continuity.py test_audit_adlib_anchors.py
# Ran 58 tests: OK
python3 audit_stage_composite.py --input 2026-11-23-1600-composite-synthetic.json --output 2026-11-23-1600-composite-report.json --strict
# PASS: 8/8 synthetic expectations met
python3 validate_run.py --tasks 2026-11-23-1600-composite-tasks.jsonl --responses 2026-11-23-1600-chat-responses.jsonl --output 2026-11-23-1600-format-report.json --strict
# 8/8 + 8/8 text-format PASS
python3 audit_comparison_provenance.py --tasks 2026-11-23-1600-composite-tasks.jsonl --responses 2026-11-23-1600-chat-responses.jsonl --output 2026-11-23-1600-provenance-report.json
# NOT_COMPARABLE
python3 comedy/benchmarks/check_injury_2min.py
# PASS (22 turns, 714 spoken chars); real voice and duration NOT_MEASURED
```
上記の初回実行はMac miniの`/tmp/comedy-cycle-1600`でmainのソースを取り寄せて実施。全てPython標準ライブラリで実行。実際の上演録音・外部API出力は用いていない。

## 保護対象（変更禁止）
- `comedy/sagi-injury-help.md` v8: Git blob SHA `099ab68381e23f838299a9706c64f82bfc2dce1d`
- `comedy/sagi-denwa-2026-09-06-live.md` 9/6確定稿: `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`
- `comedy/sagi-injury-help-2min-live.md`: `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`
- `skills/comedy-agent/SKILL.md`: `fe21da855d08d5d01feff89be7244176087d4044`
いずれも本文変更なし。PR後のmainからblob SHAを再照合する。

## 外部規範・残課題
- コメディ原則の参考：UCB授業ノート「一つ情報を出して相方の反応を待つ」 https://drewtarvin.com/comedy/ucb-improv-201-class-notes/ 。外部の作品や台詞の複製ではなく、構造だけ参考にした。
- 残課題：実際のVoiceで開始合図前発声0、第一声と第二声一致、第三者音声無反応、後方音量、観客の電話先AI理解、アドリブと身体反応の笑いを**別個に実測**。この静的テストPASSをライブの性能改善と呼ばない。
- `publish_enabled=false`、`auto_reply_enabled=false`。X・大喜利サイト・外部応募・自動返信・無差別アクセスは**実行なし**。内部GitHub成果物以外の公開処理をしていない。
