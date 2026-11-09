# BehaviorBench × Psych-101：人間の行動モデルに何を学習させるのか

**2026-11-08 / source-based technical lecture / 教育・完全合成実験のみ。**
本講義は既存のP00〜P12カリキュラムに追加する深掘りであり、会社の別実装TODOを作らない。現在の正式実装順は統合SSOT MG-01〜MG-18を参照。

## 0. 最重要な結論
1. BehaviorBench（Huang et al., arXiv:2606.24162）の**公開データセットは評価専用**。論文で実施したBe.FM 1.5のSFT用649,394例は、異なる被験者・論文から構成される11タスク側であり、公開の評価用JSONLを学習させてはいけない。
2. Psych-101は**60,092人の実験セッション記録**（160研究、10,681,650人間の選択、約253,597,411 text tokens）。1つの行に多数の人間の選択を含み、各選択を<<D>>のように区切る。
3. モデルが答える問いを固定する。次の選択、母集団の回答分布、推論ゲームの勝率、論文の方法、介入の因果効果、実生活の改善は別々の予測・評価問題。
4. 訓練は使用権のあるデータのみ。BehaviorBench評価データのコンピレーションはCC BY-NC-ND4.0、評価コードはMIT、Psych-101公開trainカードはApache2.0、Psych-101-testはgatedのCC BY-ND4.0。モデルadapterは別ライセンス。コードがOpenだからデータを商用SFTできるとは限らない。
5. 学習用の講義コード37件テストは完全合成。実人間データからの新BFM訓練・実人間への便益・売上の証拠ではない。

## 1. 同名ベンチマークに注意
本教材のBehaviorBenchは**Huang et al. (2026), arXiv:2606.24162, Benchmarking Foundation Models for Behavioral Science Tasks**。
同名の別研究であるYang et al. (arXiv:2606.02798)は、予測市場とウォレット履歴のbelief/tradeを評価する。IJCAI 2026の別BehaviorBenchはBig Fiveの行動表現を扱う。名前だけでデータ/採点器を混同しない。

## 2. BehaviorBenchの12タスク：能力ごとの正解とメトリクス

論文の基本表現は p(y | x, c, K)。y=人の行動、x=人物特徴、c=状況、K=行動科学知識。

| 能力 | タスク（論文v3） | 観測入力とラベル | 主要評価 |
|---|---|---|---|
| 行動予測/模擬 | Game Behav. Sim. | ゲーム規則→人間集団の初回選択分布 | Wasserstein（W） |
| 同上 | Multi-Round Pred. | 同じ被験者の過去の選択→次の数値選択 | MAE、W |
| 同上 | Across-Ctx Pred. | 別ゲームの本人選択→新ゲームの選択 | MAE、W |
| 同上 | Demo. To Resp. | 属性+Big Five質問→本人の回答 | Accuracy、W |
| 同上 | Seq. Resp. Pred. | 前の質問への本人回答→次の回答 | Accuracy、W |
| 同上 | Masked Resp. Pred. | ほか49回答→隠れた回答 | Accuracy、W |
| 戦略 | Strategic Game Play | Beauty Contestの状況→対戦で勝つ行動 | 勝率 |
| 特徴推定 | Demo. To Pers. | 属性→Big Fiveの因子得点 | MAE、W |
| 同上 | Across-Dim Pers. Pred. | 他4因子→5番目の因子得点 | MAE、W |
| 同上 | Pers. To Demo. | Big Five得点→年齢 | MAE、W |
| 知識応用 | Scientific Workflow | 論文の記述→研究Idea/Method/Outcome/Title/Impact | BLEURT |
| 同上 | Economics Contest | 経済学の択一問題→公式正答 | Accuracy |

**重要**：ゲーム勝利は人間の選択の模倣ではない。IEO正答と論文のWorkflowは実験参加者の行動ではない。集団のWasserstein距離は個人Accuracyではない。異なる尺度を一つの総合Accuracyとして扱わない。

一次論文： https://arxiv.org/html/2606.24162v3

## 3. BehaviorBenchの3種類の学習元データ＋1種類の評価のみ

### A. MobLabの経済ゲーム
569,795件の生ログを、無効ラベル・行動範囲外・非標準ゲーム設定・連続試行の欠落で整理し、**379,754ゲーム記録、76,035参加者**を保持。Dictator、Ultimatum、Trust、Public Goods、Bomb Risk、Beauty Contest、Push/Pull等で、ゲーム規則・状況・本人の過去の選択から観測された次の行動を学ぶ。

### B. Big Fiveの自己申告
**19,630人、981,500項目回答**、5因子×10項目と属性情報を利用。自己申告、個人特徴、文化、人口構成が含まれ、敏感属性や採用/与信/医療などの利用制限を慎重に扱う。個人の性格得点を予測することと、その人への介入の因果効果は別。

### C. 学術論文のタイトル・要約
American Economic Review 6,515報、Nature Human Behaviour 871報を参照。タイトルと要約からGPT-5等でContext/Idea/Method/Outcome/Impactを構造化した学習例を作る。**論文の構造化文章は人間の次の行動を観測したラベルではない**。著作権・用途・論文情報の版を確認する。

### D. 国際経済オリンピック（IEO）
絵が必要な6問を除いた124問の公式正解を**評価だけ**に使う。経済学の問題解決能力を測るもので、行動の個人差を測るものではない。

## 4. SFTデータ649,394例と公開評価19,893例を混同しない

BehaviorBench論文v3 Table 5：**学習11タスク計649,394例、評価12タスク計19,893例**。学習例はMobLabの参加者単位70/10/20、Big Five参加者単位90/10、論文では2025年をテストとする時間分割で分ける。Push/Pullはゲーム自体を学習側から完全に除き、テスト参加者も学習側と重複させない。IEOはevaluation-only。

公開HuggingFace「befm/BehaviorBench」は評価専用のChat形式のJSONL。各行はおおむねsystem（タスク説明）、user（入力）、assistant（参照正解）で構成。ただしassistantが「実際の人間の回答」か「年齢/人格得点」か「試験正答」か「論文に由来する文章」かをタスクごとに区別する。
公開READMEでMulti-Roundの3,498件と、論文v3の3,623件が一致しない。論文v3の科学ワークフロー1,084件と公開ファイルの総件数にも集計単位/版差がある。使用するGit/HF revision・ファイルハッシュ・タスクごとの行数を必ず固定する。

学習には「公開のtest.jsonlを丸ごと入れる」のでなく、著者が学習側として分けた元データから権利を確認した上で**別に学習例を生成**する必要がある。公開のevaluation GitHubは「訓練コードなし」と明示。

評価コード：https://github.com/umich-foreseer/behaviorbench_eval
評価データ：https://huggingface.co/datasets/befm/BehaviorBench

## 5. Be.FM 1.5：実際の学習方法

論文Appendix Dに記された具体条件：
- ベース：Qwen3-4B と Llama3.3-70B。
- SFTデータ：11タスク・649,394例。最終評価とはSubject/Paperで非重複。
- LoRA：rank **8**、alpha **32**、全線形層、ms-swift。
- **1 epoch**、最大学習率 **1×10^-4**、最大系列長 **2048**、effective batch size **128**。
- GPU：**4×A100 80GB**、4Bで約60 A100-GPU時間、70Bで約600 A100-GPU時間と報告。
- Task mix：属性→性格因子予測のタスクを3倍Upsample、Beauty Contestでは複数の勝ち手を最大10個の学習例に拡張。

これらは論文の研究条件であり、Aniccaの実際の支払額や再現済み学習ログではない。学習時のNLLを下げただけでは、未知の人の実行動の汎化は保証されない。

**個人の回答を反復生成して得る分布**と、**モデルが一度で言語化した確率分布**は異なる評価。原論文Appendix Eの順位相関はSpearman rho≈0.51で、行動特化モデルの順位は方式によって逆転するケースがある。

## 6. Psych-101：1レコード＝1回の選択ではない

HF公開データの行は以下の3項目を持つ：
- text：心理学実験の説明＋人間参加者1人の試行と選択の全文
- experiment：元実験のID
- participant：その実験内の参加者ID

研究規模：160実験、60,092人、10,681,650選択、253,597,411 text tokens。HFのpublic trainには約60.1k行がある。紙面のParticipant Holdout 90/10と、HFのsplit名だけを安易に同一視しない。Testは別gated CC BY-ND4.0、TrainカードはApache2.0。

文中では、人間の回答だけが二重山括弧で囲まれる。以下は**著者が作った架空例**であり、実験データの転載ではない。

~~~text
Synthetic experiment: Select LEFT or RIGHT.
Trial 0: Context 1. Human chooses <<L>>.
Trial 1: Context 0. Human chooses <<R>>.
~~~

通常のLLMは、入力文章を含む多くの位置に言語モデルのCross Entropyを計算できる。しかしCentaurは、**人間の選択token部分のみ**を損失に含める。
L = -(Σ_t m_t log p_theta(w_t | w_<t))/(Σ_t m_t), m_t∈{0,1}。

Centaur元コードはTRL DataCollatorForCompletionOnlyLMを使用し、response_templateを「 <<」、instruction_templateを「>>」としている。実際の実装ではTokenizerで分割されたtoken境界と損失マスクを適切にそろえる。文字単位MaskをそのままLLM token maskと呼ばない。
学習はLlama3.1-70Bの4bit baseとLoRA rank8を用い、回答に対するCEを1 epoch。追加学習パラメータは約0.15%、A100 80GBで約5日。推論はAdapterを対応するLlamaベースへ載せる。ベースAdapterの権利はLlama3.1 Community Licenseであり、公開trainデータカードと同一ではない。

元コード：https://raw.githubusercontent.com/marcelbinz/Llama-3.1-Centaur-70B/main/finetune.py
Dataset：https://huggingface.co/datasets/marcelbinz/Psych-101
Adapter：https://huggingface.co/marcelbinz/Llama-3.1-Centaur-70B-adapter

### 未来漏洩と汎化の境界
試行tの行動を予測するとき、入力は現在までの観測された課題説明・報酬・本人のt-1までの選択のみ。t以降の実際の選択を入力に入れない。人物Holdout、研究Holdout、課題変種、言語と文化Holdoutを別に評価する。

## 7. 比較まとめ

| | BehaviorBench (2606.24162) | Psych-101 / Centaur |
|---|---|---|
| 主用途 | 多能力の評価 | 人間の選択履歴の学習 |
| 学習例単位 | Task別instruction-response | セッション内の多くのtrial response |
| 生データ源 | MobLab、Big Five、学術論文、IEO（評価のみ） | 160種類の心理実験 |
| ラベル | 実行動・自己申告・論文表現・公式解答が混在 | 人間が実際に選んだ応答 |
| 評価 | MAE/Accuracy/W/BLEURT/Win rate | 人間の回答NLLとHoldout等 |
| 公開 | test用JSONL、CC BY-NC-ND | train Apache表示、test gated |
| そのまま言えないこと | 実生活全般や増分介入の成功 | 商用日本語通知や苦痛軽減の効果 |

## 8. Anicca：研究用と商用用のデータ戦略を分ける

### Track R — 認知・選択予測研究
権利を確認したPsych-101等で人間の選択を予測し、少なくとも単純統計モデル/汎用LLM/専用モデルを、Study/Subject/Time Holdoutで比較する。BehaviorBenchの公開評価データは**評価側に固定**し、SFTに混ぜない。NLL・校正・分布W・人物/研究間の一般化を検証。

### Track P — 最初の商用能力仮説
最初の候補として、本人と顧客から正当な許可を得た非臨床の日本語メッセージ案について、事前に反応確率と候補順位を推定し、顧客の実験候補選択を支援する。ただし**支払意思・収益性・人間への便益が実証済みという意味ではない**。
- 入力：許可された文面、用途、チャネル、時点情報、過去に観測できた集約結果。
- 出力：期間を固定した反応確率、校正、不確実性、棄権。
- Label：提供元の実記録による独立結果。モデルの自己申告は不可。
- Split：新しいcampaign/variant family/tenant/future time。似た文面や同じA/B研究の重複を検出。
- Baselines：過去平均、カテゴリ平均、Logistic/Ridge、既存Qwen等を同条件で比較。
- 経済評価：1件の独立確認できた成功あたりの費用/増分価値/害。
- **Upliftを販売するなら追加で割付確率、NO_ACTION、因果効果推定が必要**。単純な購買確率を介入効果と言わない。

### 商用向け必要データレコード（最小候補）
work_id, study/experiment_id, tenant_ref, candidate_id, content_hash, consent/rights_ref, decision_at, context_snapshot_at, allocation_probability, delivery_status, outcome_due_at, observed_outcome_at, outcome, missingness_reason, data_class。
モデルが予測した時点より未来の結果が特徴に混入しないよう時点を固定。高感度な個人属性は必要性と権利を別審査。

## 9. 完全合成の訓練デモと正しい結果のラベル
ソフト教材：[コード](experiments/behaviorbench_psych101_data_contract.py)・[37テスト](experiments/test_behaviorbench_psych101_data_contract.py)。

架空の**128セッション・1152試行**を生成し、各研究の人物IDでtrain/validation/test分割。モデルには過去の選択のみを渡し、応答の文字だけChar-level Maskで指定。実際に小型のLogisticの重みを合成データで更新し、未知人物の試行上で比較した。
- 定数Baseline NLL≈0.690697、Toy Logistic NLL≈0.535906。
- 定数Baseline Brier≈0.248776、Toy Logistic Brier≈0.177371。
- **実在の人間データは使っていない。BFMの重みは訓練していない。商用権利は認定していない。**
- ライセンスGateはBehaviorBench evaluationデータの商用学習を拒否する。
- Character maskは教育用であり、Transformer/Tokenizerの正規Cross Entropy実装ではない。

## 10. Manager現在地と次の研究決定
既存の[4領域ManagerBench結果](../../verification/MANAGERBENCH_V1_FOUR_REAL_TRACKS_20261107.json)ではNatureの探索的改善は報告される一方、MaMe-ReやQwenの優位は未証明、HBCPも観測の小差はCIがゼロを含む。学習済みHBCP Ridge Headも別のStudy Holdoutで単純Baselineに敗れている。**複数領域での共通BFMの真の優位はまだ実証していない**。
次は、研究Track Rで「初回ゲームの集団分布」「Multi-Round」「Across-Context」の三能力を同じ公式手順でBaseline比較し、Track Pでは実データ権限・保有量・価値評価が成立する小さい業務を選ぶ。モデルを大きくする前にデータと分割と採点を決める。

現在の会社実装NEXTは単一MG-SSOTを確認すること。本講義は別実装計画・データコピー許可・本番学習命令ではない。

## 11. Primary sources
- Huang et al. 2026 https://arxiv.org/html/2606.24162v3
- Official evaluation code https://github.com/umich-foreseer/behaviorbench_eval
- BehaviorBench eval dataset and rights https://huggingface.co/datasets/befm/BehaviorBench
- Be.FM model and gated terms https://huggingface.co/befm/BeFM1.5-4B
- Binz et al. Nature 2025 https://doi.org/10.1038/s41586-025-09215-4
- Psych-101 train / test https://huggingface.co/datasets/marcelbinz/Psych-101 ; https://huggingface.co/datasets/marcelbinz/Psych-101-test
- Centaur source https://raw.githubusercontent.com/marcelbinz/Llama-3.1-Centaur-70B/main/finetune.py
- Centaur adapter https://huggingface.co/marcelbinz/Llama-3.1-Centaur-70B-adapter
- Mei et al. MobLab 2024 https://doi.org/10.1073/pnas.2313925121
- Yang et al. different BehaviorBench https://arxiv.org/abs/2606.02798
- IJCAI different BehaviorBench https://ijcai.org/proceedings/2026/658
