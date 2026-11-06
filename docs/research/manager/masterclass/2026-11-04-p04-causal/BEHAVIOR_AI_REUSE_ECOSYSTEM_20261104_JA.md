# 2026年11月4日｜Behavior AI・What-if Machine・自律実行の先行研究・OSS・実際の設計を徹底比較

**目的：** 人間行動Foundation ModelとManager Executorを作るにあたり、最新の実際に公開された論文・OSS・評価・既存企業の公開説明を検査し、車輪の再発明を避ける。これは2026-11-04時点の一次資料と公式サイトに基づく技術監査。企業の自己申告スコアを独立証明と混同しない。

> **研究の中核結論**：モデルと実行系を最初から作り直さない。OSSの評価ハーネス・学習コード・行動変容Ontology・実行管理機構を再利用する。本当の技術的な差別化は「未知の人物/研究/未来への汎化 → 介入による変化の予測 → 権限内で行動 → 独立した実結果で校正」の接続にある。

## 1. 全体像：何をどのレイヤーで再利用するか

| レイヤー | 既存ソリューション | Managerが再利用する価値 | 再発明してはいけないもの |
|---|---|---|---|
| 社会の人工生成 | Epstein/AxtellのABM、OASIS、MiroFish、Generative Agents | エージェント、環境、相互作用、記憶/計画の部品 | 模擬SNS全体、Agent loopの一般機構 |
| 実人間の調査収集 | Listen Labs、Expected Parrot EDSL、Interview agents | 調査作成・回答者ごとの情報と根拠 | Survey DSL、質問スキーマ、回答画面 |
| 行動模型の学習 | SOCRATES、Be.FM 1.5（公開LoRA）、Qwen + PEFT / TRL | 人間実験回答による適応、学習方法と検証 | Qwenの事前学習、trainer、adapter機構 |
| 人物/集団の反応予測 | Stanford interviews、Simile、Listen Twins、Rehearsals、Aaru、Artificial Societies | 回答分布・個別回答・相互作用と限界の解釈 | 人間への根拠なしの「超人的なデジタルツイン」宣伝 |
| 予測能力の評価 | SimBench、BehaviorBench、HumanStudy-Bench、Rehearsals Human Behavior Bench、AS Benchmark | 未見の人/研究/時点、集合・個別、科学的帰結の尺度 | 新規独自ベンチマークを標準と呼ぶこと |
| 因果効果・方策価値 | DoWhy、EconML、OpenBanditPipeline、RCT、JITAI/MRT | 識別・推定・感度分析・Off-policy評価 | 独自の統計検定を一から実装 |
| 意味・記憶と行動記録 | BCIO、BCTTv1、PROV-O、JSON-LD、Graphiti、Palantir Ontology | 意味/有効時間/出典/実行の区別 | 既存名詞をすべて新Ontology化 |
| 実行・復旧・監査 | **既存Manager Core**、MCP、OpenTelemetry、既存Outbox/Verifier | 同意・権限・実行の不明状態・独立読み戻し | 2つ目の権限DB、既存Event ledgerの作り直し |
| 実業務A/B・価値確認 | Statsig、既存自社発行基盤、実売上/業務ログ | 比較群・費用込み利益・停止規則と独立実績 | 成果の自己申告を真実と数えること |

以下では、**誰が何を本当に発表・公開・検証したか**と**Managerが利用できる権利**を分離する。

## 2. 論文・研究機関：長い研究の流れ

### 1996年：Agent-Based Modeling（ABM）

Epstein & Axtell『Growing Artificial Societies』：個々の簡潔な行動規則から集団の現象を生み、機構とマクロパターンの対応を研究する。この系譜はLLMや「AI Twin」という商品名よりはるかに前から存在する。**仮想社会に現れた複雑さは、実社会の将来を予知できたという証拠ではない**。

### 2023年：Generative Agents

Park et al., UIST 2023：LLMへ**経験の記憶→検索→振り返り→計画**を組み合わせ、25人の住民が動く仮想町を構築。個別Agentの架空で自然な挙動を示したが、現実の購買・心理・因果効果を精度検証したわけではない。Managerはこの記憶・計画の構成を参考にしてよいが、そのままBehavior Foundation Modelと名乗らない。

一次資料：https://research.google/pubs/generative-agents-interactive-simulacra-of-human-behavior/

### 2024–2025年：実人間の面接に根ざした「本人模型」

Stanford HAIが公開する1,000人以上のインタビュー型生成Agent研究：本人の詳細な面談情報をLLMへ渡し、同じ本人の後日アンケート回答と比較。General Social Surveyの回答一致率は**本人自身の2週間後の再回答一致率の85%に相当**と報告。**85%の正答率と読み替えてはいけない**。その対象・測定課題の範囲内の比較であり、未知の介入効果や長期の実行利益は別問題。

一次資料：https://hai.stanford.edu/policy/simulating-human-behavior-with-ai-agents

### 2025年：SOCRATESが既存Qwenを実人間データで追加学習

Kolluri et al.（EMNLP 2025）『Finetuning LLMs for Human Behavior Prediction in Social Science Experiments』。**210研究、約40万参加者、約290万回答**のSOCSCI210で、実際の研究回答からQwen等をSFT/DPO。未知研究では**arXiv版ではベースモデル比26%、EMNLP 2025収録版では36%の分布整合性改善（**版の差**）**したと報告。

**これはManagerの既存研究に最も直接的な再利用候補のひとつ**：
1. 公式`socrates`のコードと`socratesft/SocSci210`のデータ契約を調査。
2. Qwen 14Bの公開SFT/DPO重みとlicense/依存するデータの利用権を確認。
3. 各実験の訓練/未見研究境界を再現する。
4. 単純ルール・同一Qwen未調整版と実際の未知条件で比較。
5. 人間研究データの用途と公開範囲を守る。論文での「未知研究」がそのまま未来の購買や人間の苦しみ改善を保証するわけではない。

公式論文（EMNLP 2025）：https://aclanthology.org/2025.emnlp-main.1530/（36%）／arXiv初期版：https://arxiv.org/abs/2509.05830（26%）。発表では**結果の版と母数**を添える。
公式研究：https://stanfordhci.github.io/socrates/
OSS：https://github.com/akaashkolluri/socrates
公開モデル：https://huggingface.co/socratesft/socrates-qwen2.5-14b-sft

### 2026年：BehaviorBenchとBe.FM 1.5

Huang et al. (2026)『BehaviorBench: Benchmarking Foundation Models for Behavioral Science Tasks』は**個別予測と集団分布の両方**を含む20シナリオの標準評価。28モデルの順位表があり、ゲーム、行動、性格、経済、実験ワークフローなどを分ける。公式**MIT**の評価コードはローカルのOpenAI互換モデルにも利用できる。

**Be.FM 1.5-4BはQwen/Qwen3-4B-Instruct-2507を元にした公開LoRA adapter**で、モデルカードにApache-2.0が掲示されている。既存の基盤モデルを再利用するので、モデル本体を一から事前学習しなくてよい。ただし独自の利用規約も記載されているので正確に確認する必要がある。

重要な権利差：`befm/BehaviorBench`の**データセットはCC BY-NC-ND 4.0表記**。モデルや評価コードのライセンスから、そのデータを商用学習へ無条件流用できると解釈しない。テストセットを学習に混ぜればそもそもベンチマークの意味が消える。

公式評価：https://github.com/umich-foreseer/behaviorbench_eval
公式結果：https://umich-foreseer.github.io/behaviorbench/
公開モデル：https://huggingface.co/befm/BeFM1.5-4B
データカード：https://huggingface.co/datasets/befm/BehaviorBench

### 2026年：実験の復元と人間への外部汎化

**SimBench（ICLR2026）**は20の人間行動データセットを統合した評価。報告された最良LLMの**40.80/100は独自スコアであって正答率40.8%ではない**。モデルサイズやinstruction tuningで実際の人間の多様性を十分再現できるわけではない。

ICLR公式：https://proceedings.iclr.cc/paper_files/paper/2026/hash/2fc4d6a6400addda7493b9db258c34e0-Abstract-Conference.html

**HumanStudy-Bench（2026）**は12実験の再現用実行エンジン。論文の手順・参加者の逐次行動・元の統計分析まで再生し、モデルの回答だけでなく**科学的な結論の一致**を評価する。OSSはMIT。Manager独自の実験実行ハーネスを再発明せずに使える可能性がある。

OSS：https://github.com/HumanStudy-Hub/HumanStudy-Bench

**Digital twins are funhouse mirrors（Science Advances 2026）**は、本人の500問超の過去回答に基づくTwinを19の事前登録研究・164結果で検証し、個人回答との平均相関が**0.20**だった。偏りと個人差の過少再現を報告。これはAaru/Listen等の全商品の性能を否定する測定ではないが、精緻な人格設定だけで汎用の行動正確性を主張すべきでない根拠。

論文：https://pmc.ncbi.nlm.nih.gov/articles/PMC13537255/

## 3. 実際に成果を主張している企業：何をコピーするか

**Aaru（2026-09）**：
- 一般的な人格プロンプトだけでなく、外部データ・調査・カード決済/実際の購入順位などを取り込む。
- 公表ベンチマークは**2,993質問、186研究、13,727回答割合**。同社公表の観測平均TVD=**7.62ポイント**、サンプル誤差補正後=**5.98ポイント**。調査正解との整合性と、実購入順位による別評価を分ける。
- 自社スコアであり、SimBench/Human Behavior Benchと同一データで順位付けできない。**盗みたい（再利用したい）方法は、同じ実人間の成果と比較し、予測の誤差を事前に予測する校正の設計**。

一次資料：https://aaru.com/publications/population-simulation-at-the-replication-floor-research

**Listen Labs / Listen Twins（2026-10-27/28公開）**：
- 実在の参加者を深掘り面接し、その人一人ひとりのTwinを構築、顧客の実際の発話に根拠を持たせ、分からないときは棄権を促す。
- 同社は**93%の回答分布一致**と自己報告。分母、独立評価、未来行動や実験の因果効果について同社の発表値だけで同等と断定しない。
- 公開APIは**Study management/response retrieval**。組織キーで`GET /wallets`と`GET /studies`が過去ターンにHTTP200で稼働した実績がある。しかし**Twin推論専用の公開RESTエンドポイントは今回確認できず**。
- 2026-11-04に**TinyFishの実ブラウザー**で`https://dev.listenlabs.ai/twins`、`/book-twins-demo`等を巡回。『Run a Simulation』は公開UIからは**デモ予約フォーム**へ遷移した。ログイン済みのTwins panelとその利用権が確認できなかったため**Twins予測そのものは実行していない**。Study作成、参加者募集、課金、本人の録音へのアクセスは行わない。
- 再利用できるのは**インタビュー→証拠つきTwin→棄権→実人間での独立検証**という設計であり、非公開モデルそのものではない。

公式製品：https://dev.listenlabs.ai/twins
2026プレス：https://kyodonewsprwire.jp/release/202610288828
実ブラウザー：https://agent.tinyfish.ai/runs/89af8069-6d12-45dd-8573-50d9cd2fa195
公開API：https://docs.listenlabs.ai/api-v2/overview

**Rehearsals / Human Behavior Bench（2026-10）**：
- First-partyパネル**1,244人**の米国成人の2026年6〜9月回答から**1,199課題**（公開239/非公開960）を設定。
- 回答分布の評価は`100*(1-TVD)`という透明な指標。同社のEngram1.0は**94.1**、一般LLMは**76.2〜80.6**と公表。ただし**一般モデルはKaggle実行、Engramは同社内部ハーネス**であり「完全な第三者が同じサーバーで検証した優位性」とは言えない。
- この評価は**群ごとの質問への回答分布**であり、個人の未来購買や実際の介入利益は測っていない。自社のパネルという評価対象へのアクセス差も考慮する。
- 再利用するのは**TVDを使う共通scorecard、公開/非公開holdout、ベースモデルの強い比較、定期更新**。指標が透明だからこそ他モデルで再現しやすい。

公式：https://www.getrehearsals.com/human-behavior-bench

**Artificial Societies / Rothko**：
- 多主体と社会的相互作用を含む意思決定シミュレーション。企業の説明は実際に存在するが、一般の未見の人間社会を万能に予測する独立ベンチマークがあるかは別に調べる。
- **コピーするのは社会・ネットワーク・介入の表現を分離し、用途と反証可能な検査を作る点**。自社の製品説明を共通ランキングとして採用しない。

公式：https://www.societies.ai/

**Palantir**：
- Data/Object/Linkの意味層、Action/Functionの実行層、dynamic security/権限層を分ける。Managerの`StateMachine/AuthorityVerifier/Outbox/Verifier`を正本にすれば、この発想は独自の巨大なGraph DBなしでも再利用できる。
- **SDK公開≠FoundryのOntologyバックエンドがOSS**。企業の権利・契約を遵守。

公式：https://www.palantir.com/docs/foundry/ontology

## 4. OSSとして今すぐ使えるもの

| OSS / artifact | 目的 | 実装状況・条件 |
|---|---|---|
| **Expected Parrot EDSL (MIT)** | AIエージェントと調査の記述、質問・回答・モデル切替 | Mac miniで既にtest modelを実行。人間の正解ではない。 |
| **SOCRATES + Qwen SFT/DPO weights** | 社会科学実験回答の追加学習 | 公開コード・モデルある。SocSci210の研究別分割とライセンスを監査して利用。 |
| **Be.FM 1.5-4B LoRA (Apache-2.0 + Terms)** | 独自行動モデルの実際の比較相手・初期adapt候補 | 公開Qwen3-4B基盤＋LoRA。公式モデルカードに24GB以上のGPU案内。 |
| **BehaviorBench evaluator (MIT)** | 個別と分布の標準採点 | macOSで公式tests/評価コードの依存を導入し検証。**データセットは別のNC/ND条件**。 |
| **HumanStudy-Bench (MIT)** | 本物の実験の試行と統計計算を再生 | 12研究の元手順を再現するハーネス。モデル呼出し費用と人間正解に権利確認が必要。 |
| **BCIO / BCTTv1 / COM-B** | 行動・介入・文脈の共通語彙 | 公式BCIO OWL 2,634クラスを先に解析。既存語彙を作り直さない。 |
| **Graphiti / Zep** | episodeの意味・valid-time・矛盾・検索 | Mac上で型を検証済み。Full ingest/searchは依存DB+LLM等、全件採用を急がない。 |
| **OASIS / MiroFish** | ネットワークを持つ人工集団の反復シミュレーション | ソース監査済み。OASIS Apache、MiroFish AGPL。現実のXでのバズを保証しない。 |
| **DoWhy / EconML / OpenBanditPipeline** | 因果識別・CATE・オフライン方策評価 | 他方の前提・positivity・交絡を満たす必要。OSSは仮定を自動で成立させない。 |
| **Statsig / OpenTelemetry / existing Manager Core** | 実事業のA/B・feature gates・proof・独立観測 | 既存のイベント・権限・復旧を残す。新しい正本を増やさない。 |

## 5. 評価指標は少なくとも5種類に分ける

**どのモデルが世界一か**の一言では科学的でない。次を区別する：

1. **個人反応**：同じ本人に対する後日・未見の回答正解率/校正。
2. **集団の分布**：TVD、Brier、KL等、選択肢の割合を予測できるか。
3. **実験の効果**：方向だけでなく介入vs対照の増分値（ATE/CATE）を当てるか。
4. **逐次社会・フィードバック**：複数エージェント/ネットワーク/時間が変わっても現実と整合するか。
5. **実際の事業と本人の益**：独立に測定した純増利益・本人が望む行動達成・反すうの尺度と負担・害。

同じスコアや「93%」でも**分母・母集団・入力条件・holdout・費用・データ利用権・外部評価者**が違えば比較できない。

## 6. Tomorrow-ready 話す内容：P06〜P12の完了を待たない

2026-11-05のジャーナルクラブは「分野の基礎→歴史→研究の現在→評価→因果→Managerの反証可能な研究構想」を**34枚、43分＋質疑15分＋余裕2分**で話せる。必要なのはP05までの理解と、主要論文/企業の数値の扱いを説明できること。**P06-2やOpen weightの完成は発表の前提ではない**。

現行PPTXの第19枚には独立Digital Twinの反例とSimBench、第26枚には複数の共通ベンチマークが既に載っている。今回新しく重要だったBehaviorBench/Be.FMを同じ第26枚へ置き換えて追加するのが、枚数を増やさず最新研究を紹介する方法。ただし分野の地図を1枚のSOTAランキングにしない。

## 7. Managerへの具体的な「コピーして使う」実装計画

- **今**：研究用のSOCRATES/Be.FM/BehaviorBenchを独立したfixtureで再現し、モデル・データ・学習・評価の権利と計算資源を固定する。小さなQwen/LoRAの技術的な学習と、Behavior FMという科学的主張は別。
- **今**：実行を伴わない最初の自社Shadow候補を同じ入力・行動・費用で比較する。実業務の新しい変更をする前に既存の許可機構と公開readbackで検証。
- **次**：P06-2で人工のwhat-if 2×2モデルと4 baseline候補の比較を実際に実行済み。次は公開の未見RCTを使って同じ評価形式を繰り返す。
- **その後**：リアル会社で正規権限の限定実行1件を行い、公式receiptと独立した読み戻しを取得。販促活動は購入/継続/実費込み利益で検証し、クリックだけを便益にしない。
- **人への価値**：本人が明確に望む低リスクな習慣支援から、同意/停止/害/本人の負担を観測。反すう・マインドフルネスの結果は別の適切な比較研究で測る。
- **公開**：オープンソースのコード・評価ハーネス・自社の権利のあるweightsとModel Cardを段階的に公開。第三者のNC/NDデータや本人の健康記録を商用訓練へ無断流用・公開しない。

## 8. 明日までに発表者が説明できれば十分な5問

1. **人工エージェントと実行エージェントは何が違う？**
2. **Generative Agents / 1:1 Interview Twin / SOCRATES / Be.FMは、何を学習して何を評価している？**
3. **Aaru 7.62TVD、Listen93%、Rehearsals94.1、SimBench40.8はなぜ単純比較できない？**
4. **モデルが本人の選択を当てることと、介入によって本人が改善することはどう違う？**
5. **Managerは予測だけでなくExecutorと独立結果をどのように結び、実会社/人への効果をどう反証可能にする？**

この五問に筋道立てて答えられれば、P06〜P12が未完でも明日のプレゼンの学術的な目的は達成できる。

---

## 参考文献・コード・ライセンス（一次資料）

- Stanford Generative Agents: https://research.google/pubs/generative-agents-interactive-simulacra-of-human-behavior/
- Stanford 1,052 interview digital twins: https://hai.stanford.edu/policy/simulating-human-behavior-with-ai-agents
- Stanford SOCRATES + SOCSCI210: https://stanfordhci.github.io/socrates/ ・ https://github.com/akaashkolluri/socrates
- SimBench ICLR2026: https://proceedings.iclr.cc/paper_files/paper/2026/hash/2fc4d6a6400addda7493b9db258c34e0-Abstract-Conference.html
- BehaviorBench: https://umich-foreseer.github.io/behaviorbench/ ・ https://github.com/umich-foreseer/behaviorbench_eval
- Be.FM1.5-4B: https://huggingface.co/befm/BeFM1.5-4B
- Dataset rights: https://huggingface.co/datasets/befm/BehaviorBench
- HumanStudy-Bench: https://github.com/HumanStudy-Hub/HumanStudy-Bench
- Rehearsals Human Behavior Bench: https://www.getrehearsals.com/human-behavior-bench
- Aaru validation: https://aaru.com/publications/population-simulation-at-the-replication-floor-research
- Listen Twins launch (company press): https://kyodonewsprwire.jp/release/202610288828
- Listen official Twins product: https://dev.listenlabs.ai/twins
- Listen public Study API: https://docs.listenlabs.ai/api-v2/overview
- Listen browser run (2026-11-04): https://agent.tinyfish.ai/runs/89af8069-6d12-45dd-8573-50d9cd2fa195
- Artificial Societies: https://www.societies.ai/
- Palantir Ontology: https://www.palantir.com/docs/foundry/ontology
- Graphiti: https://github.com/getzep/graphiti
- Expected Parrot EDSL: https://github.com/expectedparrot/edsl
- OASIS: https://github.com/camel-ai/oasis
- MiroFish: https://github.com/666ghj/MiroFish
- DOWHY / EconML / OBP: https://github.com/py-why/dowhy ・ https://github.com/py-why/EconML ・ https://github.com/st-tech/zr-obp

**本研究は2026-11-04に公開された資料の監査であり、各企業と提携していることや、その非公開モデルを自社で実際に推論実行したことを意味しない。**
