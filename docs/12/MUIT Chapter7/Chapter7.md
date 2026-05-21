# 第7章 マーケティング施策支援エージェント

# ABC社様
# XXXプロジェクト計画書

---

## 目次

1.  プロジェクト概要
2.  プロジェクト体制
3.  スケジュール・マイルストーン
4.  開発アプローチ
5.  使用ツール・技術スタック
6.  成果物
7.  リスク管理
8.  次のステップ

---

## プロジェクト概要

### 目的
ABC社様のデジタル変革を支援しDXを図る

### 目標
- 業務効率の向上（従来比XX%向上目標）
- 持続可能な開発体制の構築
- 組織全体へのナレッジ共有

---

## プロジェクト体制

### 体制図
| 役割 | 担当者 | 責任範囲 |
| :--- | :--- | :--- |
| プロジェクトマネージャー | [PM名] | 全体管理、進捗、課題管理 |
| テックリード | [リード名] | 技術選定、設計、コードレビュー |
| 開発担当 | [開発者名] | 機能実装、テスト |

### コミュニケーション
- **定例会議:** 毎週月曜日 10:00-10:30
- **連絡ツール:** Slack, Google Meet

---

## スケジュール・マイルストーン

### 全体期間
**[開始日] 〜 [終了日]**

### 主要マイルストーン
- **Week 2:** 要件定義完了
- **Week 5:** プロトタイプ版リリース
- **Week 8:** 全機能実装完了
- **Week 9:** 関係者テスト・検収
- **Week 10:** 正式リリース

---

### （ここに次のスライドを追加）

---
---
---

# Design Guideline
## このテンプレートを美しく保つためのルール

---

## スライドタイトル (`##`) のルール

### **原則: 必ず1行に収めること**
タイトルが2行になると、後続のコンテンツと重なり、レイアウトが完全に崩れてしまいます。これは最も重要なルールです。

### **目安: 全角30文字以内**
簡潔で分かりやすいタイトルを心がけてください。

<br>

#### <span class="bad-example">悪い例 (Bad) </span>
`## このプロジェクトにおける非常に重要な技術的負債とその具体的な返済計画に関する長大な考察`
（長すぎて改行され、レイアウトが崩れます）

---

## 本文・箇条書きのルール

### **原則: 1スライド・1メッセージ**
1枚のスライドに情報を詰め込みすぎず、聞き手が集中できるよう、最も伝えたいメッセージを1つに絞りましょう。

### **推奨するレイアウトと文字量**
- **1行あたりの文字数:** **全角35〜45文字**
  - これを超えると視線の移動が大きくなり、読みにくくなります。適度な位置で改行を入れましょう。
- **箇条書きの項目数:** **5〜7個**まで
- **各項目の行数:** **1〜2行**が理想
- **文章（パラグラフ）の行数:** **5〜7行**程度まで

スライドはドキュメントではありません。詳細は口頭で補うか、別途資料を配布しましょう。

---

## その他の要素のルール

### 見出し3 (`###`)
サブタイトルや小見出しとして使用します。
- **目安:** 全角15文字以内
- **役割:** これから話す内容を簡潔に示します。

### テーブル (`| |`)
情報を整理して見せる際に有効ですが、複雑になりすぎないように注意が必要です。
- **推奨カラム（列）数:** **3〜4列**まで
- **セル内のテキスト:** 可能な限り簡潔に。長いテキストは箇条書きにするなど、表現を工夫しましょう。

# 第7章 マーケティングを支援する

マーケティングは、企業の成長を支える重要な業務機能です。本章では、マーケティング業務においてAIエージェントをどのように活用できるかについて詳しく解説します。7.1節ではマーケティングプロセスを整理し、7.2節では課題とAIによる解決策について説明します。7.3節以降では、マーケティング業務におけるAIエージェントの活用事例として、3つのケーススタディを紹介します。

## 7.1 マーケティング業務とは

マーケティングとは、製品やサービスを「売れる」仕組みを作る業務です。かつては大量生産と広告による一方向的なアプローチが主流でしたが、顧客ニーズの多様化やデジタル技術の発展により、マーケティングの手法も多様化してきました（図7.1を参照）。現代では、大勢の顧客に同じメッセージを送るのではなく、個々の顧客のニーズや期待に合わせたパーソナライズされた情報やメッセージを、最適なタイミングで提供することが求められています。

### 図7.1 マーケティングの変遷

**1900~1950年: 製品中心**
- 大量生産を行い、製品を市場に供給することが目的

**1950~1970年: 顧客中心**
- 顧客のニーズを理解し、それに基づいて製品やサービスを提供することが重要

**1970~2000年: 価値志向**
- 社会的責任や倫理的な側面を考慮し、顧客との関係を深めることが重要

**2000~2010年: 自己実現**
- 顧客の自己実現を支援することが重要

**2010~2020年: テクノロジー活用**
- AIやビッグデータを活用し、顧客体験の向上を目指すことが重要

**2020~: 顧客の価値観を重視**
- 顧客の価値観を重視したアプローチ

フィリップ・コトラーの「マーケティング5.0」では、デジタル技術を活用した新たな戦略が提唱されています。AIやその他の技術を活用して、顧客の行動や潜在的なニーズを深く理解し、パーソナライズされた体験を提供することが重要です。「誰に、どのような価値を、いつ提供するか」という視点がこれまで以上に重要になっており、顧客の価値観を重視したマーケティング施策が求められています。

### 7.1.1 購買意思決定プロセスとは

顧客の価値観を重視したマーケティング施策を実現するためには、顧客の購買行動を理解することが不可欠です。代表的なフレームワークとして、コトラーの「購買意思決定プロセス」があります。これは、顧客が製品やサービスを選択してから購入するまでの行動を5つの段階に分けたものです（図7.2を参照）。

### 図7.2 購買意思決定プロセスの流れ

1. **認知**: 自分が抱える課題やニーズを意識する段階
2. **情報検索**: 必要な商品やサービスの情報を集める段階
3. **比較評価**: 複数の候補を比較し、最適な選択肢を絞り込む段階
4. **購買**: 実際に購入アクションを起こす段階
5. **購買後の行動**: 購入結果の評価、レビュー投稿、次の購買行動への影響など

このプロセスを理解することで、より精度の高いマーケティング施策を実施することができます。例えば、「認知」段階では、「XX問題を解決しましょう！」といったキャッチーなフレーズで、顧客に課題やニーズを意識させるコンテンツを提供できます。各段階で顧客を適切にサポートし、スムーズな意思決定を促すことで、顧客満足度の向上や、購入・口コミによる新規顧客獲得につながります。

### 7.1.2 マーケティング業務の内容

マーケティングプロセスは、購買意思決定プロセスに合わせて設計することで、効果的な実施が可能になります（図7.3を参照）。

### 図7.3 マーケティングプロセスと対応する業務の例

| 役割 | 企業顧客 | 施策 |
|------|---------|------|
| マーケティング部門 | 調査・分析 | 自社分析、顧客分析、SWOT分析、競合調査、市場分析、STP分析 |
| マーケティング部門 | 戦略策定 | 4P/4C、ペルソナ設計、カスタマージャーニー作成、コンテンツマーケティング |
| マーケティング部門 | 集客（認知） | プロモーション（Web広告、DM、動画、ビジネスブログ、ホワイトペーパーなど）作成・配信、SEO対策、SNS発信、プレスリリース |
| マーケティング部門 | リード顧客獲得（情報検索） | ランディングページ作成、展示会、セミナー開催、フォーム作成 |
| マーケティング部門 | リード顧客育成（比較評価） | 商品カタログ作成、導入事例作成、行動分析、リード管理、メルマガ配信、A/Bテスト、効果測定 |
| インサイドセールス | - | - |
| 営業部門 | 商談・受注（購買） | 営業活動、契約までのフォロー |
| 営業部門 | 活用支援（購買後の行動） | 顧客満足度調査、商品レビュー |

マーケティング業務の目的は、顧客をインサイドセールスや営業に適切に引き継ぐことです。マーケティングは特に、顧客獲得、リード顧客（見込み客）の獲得、育成を担当します。例えば、「集客」段階では、コンテンツや広告を通じて、顧客に自社や課題を認知させることが目的です。「リード顧客獲得・育成」段階では、メルマガやセミナー、比較情報（価格・性能表など）や具体的な導入事例の提供などの活動を行います。これらのプロセスを通じて、マーケティングは顧客の購買意欲を高め、次の段階へのスムーズな移行を目指します。

## 7.2 マーケティング業務におけるAIエージェントの活用

### 7.2.1 マーケティング業務の課題

購買意思決定プロセスに基づいた顧客視点を重視したマーケティングの重要性は理解できても、顧客ニーズの多様化やデジタルチャネルの増加により、現代のマーケティングでは、マーケティングプロセスの各段階で課題が顕在化しています。

**1. データの多様化と分析コストの増大**

WebサイトやSNSなど、さまざまなチャネルから日々膨大なデータが蓄積され、それらを統合・分析することは大きな負担となっています。これにより、スタッフが戦略的・創造的な業務に集中することが困難になっています。顧客データを一元管理するCRM（Customer Relationship Management）や、マーケティング施策を自動化するMA（Marketing Automation）などのデジタルツールが登場し、適切なタイミングでパーソナライズされた情報を提供することが可能になりました。しかし、SNSや動画データなどの非構造化データから深い顧客インサイトを抽出するには、専門的な知識やスキルが必要であり、これらのデジタルツールを活用し、データ分析を行うことができる人材が大幅に不足しています。

**2. パーソナライズの限界**

個々の顧客の興味や行動パターンを正確に把握することが困難な場合が多く、画一的な情報発信や施策になってしまうことがあります。このような状況では、顧客エンゲージメント（ブランドやサービスへの関与度）やコンバージョン率（購入、登録など）の向上が困難になります。

**3. 適切なタイミングでの施策実行の限界**

顧客の購買意思決定プロセスに合わせた最適な情報を提供できない場合、競合他社に顧客を奪われるリスクが高まります。また、市場やトレンドの変化に迅速に対応することが困難であり、タイミングを逃すとキャンペーンの効果が低下してしまいます。CRM/MAツールでよく用いられるトリガーメールやスケジュール配信と、店舗でのリアルタイムな顧客との対話を比較すると、顧客の状況や意図をリアルタイムで理解し、その場で最適なコンテンツを提供することの難しさが浮き彫りになります。

**4. マーケティングプロセスのサイクルの長期化**

マーケティング施策は、仮説を立て、実施し、効果を検証し、改善するというPDCAサイクルを繰り返すことで継続的に改善していく必要があります。しかし、データ分析や計画立案に時間をかけすぎると、意思決定が遅れ、市場機会を逃すことになります。さらに、CRMやMAなどのデジタルツールの導入自体が目的化してしまい、それらを活用する仕組みが整っていないケースも多く見られます。ツールを導入しても、運用ノウハウが属人化し、部門間の連携が不十分な場合、PDCAサイクルを効率的に回すことができません。その結果、ツール操作が複雑になり、導入効果を十分に発揮できない状況に陥ります。

### 7.2.2 AIエージェントのメリット

上記の課題を解決する有望な手段として、AIエージェントが注目されています。

**1. マーケティングプロセスの自動化・加速化**

マーケティング業務にAIエージェントを適用する第一のメリットは、マーケティングプロセスの自動化・加速化です。AIエージェントは、これまで多大な時間と労力を要していた分析、実行、改善の一連のワークフローを効率化します。計画から実行、効果検証、改善まで一貫したサポートを提供することで、PDCAサイクルをより迅速に完了させることができ、動的な市場変化に対して柔軟に対応することが可能になります。

**2. 顧客体験の向上とコンテンツの最適化**

AIエージェントは、顧客の行動や興味を詳細に分析し、個々の顧客に合わせたパーソナライズされたコンテンツやレコメンデーションを提供します。このアプローチにより、画一的なアプローチでは実現できなかった高いエンゲージメントやコンバージョン率を達成することが期待され、顧客体験の向上につながります。

AIエージェントは、単なる効率化ツールではなく、顧客とより深く、より柔軟に対話するマーケティングパートナーとして機能します。企業が煩雑な業務から解放されることで、顧客との対話に最大限の時間を割くことができ、結果として市場での競争力を高めることができます。

### 7.2.3 マーケティングを支援するAIエージェントの活用事例（ソリューション紹介）

マーケティングを支援するAIエージェントは、すでにさまざまなプラットフォームやベンダーから提供されており、代表的な事例を以下に紹介します。

**■Agentforce: Sales Development Representative (SDR) Agent**

リード顧客との初回接触を自動化し、リード育成を支援するエージェントです。製品に関する質問に自律的に回答し、反論に対応し、営業担当者に代わってアポイントメントを設定することもできます。ユーザーは、AIエージェントとの対話の頻度やチャネル、営業担当者への引き継ぎタイミングを指定でき、SMSやWhatsAppなどの希望するチャネルで、あらゆる言語でコミュニケーションを取ることができます。

**■Agentforce: Personal Shopper Agent**

ショッパーと対話し、パーソナライズされた商品を提案することで、顧客のショッピング体験を向上させるAIエージェントです。情報検索から交渉、購入段階での成約まで、顧客をサポートします。

**■JAPAN AI AGENT**

日本の市場に特化した自然言語処理と法的コンプライアンスを備えたエージェントで、マーケティング活動を支援します。マーケティングプロセスに合わせてカスタマイズでき、特定の企業のニーズに適応することができます。

### 7.2.4 マーケティングを支援するAIエージェントによる課題解決のアプローチ

以降の7.3節以降では、マーケティング業務を支援するAIエージェントの具体的な実装例を紹介します。「新サービスを成功させるためにAIエージェントを活用する」というシナリオに基づいて、マーケティング業務の課題をAIエージェントがどのように解決できるかを説明します。

**シナリオの背景**

IT企業が、AIエージェントを活用して業務効率化を目指すビジネスパーソンを対象とした「AIエージェント実践講座」という新サービスを立ち上げました。しかし、この企業は2つの主要なケースで課題を抱えており、それぞれの課題に対してAIエージェントを活用してサポートすることを目指しています。

**ケース①: 集客・リード顧客獲得プロセスにおける課題（図7.4の範囲）**

**■課題**: 顧客ニーズに合った最適なコンテンツを選定することが課題です。A/Bテストで効果を測定することはできますが、結果の解釈が困難であり、十分なデータ収集には時間がかかるため、迅速な意思決定が困難です。

**■解決策**: 7.4節でロールプレイングによる意思決定支援エージェントを作成し、ターゲットとなる顧客層に最適なコンテンツの効果をロールプレイング形式でシミュレーションします。シミュレーション結果をマーケティングチームにフィードバックすることで、マーケティングチームの迅速な意思決定を支援します。

**ケース②: リード顧客獲得・リード顧客育成プロセスにおける課題（図7.5の範囲）**

**■課題**: 顧客ニーズを迅速に把握し、適切なタイミングでコンテンツを提供することでリード顧客を育成し購買につなげたいと考えているものの、施策を実施するための十分な人員やツールが整っていない状況です。

**■解決策**: 7.5節でパーソナライズ施策支援エージェントを作成し、個別の顧客ニーズにあった商品提案やレコメンドを支援します。このAIエージェントは、顧客と対話することで顧客の興味を引き出し、文脈や意図を反映した商品提案や広告を提供することで、顧客の購買行動を促進します。

ここからは、上記2つのケースに対応したAIエージェントの実装例を紹介していきます。

### 7.2.5 各エージェントやツールの紹介

本項以降で扱うコードはリポジトリのchapter7フォルダにあります。内容は以下の通りです。

```
chapter7/
├── notebooks/
│   └── <各節のエージェント名>_runner.ipynb
├── uv.lock
├── pyproject.toml
└── src/
    └── <各節のエージェント名>/
        ├── agent.py
        ├── configs.py
        ├── custom_logger.py
        ├── models.py
        └── prompts.py
```

それぞれのファイルの内容は表7.1の通りです。

### 表7.1 7章で使用するファイルの説明

| ファイル名 | 説明 |
|----------|------|
| `notebooks/` | 各種Jupyter Notebookが含まれており、個別の処理の実行確認に使用します |
| `uv.lock, pyproject.toml` | uvによる依存関係管理のファイルです |
| `src/` | Pythonのソースコードが配置されています |
| `src/<各節のAIエージェント名>/agent.py` | AIエージェントの主要な処理が記述されています |
| `src/<各節のAIエージェント名>/configs.py` | .envの内容を読み込むクラス定義ファイルです |
| `src/<各節のAIエージェント名>/custom_logger.py` | カスタムロガーを定義しています |
| `src/<各節のAIエージェント名>/models.py` | データモデルの定義が含まれています |
| `src/<各節のAIエージェント名>/prompts.py` | プロンプトの定義が含まれています |

uvはPythonの依存関係管理ツールであり、`uv sync`を実行することで必要な依存関係がインストールされます。各節での処理にはOpenAIのAPIを使用するため、`.env`ファイルにOpenAI APIキーを設定してください。使用するモデルは`gpt-4o (ver: 2024-08-06)`です。

## 7.3 ロールプレイングによる意思決定支援エージェント

ロールプレイングによる意思決定支援エージェントは、ターゲットとなる顧客層に対するコンテンツの効果をシミュレーションすることで、マーケティングチームの迅速な意思決定を支援します。

複数のコンテンツ案を評価する際、迅速な意思決定が求められますが、データが不足している場合や、議論に時間がかかる場合、実装が遅れてしまうことがあります。従来のA/Bテストでは、選択肢が限られ、十分なデータを収集するまでに時間がかかります。ロールプレイングプロセスを導入することで、意思決定に必要な時間とリソースを大幅に削減することができます。

図7.6に示すように、ターゲットペルソナを定義し、AIエージェントがコンテンツに対するペルソナの反応をシミュレーションします。シミュレーション結果をフィードバックとして活用することで、コンテンツの改善や、より正確で迅速な意思決定が可能になります。

### 図7.6 AIエージェントによる意思決定支援のイメージ

```
想定顧客に対するコンテンツの効果測定をしたい
  ↓
ペルソナによる疑似的な評価結果を提供
  ↓
AIエージェントが意思決定を支援
  ↓
完了
```

意思決定支援の具体例として、以下では複数のコンテンツ案の評価・改善を取り上げます。

### 7.3.1 コンテンツ案の評価・改善を行うマルチエージェント

ターゲット顧客がコンテンツ案に対してどのような印象を持つかを評価するため、まずターゲットペルソナを作成し、アンケート形式で評価をシミュレーションします。さらに、アンケート結果を分析し、改善を行うプロセスを含むマルチエージェントシステムを構築します。実装したマルチエージェントシステムは、図7.7に示すビジネスプロセスフローに従って動作します。

### 図7.7 意思決定支援エージェントの処理の流れ

```
開始
  ↓
Persona Generator（ペルソナを作成するエージェント）
  ↓
Contents Evaluator（ペルソナによる評価を実施するエージェント）
  ↓
Contents Analyzer（評価結果を分析し、レポート作成をするエージェント）
  ↓
Contents Improver（分析結果をもとにコンテンツ案を改善するエージェント）
  ↓
最終結果
```

コンテンツ案をペルソナに評価させるため、まずペルソナを作成するPersona Generatorを定義します。次に、作成したペルソナを使用して評価を実施するContents Evaluatorを定義します。その後、評価結果を分析し、レポートを作成するContents Analyzerを定義します。最後に、評価の分析結果に基づいてコンテンツ案を改善するContents Improverを定義します。

### 7.3.2 各エージェントやツールの紹介

本節で扱うコードはリポジトリの`chapter7/src/decision_support_agent`フォルダにあります。

#### 7.3.2.1 全体のワークフローの定義

`AgentState`クラスで、リクエスト内容、ペルソナ、アンケート、レポート、評価データ、コンテンツ案、改善後のコンテンツ案などの各種状態を管理します。

### プログラムリスト 7.1 chapter7/src/decision_support_agent/agent.py

```python
# ステートの定義
class AgentState(TypedDict):
    request: str
    contents: list[str]
    personas: list[str]
    questionnaire: str
    report: str
    evaluations: list[dict[str, str | int]]
    improved_contents: list[str] | None

# 意思決定支援エージェントのクラス定義
class DecisionSupportAgent:
    def __init__(self):
        self.settings = Settings()
        self.deployment_name = self.settings.OPENAI_DEPLOYMENT_NAME
        
        # Chat OpenAI client setup（省略）
        
        # 各エージェントのインスタンス化
        self.persona_generator = PersonaGeneratorAgent(...)
        self.contents_evaluator = ContentsEvaluatorAgent(client=self.client)
        self.contents_analyzer = ContentsAnalyzerAgent(client=self.client)
        self.content_improver = ContentImproverAgent(client_improver=self.client_improver)
    
    def create_graph(self) -> Pregel:
        """AIエージェントのメイングラフを作成する"""
        workflow = StateGraph(AgentState)
        
        # 各エージェントのノードを追加
        workflow.add_node("persona_generator", self.persona_generator.run)
        workflow.add_node("contents_evaluator", self.contents_evaluator.run)
        workflow.add_node("contents_analyzer", self.contents_analyzer.run)
        workflow.add_node("content_improver", self.content_improver.run)
        
        # エッジの定義
        workflow.set_entry_point(START)
        workflow.add_edge(START, "persona_generator")
        workflow.add_edge("persona_generator", "contents_evaluator")
        workflow.add_edge("contents_evaluator", "contents_analyzer")
        workflow.add_edge("contents_analyzer", "content_improver")
        workflow.add_edge("content_improver", END)
        
        return workflow.compile()
```

#### 7.3.2.2 各エージェントの設定

下記のコードは、各エージェントをそれぞれクラスとして定義したものです。

**Persona Generator**

**■persona_generator_agent: ペルソナを作成するエージェント**

まず、コンテンツ評価に適したペルソナを作成します。ペルソナ作成を実行する関数（persona_create_run）は別途定義されています。ツールとして保持することもできますが、このノードで必ず実行される関数であるため、プロセスとして定義しています。今回は、各役割について5種類のペルソナを作成するように設定しています。

### プログラムリスト 7.2 chapter7/src/decision_support_agent/agent.py

```python
# ペルソナ作成用システムプロンプト
PERSONA_CREATE_SYSTEM_PROMPT = (
    """プロフィールガイドラインに基づいて、独自のペルソナを作成できます。
    
    ## ペルソナプロフィールガイドライン
    
    ## 職業
    - ペルソナの職業を設定してください
    
    ## 趣味・関心
    - ペルソナが関心を持っている趣味や日常的な興味をリスト形式で設定してください。
    
    ## スキルや知識
    - ペルソナが持つ特定のスキルや専門知識をリスト形式で設定してください。
    """
)

# ペルソナ生成エージェント用システムプロンプト
PERSONA_GENERATOR_PROMPT = (
    """あなたはコンテンツ評価に必要なペルソナを作成するエージェントです。
    # 行動
    - コンテンツ評価に必要なペルソナを作成する
    
    # 制約
    - ユーザーのリクエストに基づいてのみペルソナを作成すること
    """
)

class PersonaGeneratorAgent(BaseAgent):
    def __init__(self, ...):
        self.client_persona_role = ChatOpenAI(...)
        self.client_persona = ChatOpenAI(...)
    
    def persona_create_run(self, i, persona_list, persona_profile_list, user_request, target_text):
        for i in range(5):
            text_messages = [
                {
                    "role": "system",
                    "content": PERSONA_CREATE_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": (
                        f"{persona_list[i]}\n"
                        "上記の情報に基づいて、ペルソナを作成してください。\n"
                        f"{user_request}"
                    )
                }
            ]
            # ... 処理 ...
            persona_profile = (
                f"役割: {persona_list[i]}\n"
                f"職業: {response.content}\n"
                f"趣味・関心: {response.content}\n"
                f"スキルや知識: {response.content}"
            )
            persona_profile_list.append(persona_profile)
        return persona_profile_list
    
    def run(self, state: AgentState) -> AgentState:
        persona_profile_list = []
        message = [
            {
                "role": "system",
                "content": PERSONA_GENERATOR_PROMPT
            },
            {
                "role": "user",
                "content": (
                    f"リクエスト: {state['request']}\n"
                    f"評価対象のコンテンツ: {state['contents']}"
                )
            }
        ]
        persona_list = self.client_persona_role.invoke(message).persona_list
        logger.info("persona_list: %s", persona_list)
        
        for i in range(len(persona_list)):
            persona_profile_list = self.persona_create_run(
                i, persona_list, persona_profile_list, 
                state['request'], state['contents']
            )
            logger.info("生成ペルソナプロファイル: %s", persona_profile_list[i])
        
        state["personas"] = persona_profile_list
        return state
```

**Contents Evaluator**

**■contents_evaluator_agent: ペルソナによって評価を実施するエージェント**

評価項目に沿って、コンテンツ案を評価します。

### プログラムリスト 7.3 chapter7/src/decision_support_agent/agent.py

```python
# コンテンツ評価エージェント用システムプロンプト
CONTENTS_EVALUATOR_PROMPT = (
    """あなたはペルソナの視点からコンテンツを評価するエージェントです。
    ペルソナ: {persona}
    # 行動: コンテンツを評価する
    # 評価項目: {questionnaire}
    # 制約: ペルソナ視点で批判的に評価
    """
)

class ContentsEvaluatorAgent(BaseAgent):
    def __init__(self, client: ChatOpenAI):
        self.client = client
    
    def run(self, state: AgentState) -> AgentState:
        evaluations = []
        for persona in state["personas"]:
            logger.info("評価実施ペルソナ: %s", persona)
            message = [
                {
                    "role": "system",
                    "content": CONTENTS_EVALUATOR_PROMPT.format(
                        persona=persona,
                        questionnaire=state["questionnaire"]
                    )
                },
                {
                    "role": "user",
                    "content": f"以下のコンテンツを評価してください:\n{state['contents']}"
                }
            ]
            logger.info("message: %s", message)
            text_response = self.client.invoke(message)
            evaluations.append({
                "persona": persona,
                "feedback": text_response.content
            })
        state["evaluations"] = evaluations
        return state
```

評価項目には以下のアンケート形式の項目を設定することにします。

### プログラムリスト 7.4 chapter7/src/decision_support_agent/prompts.py

```python
DEFAULT_QUESTIONNAIRE = """
複数のコンテンツの中で、もっとも魅力的だと感じたものを選んでください。

### 1. 魅力
コンテンツのどの部分が魅力的だと感じましたか?
- 魅力的だと感じた理由を教えてください。

### 2. 訴求力
このコンテンツの内容にどれだけ興味を持ちましたか?
- 非常に興味を持った
- 少し興味を持った
- 興味を持たなかった
- 自由記述: 興味を持たなかった場合、その理由を教えてください。

### 3. 理解しやすさ
コンテンツを見たとき、内容を明確にイメージできましたか?
- はい
- 部分的に
- いいえ
- 自由記述: 理解しやすさについて感じたことや改善案があれば教えてください。

### 4. 興味喚起
コンテンツはあなたの興味をどれくらい喚起しましたか?
- 非常に興味を持った
- 興味を持った
- 少し興味を持った
- 興味を持たなかった
- 自由記述: さらに興味を喚起するために改善できる点は何ですか?

### 5. 行動喚起
コンテンツを見た後、次のアクションを取りたくなりましたか?
- すぐに内容を読みたくなった
- 詳細を調べたくなった
- 他の人に勧めたくなった
- とくに何も行動したくならなかった
- 自由記述: 行動を促すためにコンテンツに求める要素は何ですか?
"""
```

アンケートの項目はLLMに作成させることも可能ですが、最終的な結果を左右する重要な部分であるため、今回は事前に定義したアンケート項目を使用します。また、ペルソナを模倣したエージェントからの回答を求める場合、人間に負担をかける定量的なアンケート項目を使用する必要はありません。定性的な項目を設定することで、インタビュー形式の質問により、定量的なアンケートでは得られないインサイトを引き出すことができます。

**Contents Analyzer**

**■contents_analyzer_agent: 評価結果を分析し、レポートを作成するエージェント**

ペルソナから提供されたアンケート結果を分析し、コンテンツ案の改善に役立つインサイトを抽出し、レポートを作成します。

### プログラムリスト 7.5 chapter7/src/decision_support_agent/agent.py

```python
# コンテンツ分析エージェント用システムプロンプト
CONTENTS_ANALYZER_PROMPT = (
    """あなたは評価結果を分析し、改善レポートを作成するエージェントです。
    # 行動: 詳細な改善レポートを作成する
    # 制約
    - ペルソナの視点を重視して評価結果を分析すること
    - このレポートはコンテンツの改善に使用されるため、具体的な改善点を示すこと
    # 評価を実施したペルソナ: {personas}"""
)

class ContentsAnalyzerAgent(BaseAgent):
    def __init__(self, client: ChatOpenAI):
        self.client = client
    
    def run(self, state: AgentState) -> AgentState:
        message = [
            {
                "role": "system",
                "content": CONTENTS_ANALYZER_PROMPT.format(
                    personas=state["personas"]
                )
            },
            {
                "role": "user",
                "content": (
                    f"評価結果: {state['evaluations']}\n"
                    "上記評価結果に基づき、具体的な改善レポートを作成してください。"
                )
            }
        ]
        text_response = self.client.invoke(message)
        state["report"] = text_response.content
        logger.info("作成レポート: %s", state["report"])
        return state
```

**Contents Improver**

**■content_improver_agent: 分析結果をもとに改善するエージェント**

アンケートの評価レポートに基づいて、コンテンツ案を改善します。これにより、想定ペルソナにより適合したコンテンツ案を作成することができます。

### プログラムリスト 7.6 chapter7/src/decision_support_agent/agent.py

```python
# コンテンツ改善エージェント用システムプロンプト
CONTENT_IMPROVER_PROMPT = (
    """あなたはコンテンツ改善エージェントです。
    # 行動: 評価レポートに基づいてコンテンツを改善する
    # 制約: 必ず改善後のコンテンツだけ出力すること"""
)

class ContentImproverAgent(BaseAgent):
    def __init__(self, client_improver: ChatOpenAI):
        self.client_improver = client_improver
    
    def run(self, state: AgentState) -> AgentState:
        message = [
            {
                "role": "system",
                "content": CONTENT_IMPROVER_PROMPT
            },
            {
                "role": "user",
                "content": (
                    f"コンテンツ: {state['contents']}\n"
                    f"リクエスト: {state['request']}\n"
                    f"評価レポート: {state['report']}\n"
                    "上記に基づき、改善後のコンテンツを生成してください。"
                )
            }
        ]
        text_response = self.client_improver.invoke(message)
        state["improved_contents"] = text_response.content
        logger.info("改善後コンテンツ: %s", state["improved_contents"])
        return state
```

### 7.3.3 ロールプレイングによる意思決定支援エージェントの挙動確認

評価対象は、認知フェーズに対するコンテンツのテーマ案とします。

## プログラムリスト 7.7 chapter7/src/decision_support_agent/prompts.py

```python
CONTENTS_LIST = (
    #認知フェーズ
    形式: ブログ記事
    コンテンツタイトル: AI エージェント活用事例:業務効率化の成功ストーリー
    コンテンツ概要: LinkedIn や X (Twitter) でシェアするためのブログ記事。AIエージェントを活用して業務効率化を実現した企業の成功事例を紹介し、ビジネスパーソンに興味を持たせる。

    #認知フェーズ
    形式:ウェビナー
    コンテンツタイトル: AI エージェントの可能性を探る: 業界リーダーによるディスカッション
    コンテンツ概要: 業界関連のオンラインイベントでのプレゼンテーション。AIエージェントの活用方法や業務効率化の具体例を業界リーダーがディスカッションするウェビナー。

    #認知フェーズ
    形式: ポッドキャスト
    コンテンツタイトル: AI エージェントで変わるビジネスの未来
    コンテンツ概要: マーケティング関連のポッドキャストでのゲスト出演。AI エージェントがどのようにビジネスの未来を変えるかについてのインタビューを通じて、リスナーに認知を広げる。
)
```

想定シナリオの講座のターゲットとなるビジネスパーソンをペルソナとして設定し、改善を依頼してみます。

```python
user_request = "AI エージェントを活用して業務効率化を目指すビジネスパーソンに興味をもってもらえるようにコンテンツのテーマを改善して"
```

まず、コンテンツ評価に必要なペルソナが作成されます。

### ■作成されたペルソナの例

```
役割: ビジネスパーソン
職業: コンサルタント
趣味・関心:最新の技術革新、ビジネス書の読書、ジョギング
スキルや知識: 業務プロセス改善, デジタルツールの導入と管理, リーダーシップト
```

次に、各ペルソナに対してアンケートが実施された後、アンケート結果をもとに以下のレポートが作成されます。

### ■レポートの結果 (結論部分のみ抜粋)

```
##結論

全体的に、どのコンテンツもビジネスパーソンにとって魅力的であり、興味を引く要素が多く含まれています。上記の改善点を考慮し、より効果的な情報発信を目指すことが重要です。とくに、ウェビナーやポッドキャストにおいては、具体的な事例やインタラクティブな要素を強化することで、参加者の興味をさらに引き出すことができるでしょう。
```

最後に、レポート結果をもとに、コンテンツ案の改善を実施します。

### ■改善後のコンテンツのテーマ案

```
# **認知フェーズ 形式: ブログ記事**

コンテンツタイトル: AI エージェント活用事例:業務効率化の成功ストーリー

コンテンツ概要: LinkedIn や X (Twitter) でシェアするためのブログ記事。AIエージェントを活用して業務効率化を実現した企業の成功事例を紹介し、ビジネスパーソンに興味を持たせる。具体的な成功事例をさらに掘り下げ、インフォグラフィックや図表を用いて視覚的に情報を伝える工夫を加える。
```

「可能性」、「成功ストーリー」という曖昧な表現から、具体的な事例を「掘り下げる」という表現や視覚要素 (インフォグラフィック・図表)が追加され、より読者の興味に絞ってわかりやすい表現を行うように変化しています。

## 7.4 パーソナライズ施策支援エージェント

7.3 節のエージェントを活用したマーケティング施策によって顧客の認知や自社サイトへの流入を高めることができても、リード顧客を獲得し、最終的に購買 (受講) アクションへつなげることには課題が残ります。想定シナリオにおける「AI エージェント実践講座」のように、AI エージェントを活用した業務効率化に興味のあるビジネスパーソンを広く募ったとしても、顧客の興味や検討フェーズに反したプロモーション (DM やバナー広告など)やコンテンツを提示してしまった場合、顧客が離脱する可能性があります。たとえば、AI エージェントにまだ触れたことのない初心者から、すでに業務で活用を始めている上級者まで、幅広い層が存在するため、一括りにしたプロモーションでは訴求力に限界があります。また、「この講座を受講するとどのようなメリットがあるのか」や「どんな課題を解決できるのか」など、顧客の興味・関心や検討フェーズに応じた適切な情報を提供することが重要です。

従来のレコメンドシステムでは、過去の購買履歴や閲覧履歴などのデータに基づいて推薦を行うため、新規ユーザーに対しては十分なデータがない「コールドスタート問題」が発生します。また、ユーザーのリアルタイムな文脈や意図を反映することが難しく、パーソナライズの限界があります。

このような課題を解決するために、会話を通じてユーザーの興味やニーズを理解し、柔軟にパーソナライズされたレコメンドを提供する会話型AIエージェントが注目されています。本節では、会話型レコメンドシステムの一例として、Multi-Agent Conversational Recommender System (MACRS) を紹介します。

### 表7.2 従来型のレコメンドとAI エージェントによるレコメンドの違い

| 課題 | 従来型のレコメンド | AIエージェントによるレコメンド |
|------|-------------------|------------------------------|
| コールドスタート問題 | データが不足すると対応不可 | 文脈や外部情報を会話から取得して対応可能 |
| パーソナライズの限界 | 過去データに依存 | リアルタイム文脈やトレンドを反映 |
| 提案の多様性不足 | 類似商品に偏る | 異なるカテゴリや新しい関連性を提案 |
| フィードバックの活用 | 基本的に対応不可 | リアルタイムでの応答と提案変更が可能 |

### 図7.8 MACRSのイメージ

(脚注7の Figure 1: Example of modeling a Conversational Recommendation System (CRS) using a multi-agent frameworkをもとに筆者が作成)

**MACRS (Multi-Agent Conversational Recommender System) の構成:**

- **プランナーエージェント**: どの応答エージェントに応答してもらうか計画
- **応答エージェント**:
  - 質問エージェント
  - 推薦エージェント
  - 雑談エージェント

**チャット欄の例:**

1. **ユーザー**: こんにちは! リラックスできるアニメ映画を観たいです。
2. **MACRS (質問)**: もちろんです! クラシックな映画をお探しですか、それとも最近のものが良いですか?
3. **ユーザー**: 最近の映画を探しています。
4. **MACRS (推薦)**: 「マイ・エレメンタル」はいかがですか? これはアニメ映画です
5. **ユーザー**: ありがとう。でも、私はロマンチックなストーリーはあまり好みではありません。

### 7.4.1 会話型レコメンドを行うマルチエージェント

本節では、MACRSを参考に、会話型レコメンドを行うマルチエージェントを実装します。プランナーエージェント (ルーター) が複数の応答エージェントの中から最適なものを選択し、その応答をユーザーに返します。図7.9に示すように、マルチエージェントシステムは状況に応じて必要なエージェントを呼び出すように構成されています。

### 図7.9 パーソナライズ施策支援エージェントの処理の流れ

```
ユーザー入力処理ノード
  ↓
プランナーエージェント (どの応答エージェントに応答してもらうか選択する)
  ↓
応答エージェント
  ├─ 質問エージェント
  ├─ 推薦エージェント
  └─ 雑談エージェント
```

ユーザーからの問い合わせに対し、以下のどの応答エージェントに回答させるかプランナーエージェントが計画し、以下の中から最適なエージェントを選択します。

- **■質問エージェント**: ユーザーの好みやニーズを引き出すために質問を生成します。
- **■推薦エージェント**: ユーザーの興味に基づいてコンテンツのレコメンドを行います。
- **■雑談エージェント**: ユーザーと雑談を交えることで興味を引き出します。

### 7.4.2 各エージェントやツールの紹介

本節で扱うコードはリポジトリのchapter7/src/macrs フォルダにあります。

#### 7.4.2.1 全体のワークフローの定義

AgentState クラスで、ユーザーの設定や会話履歴、最終応答、エージェント選択などの状態を管理します。プランナーエージェントの出力 (selected_agent)に基づいて、適切なエージェント (質問生成、レコメンド、雑談)にルーティングします。

### プログラムリスト 7.8 chapter7/src/macrs/agent.py

```python
# ステートの定義
class AgentState(TypedDict):
    user_input: str
    conversation_history: str
    exit: bool
    selected_agent: str
    current_response: str

# MACRS クラス: 各エージェントを管理
class MACRS:
    def __init__(self):
        load_dotenv()
        self.settings = Settings()
        self.deployment_name = self.settings.OPENAI_DEPLOYMENT_NAME

# Chat OpenAI クライアントのセットアップ

# 各エージェントのインスタンス化
        self.user_input_agent = UserInputAgent()
        self.question_agent = QuestionAgent(self.client)
        self.recommendation_agent = RecommendationAgent(self.client)
        self.chitchat_agent = ChitChatAgent(self.client)
        self.planner_agent = PlannerAgent(self.client_router)

    def create_graph(self) -> Pregel:
        """エージェントのメイングラフを作成する"""
```

### プログラムリスト 7.9 chapter7/src/macrs/agent.py

```python
# 各エージェントの run メソッドをノードとして追加
        workflow = StateGraph(AgentState)
        workflow.add_node("get_user_input", self.user_input_agent.run)
        workflow.add_node("QuestionAgent", self.question_agent.run)
        workflow.add_node("RecommendationAgent", self.recommendation_agent.run)
        workflow.add_node("ChitChatAgent", self.chitchat_agent.run)
        workflow.add_node("planner_agent", self.planner_agent.run)

# エントリーポイントの設定とエッジの接続
        workflow.set_entry_point("get_user_input")

# exit が True ならば処理を終了、そうでなければ planner に進む
        workflow.add_conditional_edges(
            "get_user_input",
            lambda state: "exit" if state.get("exit") else "continue",
            {
                "exit": END,
                "continue": "planner_agent"
            }
        )
        workflow.add_conditional_edges(
            "planner_agent",
            lambda state: state["selected_agent"],
            path_map={
                "QuestionAgent": "QuestionAgent",
                "ChitChatAgent": "ChitChatAgent",
                "RecommendationAgent": "RecommendationAgent",
            },
        )
        return workflow.compile()
```

```python
# ユーザー入力エージェント
class UserInputAgent(BaseAgent):
    async def run(self, state: dict, prompt="あなた: ") -> dict:
        user_input = input(prompt)
        logger.info("ユーザー: %s", user_input)
        if user_input.lower() == "exit":
            print("対話を終了します。ありがとうございました!")
            state["exit"] = True
            return state
        else:
            state["conversation_history"] += f"\nユーザー: {user_input}"
            state["user_input"] = user_input
            state["exit"] = False
            return state
```

#### 7.4.2.2 ユーザー入力処理ノード

**■ UserInputNode: ユーザー入力処理ノードのクラス定義**

ユーザーからの問い合わせによって対話を継続するかどうか判定します。

#### 7.4.2.3 応答エージェント

ユーザーからの問い合わせの応答に用いる3つの応答エージェントを実装します。以下の構成となっています。

**■ QuestionAgent: 質問エージェントのクラス定義**

- ユーザーとの会話履歴を参照しながら、興味を引き出す質問を生成。
- ユーザーとの会話履歴や提供されたコンテンツリストをもとに質問を生成。

**■ RecommendationAgent: 推薦エージェントのクラス定義**

- ユーザーとの会話履歴に基づいて、コンテンツリストから適切な推薦を行う。

**■ ChitChatAgent: 雑談エージェントのクラス定義**

- ユーザーとの親しみやすい会話を行う。

### プログラムリスト 7.10 chapter7/src/macrs/agent.py

```python
# 質問生成エージェント
class QuestionAgent(BaseAgent):
    def __init__(self, client: ChatOpenAI):
        self.client = client

    async def run(self, state: dict) -> dict:
        prompt = QUESTION_PROMPT
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"ユーザーとの過去の会話履歴:\n{state['conversation_history']}")
        ]
        response = await self.client.ainvoke(messages)
        question = response.content
        logger.info("AI エージェント (質問): %s", question)
        state["conversation_history"] += f"\n質問: {question}"
        return state

# レコメンデーション生成エージェント
class RecommendationAgent(BaseAgent):
    def __init__(self, client: ChatOpenAI):
        self.client = client

    async def run(self, state: dict) -> dict:
        prompt = RECOMMENDATION_PROMPT
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"ユーザーとの過去の会話履歴:\n{state['conversation_history']}")
        ]
        response = await self.client.ainvoke(messages)
        recommendation = response.content
        logger.info("AI エージェント (レコメンド): %s", recommendation)
        state["recommendation"] = recommendation
        state["conversation_history"] += f"\nレコメンド: {recommendation}"
        return state

# 雑談エージェント
class ChitChatAgent(BaseAgent):
    def __init__(self, client: ChatOpenAI):
        self.client = client

    async def run(self, state: dict) -> dict:
        messages = [
            SystemMessage(content=CHITCHAT_PROMPT),
            HumanMessage(content=f"ユーザーとの過去の会話履歴:\n{state['conversation_history']}")
        ]
        response = await self.client.ainvoke(messages)
        chitchat = response.content
        logger.info("AI エージェント (雑談): %s", chitchat)
        state["conversation_history"] += f"\nおしゃべり: {chitchat}"
        return state
```

応答エージェントはシステムプロンプトを与えただけのシンプルなエージェントです。

#### 7.4.2.4 プランナーエージェント

プランナーエージェントは、どの応答エージェントに応答してもらうか選択するルーターの役割を担っています。

**■ PlannerAgent: プランナーエージェントのクラス定義**

ユーザーの入力や会話履歴をもとに、適切なエージェント (QuestionAgent、RecommendationAgent、ChitChatAgent) を選択します。

### プログラムリスト 7.11 chapter7/src/macrs/agent.py

```python
# プランナーエージェントのクラス定義
class PlannerAgent(BaseAgent):
    def __init__(self, client_router: ChatOpenAI):
        self.client_router = client_router

    async def run(self, state: dict) -> dict:
        messages = [
            SystemMessage(content=PLANNER_PROMPT),
            HumanMessage(content=f"ユーザーの入力: {state['user_input']}\n\nユーザーとの過去の会話履歴:\n{state['conversation_history']}")
        ]
        response = await self.client_router.ainvoke(messages)
        selected_agent = ["QuestionAgent", "ChitChatAgent", "RecommendationAgent"][response.selected_agent_int]
        state["selected_agent"] = selected_agent
        logger.info("選択されたエージェント: %s", selected_agent)
        return state
```

### 7.4.3 パーソナライズ施策支援エージェントの挙動確認

レコメンド対象のコンテンツ候補リストは、7.3節で作成したコンテンツ提案をもとに、購買意思決定プロセスの各フェーズに適したコンテンツを推薦できるように設計されています。なお、記載されているURLは架空のものです。

### プログラムリスト 7.12 chapter7/src/macrs/prompts.py

```python
# コンテンツリストの定義
CONTENT_LIST = """
# 認知フェーズ
形式: ブログ記事
コンテンツタイトル: AI エージェント活用事例:業務効率化の成功ストーリー
コンテンツ概要: LinkedIn や X (Twitter) でシェアするためのブログ記事。AIエージェントを活用して業務効率化を実現した企業の成功事例を紹介し、ビジネスパーソンに興味を持たせる。
URL: https://www.agent.advanced.book.example1.com

# 情報検索フェーズ
形式: メールニュースレター
コンテンツタイトル: 最新のAIエージェント情報: 業務効率化のヒント
コンテンツ概要: メールニュースレター。最新のAIエージェント情報や業務効率化のヒントを提供し、読者の興味を維持する。
URL: https://www.agent.advanced.book.example2.com

# 比較・評価フェーズ
形式: ダウンロード資料
コンテンツタイトル: AIエージェント vs 他のAIツール: 比較ガイド
コンテンツ概要: ダウンロード可能な比較ガイド。AIエージェントと他のAIツールを比較し、読者が適切な選択をできるようにサポートする。
URL: https://www.agent.advanced.book.example3.com

# 購入フェーズ
形式: プロモーションメール
コンテンツタイトル: 期間限定! AIエージェント実践講座が割引価格で受講可能
コンテンツ概要: プロモーションメール。期間限定の割引情報を提供し、読者の購買意欲を高める。
URL: https://www.agent.advanced.book.example4.com

# 購入後の行動フェーズ
形式: コミュニティフォーラム
コンテンツタイトル: 参加者同士の交流を深める: AIエージェントコミュニティ
コンテンツ概要: コミュニティフォーラム。受講者同士が交流し、知識を共有できる場を提供する。
URL: https://www.agent.advanced.book.example5.com
"""
```

出力結果は以下の通りです。

### 対話例

```
ようこそ! 対話を開始してください(終了するには 'exit' と入力してください)。

対話1回目
ユーザー: こんにちは、
選択されたエージェント: ChitChatAgent
AI エージェント (雑談): こんにちは! 今日はどんなことをお手伝いできますか?

対話2回目
ユーザー: AI エージェントについて学びたいと思っています。
選択されたエージェント: QuestionAgent
AI エージェント (質問): AI エージェントについて学びたいとのことですが、具体的にどのような情報をお探しですか? たとえば、ビジネス活用事例や導入ガイド、または講座のカリキュラムについて興味がありますか?

対話3回目
ユーザー: ビジネス活用事例が知りたいです。
選択されたエージェント: RecommendationAgent
AI エージェント (レコメンド): AI エージェントのビジネス活用事例に興味があるとのことですね。それなら、こちらのコンテンツがおすすめです:
- AI エージェントのビジネス活用事例と成功ストーリー: 業務効率化とアイデア創出の実践ガイド
URL: https://www.agent.advanced.book.example1.com
このガイドでは、AIエージェントを活用した具体的なビジネス事例や成功ストーリーを紹介しています。ぜひご覧ください!

対話4回目
ユーザー: ありがとうございます。講座についての情報がありますか。
選択されたエージェント: RecommendationAgent
AI エージェント (レコメンド): AI エージェントの講座について興味があるとのことですね。以下のコンテンツがおすすめです:
- AI エージェント講座のカリキュラム比較と受講者レビュー
URL: https://www.agent.advanced.book.example3.com
このコンテンツでは、さまざまな講座のカリキュラムを比較し、受講者のレビューを紹介しています。講座選びの参考にぜひご覧ください!
```

ユーザーからの問い合わせに対し、適切なエージェントが選択されて、ユーザーの興味を引き出しながらコンテンツをレコメンドできていることが確認できます。また、ユーザーとの対話履歴を蓄積して解析することで、顧客ニーズを把握することができるため、次のマーケティング施策に活用することが可能です。

## 7.5 まとめ

現代のマーケティングにおける課題を解決するために、AIエージェントを活用した2つのケースを紹介しました。

1. **ロールプレイングによる意思決定支援エージェント (7.3節)**: ペルソナを活用した評価とフィードバックにより、マーケティングチームの意思決定を支援します。

2. **パーソナライズ施策支援エージェント (7.4節)**: MACRSを参考にした会話型レコメンドシステムを実装し、プランナーエージェントが最適な応答を選択し、ユーザーの文脈をリアルタイムで反映します。

AIエージェントは、顧客体験の向上やマーケティング生産性の最大化を実現する強力なツールであり、今後のマーケティング戦略において重要な役割を果たすことが期待されます。

## 参考文献

*1 フィリップ・コトラー: コトラーのマーケティング 5.0 デジタル・テクノロジー時代の革新戦略,朝日新聞出版.2022, pp.23-39

*2 デジタルを活用したマーケティングにおける課題としては、「人材の不足」がもっとも票を集め、知識・ノウハウ不足に対する課題感が強いことが報告されている。Repro社 「デジタルマーケティング実態調査レポート 2024」・https://repro.io/books/digital-marketing-survey-2024/

*3 Salesforce「State of Marketing Report 2024」https://www.salesforce.com/resources/reports/state-of-marketing/

*4 Japan AI「AI活用実態調査2024」https://japan-ai.com/survey2024/

*5 Jiabao Fang: A Multi-Agent Conversational Recommender System. 2024. https://arxiv.org/pdf/2402.01135

*6 LangGraph Documentation: https://langchain-ai.github.io/langgraph/

*7 OpenAI API Documentation: https://platform.openai.com/docs

