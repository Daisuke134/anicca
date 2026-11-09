# 「人間の行動を学習するAI」は、実際には何を学習しているのか

*Anicca Research / 2026年11月8日 / BehaviorBench × Psych-101 データ・モデル徹底解説*

「人間の行動を予測するFoundation Modelを作る」と聞くと、すべての人間の意思決定を理解する巨大なAIを想像するかもしれない。しかし、そのモデルに、具体的に何を正解として与えるのだろう。

心理学実験の選択か。アンケートへの回答か。広告のクリックか。介入した後の行動変化か。

**この違いを決めない限り、モデルが学習するべきデータも、良いモデルの定義も決められない。**

![BehaviorBenchとPsych-101のデータ、学習、評価を区別するAniccaオリジナル図]({{BEHAVIORBENCH_DATA_FLOW_IMAGE}})

## BehaviorBenchの驚くべき点：公開データは「学習用」ではない

2026年のHuangらの[BehaviorBench](https://arxiv.org/html/2606.24162v3)は、行動予測、戦略的な選択、本人の特性推定、行動科学知識の応用を、12タスクで評価する。

重要なのは、論文で追加学習に使ったデータと、公開している最終評価データが別だということだ。

著者らは、MobLabの経済ゲーム、Big Fiveの自己報告、経済学・行動科学の論文から、**649,394件の学習例**を構築した。一方、論文Table 5にある最終評価は**19,893件**で、同じ参加者や論文が訓練と評価に重複しないよう分割している。

公式の[Hugging Faceデータセット](https://huggingface.co/datasets/befm/BehaviorBench)は**評価専用**であり、[公開評価コード](https://github.com/umich-foreseer/behaviorbench_eval)にはモデルの訓練コードが含まれていない。

評価データを追加学習させて高得点を出しても、未知の人間行動を学んだことにはならない。

## 行動の正解には、いくつもの種類がある

MobLabでは、Dictator、Trust、Public Goods、Beauty Contestなどのゲームにおける人間の実際の選択を観測する。Big Fiveでは、本人が回答した50項目の自己報告を使う。研究ワークフロー課題では、学術論文のタイトルと要約から構造化した研究内容を予測する。経済学オリンピックの問題では、公式の正答を採点する。

しかし、経済学の問題を正しく解くことは、人間が実際にどう答えるかを予測することではない。ゲームに勝つことも、人間らしい選択を模擬することとは違う。

評価も一種類ではない。数値選択はMAE、カテゴリ回答はAccuracy、集団の選択分布はWasserstein距離、研究文章はBLEURTなどを使う。

**一つの「人間理解スコア」だけで能力を語ると、何が良くて何が悪いかが見えなくなる。**

## 研究者はどうモデルを追加学習しているか

BehaviorBench論文は、Qwen3-4BとLlama-3.3-70BにLoRAを適用した。rank 8、alpha 32、最大系列長2048、1 epoch、最大学習率0.0001、effective batch size128、4基のA100 80GB GPUを使い、4Bモデルは約60 A100-GPU時間、70Bは約600 A100-GPU時間と報告している。

学習元の11タスクを混ぜて学習する一方、評価対象の人物や研究は学習側から除外する。重要なのは単純な計算量よりも、**どの種類の人間データを混ぜると、どの未知タスクが改善するか**である。

## Psych-101はもっと直接的だ

2025年のNature論文で紹介された[Centaur](https://doi.org/10.1038/s41586-025-09215-4)は、[Psych-101](https://huggingface.co/datasets/marcelbinz/Psych-101)の160実験、60,092人、10,681,650件の実際の選択を使う。

データでは、1人の試行履歴が文章として記録される。人間が選んだ回答は二重山括弧で表され、**損失関数はその回答部分だけを学習する**。これは「心理学に詳しく話すAI」と「実際の人間の選択に確率を割り当てるAI」の違いだ。

Centaurの元[学習コード](https://github.com/marcelbinz/Llama-3.1-Centaur-70B/blob/main/finetune.py)には、応答境界に合わせて損失を計算する仕組みがある。公開の学習データはApache 2.0の表示だが、試験データは別のgatedなCC BY-ND 4.0、モデルAdapterはLlama 3.1系の権利に従う。評価、学習、商用利用の許可は分けなければならない。

## 私たちは「少しだけ学習する」実験も作った

理解のため、架空の128セッション、1,152回の選択を生成した。人物ごとに学習/検証/評価を分け、過去の選択だけを見て次を予測する単純なロジスティック回帰を実際に訓練した。

未知の架空人物でのNegative Log-Likelihoodは、全体平均だけの予測で約0.691、学習した小型モデルで約0.536だった。37件のテストで、人物の重複、未来の回答の混入、回答だけを学習するMask、ライセンス境界などを確認した。

これは**完全に人工の行動データ**であり、CentaurやBe.FMのモデル重みを再学習したものではない。実在する利用者への価値を示したものでもない。

## では、Aniccaは何のデータを集めるべきか

研究目的のTrackでは、権利が確認できる心理実験データから、「未知の人物の次の選択」や「未知のゲームの集団分布」を比較する。

商用製品のTrackでは、最初に改善したい顧客の判断を一つ定める。例えば、許可された日本語メッセージ候補から、実験する順序を決める問題だ。必要なのは、配信前に存在した情報、独立に観測された反応、実験や顧客ごとの識別子、時点、利用許諾、欠測の記録である。

クリックの確率が高いことと、通知を送った結果クリックが増えたことは違う。後者を主張するなら、ランダム割付や適切な因果評価が必要になる。

**大きなモデルを作るために、データを集めるのではない。顧客に必要な一つの判断を改善できるか、その問いに答えるデータを集める。**

### 主要な一次資料
- [Huang et al., BehaviorBench (2026)](https://arxiv.org/html/2606.24162v3)
- [BehaviorBench official evaluator](https://github.com/umich-foreseer/behaviorbench_eval)
- [BehaviorBench evaluation dataset and license](https://huggingface.co/datasets/befm/BehaviorBench)
- [Binz et al., Centaur, Nature (2025)](https://doi.org/10.1038/s41586-025-09215-4)
- [Psych-101 dataset](https://huggingface.co/datasets/marcelbinz/Psych-101)
- [Centaur training code](https://github.com/marcelbinz/Llama-3.1-Centaur-70B/blob/main/finetune.py)
- [Be.FM 1.5 model card and terms](https://huggingface.co/befm/BeFM1.5-4B)

*注：論文の数値は各著者が報告したもの。Aniccaの0.691→0.536は完全合成の教育例。実人間の選択への効果、商用モデルの訓練、経済的価値は未検証。AI執筆支援を使用した研究記事ドラフト。*
