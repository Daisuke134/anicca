# Comedy AI 内部研究 2026-11-24 03:55 JST：台本の固有名詞だけを繰り返す「疑似回収」を検出

## 正本・安全境界
- 読込正本：GitHub `Daisuke134/anicca` の `main`（開始時 commit `e017f2f907dc52ce824936c9d99fca20d6b1ea1e`）。
- 確認資料：`comedy/AGENTS.md` / `skills/comedy-agent/SKILL.md` / `comedy/COMEDY-AGENT-LOOP.md` / `comedy/benchmarks/README.md` / `comedy/IMPROV-PLAYBOOK.md` / `comedy/feedback/KANEKO-2026-11-15.md`。
- Skill v0.2.1 blob SHA `fe21da855d08d5d01feff89be7244176087d4044`。
- **既存台本への改変なし**：長尺 v8 `comedy/sagi-injury-help.md` blob `099ab68381e23f838299a9706c64f82bfc2dce1d`、9/6確定上演稿 `comedy/sagi-denwa-2026-09-06-live.md` blob `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`、選択中2分舞台稿 `comedy/sagi-injury-help-2min-live.md` blob `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`。
- 外部投稿・自動返信・大喜利サイトへの自動応募は**ゼロ**。publish/auto-reply = **OFF**。新作は社内開発題のみ。

## 研究仮説と先行研究
「会田アイタロウです。」のように**既出名詞を言っただけ**の応答は、金子さんの指摘したアドリブ回収・ダイスのリアクションを生む手配と区別すべきである。従来 `validate_run.py` の `any_of` は固有名詞の包含だけを確認するので、次の二点は確認していない：
1. 直前のダイスの意外な発話（例：「会えた通知が来た」）を言葉として拾ったか。
2. 電話先AI職員らしい具体的な手配・登録・変更の**動詞**を含んだか。

新規 `audit_improv_relevance.py` は元の採点器を変更せず、この二つを追加の**字面上の診断**として計測する。これは語用論的な「本当に会話が成立した」判定ではない。応答の因果・意外性・面白さには人間の盲検評価と実演が必要。

背景：Sakabe et al., AAAI 2026, https://doi.org/10.1609/aaai.v40i39.40567 は日本語大喜利を6軸に分け、人間評価とモデル評価の相違を論じる。Palacios Patiño et al., 2026-10-31, https://arxiv.org/abs/2611.00492 は即興対話の自然な話者間相互作用の限界を論じる。これらを本実験の結果と混同しない。

## 何を本当に実行したか
- **題の区別**：固定ベンチは今回**未使用**。完全新規の社内オリジナル開発題8題（一般大喜利4、電話先AIの初見アドリブ4）、各2候補、計**16テキスト**。元サイト作品のコピーや外部応募ではない。
- 出力元：**このChatGPT GPT-6製品内の単一チャット**で作った候補。正確なモデルビルド、サンプリング温度、推論予算、プロバイダAPIレシートは未取得。独立プロバイダ実行ではない。
- 形式・字面診断：ローカル Python 3.13 で `python -m unittest discover ... -p 'test_*.py' -v` の**合成回帰15/15 PASS**。ローカル `audit_improv_relevance.py --strict` は**8題16回答中16/16 PASS**。さらにGitHubブランチから実際に再取得したJSONLを独立したJSチェックで読み直し、**16/16 PASS**を再確認した。
- 負例：既出の会田の名前を言うだけで「通知」への言及も手配動詞もない回答は、新しい診断で `NO_EXPLICIT_CUE_ACKNOWLEDGEMENT` と `NO_EXPLICIT_ACTION_MARKER` を返してFAIL。固有名詞だけの擬似回収を識別する単体テスト。
- 舞台の4題×2応答の診断値：**8/8**で既出世界アンカー、ダイスの合図に関する語、手配などの動詞がすべて字面一致。質問文なし、禁止フレーズなし。**これらはキーワード包含率であり「面白い」正答率ではない**。
- Grok/Muse：Reason Networkの3接続について `list_team` を試したが、いずれも **HTTP 409 `agent_network_offline`**。出力0件、モデル版0件。比較・ランキングは **`NOT_COMPARABLE`**。架空のGrok/Muse回答は一切保存しない。
- 実機Voice録音、音声の開始合図遵守、第一/第二声の実機完全一致、電話先AIの客席理解、客席後方の明瞭度、ダイスの身体演技による笑い、アドリブ回収後の観客笑い、話者分離精度：**すべて `NOT_MEASURED`**。

## 今回の課題と次の測定設計
1. **電話先AIを理解したか**：観客が自由回答で音声の役割を説明できる割合を測定する。観客への誘導質問はしない。
2. **開幕・第二声を守ったか**：ダイス合図前のAI音声0、台本第一声と第二声が文字起こし上で厳密一致するかを実録で検証する。演技中の台本照会は禁止。
3. **アドリブを拾うか**：実録で「ダイスの新しい入力→既出人物→具体的な行動→悪化→ダイスの身体反応」という連鎖を注釈。今回の字面診断では因果や笑いは測れない。
4. **聞こえ・再現性**：WAVの重複・無音監査と、実機での役割理解、固有名詞の後方可聴性・音声遅延を別々に測定する。同一録音を別試行と数えない。
5. **公平な複数モデル比較**：独立実行可能な接続だけで同一Skill blob、同一問題、出力数、推論条件、正確なモデルID、APIレシートを保存する。現時点の出力を勝率に変換しない。

## 成果物
- `comedy/benchmarks/audit_improv_relevance.py`：新規の静的字面診断CLI。
- `comedy/benchmarks/test_audit_improv_relevance.py`：15の人工単体テスト。
- `comedy/benchmarks/runs/2026-11-24-0355-original-tasks.jsonl`：8つの完全新規題、権利・使用条件。
- `comedy/benchmarks/runs/2026-11-24-0355-chat-responses.jsonl`：16候補全文、モデル出自、Skill SHA、推論設定未取得の明記。
- `comedy/benchmarks/runs/2026-11-24-0355-improv-gate-report.json`：ブランチ再取得による評価明細。
- **公開サイトへの投稿はなし**。新しい台本の原文・キャラシート・舞台プロトコル・Skill本文は変更しない。

**結論**：今回実証したのは「既出人物の名前を口にしただけ」と「新しいダイスの一言を拾い、役らしい行為の語を含めた」という**文字列上の区別**が可能になったことだけ。ChatGPTの面白さ・実機演技・モデル間優劣の改善は未実証。
