# naistQmd 環境構築手順書

**Apple Silicon Macでの動作確認済み**

この手順書では、naistQmdテンプレートをエラーなくスムーズに使用できるよう、実際のインストール経験に基づいた詳細な手順を説明します。

---

## 目次

1. [前提条件](#前提条件)
2. [インストール手順](#インストール手順)
3. [動作確認](#動作確認)
4. [トラブルシューティング](#トラブルシューティング)
5. [よくある質問（FAQ）](#よくある質問faq)

---

## 前提条件

### 必要な環境

- **macOS** (Apple Silicon推奨)
- **Homebrew** がインストールされていること
- **インターネット接続**

### 事前確認

以下のコマンドで、既にインストール済みのツールを確認できます：

```bash
# Python 3の確認
python3 --version

# Quartoの確認
quarto --version

# LaTeX環境の確認
xelatex --version
```

**注意**: これらのコマンドでエラーが出ても問題ありません。これからインストールします。

---

## インストール手順

### ステップ1: リポジトリのクローン

```bash
git clone https://github.com/HOgishima/naistQmd.git
cd naistQmd
```

**確認**: `paper.qmd`ファイルが存在することを確認してください。

```bash
ls -la paper.qmd
```

---

### ステップ2: Python 3の確認

Python 3は通常macOSに標準でインストールされています。確認してください：

```bash
python3 --version
```

**出力例**: `Python 3.13.3` などが表示されればOKです。

**もしPython 3がインストールされていない場合**:

```bash
# Homebrewでインストール
brew install python3
```

---

### ステップ3: Quartoのインストール

#### 方法A: Homebrewを使用（推奨）

```bash
brew install --cask quarto
```

**注意**: sudoパスワードの入力が求められる場合があります。ターミナルで直接実行してください。

#### 方法B: 公式サイトからダウンロード

1. https://quarto.org/docs/get-started/ にアクセス
2. macOS用のインストーラー（.pkg）をダウンロード
3. ダウンロードしたファイルをダブルクリックしてインストール

#### インストール確認

```bash
quarto --version
```

**出力例**: `1.8.26` などが表示されればOKです。

---

### ステップ4: LaTeX環境のインストール（重要）

**重要**: naistQmdテンプレートは**TeX Live 2025**が必要です。Quarto経由でTinyTeXをインストールする方法が最も簡単で確実です。

```bash
quarto install tinytex
```

このコマンドを実行すると：

1. TinyTeX v2025.12が自動的にダウンロードされます（約250MB）
2. 必要なLaTeXパッケージが自動的にインストールされます
3. インストールには5-10分程度かかります

**インストール完了の確認**:

```bash
quarto check
```

出力に以下が表示されればOKです：

```
TinyTeX: v2025.12
[✓] Checking LaTeX....................OK
Using: TinyTex
```

**注意**: `quarto install tinytex`を実行すると、Quartoが自動的に必要なLaTeXパッケージ（`bxjscls`、`zxjatype`、`xecjk`、`haranoaji`など）をインストールします。手動でパッケージをインストールする必要はありません。

---

### ステップ5: Rパッケージのインストール（必須）

**重要**: naistQmdテンプレートにはRコードチャンクが含まれているため、QuartoがRパッケージを必要とします。Rを使わない場合でも、最小限のパッケージをインストールする必要があります。

#### Rの確認

まず、Rがインストールされているか確認してください：

```bash
R --version
```

**もしRがインストールされていない場合**:

```bash
# Homebrewでインストール
brew install --cask r
```

#### Rパッケージのインストール

Rを使わない場合でも、以下の2つのパッケージは必須です：

```bash
Rscript -e "install.packages(c('knitr', 'rmarkdown'), repos='https://cran.rstudio.com/')"
```

このコマンドを実行すると：

1. `knitr`と`rmarkdown`がインストールされます
2. 依存パッケージも自動的にインストールされます
3. インストールには2-3分程度かかります

**インストール確認**:

```bash
Rscript -e "library(knitr); library(rmarkdown); cat('OK\n')"
```

`OK`が表示されれば成功です。

---

### ステップ6: Rコードチャンクの無効化（Rを使わない場合）

Rを使わない場合は、Rコードチャンクを無効化する必要があります。

#### 6-1. `_quarto.yml`の設定

`_quarto.yml`ファイルに以下を追加します：

```yaml
# Rエンジンを無効化（Rを使わない場合）
execute:
  enabled: false
```

**確認**: `_quarto.yml`ファイルを開いて、以下の内容が含まれているか確認してください：

```yaml
project:
  type: default

post-render: scripts/post-render.sh

# Rエンジンを無効化（Rを使わない場合）
execute:
  enabled: false
```

#### 6-2. Rコードチャンクの設定変更

`03_result.qmd`と`05_supplementary.qmd`ファイル内のRコードチャンクに`eval=FALSE`を追加します。

**注意**: これらのファイルは既に`eval=FALSE`が設定されている場合があります。確認してください。

**確認方法**:

```bash
# Rコードチャンクにeval=FALSEが設定されているか確認
grep -n "^```{r" 03_result.qmd | head -3
```

出力に`eval=FALSE`が含まれていればOKです。例：````{r eval=FALSE, tbl-descriptive, echo=FALSE}`

#### 6-3. インラインRコードのコメントアウト（必要に応じて）

`03_result.qmd`ファイル内にインラインRコード（`` `r sprintf(...)` ``）が含まれている場合、これらをコメントアウトする必要があります。

**確認方法**:

```bash
# インラインRコードが含まれているか確認
grep -n "`r " 03_result.qmd
```

**注意**: 現在のテンプレートでは、インラインRコードは既にコメントアウト（`<!-- r ... -->`）されています。もしエラーが出る場合は、手動でコメントアウトしてください。

---

## 動作確認

### PDFの生成

すべてのインストールが完了したら、サンプルPDFを生成して動作確認します：

```bash
cd /path/to/naistQmd
quarto render paper.qmd
```

このコマンドを実行すると：

1. Quartoが`paper.qmd`を`paper.tex`に変換します
2. `post-render.sh`が自動実行され、YAML変数を展開します
3. XeLaTeXでPDFを生成します（3回実行 + biber 1回）
4. 処理には1-2分程度かかります

**成功の確認**:

```bash
ls -lh paper.pdf
```

`paper.pdf`ファイルが生成されていれば成功です（通常200KB程度）。

### 正常な出力例

PDF生成が成功すると、以下のような出力が表示されます：

```
processing file: paper.qmd
...
Rendering PDF
running xelatex - 1
running xelatex - 2
running xelatex - 3
Output created: paper.pdf
```

### 警告について

以下の警告が表示されることがありますが、**無視して問題ありません**：

- `Unable to resolve crossref @fig-histogram` - Rコードチャンクが無効な場合に表示されます
- `FloatRefTarget with no content: tbl-descriptive` - Rコードチャンクが無効な場合に表示されます
- `Duplicate entry key` - 参考文献の重複キー警告（`bibliography-en.bib`内）

これらはPDF生成には影響しません。

---

## トラブルシューティング

### エラー1: Rパッケージが見つからない

**エラーメッセージ例**:

```
Error in loadNamespace(x) : there is no package called 'rmarkdown'
The knitr package is not available in this R installation.
```

**解決方法**:

```bash
# Rパッケージをインストール
Rscript -e "install.packages(c('knitr', 'rmarkdown'), repos='https://cran.rstudio.com/')"
```

**確認**:

```bash
Rscript -e "library(knitr); library(rmarkdown); cat('OK\n')"
```

---

### エラー2: LaTeX環境が見つからない

**エラーメッセージ例**:

```
No TeX installation was detected.
Please run 'quarto install tinytex' to install TinyTex.
```

**解決方法**:

```bash
# Quarto経由でTinyTeXをインストール
quarto install tinytex
```

**確認**:

```bash
quarto check
```

---

### エラー3: Rコードチャンクの実行エラー

**エラーメッセージ例**:

```
Error: object 'male_bfi' not found
```

**解決方法**:

1. `_quarto.yml`に`execute: enabled: false`を追加（ステップ6-1を参照）
2. Rコードチャンクに`eval=FALSE`を設定（ステップ6-2を参照）
3. インラインRコードをコメントアウト（ステップ6-3を参照）

**確認**: 
- `_quarto.yml`ファイルを開いて、`execute: enabled: false`が設定されているか確認してください
- Rコードチャンクに`eval=FALSE`が設定されているか確認してください

---

### エラー4: XeLaTeXが見つからない

**エラーメッセージ例**:

```
xelatex not found
```

**解決方法**:

TinyTeXをインストールした場合、PATHの設定は通常不要です。Quartoが自動的にTinyTeXを見つけます。

もし手動でPATHを設定する必要がある場合：

```bash
# ~/.zshrcに追加
echo 'export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

### エラー5: PDF生成時のエラー

PDF生成時にエラーが出た場合、以下のログファイルを確認してください：

```bash
# XeLaTeXのログ
cat paper-xelatex-1.log
cat paper-xelatex-2.log
cat paper-xelatex-3.log

# biberのログ
cat paper-biber.log

# post-render.shのログ
ls -lt /tmp/quarto-post-render-*.log | head -1 | xargs cat
```

---

## よくある質問（FAQ）

### Q1: TeX Live 2025が必要ですか？

**A**: はい、naistQmdテンプレートはTeX Live 2025が必要です。`quarto install tinytex`を実行すると、TinyTeX v2025.12（TeX Live 2025ベース）がインストールされ、これで十分です。

### Q2: Rを使いたい場合はどうすればいいですか？

**A**: Rを使う場合は、以下の手順を実行してください：

1. `_quarto.yml`から`execute: enabled: false`を削除
2. 必要なRパッケージをインストール：
   ```bash
   Rscript -e "install.packages(c('kableExtra', 'tidyverse', 'psych', 'gridExtra', 'jtools', 'ggsignif', 'effsize', 'apaTables'), repos='https://cran.rstudio.com/')"
   ```
3. `03_result.qmd`と`05_supplementary.qmd`のRコードチャンクから`eval=FALSE`を削除

### Q3: WindowsやLinuxでも使えますか？

**A**: はい、使えます。ただし、この手順書はmacOS（Apple Silicon）向けです。WindowsやLinuxの場合は、以下の点が異なります：

- LaTeX環境のインストール方法が異なります
- PATHの設定方法が異なります

詳細は[公式README](README.md)を参照してください。

### Q4: インストールにどのくらい時間がかかりますか？

**A**: 初回インストールの場合：

- Quarto: 1-2分
- TinyTeX: 5-10分（ダウンロードとインストール）
- Rパッケージ: 2-3分

合計で**10-15分程度**です。

### Q5: PDF生成にどのくらい時間がかかりますか？

**A**: 初回生成の場合、1-2分程度です。2回目以降は、変更がない部分はキャッシュされるため、より高速になります。

### Q6: エラーが出た場合はどうすればいいですか？

**A**: まず、この手順書の[トラブルシューティング](#トラブルシューティング)セクションを確認してください。それでも解決しない場合は、以下の情報を確認してください：

- エラーメッセージの全文
- `quarto --version`の出力
- `quarto check`の出力
- ログファイルの内容

---

## 次のステップ

環境構築が完了したら、以下の手順で論文を作成してください：

1. `paper.qmd`を開いて、YAMLヘッダーに論文情報を記入
2. 各セクション（`01_introduction.qmd`など）を編集
3. `quarto render paper.qmd`でPDFを生成

詳細な使用方法は[README.md](README.md)を参照してください。

---

## まとめ

この手順書に従ってインストールすれば、エラーなくPDFを生成できます。詰まった場合は、[トラブルシューティング](#トラブルシューティング)セクションを確認してください。

**インストール手順の要約**:

1. ✅ リポジトリをクローン
2. ✅ Python 3を確認
3. ✅ Quartoをインストール
4. ✅ TinyTeXをインストール（`quarto install tinytex`）
5. ✅ Rパッケージをインストール（`knitr`、`rmarkdown`）
6. ✅ Rコードチャンクを無効化（Rを使わない場合）
7. ✅ PDFを生成して動作確認

---

**最終更新**: 2025年12月12日  
**動作確認環境**: macOS (Apple Silicon), Quarto 1.8.26, TinyTeX v2025.12

