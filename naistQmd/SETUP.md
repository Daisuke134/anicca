# naistQmd 環境構築ガイド

このドキュメントでは、naistQmdテンプレートを使用するための環境構築手順を説明します。

## 必要な環境

以下のツールが必要です：

1. **Quarto** (>=1.2.0) - ドキュメント生成ツール
2. **LaTeX環境** - PDF生成用
   - XeLaTeXエンジン
   - biber（参考文献処理用）
   - 日本語フォント対応
3. **Python 3** - YAML変数展開スクリプト用

## インストール手順

### 1. Python 3の確認

Python 3は既にインストールされていることを確認してください：

```bash
python3 --version
# Python 3.13.3 などが表示されればOK
```

### 2. Quartoのインストール

#### 方法A: Homebrewを使用（推奨）

```bash
brew install --cask quarto
```

**注意**: sudoパスワードが必要な場合があります。ターミナルで直接実行してください。

#### 方法B: 公式サイトからダウンロード

1. https://quarto.org/docs/get-started/ にアクセス
2. macOS用のインストーラー（.pkg）をダウンロード
3. ダウンロードしたファイルをダブルクリックしてインストール

#### インストール確認

```bash
quarto --version
# quarto 1.8.26 などが表示されればOK
```

### 3. LaTeX環境のインストール

#### 方法A: MacTeX（フル版、推奨）

完全なLaTeX環境をインストールします（約4GB）：

```bash
brew install --cask mactex
```

**注意**: ダウンロードとインストールに時間がかかります（30分〜1時間程度）。

#### 方法B: BasicTeX（軽量版）

最小限のLaTeX環境をインストールします（約100MB）：

```bash
brew install --cask basictex
```

BasicTeXを使用する場合、追加パッケージのインストールが必要です：

```bash
# tlmgr（TeX Live Manager）を使用してパッケージをインストール
sudo tlmgr update --self
sudo tlmgr install \
  collection-langjapanese \
  biblatex \
  biber \
  bxjscls \
  luatexja \
  zxjatype \
  zxjafont
```

#### インストール確認

```bash
xelatex --version
# XeTeX 3.141592653 ... などが表示されればOK

biber --version
# biber version: 2.21 ... などが表示されればOK
```

### 4. 日本語フォントの確認

日本語フォントがインストールされていることを確認してください。macOSには標準で以下のフォントが含まれています：

- Hiragino Mincho ProN
- Hiragino Sans
- Noto Serif CJK JP（macOS 10.13以降）

必要に応じて、以下のフォントをインストールすることもできます：

```bash
# HomebrewでNotoフォントをインストール
brew install --cask font-noto-serif-cjk
```

## 動作確認

### 1. テンプレートの確認

リポジトリがクローンされていることを確認：

```bash
cd /Users/cbns03/Downloads/anicca-project/naistQmd
ls -la paper.qmd
```

### 2. サンプルPDFの生成

```bash
quarto render paper.qmd
```

このコマンドを実行すると、以下の処理が自動的に行われます：

1. Quartoが`paper.qmd`を`paper.tex`に変換
2. `post-render.sh`が自動実行され、YAML変数を展開
3. XeLaTeXでPDFを生成（3回実行 + biber 1回）

生成されたPDFは`paper.pdf`として保存されます。

### 3. エラーの確認

PDFが生成されない場合、以下のログファイルを確認してください：

- `paper-xelatex-1.log` - 1回目のXeLaTeX実行ログ
- `paper-xelatex-2.log` - 2回目のXeLaTeX実行ログ
- `paper-xelatex-3.log` - 3回目のXeLaTeX実行ログ
- `paper-biber.log` - biber実行ログ
- `/tmp/quarto-post-render-*.log` - post-render.shの実行ログ

## トラブルシューティング

### Quartoが見つからない

```bash
# PATHに追加（必要に応じて）
export PATH="/Applications/quarto/bin:$PATH"
```

### XeLaTeXが見つからない

```bash
# MacTeXの場合
export PATH="/usr/local/texlive/2024/bin/universal-darwin:$PATH"

# BasicTeXの場合
export PATH="/Library/TeX/texbin:$PATH"
```

上記のパスを`~/.zshrc`または`~/.bash_profile`に追加してください。

### biberが見つからない

```bash
# BasicTeXを使用している場合、biberをインストール
sudo tlmgr install biber
```

### 日本語が表示されない

日本語フォントが正しく設定されているか確認：

```bash
fc-list | grep -i "noto\|hiragino"
```

## 次のステップ

環境構築が完了したら、`paper.qmd`を編集して論文を作成してください。

詳細な使用方法は`README.md`を参照してください。










