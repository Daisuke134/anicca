# COMEDY BENCHMARK v1 — 4つの違う能力を混同しない

Canonical: 2026-11-22。Skill正本：[`skills/comedy-agent/SKILL.md`](../../skills/comedy-agent/SKILL.md)。
目的：**既存ベンチで外部モデル比較しつつ、独自の日本語・音声・舞台能力を再現可能に検証する**。点数の出ていないものはNOT_MEASUREDで保存。実行前にライセンスと同意・利用規約を確認。

## A. 既存ベンチマーク（それぞれ目的が違う）

| ベンチマーク | 何を測るか | 採用方法 | 限界 |
|---|---|---|---|
| **Oogiri-Master** (Murakami et al. 2025) | 日本語大喜利回答の**面白さを見分ける理解力** | 作者公開の600件の多肢選択問題を固定。回答はblind、正答率・タスク種類別・サンプル数で比較 | **大喜利を作る力・舞台で演じる力**ではない |
| **Oogiri-Corpus** | 82,536件の回答と投票数 | データ分布・言語的な特徴を学ぶ**開発資料**。投票と人気を面白さの絶対真理としない | 学習データとテストの汚染に注意 |
| **AAAI 2026 Oogiri six-axis** (Sakabe et al.) | 回答生成の Novelty / Clarity / Relevance / Intelligence / Empathy / Overall Funniness | 6項目各1～5で人間評価、モデル名を隠した一対比較も行う | 自動採点の1点差を誇張しない |
| **HumorBench (speech)** | 音声での**Delivery / Humanness / Timing**等の演技 | 音量・声の間・わかりやすさ・人間とAIの演技を音声を聞いて判定 | デモの小規模調査はランキングとして過信しない |
| **HumorBench (cartoon understanding)** | 漫画のジョークを説明し理解する力 | 外部の補助的な理解力テスト | 同名でも**音声HumorBenchとは別研究** |

- Oogiri-Master / dataset builder: https://github.com/CyberAgentAILab/oogiri-dataset-builder
- Oogiri-Master 論文: https://arxiv.org/abs/2512.21494
- AAAI 2026 6軸: https://ojs.aaai.org/index.php/AAAI/article/view/40567
- HumorBench (speech): https://humorous.dev/reports/humorbench
- HumorBench (cartoon): https://arxiv.org/abs/2507.21476

## B. オリジナルComedy-AI Bench（テキスト＋舞台）
[`taskset-v1.jsonl`](./taskset-v1.jsonl)は少量の公開サンプル。**テストデータを新しいSkillの暗記素材に使わない。** 開幕の文字一致、観客への無言、アドリブに既存キャラで対応、現実の緊急事態の例外、大喜利の転移、ソロ90秒などのタスクがある。

### 自動検証できるもの／できないもの
- 自動可：JSONL形式、必須メタデータ、台本第一声の`expected_prefix`、禁止されたメタ発言／呼吸指導、期待される設定の語句があるか、雑音時に無言だったか。
- 自動不可：本当に面白いか、観客が聞き取れたか、ダイスが面白く見えたか、人間らしい声か。これらは**録画・音声とブラインド観客評価**で測る。
- テスト例は公開されているので練習用。新規のホールドアウト（非公開の新しい問題）で評価し直し、Skillがテストに過適合していないか確認する。

### 実行（Python標準ライブラリのみ、外部送信なし）
回答を[`response-schema.md`](./response-schema.md)に沿って`responses.jsonl`に保存してから：

```bash
python3 comedy/benchmarks/validate_run.py --tasks comedy/benchmarks/taskset-v1.jsonl --responses responses.jsonl --output comedy-benchmark-results.json
```

**注意**：ファイルを置いただけではモデル比較を実行したことにならない。各モデルのAPI/コネクタが実際に使える環境で、同一のメッセージを送る。外部モデルの未取得結果を推測で埋めない。

## C. モデル比較の公平性
- 同じタスク、同じ台本・CAST・Skill SHA、同じ音声かテキストのモード、同じ上限文字数／推論労力／取得ツール条件。
- モデルの出力は先に**独立生成**して保存。GrokがChatGPTの回答を見た状態で回答を作る比較は不公平。
- 順番効果を防ぐため、人間評価はモデル名を隠し提示順をランダムにした**ペアワイズ**を基本とする。主観的な項目は評価者間の一致と数を報告。
- 同じ入力を複数回繰り返し生成して、平均だけでなく分散を記録。ペア比較は勝率・同点・標本数、可能ならブートストラップ区間で示す。
- 新しい `SKILL.md` が過去版を本当に改善したかは、**未使用のお題**で確認。Oogiri-Masterの理解力、OGIRI生成力、ライブの掛け合いは単一総合点に混ぜない。

## D. ライブ音声の追加チェック
1. ダイスの一声より前のAI音声 = 0。
2. 最初のAI台詞が台本通りか。
3. 観客・スタッフ等への誤応答 = 0（完全な声の分離を保証するわけではない）。
4. 重要語句が会場後方で聞き取れるか。
5. 観客が「電話先のAI指令員」を理解できるか。
6. ランダムな「会いたい」への返しが具体的な人物行動に繋がるか。
7. AIの台詞の笑い／ダイスの身体演技の笑い／偶然の笑いを分けて記録。
8. 同じセッティングで再演しても笑いが成立したか。

上記はまだ**本番未計測**。一度の大きな偶然の笑いを恒常性能と扱わない。

## E. 結果の永続化
1 run = 1 immutable ID。タスク・Skill SHA・モデルID・応答・人間評価・音声ファイル参照・失敗理由・公開先URL（投稿した場合のみ）を残す。生の個人の声や観客情報は許諾・プライバシー確認のうえで適切に保持し、公開GitHubに無断アップロードしない。
