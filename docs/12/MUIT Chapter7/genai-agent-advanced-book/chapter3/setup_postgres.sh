#!/bin/bash

# PostgreSQLセットアップスクリプト
# このスクリプトはDocker Composeを使用してPostgreSQLデータベースをセットアップします

set -e  # エラーが発生したら停止

# 色付きの出力用の関数
print_info() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

print_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

print_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

# スクリプトの実行ディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

print_info "PostgreSQLセットアップを開始します..."

# Dockerがインストールされているかチェック
if ! command -v docker &> /dev/null; then
    print_error "Dockerがインストールされていません。"
    print_info "以下のコマンドでDockerをインストールしてください:"
    print_info "  Ubuntu/Debian: sudo apt update && sudo apt install docker.io docker-compose"
    print_info "  macOS: brew install docker docker-compose"
    exit 1
fi

# Docker Composeがインストールされているかチェック
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Composeがインストールされていません。"
    print_info "以下のコマンドでDocker Composeをインストールしてください:"
    print_info "  Ubuntu/Debian: sudo apt install docker-compose"
    print_info "  macOS: brew install docker-compose"
    exit 1
fi

# 必要なファイルの存在チェック
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.ymlファイルが見つかりません。"
    exit 1
fi

if [ ! -f "init.sql" ]; then
    print_error "init.sqlファイルが見つかりません。"
    exit 1
fi

print_success "必要なファイルが確認されました。"

# 既存のコンテナを停止・削除
print_info "既存のPostgreSQLコンテナを停止・削除しています..."
docker-compose down -v 2>/dev/null || true

# 5432ポートを使用している他のPostgreSQLプロセスを確認
print_info "ポート5432の使用状況を確認しています..."
if netstat -tlnp 2>/dev/null | grep -q :5432; then
    print_warning "ポート5432が使用されています。競合する可能性があります。"
    print_info "他のPostgreSQLサービスを停止してください:"
    print_info "  システムサービス: sudo service postgresql stop"
    print_info "  または: sudo systemctl stop postgresql"
    
    # ユーザーに確認
    read -p "続行しますか？ (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "セットアップを中止しました。"
        exit 1
    fi
fi

# PostgreSQLコンテナを起動
print_info "PostgreSQLコンテナを起動しています..."
docker-compose up -d

# コンテナの起動を待機
print_info "PostgreSQLの起動を待機しています..."
sleep 5

# 最大30秒待機
TIMEOUT=30
COUNTER=0
while [ $COUNTER -lt $TIMEOUT ]; do
    if docker exec postgres-genai-ch3 pg_isready -U testuser -d testdb &>/dev/null; then
        print_success "PostgreSQLが正常に起動しました！"
        break
    fi
    
    print_info "PostgreSQLの起動を待機中... ($COUNTER/$TIMEOUT秒)"
    sleep 1
    COUNTER=$((COUNTER + 1))
done

if [ $COUNTER -eq $TIMEOUT ]; then
    print_error "PostgreSQLの起動に失敗しました。"
    print_info "以下のコマンドでログを確認してください:"
    print_info "  docker-compose logs postgres"
    exit 1
fi

# データベースの初期化確認
print_info "データベースの初期化を確認しています..."
if docker exec postgres-genai-ch3 psql -U testuser -d testdb -c "SELECT COUNT(*) FROM employees;" &>/dev/null; then
    employee_count=$(docker exec postgres-genai-ch3 psql -U testuser -d testdb -t -c "SELECT COUNT(*) FROM employees;" | xargs)
    print_success "employeesテーブルが正常に作成されました。レコード数: $employee_count"
else
    print_error "データベースの初期化に失敗しました。"
    exit 1
fi

# 接続テスト
print_info "データベース接続テストを実行しています..."
if docker exec postgres-genai-ch3 psql -U testuser -d testdb -c "SELECT version();" &>/dev/null; then
    print_success "データベース接続テストが成功しました！"
else
    print_error "データベース接続テストに失敗しました。"
    exit 1
fi

# セットアップ完了メッセージ
print_success "PostgreSQLセットアップが完了しました！"
echo
print_info "=== セットアップ情報 ==="
print_info "コンテナ名: postgres-genai-ch3"
print_info "データベース: testdb"
print_info "ユーザー: testuser"
print_info "パスワード: testpass"
print_info "ポート: 5432"
print_info "ホスト: localhost"
echo

print_info "=== 利用可能なコマンド ==="
print_info "データベースに接続:"
print_info "  docker exec -it postgres-genai-ch3 psql -U testuser -d testdb"
echo
print_info "employeesテーブルの確認:"
print_info "  docker exec postgres-genai-ch3 psql -U testuser -d testdb -c \"SELECT * FROM employees;\""
echo
print_info "コンテナの停止:"
print_info "  docker-compose down"
echo
print_info "コンテナの再起動:"
print_info "  docker-compose up -d"
echo

print_info "=== Jupyter Notebookでの使用方法 ==="
print_info "1. .envファイルにOpenAI API Keyを設定してください"
print_info "2. notebooks/examples.ipynbを開いてください"
print_info "3. SQLDatabaseChainの使用例セクションを実行してください"
echo

print_success "セットアップが完了しました。"