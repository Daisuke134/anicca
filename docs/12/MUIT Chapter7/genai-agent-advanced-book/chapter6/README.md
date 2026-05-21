# 現場で活用するためのAIエージェント実践入門 - Chapter 6

このディレクトリは、書籍「現場で活用するためのAIエージェント実践入門」（講談社）の第6章に関連するソースコードとリソースを含んでいます。

## 前提条件

このプロジェクトを実行するには、以下の準備が必要です：

- Python 3.11 以上
- OpenAI APIキー
- Anthropic APIキー
- Cohere APIキー
- Jina Reader APIキー
- LangSmith APIキー（オプション）
- VSCode

また、Python の依存関係は `pyproject.toml` に記載されています。

## VS Code ワークスペースで開く

VS Code を起動し、プロジェクトのルートディレクトリ（`genai-agent-advanced-book`）をワークスペースとして開きます。その後、ターミナルの追加で`chapter6`を選択することで、この章のコードを効率的に編集・実行できるようになります。

## 環境構築

### Python 仮想環境の作成と依存関係のインストール

依存関係の解決には`uv`を利用します。 `uv`のインストールは以下のとおりです。

**pipを使う場合：**

```bash
pip install uv
```

**MacまたはLinuxの場合：**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 依存関係のインストール

```bash
uv sync
```

### 環境変数の設定

`.env.sample` ファイルを `.env` にコピーして、必要な環境変数を設定します：

```
$ cp .env.sample .env
```

`.env` ファイルで以下の項目を設定してください：

- `OPENAI_API_KEY`: OpenAI API キー
- `ANTHROPIC_API_KEY`: Anthropic API キー
- `COHERE_API_KEY`: Cohere API キー
- `JINA_API_KEY`: Jina Reader API キー

次の項目はオプションです。LangGraph StudioとLangSmithとの連携を確認してみたいときに設定してください。

- `LANGSMITH_API_KEY`: LangSmith APIキー

## ディレクトリ構成

```
chapter6/
├── .env.sample                        # 環境変数のサンプルファイル
├── pyproject.toml                     # Python プロジェクト設定
├── uv.lock                            # 依存関係のロックファイル
├── langgraph.json                     # LangGraph設定ファイル
├── README.md                          # このファイル
├── arxiv_researcher/                  # arXiv論文リサーチャーのメインパッケージ
│   ├── __init__.py
│   ├── agent/                         # エージェント実装
│   │   ├── __init__.py
│   │   ├── paper_analyzer_agent.py    # 論文分析エージェント
│   │   ├── paper_search_agent.py      # 論文検索エージェント
│   │   └── research_agent.py          # リサーチエージェント（メイン）
│   ├── chains/                        # LangChainチェーン実装
│   │   ├── goal_optimizer_chain.py    # ゴール最適化チェーン
│   │   ├── hearing_chain.py           # ヒアリングチェーン
│   │   ├── paper_processor_chain.py   # 論文処理チェーン
│   │   ├── prompts/                   # プロンプトテンプレート
│   │   │   ├── check_sufficiency.prompt
│   │   │   ├── goal_optimizer_conversation.prompt
│   │   │   ├── goal_optimizer_search.prompt
│   │   │   ├── hearing.prompt
│   │   │   ├── query_decomposer.prompt
│   │   │   ├── reporter_system.prompt
│   │   │   ├── reporter_user.prompt
│   │   │   ├── set_section.prompt
│   │   │   ├── summarize.prompt
│   │   │   └── task_evaluator.prompt
│   │   ├── query_decomposer_chain.py  # クエリ分解チェーン
│   │   ├── reading_chains.py          # 論文読解チェーン
│   │   ├── reporter_chain.py          # レポート生成チェーン
│   │   ├── task_evaluator_chain.py    # タスク評価チェーン
│   │   └── utils.py                   # ユーティリティ関数
│   ├── logger.py                      # ロガー設定
│   ├── models/                        # データモデル
│   │   ├── __init__.py
│   │   ├── arxiv.py                   # arXiv関連モデル
│   │   ├── markdown.py                # Markdown関連モデル
│   │   └── reading.py                 # 読解関連モデル
│   ├── searcher/                      # 検索機能
│   │   ├── arxiv_searcher.py          # arXiv検索実装
│   │   └── searcher.py                # 検索インターフェース
│   ├── service/                       # サービス層
│   │   ├── markdown_parser.py         # Markdownパーサー
│   │   ├── markdown_storage.py        # Markdownストレージ
│   │   └── pdf_to_markdown.py         # PDF→Markdown変換
│   └── settings.py                    # 設定ファイル
├── fixtures/                          # テスト用データ
│   ├── 2408.14317.md                  # サンプル論文（Markdown形式）
│   ├── sample_context.txt             # サンプルコンテキスト
│   └── sample_goal.txt                # サンプルゴール
├── logs/                              # ログファイル保存先
│   └── application.log
└── storage/                           # ストレージ
    └── markdown/                      # 論文のMarkdownファイル保存先
        └── *.md                       # 処理済み論文ファイル
```

## 使用方法

### LangGraph Studioでの実行

LangGraph Studioを使用してエージェントを実行する場合：

```
$ uv run langgraph dev --no-reload
```

LangGraph Studioが起動したら、ブラウザより `http://localhost:8123` にアクセスします（自動的に開きます）。ブラウザ上のUIからリサーチゴールを入力し、エージェントを実行すると、エージェントの逐次的な動きをブラウザ上で確認することができます。

### 主要な機能

#### arXiv論文リサーチャー

このエージェントは、arXivから関連論文を検索し、PDFファイルをMarkdown形式に変換して構造化された分析を行います。ヒアリング機能でユーザーの研究目的を対話的に明確化し、収集した情報を統合してレポートを生成します。

### 補足：サブグラフのコマンドライン上での動作確認方法

各サブグラフを個別にテストして、動作を確認できます。

#### 1. PaperAnalyzerAgent（論文分析エージェント）の動作確認

単一の論文に対する詳細な分析機能を確認するためのテストです。このエージェントは論文の構造を解析し、各セクションの要約を生成するとともに、重要なポイントを抽出します。

```
$ uv run python -m arxiv_researcher.agent.paper_analyzer_agent fixtures/2408.14317.md
```

実行すると、論文のタイトル、著者、要約が表示され、Introduction、Methodology、Results等の各セクションが要約されます。さらに、主要な発見事項と貢献が箇条書きで整理され、論文の強みと限界についての分析結果も出力されます。

#### 2. PaperSearchAgent（論文検索エージェント）の動作確認

arXivからの論文検索機能を確認するためのテストです。このエージェントは検索クエリに基づいて関連論文を取得し、基本的なメタデータを抽出します。

```
$ uv run python -m arxiv_researcher.agent.paper_search_agent
```

実行すると、デフォルトの検索クエリ（例：「LLM agent」）により論文が検索され、複数の論文情報が表示されます。各論文について、タイトル、著者、発表日、arXiv IDといった基本情報とともに、論文の要約（abstract）も確認できます。

## 動作確認で使用している論文

動作確認で使用している論文は以下の通りです：

```bibtex
@article{dmonte2024claim,
  title={Claim Verification in the Age of Large Language Models: A Survey},
  author={Dmonte, Alphaeus and Oruche, Roland and Zampieri, Marcos and Calyam, Prasad and Augenstein, Isabelle},
  journal={arXiv preprint arXiv:2408.14317},
  year={2024}
}
```

## APIキーの取得方法

### OpenAI APIキーの取得方法

[platform.openai.com](https://platform.openai.com)にアクセスしてアカウントを作成します。サインアップ後、確認メールに記載されたリンクをクリックしてメールアドレスを認証します。

ログイン後、右上の「Start building」ボタンをクリックして組織（Organization）を作成します。組織名とロールを入力し、「Create organization」をクリックします。4ステップの手順に従って初期設定を完了すると、最初のAPIキーが生成されます。

生成されたAPIキーをコピーして安全に保管してください。その後、APIを使用するには支払い方法の設定とクレジットの購入が必要です。「Purchase credits」ボタンから必要なクレジットを購入します。Dashboard > API keysから生成済みのキーにアクセスできます。

### Anthropic APIキーの取得方法

[console.anthropic.com](https://console.anthropic.com)でアカウントを作成してください。

Anthropic APIは前払い制の「使用クレジット」システムを採用しています。クレジットカード情報を入力し、初期クレジットを購入します（最低$10から）。残高が一定額を下回った際に自動的にクレジットを追加する自動リロード機能を設定することも可能です。

アカウントダッシュボードの「Settings」タブに移動し、左側メニューから「API keys」をクリックします。「Create Key」ボタンをクリックし、キーに識別しやすい名前を付けて「Create Key」で作成を完了させます。生成されたキーは安全な場所にコピーしてください。ポップアップを閉じると再表示できません。

### Cohere APIキーの取得方法

[dashboard.cohere.com/welcome/register](https://dashboard.cohere.com/welcome/register)でアカウントを作成します。メールアドレスとパスワードを設定して登録を完了します。

アカウント作成時、トライアルAPIキーが自動的に生成されます。ログイン後、[dashboard.cohere.com/api-keys](https://dashboard.cohere.com/api-keys)にアクセスしてAPIキーを確認できます。

トライアルキーは無料で使用できますが、レート制限があり、商用利用は許可されていません。月間上限は1,000コールです。プロダクションキーが必要な場合は、Billing and Usageページの「Get Your Production key」ボタンからGo to Productionワークフローを完了します。

生成されたキーは一度しか表示されません。コピーして安全に保管してください。プロダクションキーは従量課金制です。

### Jina Reader APIキーの取得方法

Jina Reader APIはAPIキーなしで無料利用できます。URLの前に`https://r.jina.ai/`を付けるだけで使用開始できます。ただし、APIキーなしの場合は毎分20リクエストに制限されます。

[jina.ai/api-dashboard/](https://jina.ai/api-dashboard/)でアカウントを作成すると、自動的にAPIキーが生成されます。新規ユーザーには1,000万トークンの無料トライアルが提供されます。APIキーを使用すると、毎分200リクエストまで利用可能になります。

同一のAPIキーでJina AIの全サービス（Reader、Embeddings、Reranker等）を利用でき、トークンは全サービス間で共有されます。使用状況は「API Key & Billing」タブで確認できます。

### LangSmith APIキーの取得方法

[smith.langchain.com](https://smith.langchain.com)でアカウントを作成します。Google、GitHub、メールでのログインに対応しています。

ログイン後、Settingsページに移動し、API Keysセクションまでスクロールします。Service Keys（バックエンドサービス向け）またはPersonal Access Tokens（個人プロジェクト向け）のいずれかを選択できます。

「Create API Key」をクリックし、キーのタイプを選択します。有効期限を設定し（日数指定または無期限）、キーを生成します。生成されたキーをコピーして保存してください。

APIキーはワークスペースごとに作成する必要があります。2025年7月現在、古い「ls__」プレフィックスのキーは無効化されており、新しい「lsv2」プレフィックスのキーを使用する必要があります。
