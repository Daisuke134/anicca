# naistQmd への貢献方法

このドキュメントでは、naistQmdテンプレートを論文プロジェクトで使用する方法と、テンプレートへの貢献方法を説明します。

## 目次

1. [論文プロジェクトでテンプレートを使用する](#論文プロジェクトでテンプレートを使用する)
2. [テンプレートを修正して貢献する](#テンプレートを修正して貢献する)
3. [プルリクエストの検証方法（メンテナー向け）](#プルリクエストの検証方法メンテナー向け)

---

## 論文プロジェクトでテンプレートを使用する

### サブモジュールとして追加

論文プロジェクトのディレクトリで、naistQmdをサブモジュールとして追加します：

```bash
# 論文プロジェクトのディレクトリに移動
cd /path/to/thesis-project

# naistQmdをサブモジュールとして追加
git submodule add https://github.com/HOgishima/naistQmd.git naistQmd

# コミット
git commit -m "Add naistQmd as submodule"
```

### 既存のプロジェクトをクローンする場合

論文プロジェクトをクローンする際は、サブモジュールも一緒に取得する必要があります：

```bash
# サブモジュールを含めてクローン
git clone --recursive <thesis-projectのURL>

# または、クローン後にサブモジュールを初期化
git clone <thesis-projectのURL>
cd thesis-project
git submodule update --init --recursive
```

### テンプレートの更新を取得する

naistQmdが更新された場合、論文プロジェクトで最新版を取得できます：

```bash
cd thesis-project
git submodule update --remote naistQmd
git commit -m "Update naistQmd to latest version"
```

### 論文プロジェクトでの使用方法

サブモジュールとして追加した後、`naistQmd/paper.qmd`を参考に、論文プロジェクトのルートに`paper.qmd`を作成してください。

```bash
# 論文プロジェクトのルートに移動
cd /path/to/thesis-project

# paper.qmdを作成（naistQmdの例を参考に）
cp naistQmd/paper.qmd paper.qmd

# 必要に応じて編集
# ...
```

---

## テンプレートを修正して貢献する

### 1. リポジトリをフォークする

GitHubでnaistQmdリポジトリをフォークします。

### 2. ローカルにクローンする

```bash
# 自分のフォークをクローン
git clone https://github.com/your-username/naistQmd.git
cd naistQmd

# 元のリポジトリをupstreamとして追加
git remote add upstream https://github.com/HOgishima/naistQmd.git

# リモートを確認
git remote -v
```

### 3. 新しいブランチを作成する

```bash
# mainブランチを最新の状態に更新
git checkout main
git pull upstream main

# 新しいブランチを作成（機能名や修正内容をブランチ名に含める）
git checkout -b fix/description-of-fix
# または
git checkout -b feature/new-feature-name
```

ブランチ名の例：
- `fix/header-tex-issue`
- `feature/add-new-template-option`
- `docs/update-readme`

### 4. 変更を加える

テンプレートを修正します：

```bash
# ファイルを編集
# ...

# 変更を確認
git status
git diff
```

### 5. 変更をコミットする

```bash
# 変更をステージング
git add .

# コミット（明確なメッセージを書く）
git commit -m "Fix: 修正内容の説明

詳細な説明があればここに書く
- 変更点1
- 変更点2"
```

コミットメッセージのベストプラクティス：
- 最初の行は簡潔に（50文字以内推奨）
- 必要に応じて詳細を追加
- 変更の理由を説明

### 6. ブランチをプッシュする

```bash
# 自分のフォークにプッシュ
git push origin fix/description-of-fix
```

### 7. プルリクエストを作成する

1. GitHubで自分のフォークのページに移動
2. 「Compare & pull request」ボタンをクリック
3. プルリクエストのタイトルと説明を記入：
   - **タイトル**: 変更内容を簡潔に
   - **説明**: 
     - 変更の目的
     - 変更内容の詳細
     - テスト方法（可能であれば）
     - 関連するIssue番号（あれば）

### 8. プルリクエスト後の対応

メンテナーからのフィードバックに応じて、必要に応じて修正を追加：

```bash
# 追加の変更を加える
# ...

# コミット
git add .
git commit -m "Update: フィードバックに基づく修正"

# プッシュ（同じブランチにプッシュすると、PRが自動更新される）
git push origin fix/description-of-fix
```

### 9. upstreamの変更を取り込む（必要に応じて）

プルリクエストのレビュー中に、upstream（元のリポジトリ）が更新された場合：

```bash
# mainブランチに切り替え
git checkout main

# upstreamから最新の変更を取得
git pull upstream main

# 作業ブランチに戻る
git checkout fix/description-of-fix

# mainの変更をマージ
git merge main

# または、リベース（履歴をきれいに保つ）
git rebase main

# コンフリクトがあれば解決してから
git push origin fix/description-of-fix --force-with-lease
```

---

## プルリクエストの検証方法（メンテナー向け）

### 1. プルリクエストをローカルで確認する

```bash
# リポジトリをクローン（まだの場合）
git clone https://github.com/HOgishima/naistQmd.git
cd naistQmd

# プルリクエストのブランチを取得
git fetch origin pull/<PR番号>/head:pr-<PR番号>
# 例: git fetch origin pull/1/head:pr-1

# ブランチをチェックアウト
git checkout pr-<PR番号>
```

または、GitHub CLIを使用：

```bash
# GitHub CLIでプルリクエストをチェックアウト
gh pr checkout <PR番号>
```

### 2. 変更内容を確認する

```bash
# 変更されたファイルを確認
git diff main...pr-<PR番号>

# 変更の統計を確認
git diff --stat main...pr-<PR番号>

# コミット履歴を確認
git log main..pr-<PR番号>
```

### 3. 実際にテストする

#### 基本的なテスト

```bash
# テンプレートが正しく動作するか確認
cd /path/to/test-project

# サブモジュールを更新（または新規追加）
git submodule update --remote naistQmd
# または
cd naistQmd
git checkout pr-<PR番号>
cd ..

# Quartoでレンダリングを試す
quarto render paper.qmd
```

#### 自動テスト（可能であれば）

```bash
# スクリプトでテストを実行（もしあれば）
./scripts/test.sh
```

### 4. チェックリスト

プルリクエストをレビューする際のチェックリスト：

- [ ] 変更内容が明確に説明されている
- [ ] コードの変更が適切である
- [ ] 既存の機能を壊していない
- [ ] ドキュメントが更新されている（必要に応じて）
- [ ] コミットメッセージが適切である
- [ ] テストが成功する
- [ ] スタイルガイドに準拠している

### 5. フィードバックを提供する

GitHubのプルリクエストページで：
- コメントを追加
- 変更をリクエスト
- 承認

### 6. マージする

問題がなければ、GitHubのプルリクエストページで「Merge pull request」をクリック。

マージ後：

```bash
# ローカルのmainブランチを更新
git checkout main
git pull origin main

# 不要になったブランチを削除
git branch -d pr-<PR番号>
```

### 7. リリースノートを更新（必要に応じて）

大きな変更の場合は、CHANGELOG.mdやリリースノートを更新。

---

## トラブルシューティング

### サブモジュールの更新が反映されない

```bash
# サブモジュールの状態を確認
git submodule status

# 強制的に更新
git submodule update --remote --force naistQmd
```

### プルリクエストのコンフリクト

```bash
# コンフリクトを解決
git checkout pr-<PR番号>
git merge main
# コンフリクトを解決後
git push origin pr-<PR番号>
```

### テスト環境のセットアップ

新しい環境でテストする場合：

```bash
# クリーンな環境でテスト
cd /tmp
git clone https://github.com/HOgishima/naistQmd.git test-naistqmd
cd test-naistqmd
git checkout pr-<PR番号>
# テストを実行
```

---

## 質問やサポート

問題が発生した場合や質問がある場合は、GitHubのIssuesで報告してください。

