# AIエージェント実践入門 第3章

本プロジェクトは「AIエージェント実践入門」第3章のサンプルコードを実行するための環境です。

## 前提条件

このプロジェクトを実行するには、以下の準備が必要です：

- Python 3.12 以上
- Docker および Docker Compose
- VSCode
- VSCodeのMulti-root Workspaces機能を使用し、ワークスペースとして開いている（やり方は[こちら](../README.md)を参照）
- OpenAIのアカウントとAPIキー
- TAVILYのアカウントとAPIキー

また、Python の依存関係は `pyproject.toml` に記載されています。

## 環境構築

### 1. chapter3のワークスペースを開く
chapter3 ディレクトリに仮想環境を作成します。
VSCode の ターミナルの追加で`chapter3` を選択します。

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

```bash

```env
# OpenAI API設定
# OpenAI APIキーを持っていない場合は、[OpenAIの公式サイト](https://platform.openai.com/)から取得してください。
OPENAI_API_KEY=your_openai_api_key

# Tavily API設定（WEB検索用）
# https://tavily.com でアカウントを作成してAPIキーを取得してください
TAVILY_API_KEY=your_tavily_api_key
```