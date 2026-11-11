> 本書は 2026-11-11 Manager eval 研究3文書セットの1つ: [BehaviorBench 実走](2026-11-11-behaviorbench-run.md) ／ [競合の実走と理解](2026-11-11-competitor-runs.md) ／ [フロンティアラボ eval 調査](2026-11-11-frontier-eval-survey.md)

# BehaviorBench 実読と実行 — 2026-11-11

対象データセット（本人が直接指定）: https://huggingface.co/datasets/befm/BehaviorBench
論文: arXiv:2606.24162 "BehaviorBench: Benchmarking Foundation Models for Behavioral Science Tasks"
(Huang, Xie, Song, Zhang, Yuan, Jackson, Mei; COLM 2026。v1 2026-06-23 提出、v3 が最新版 2026-10-11)

> 注記: 2026-11-10 に「外部に同名ベンチマークは存在しない」と誤結論した件への訂正を兼ねる。
> BehaviorBench は実在し、論文・公式サイト・公式データ・公式評価コードの全てが公開されている。
> なお同名の無関係な論文が複数ある（予測市場の行動トレース版 arXiv:2606.02798、性格心理学版
> IJCAI-26、臨床支援版）。本書の対象は Be.FM チームのものだけである。

## 1. BehaviorBench は何を測るベンチマークか（一次情報の実読）

人間の行動を条件付き確率 p(y | x, c; K) と捉え（y=行動、x=被験者の特性、c=文脈、
K=行動科学の知識）、基盤モデルを4つの能力で評価する:

1. **行動の予測とシミュレーション**（y の順方向推論）
2. **戦略的意思決定**（目標を達成する y の生成）
3. **被験者特性の推論**（x の逆方向推論）
4. **行動科学知識の応用**（K を研究問題へ使う）

評価は2つのレベルで行うのが特徴:
- **個人レベル**: 被験者ごとの正解への近さ（Accuracy / MAE 等）
- **分布レベル**: 母集団の回答分布との一致（Wasserstein 距離 + KS 検定）。
  「平均は当てても多様性を潰す」モデルを落とすための物差し。

データの出所は3系統（論文 §2.1）:
- 実験データ: MobLab の経済ゲーム記録（評価サンプル 12,685 観測 / 6,279 人）
- 調査データ: Big Five 人格検査の公開データ（評価サンプル 6,000 回答 / 1,886 人）
- 文献データ: AER と Nature Human Behaviour の 2025 年論文のタイトル・要旨を
  研究ワークフロー（背景・着想・方法・結果・影響）に分解したもの

論文の主要結果: 汎用モデルは個人レベルと知識系に強く、行動データで微調整した
Be.FM-1.5 は分布レベルで最強（公式リーダーボード: 分布レベル Mean Win Rate で
Be.FM-1.5-4B が 95.3% で1位、個人レベルは 66.5%）。Be.FM-1.5 の学習データは
BehaviorBench から held-out されている（論文明記）。

## 2. データセットの実測（befm/BehaviorBench、生ファイル直接取得）

- 取得経路: HF の Dataset Viewer は生成に失敗している（実測: CastError —
  metadata 列が宣言スキーマ {system, user, assistant} と一致しないため）。
  標準の viewer / datasets 経路では全件読めない。今回は huggingface_hub の
  snapshot_download で生 JSONL を直接取得した（54ファイル、取得成功）。
- ライセンス表記: **CC BY-NC-ND 4.0**（データセット README の front-matter で実測）。
  研究評価目的の利用のみ。再配布はしない。
- 行の形: {system, user, assistant} のチャット形式 + 一部ファイルに metadata
  （JSON文字列: subject_idx, dimension, target_item, context_item_count 等）。
- 固定の評価スプリットのみが公開されている。**train スプリットは存在しない**
  （behaviorbench_indices.json は評価サンプルの抽出インデックス）。
- 件数（実測、全54ファイル合計 20,977 行）:
  - big_five/ 6タスク × 1,000 行（pers_score_pred, surv_resp_pred, missing_surv_resp,
    seq_surv_resp, demo_pred_age, acrossdim_pers_score）
  - moblab/game_behavior/ 9ゲーム × 200 行
  - moblab/multiround_behavior/ 8種 × 約500 行（trust_banker_inv50 のみ 125 行、
    inv100 は 498 行）
  - moblab/acrossgame_behavior/ 9種 × 750 行（trust_banker のみ 262 行）
  - moblab/strategic_gameplay/ 1,000 行
  - workflows/ 5サブタスク、AER/NHB 別ファイルあり（合計 1,084 行 =
    combined 244+240+240+116+244）
  - economics_contests/ieo_economics.jsonl 124 行
- タスク例（実読）: pers_score_pred は「人口統計を与えて Big Five の1次元スコア
  （10–50）を予測」、missing_surv_resp は「49問の回答を与えて残り1問の回答
  （1–5）を予測」、dictator は「$100 の分配額」を人間分布と比較する。

## 3. 採点方法（公式パッケージと公式方法論ページの実読）

公式評価コード: github.com/oy2017/behaviorbench_eval（著者の Owen Yang の
リポジトリ。論文・データへのリンクとタスク定義を保持。MIT ライセンス。
今回のクローン HEAD = beaf9b334195949d5f07ffd4ca8bc3f677a1c526、2026-06-26）
※ PR #9250 が固定した commit ddd646ed… はこのリポジトリの履歴には存在しない
（別リポジトリ側の固定とみられる。今回はこちらを正として使った）。

タスクごとの指標（tasks_config.yaml で実読）:
- 調査応答予測（surv_resp_pred / missing_surv_resp / seq_surv_resp）:
  Accuracy, f1_macro, MAE, Spearman, Wasserstein+KS。項目（target_item）ごとに
  グルーピングして平均する形式が既定。
- 特性推論（pers_score_pred / acrossdim_pers_score / demo_pred_age）:
  MAE, Spearman, Wasserstein+KS（次元ごとにグルーピング）。
- ゲーム行動シミュレーション（game_behavior_*）: Wasserstein+KS のみ（分布レベル）。
  1つのプロンプトから N 回サンプリングし、人間の行動分布と比較する
  （公式方法論ページの "simulated distributions" 方式）。
- 複数ラウンド / 他ゲーム観測つき予測: MAE（正規化）, Spearman, Wasserstein+KS。
- strategic_gameplay_guessing: 上記 + win_rate（Beauty Contest の勝率）。
- ieo_economics: 多肢選択の Accuracy / f1_macro。
- workflows: BLEURT / ROUGE-1（5サブタスク一括実行が必須）。

リーダーボードの集計（公式方法論ページで実読）: 指標の尺度がタスクごとに違うため
直接平均せず、HELM 方式の **Mean Win Rate** を使う —
WR_task = (負かしたモデル数 + 0.5 × 同点数) / (N − 1) をタスクごとに計算し、
対象タスク群で平均する。個人レベル列と分布レベル列は別々に集計する。
代替として ELO（K=32、初期 1500）も併記される。

公式の実行経路: 評価器は OpenAI 互換の /v1/chat/completions エンドポイントを
叩く（--model-type local）。ほかに openai / anthropic / vertex / azure と、
ヒューリスティクス型（--model-type heuristic。ただし CEX・複数ラウンド専用で
Big Five 系には使えない）と ダミーモデル（スモークテスト用）が組み込まれている。

## 4. 今回の実行条件（全モデル同一）

- 実行系: 公式パッケージ behaviorbench_eval をそのまま使用（pip install -e .、
  Python 3.12 venv）。データは data/ へシンボリックリンク。
- モデルの出し方: llama.cpp b12137 の llama-server（OpenAI 互換）で配信。
  - Qwen3-4B-Instruct-2507: qwen3.gguf（Q4_K_M、2,497,280,736 bytes、
    sha256 は 2026-11-08 の記録と一致を確認済みの既存資産）
  - Be.FM 1.5-4B: 同じ基盤 GGUF + befm-lora.gguf（変換済み LoRA、66,094,848 bytes。
    元 adapter の sha256 62bd79fa… は固定値と一致を過去ランで確認済み）
  - サーバー設定: -t 4、ctx 8192（4スロット×2048）、--parallel 4。
- デコーディング: 個人レベル課題は temperature 0.0（決定的・再現性優先）、
  max_tokens 32、concurrency 4。論文・公式コードに温度の指定は明記されていない
  （arXiv v2 本文に "temperature" の記載なしを検索で確認）。公式リーダーボードの
  数字とはデコーディング条件が異なるため、絶対値の単純比較はしない。
- サンプル数（当初計画と、実際に完走したスコープ）: 当初は公式の
  --num-samples（seed 42 で random.sample）で surv_resp_pred n=50、
  pers_score_pred n=50、missing_surv_resp n=20、game_behavior_dictator は
  --num-samples-per-game 200（人間の n=200 と同数）を計画した。しかし本 VM の
  実測スループットが律速だった（llama-server のタイミングログ実測:
  プロンプト処理は 4 並列時で集計 0.56–1.41 tok/s 相当、生成は 1 リクエスト
  67 トークンで 3分22秒の実測あり。VM 全体の負荷平均は他ループの処理と
  合わせて 13–23 に達していた）。missing_surv_resp のプロンプトは約950トークンで、
  この速度では LLM 実行だけで数時間規模になる。加えて Qwen の最初の実行
  （run1、n=50）は推論サーバーの死亡で成果ゼロに終わった。
  そのため**実際に完走したスコープは以下に縮小した**（全モデル同一条件）:
  - surv_resp_pred: n=20（seed 42）
  - pers_score_pred: n=20（seed 42）
  - game_behavior_dictator: 50 サンプル（--num-samples-per-game 50、
    temperature 1.0。分布を出すためにサンプリングが必要。人間の参照分布は n=200）
  - missing_surv_resp: **LLM 実行は未実施**（prior のみ。理由は上記の速度実測）
  なお Be.FM の dictator は初回実行の途中で VM 自体が再起動して中断したため、
  サーバーを同一設定で再起動して dictator のみ再実行し完走した
  （2026-11-11 05:53:54–05:58:36 UTC）。
- 対照（prior）: 公式ハーネスのタスククラスと指標コードをそのまま使い、
  自作の callable をモデルとして渡した。
  - prior_marginal: 項目ごとの最頻回答（調査系）/ 次元ごとの平均（スコア系）。
    BehaviorBench には train スプリットが無いため、評価スプリットのラベル
    周辺分布から計算した。**周辺分布のみを使い、項目と正解の対応は使っていない**
    が、train prior の代用としては楽観側の物差しであることを明記する。
  - prior_constant: 情報ゼロの定数。調査系は [3]（尺度中点）、スコア系は [30]。
  - prior は推論コストゼロのため full（n=1,000）と LLM と同一サブセット
    （seed 42）の両方を回した。

## 5. 結果

実行日時: 2026-11-11。Qwen3-4B-Instruct-2507 = run2（05:03–05:22 UTC）、
Be.FM 1.5-4B = run3（05:24–05:59 UTC、dictator のみ VM 再起動後に再実行）。
全て公式ハーネス behaviorbench_eval の出力 JSON が正本（レシートは §5 末尾）。
個人レベル課題は temperature 0.0 / max_tokens 32 / concurrency 4 / seed 42。
指標はタスクのグルーピング単位で平均した値（ハーネスの *_averaged）。

### 5.1 surv_resp_pred（調査応答予測、n=20、target_item 16グループ平均。回答は 1–5）

| モデル | Accuracy | f1_macro | MAE | Spearman | Wasserstein |
|---|---|---|---|---|---|
| Qwen3-4B-Instruct-2507 | **0.4375** | 0.0875 | 1.0000 | 0.0541 | 0.9583 |
| Be.FM 1.5-4B | 0.3542 | 0.0833 | 1.1875 | −0.1166 | 1.0208 |
| prior_marginal（同一サブセット） | 0.4167 | 0.0875 | **0.8750** | 0.0000 | 0.8750 |
| prior_constant（同一サブセット） | 0.2708 | 0.0563 | 1.0000 | 0.0000 | 1.0000 |

参考（prior の full、n=1,000）: marginal は Accuracy 0.3944 / MAE 1.0028、
constant は Accuracy 0.2239 / MAE 1.1351。

読み: Qwen は Accuracy でだけ prior_marginal をわずかに上回ったが、MAE では
prior_marginal が両 LLM より良い。Be.FM はこの課題・この n では prior_marginal
にも Qwen にも届かなかった（Spearman は負）。

### 5.2 pers_score_pred（Big Five スコア予測、n=20、5次元グループ平均。スコア範囲 10–50）

| モデル | MAE | Spearman | Wasserstein |
|---|---|---|---|
| Qwen3-4B-Instruct-2507 | 6.59 | 0.1028 | 6.33 |
| Be.FM 1.5-4B | 5.68 | **0.1558** | 4.48 |
| prior_marginal（同一サブセット） | **4.73** | 0.0000 | 4.73 |
| prior_constant（同一サブセット） | 7.29 | 0.0000 | 7.29 |

参考（prior の full、n=1,000）: marginal MAE 6.3668、constant MAE 8.1417。

読み: Be.FM は Qwen より全指標で良いが、**MAE では prior_marginal（次元ごとの
平均を返すだけ）が両 LLM より良い**。n=20 では prior 側のサブセット値自体が
full 値から大きく振れている（marginal の MAE は full 6.37 に対し n=20 で 4.73、
n=50 で 7.63）ため、この順位はサンプリングノイズの範囲を出ない可能性が高い。

### 5.3 game_behavior_dictator（独裁者ゲームの分布再現、50サンプル、temperature 1.0、人間の参照分布は n=200、平均 24.715・標準偏差 19.19、単位は $100 の分配額）

| モデル | Wasserstein 距離 | KS 統計量 | KS p値 | KS 検定 |
|---|---|---|---|---|
| Qwen3-4B-Instruct-2507 | 20.275 | 0.69 | ≈0.0 | 不合格 |
| Be.FM 1.5-4B | **2.105** | 0.07 | 0.9856 | 合格 |

読み: 分布レベルでは Be.FM が圧倒的に人間の分布に近く、Qwen は分布を再現
できなかった（Wasserstein で約10倍の差）。これは論文の主張（Be.FM-1.5 は
分布レベルで最強）と方向が一致する。ただしサンプルはモデル側 50 件のみで、
公式条件（人間の n=200 と同数サンプリング）より小さい。

### 5.4 missing_surv_resp（欠損した調査回答の予測）

LLM の実行は**未実施**（§4 の速度実測のため）。prior のみ記録する:
- full（n=1,000）: prior_marginal Accuracy 0.3864 / MAE 0.9973、
  prior_constant Accuracy 0.2236 / MAE 1.1361。
- n=20 サブセット: prior_marginal Accuracy 0.3125 / MAE 1.0625、
  prior_constant Accuracy 0.0000 / MAE 1.5625。

### 5.5 総合判定（この条件・この n での範囲）

- 個人レベルの Big Five 課題（n=20）では、Be.FM も Qwen も「素朴な物差し」
  prior_marginal を安定して上回れなかった。これは自前 MaMe-Re 評価で
  Be.FM が prior に勝てなかった結果（§6）と方向が一致する。
- 分布レベルの dictator では Be.FM が明確に勝ち、論文の主張と一致した。
- つまり「Be.FM は分布の再現に強く、個人レベルの点予測では素朴な周辺分布
  ベースラインに届かないことがある」というのが、今回の実測の要約である。

### 5.6 レシート（実行ログ・結果ファイル）

- Qwen 結果: `behaviorbench_eval/outputs/run2/qwen3-4b-instruct/`
  （surv_resp_pred_20261111_051116.json / pers_score_pred_20261111_051833.json /
  game_behavior_dictator_20261111_052157.json）
- Be.FM 結果: `behaviorbench_eval/outputs/run3/befm-1.5-4b/`
  （surv_resp_pred_20261111_053029.json / pers_score_pred_20261111_054035.json /
  game_behavior_dictator_20261111_055835.json）
- 実行ログ: `phase-qwen-run2.log`、`phase-befm-run3.log`、
  `phase-befm-run3-dictator.log`（いずれも本書と同じフォルダ）
- サーバーログ: `server-qwen2.log`（Qwen）、`server-befm.log` /
  `server-befm2.log`（Be.FM、再起動前後）
- 実行コマンド: `bb-work/run_llm_phase.sh <model> <phase> <task:n:temp> ...`
  （公式 CLI behaviorbench-eval を --model-type local で呼ぶラッパー）
- prior の集計: `bb-work/prior_summary.txt`、結果は `outputs-priors/`

## 6. 既存の自前評価（MaMe-Re 凍結24文脈）との違い

| | 自前評価（2026-11-08〜09） | BehaviorBench（今回） |
|---|---|---|
| データ | MaMe-Re から seed 固定で 24 文脈を抽出 | BehaviorBench 公式評価スプリット（Big Five / MobLab / Workflows / IEO） |
| 課題の形 | 2択のペア比較（どちらが人間の反応に近いか） | 実タスクそのもの（調査回答・スコア・ゲーム行動の生成） |
| 指標 | 厳格正答率（非タイ件数ベース）、平均 regret | Accuracy / MAE / f1 / Spearman / Wasserstein+KS、集計は Mean Win Rate |
| 対照 | train prior（学習データの平均） | prior_marginal（評価スプリットの周辺分布）/ prior_constant |
| 分布レベル | 測っていない | Wasserstein で母集団分布との一致を測る（dictator で実施） |
| 数字の正本 | 公式 Actions ラン（Be.FM 0.5556 (10/18) vs prior 0.6111） | 本書 §5 |

数字を単純比較してはいけない理由: 課題・指標・分母が全て違う。自前評価の
0.5556 は「18件の非タイペアのうち10件」で、BehaviorBench の Accuracy は
「項目ごとにグルーピングした正答率の平均」であり、単位が異なる。また
Be.FM の学習データは MaMe-Re 側に含まれていた可能性がある一方、
BehaviorBench からは held-out されている（論文明記）ため、条件の意味も違う。
比較できるのは「素朴な物差しに勝てたか」という判定の方向だけである。

## 7. 残件・正直な限界

- **n が小さい**: 個人レベル課題は n=20 のみ（公式は最大 1,000 件）。prior の
  サブセット値が full 値から大きく振れる実測（§5.2）があり、LLM 同士・
  LLM と prior の順位はサンプリングノイズの範囲を出ない可能性がある。
  順位の確定には n を大きくした再実行が要る。
- **公式リーダーボードと条件が違う**: こちらは temperature 0.0（決定的）で
  回したが、論文・公式コードに温度指定の明記はなく、リーダーボード側の
  デコーディング条件は不明。したがって §5 の絶対値を公式リーダーボードの
  数字と単純比較してはならない。比較が有効なのは同一条件で並べた
  4 者（Qwen / Be.FM / prior 2種）の相対関係だけである。
- **カバレッジは 3 タスクのみ**: BehaviorBench 全体は 30 種超のタスク群
  （Big Five 6種、ゲーム 9種、複数ラウンド、ワークフロー、IEO 等）だが、
  今回 LLM で回したのは surv_resp_pred / pers_score_pred /
  game_behavior_dictator の 3 つだけ。残りは未計測。
- **missing_surv_resp は LLM 未実施**: プロンプトが約950トークンと長く、
  本 VM の実測スループット（他ループと CPU を共有し負荷平均 13–23）では
  数時間規模になるため見送った。prior の数字のみ §5.4 にある。
- **dictator のサンプル数**: モデル側 50 サンプルで、公式の想定
  （人間の n=200 と同数）より小さい。KS 検定の検出力もその分低い。
- **prior_marginal は楽観側の物差し**: BehaviorBench に train スプリットが
  無いため評価スプリットの周辺分布から作った。項目と正解の対応は使って
  いないが、本来の train prior より有利な条件である点は割り引いて読む。
- **seed は 42 の 1 本のみ**: サブセット抽出の seed 依存性は未検証。
- **実行環境の事故**: Qwen の run1 はサーバー死亡で成果ゼロ、Be.FM の
  dictator 初回は VM 再起動で中断し再実行した。いずれも結果ファイルが
  残った run2 / run3 のみを正本として使っている。
- **Be.FM の利用権**: LoRA adapter は利用権の不整合（ライセンス表記の
  食い違い）が未解消のため、本実行は研究評価のみ。商用ロードはしていない。
  データセットも CC BY-NC-ND 4.0 のため研究評価のみ・再配布なし。
