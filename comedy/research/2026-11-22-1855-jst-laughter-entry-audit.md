# Comedy AI 内部研究 — 2026-11-22 18:55 JST / audience-laughter entry audit

## 結論（測定対象を混同しない）
**合成・手動注釈の時間区間に対し、AIが既に始まっている観客笑いへ入り込んだ量を検査する評価器を実行した。** 音声モデルを本番環境で実行した証拠、観客の実際の笑いの測定、モデルの性能向上の証拠ではない。

- Repository SSOT: `Daisuke134/anicca` `main`、開始時 HEAD `de68740ed8352c33595fff3775c6d4b148a4aed9`。検証対象の固定原稿とSkillは無変更。
- 事前に確認した必須6ファイル：`comedy/AGENTS.md` (blob `aa5b798ccb38cb2c3c6dd045e7a26f7adac44b09`)、`skills/comedy-agent/SKILL.md` (`fe21da855d08d5d01feff89be7244176087d4044`)、`comedy/COMEDY-AGENT-LOOP.md` (`a3325b5851155311a09805d443ea352a239347e6`)、`comedy/benchmarks/README.md` (`a0652f59fdf4b0a6f89c41f8340459b13485ef55`、変更前)、`comedy/IMPROV-PLAYBOOK.md` (`5f494c648ac6a630fe932342b53c575f4349e3db`)、`comedy/feedback/KANEKO-2026-11-15.md` (`6c26deba72a978b29da3cfb1975a96d6993451ca`)。
- GitHubマージ後の `main` readback はPR処理後に別途確認する。
- Skill v0.2.1 / **Skill blob SHA** `fe21da855d08d5d01feff89be7244176087d4044`。生成時の参照コミットは上記 HEAD。Skill本文は編集しない。

## 課題と理由
金子さんの指摘：AI音声が小さい／正体が分かりづらい／ダイスの身体リアクションの余白が必要／偶発的なアドリブを拾う一方で再現性が必要。既存 `validate_stage_dialogue.py` は観客発話と「笑い」を区別し、`measure_stage_timing.py` はダイスとAIの応答間隔や被りを計測するが、**AIの新しい台詞が笑いの途中へ割り込んだか**という区間指標がなかった。

参考文献：Pope, Stewart & Chew (2018), *Audience Laughter Distribution in Live Stand-up Comedy*, https://www.isca-archive.org/lw_2018/pope18_lw.html （ライブでの笑いの相対時刻に注目）。Zribi et al. (2026), *TIC-TALK*, https://aclanthology.org/2026.chum-1.2/（文章・音声・笑い・身体動作を時間整列する研究）。他者の作品本文をコピーせず、内部評価仕様の参考に留める。

## 変更と実行
1. `comedy/benchmarks/measure_stage_timing.py` に **注釈済み観客笑いとAI発声の区間重複**を加えた。観客笑いの開始がAIより後なら、AIが笑いに割り込んだことにしない。二重ラベルは区間の和集合を用い重複カウントしない。閾値 `--max-ai-entry-laughter-ms` はオプションで、未設定時は発話の合否に影響しない。実機の強制ミュート・音声識別を実装したわけではない。
2. `comedy/benchmarks/test_measure_stage_timing.py` に7件の合成テストを追加。**ベース57/57 → 64/64 Python unittest PASS**（2026-11-22 JST、macOS上の一時スパースクローンで実行）。`test_stage_dialogue` 等の既存試験も含む。
3. 合成のAI発話開始時に笑いが継続：`entry-synthetic`、重複150ms、`--max-ai-entry-laughter-ms 0 --strict` は **FAIL/exit1**。AI発話開始後に笑い発生：`midline-synthetic`、総重複300msでも開始時違反0で **PASS/exit0**。どちらも `text_gate=PASS`。数値は全て**作成したフィクスチャ**で、実録ではない。
4. 今回は**固定ベンチを使っていない**。新規**独自オリジナル8題（大喜利4、舞台アドリブ4）×2候補 = 16回答**を `...-tasks.jsonl` / `...-responses.jsonl` に全文保存。回答生成は**このChatGPT GPT-6セッションが執筆した2案**で、独立 API の反復サンプリングではない。同じSkill・お題・文字数制約での2候補。`validate_run.py --strict` の形式・語句制約は **16/16 PASS / 欠損0**。これは面白さの採点ではない。

## モデル・公平性・外部接続
| モデル | 今回の実行 | モデル版と設定 | 正当な比較か |
|---|---|---|---|
| ChatGPT | 同一テキストセッションで16回答を執筆 | GPT-6 / serving build NOT_EXPOSED / temperature NOT_EXPOSED / effort NOT_EXPOSED | 単一セッションの案出し。独立生成・API比較ではない |
| Grok | 未実行 | NOT_AVAILABLE | モデル比較不可 |
| Muse | 未実行 | NOT_AVAILABLE | モデル比較不可 |
| Reason Network | 3リンクに `list_team` を実行したが各々 **409 agent_network_offline** | 2026-11-22時点の接続検査 | メッセージ送信なし／モデル実行なし |

`model_version`、`skill_commit`、`skill_blob_sha`、`independent_api_sample=false`、`fun=NOT_MEASURED` は応答JSONLに記録。ChatGPTと他モデル間の勝敗・ランキング・同条件比較は **NOT_MEASURED**。

## 舞台向け実験の境界と未解決
- 既存の第一声・第二声完全一致、ダイスの開演合図、電話先AI職員の設定、第三者の声の無視、終幕後の沈黙は引き続き既存ゲートの対象。今作業は台本上の決め台詞を変えず、**実機Voiceが合図どおり動くことを保証しない**。
- 笑い中のAI割り込みゼロを本番合格基準と即断しない。現実の笑いがAIの台詞途中から生じる場合もあるし、ラベル誤りもある。境界試験0msは**あくまで合成の実行例**。
- 客席後方の聞き取り、AIが電話先にいるという認識率、ダイスの身体演技、実際の笑いの反応タイミング・大きさ・再演分散、音声モデルの遅延・話者分離、金子さんの提案の効果は **NOT_MEASURED**。実録を得た際には本人・観客の同意とプライバシーを確認し、公開repoに生の音声を出さずに注釈だけ評価する。
- 『痛い痛い！』長尺v8 blob `099ab68381e23f838299a9706c64f82bfc2dce1d`、9/6確定上演稿 blob `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`、現行2分稿 blob `892ce8db0cc84eece3a64ecf661a7fdc90cc5784` を**変更しない**。
- `publish_enabled=false`, `auto_reply_enabled=false`。X・大喜利サイトへの投稿、無差別リプ、第三者サイト規約外の自動アクセス：**実行なし**。GitHub内部研究PR以外に公開しない。

## 再現コマンド
```bash
python3 -m unittest discover -s comedy/benchmarks -p 'test_*.py' -q
python3 comedy/benchmarks/validate_run.py --tasks comedy/benchmarks/runs/2026-11-22-1855-laughter-tasks.jsonl --responses comedy/benchmarks/runs/2026-11-22-1855-laughter-responses.jsonl --output /tmp/comedy-1855-format-report.json --strict
python3 comedy/benchmarks/measure_stage_timing.py --input comedy/benchmarks/runs/2026-11-22-1855-laughter-entry-synthetic.json --output /tmp/comedy-entry-report.json --max-ai-entry-laughter-ms 0 --strict
python3 comedy/benchmarks/measure_stage_timing.py --input comedy/benchmarks/runs/2026-11-22-1855-laughter-midline-synthetic.json --output /tmp/comedy-midline-report.json --max-ai-entry-laughter-ms 0 --strict
```
