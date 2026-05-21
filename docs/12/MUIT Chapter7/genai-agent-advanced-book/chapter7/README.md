# 現場で活用するためのAIエージェント実践入門 - 第7章

このディレクトリは、書籍「現場で活用するためのAIエージェント実践入門」（講談社）の第7章に関連するソースコードとリソースを含んでいます。

第7章では、**意思決定支援エージェント**と**パーソナライズ施策支援エージェント**の実装を通じて、マルチエージェントの構築方法を学習します。

7章記載のコードを実行するためには、以下の手順に従ってください。

## 前提条件

このプロジェクトを実行するには、以下の準備が必要です：

- Python 3.12 以上
- VSCode
- VSCodeのMulti-root Workspaces機能を使用し、ワークスペースとして開いている（やり方は[こちら](../README.md)を参照）
- OpenAIのアカウントとAPIキー

また、Python の依存関係は `pyproject.toml` に記載されています。

## 環境構築

### 1. chapter7のワークスペースを開く
chapter7 ディレクトリに仮想環境を作成します。
VSCode の ターミナルの追加で`chapter7` を選択します。

### 2. uvのインストール

依存関係の解決には`uv`を利用します。
`uv`を使ったことがない場合、以下の方法でインストールしてください。

`pip`を使う場合：
```bash
pip install uv
```

MacまたはLinuxの場合：
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Python 仮想環境の作成と依存関係のインストール

依存関係のインストール
```bash
uv sync
```

インストール後に作成した仮想環境をアクティブにします。

```bash
source .venv/bin/activate
```

### 4. 環境変数のセット
.env.exampleファイルをコピーし、以下の内容を追記した`.env` ファイルを作成してください。

OpenAI APIキーを持っていない場合は、[OpenAIの公式サイト](https://platform.openai.com/)から取得してください。

```bash

```env
# OpenAI API設定
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_BASE="https://api.openai.com/v1"
OPENAI_MODEL= "gpt-4o-2024-08-06"
```

## ディレクトリ構成

```
chapter7/
├── .env.sample                           # 環境変数のサンプルファイル
├── .python-version                       # Python バージョン指定
├── pyproject.toml                        # Python プロジェクト設定
├── uv.lock                              # 依存関係のロックファイル
├── notebooks/                           # Jupyter Notebook ファイル
│   ├── decision_support_agent_runner.ipynb  # 意思決定支援エージェントの実行例
│   └── macrs_runner.ipynb               # MACRS の実行例
└── src/                                 # ソースコード
    ├── custom_logger.py                 # カスタムロガー
    ├── decision_support_agent/          # 意思決定支援エージェント
    │   ├── agent.py                     # エージェントのメインロジック
    │   ├── configs.py                   # 設定ファイル
    │   ├── models.py                    # データモデル
    │   └── prompts.py                   # プロンプトテンプレート
    └── macrs/                           # MACRS（Multi-Agent Collaborative Review System）
        ├── agent.py                     # パーソナライズ施策支援エージェントのメインロジック
        ├── configs.py                   # 設定ファイル
        ├── custom_logger.py             # カスタムロガー
        ├── models.py                    # データモデル
        └── prompts.py                   # プロンプトテンプレート
```

## 使用方法

### 意思決定支援エージェント

1. `notebooks/decision_support_agent_runner.ipynb` を開きます。
2. セルを順番に実行して、意思決定支援エージェントの動作を確認します。

### MACRS（Multi-Agent Collaborative Review System）

1. `notebooks/macrs_runner.ipynb` を開きます。
2. セルを順番に実行して、パーソナライズ施策支援エージェントの動作を確認します。

## 主要な機能

### 意思決定支援エージェント
- ペルソナベースの多角的な意見生成
- 改善提案の自動生成
- LangGraphを使用した複雑なワークフロー管理

### MACRS
- 複数エージェントによる協調的なレビューシステム
- 非同期処理による効率的なレビュープロセス

## 注意事項

- OpenAI API キーが必要です。事前に取得してください。
- Python の仮想環境を有効にした状態で作業を行ってください。
- 詳細は書籍の該当章を参照してください。
