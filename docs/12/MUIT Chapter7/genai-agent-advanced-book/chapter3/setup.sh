#!/bin/bash

# 現在のディレクトリを確認
echo "作業ディレクトリ: $(pwd)"

# uvがインストールされているか確認
if ! command -v uv &> /dev/null; then
    echo "uvをインストールしています..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # PATHに追加するための提案
    echo "uvがインストールされました。必要に応じて以下のコマンドを実行してPATHに追加してください："
    echo 'export PATH="$HOME/.cargo/bin:$PATH"'
    # 直接PATHに追加
    export PATH="$HOME/.cargo/bin:$PATH"
else
    echo "uvは既にインストールされています: $(which uv)"
fi

# 仮想環境の作成と依存関係のインストール
echo "Python 3.12の仮想環境を作成し、依存関係をインストールしています..."
uv sync

# Jupyter用カーネルを設定 (Python 3.12環境)
echo "Jupyterカーネルを登録しています..."
uv run python -m ipykernel install --user --name genai_ch3 --display-name "Python 3.12 (Chapter 3)"

# 環境変数ファイルの作成（すでに存在する場合はスキップ）
if [ ! -f .env ]; then
    echo "環境変数ファイル(.env)を.env.exampleから作成しています..."
    cp .env.example .env
    echo "※ .envファイルに適切なAPIキーを設定してください"
fi

echo "環境構築が完了しました！"
echo "以下のコマンドで仮想環境をアクティベートできます：source .venv/bin/activate"
echo "または uv run を使用してコマンドを実行できます：uv run python your_script.py"
echo "以下のコマンドでJupyter Notebookを起動できます：uv run jupyter notebook"
