# naistQmdをproject_xxに同期する方法

このガイドでは、`naistQmd`テンプレートの内容を`project_xx`に移行し、更新を反映させる方法を説明します。

## 方法1: Git Subtree（推奨）

### 初回セットアップ

```bash
# project_xxのディレクトリに移動
cd /path/to/project_xx

# naistQmdをリモートとして追加（オプション、後で更新しやすくするため）
git remote add naistqmd https://github.com/HOgishima/naistQmd.git

# naistQmdの内容をサブディレクトリとして追加
git subtree add --prefix=naistQmd naistqmd main --squash

# コミットしてプッシュ
git commit -m "Add naistQmd template"
git push
```

### 更新を反映する

```bash
# project_xxのディレクトリで
cd /path/to/project_xx

# naistQmdの最新の変更を取得
git subtree pull --prefix=naistQmd naistqmd main --squash

# コミットしてプッシュ
git commit -m "Update naistQmd template"
git push
```

### ルートに直接展開する場合

もし`naistQmd`の内容を`project_xx`のルートに直接展開したい場合：

```bash
# project_xxのディレクトリで
cd /path/to/project_xx

# 一時的にnaistQmdをクローン
git clone https://github.com/HOgishima/naistQmd.git temp_naistqmd

# 必要なファイルをコピー（.gitディレクトリは除外）
rsync -av --exclude='.git' temp_naistqmd/ .

# クリーンアップ
rm -rf temp_naistqmd

# コミット
git add .
git commit -m "Add naistQmd template files"
git push
```

ただし、この方法では更新の反映が手動になります。

## 方法2: 手動コピー + スクリプト

更新を自動化するスクリプトを作成：

```bash
#!/bin/bash
# sync_naistqmd.sh

cd /path/to/project_xx

# naistQmdを一時的にクローン
git clone https://github.com/HOgishima/naistQmd.git temp_naistqmd

# ファイルをコピー（.gitと_outputは除外）
rsync -av --exclude='.git' --exclude='_output' temp_naistqmd/ .

# クリーンアップ
rm -rf temp_naistqmd

# 変更をコミット
git add .
git commit -m "Sync naistQmd template $(date +%Y-%m-%d)"
git push
```

## 方法3: GitHub Actionsで自動同期

`project_xx`レポジトリに`.github/workflows/sync-naistqmd.yml`を作成：

```yaml
name: Sync naistQmd

on:
  schedule:
    - cron: '0 2 * * *'  # 毎日午前2時
  workflow_dispatch:  # 手動実行も可能

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Setup Git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
      
      - name: Pull naistQmd updates
        run: |
          git subtree pull --prefix=naistQmd https://github.com/HOgishima/naistQmd.git main --squash -m "Auto-sync: Update naistQmd template"
      
      - name: Push changes
        run: |
          git push origin main
```

## 推奨事項

- **Git Subtree**を使用することを推奨します
  - 履歴が保持される
  - 更新が簡単
  - コンフリクトの解決が容易

- 定期的な更新を忘れないように、カレンダーリマインダーを設定するか、GitHub Actionsで自動化する

## トラブルシューティング

### 同期先に既に同じフォルダがある場合

同期先（`project_xx`）に既に`naistQmd`フォルダや同名のファイルが存在する場合の動作：

#### 方法1: Git Subtreeの場合

- **初回セットアップ時（`git subtree add`）**:
  - 既に`naistQmd`フォルダが存在する場合、エラーが発生します
  - 対処法：

    ```bash
    # 既存のフォルダをバックアップして削除
    mv naistQmd naistQmd_backup
    git subtree add --prefix=naistQmd naistqmd main --squash
    # 必要に応じてバックアップからファイルを復元
    ```

- **更新時（`git subtree pull`）**:
  - 既存のフォルダがある場合、マージが試みられます
  - コンフリクトが発生する可能性があります（後述の「コンフリクトが発生した場合」を参照）

#### 方法2: rsyncの場合

- `rsync -av`は既存のファイルを**上書き**します
- 既存のフォルダがある場合、その中身が上書きされる可能性があります
- **注意**: 既存のファイルが失われる可能性があるため、事前にバックアップを取ることを推奨します

  ```bash
  # バックアップを取ってから同期
  cp -r naistQmd naistQmd_backup_$(date +%Y%m%d)
  # その後、rsyncを実行
  ```

#### 方法3: GitHub Actionsの場合

- `git subtree pull`を使用しているため、方法1と同じ動作になります
- コンフリクトが発生した場合、ワークフローが失敗します

### コンフリクトが発生した場合

```bash
# コンフリクトを解決
git subtree pull --prefix=naistQmd naistqmd main --squash

# コンフリクトファイルを編集して解決
# ...

# 解決後
git add .
git commit -m "Resolve conflicts and update naistQmd"
```

### サブディレクトリではなくルートに展開したい場合

初回セットアップ時に`--prefix`を指定せずに、手動でファイルをコピーする方法を使用してください。
