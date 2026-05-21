# naistQmd

NAIST（奈良先端科学技術大学院大学）修士論文作成用のQuartoテンプレートです。

## 特徴

- Quartoを使用したMarkdownベースの論文作成
- NAISTの修士論文フォーマットに準拠
- 日本語・英語の概要ページに対応
- タイトルページ、審査委員ページを自動生成
- YAML変数で論文情報を制御
- レンダリング時に自動的にYAML変数が展開される

## 必要な環境

- [Quarto](https://quarto.org/) (最新版推奨、>=1.2.0)
- LaTeX環境
  - 日本語対応のLaTeX環境が必要です
  - **推奨**: [TeX Live](https://www.tug.org/texlive/) または [MacTeX](https://www.tug.org/mactex/)（macOS）
  - **軽量版**: [TinyTeX](https://yihui.org/tinytex/) も使用可能（必要なパッケージをインストールする必要があります）
  - `xelatex`エンジンが使用可能であること
  - `bxjsarticle`クラスを使用
  - `biblatex`と`biber`が使用可能であること（参考文献処理用）
  - 日本語フォント（例: Noto Serif CJK JP, IPAexMinchoなど）
- Python 3（YAML変数展開用）

## インストール方法

以下のコマンドでリポジトリをクローンしてください：

```bash
git clone https://github.com/HOgishima/naistQmd.git
cd naistQmd
```

`examples/`ディレクトリ内には参考用のサンプルが含まれていますが、これらは独立したgitリポジトリです。通常の使用では必要ありません。

## 使用方法

### 重要: YAML変数の自動展開

**UIのKnitボタンでも自動的に変数が展開されるように設定されています。** `_quarto.yml`に`post-render: scripts/post-render.sh`が設定されているため、RStudioやVS CodeのKnitボタンを使用しても、自動的にYAML変数が展開されます。

### 1. YAML変数の設定

`paper.qmd`を開いて、YAMLヘッダーに以下の情報を記入してください：

- `title`: 論文タイトル（英語）
- `author`: 著者名（英語）
- `date`: 提出日
- `student-id`: 学籍番号
- `japanese-title`: 日本語タイトル
- `english-title`: 英語タイトル
- `japanese-author`: 日本語著者名
- `english-author`: 英語著者名
- `japanese-year`: 提出年（和暦）
- `english-year`: 提出年（西暦）
- `submission-month`: 提出月
- `submission-day`: 提出日
- `lab-name-japanese`: 研究室名（日本語）
- `lab-name-english`: 研究室名（英語）
- `supervisor`: 主指導教員
- `co-supervisor`: 副指導教員
- `third-member`: 審査委員3（オプション）
- `third-position`: 審査委員3の役職（オプション）
- `fourth-member`: 審査委員4（オプション）
- `fourth-position`: 審査委員4の役職（オプション）
- `fifth-member`: 審査委員5（オプション）
- `fifth-position`: 審査委員5の役職（オプション）
- `sixth-member`: 審査委員6（オプション）
- `sixth-position`: 審査委員6の役職（オプション）
- `keywords-japanese`: キーワード（日本語、カンマ区切り）
- `keywords-english`: キーワード（英語、カンマ区切り）
- `japanese-abstract`: 日本語概要
- `english-abstract`: 英語概要

### 2. PDFの生成

#### 方法1: UIのKnitボタンを使用（推奨）

RStudioやVS CodeのQuarto拡張機能でKnitボタンを押すと、`post-render.sh`が自動的に実行され、YAML変数が展開されたPDFが生成されます。

#### 方法2: ターミナルから実行

```bash
quarto render paper.qmd
```

このコマンドを実行すると、`post-render.sh`が自動的に実行され、YAML変数が展開されます。

#### 方法3: Quarto Previewを使用

```bash
quarto preview paper.qmd
```

Quarto Previewでも`post-render`が実行され、ファイル変更を監視して自動的に再レンダリングされます。

### 3. 論文の内容を記述

`paper.qmd`に論文の内容を記述してください。

### 4. 参考文献

`references/bibliography-en.bib`（英語）と`references/bibliography-jp.bib`（日本語）に参考文献をBibTeX形式で追加してください。

## プロジェクト構造

```
naistQmd/
├── paper.qmd              # メインドキュメント（編集するファイル）
├── references/            # 参考文献データベース
│   ├── bibliography-jp.bib  # 日本語文献（手動管理）
│   └── bibliography-en.bib  # 英語文献（Zotero自動エクスポート）
├── figures/               # 図ファイル
├── README.md              # プロジェクト説明
│
├── _extensions/           # Quarto拡張機能（NAISTフォーマット）
│   └── naist/
│       ├── _extension.yml # 拡張機能の設定
│       ├── naist-vars.lua # YAML変数フィルター
│       └── partials/      # LaTeXパーシャルファイル
│           ├── header-expanded.tex
│           ├── before-body.tex
│           └── biblio.tex
│
├── _output/               # 生成されたPDFと中間ファイル（.gitignore対象）
├── _quarto.yml            # Quarto設定ファイル
│
├── scripts/               # 後処理スクリプト
│   ├── post-render.sh     # PDF生成後の処理（YAML変数展開、PDF再生成）
│   ├── expand_preamble.py # YAML変数展開スクリプト
│   └── add_before_body.py # before-body.tex追加スクリプト
│
├── template/              # LaTeXテンプレート（すべてのスタイルファイルはここに集約）
│   ├── naist-*.sty        # NAISTスタイルファイル
│   │   ├── naist-jmthesis.sty
│   │   ├── naist-mcommon.sty
│   │   └── naist-mthesis.sty
│   ├── jpa.*              # biblatex-jpaファイル
│   │   ├── jpa.bbx
│   │   ├── jpa.cbx
│   │   └── jpa.dbx
│   ├── biblatex-dm.cfg    # biblatex設定ファイル
│   ├── header.tex         # LaTeXヘッダー
│   ├── before-body.tex    # タイトルページなど
│   └── japanese.lbx       # 日本語言語定義
│
└── examples/              # 参考用サンプル
    ├── Mtex/              # 元のLaTeXテンプレート（大学公式）
    ├── senshuQmd/         # 修士論文テンプレート（参考）
    └── pnas-reference/    # PNASテンプレート（参考）
```

## 生成ファイル

以下のファイルは自動生成されるため、手動で編集しないでください：

- `paper.tex`: Quartoが生成するLaTeXファイル
- `paper.pdf`: 最終的なPDFファイル
- `_output/`内のファイル
- `paper_files/`内のファイル（図など）

これらのファイルは`.gitignore`に含まれています。

## 注意事項

### YAML変数の自動展開について

`post-render.sh`が以下の処理を自動的に実行します：

1. Quartoが生成したTeXファイルを修正
2. YAML変数を展開（`expand_preamble.py`を使用）
3. xelatexでPDFを再生成（参考文献の処理を含む）

このため、レンダリングには少し時間がかかりますが、常に正しいYAML変数が展開されたPDFが生成されます。

### 大学の規定について

NAISTの「修士論文・課題研究の形式および電子ファイルの提出について」によると：

> **B: LaTeX を使用するが，標準スタイルファイルは利用しない人**
> 1. 修士論文等の最初の 4 ページは，2節の内容に従い，全体の体裁，印字の位置などが，サンプルファイル mthesis.dvi または jmthesis.dvi に合致するように十分注意して作成する．
> 2. 本文は体裁を自由に決めて作成する．

つまり、**大学が提供しているスタイルファイルを使わなくても、体裁が規定に合っていれば問題ありません**。

- このテンプレートは、大学公式のスタイルファイル（`naist-jmthesis.sty`）のレイアウトをQuartoで再現するように調整されています。
- 最初の4ページがサンプルファイルに合致するように調整されています。
- このテンプレートは参考用です。実際の提出前に、NAISTの公式フォーマット要件を確認してください。

### ファイルの整理について

- すべてのLaTeXスタイルファイルは`template/`ディレクトリに集約されています
- Quartoの`format-resources`は使用していません（相対パスで参照しているため）
- レンダリング時にルートディレクトリに不要なファイルが生成されないようになっています

## トラブルシューティング

### PDFが生成されない場合

1. LaTeX環境が正しくインストールされているか確認
2. `xelatex`が使用可能か確認
3. `biber`が使用可能か確認（参考文献処理用）

### YAML変数が展開されない場合

1. `scripts/post-render.sh`が実行可能か確認（`chmod +x scripts/post-render.sh`）
2. Python 3がインストールされているか確認
3. `_quarto.yml`に`post-render: scripts/post-render.sh`が設定されているか確認

## ライセンス

MIT License

## 貢献方法

テンプレートへの貢献を歓迎します！詳細は[CONTRIBUTING.md](docs/CONTRIBUTING.md)を参照してください。

- バグ報告や機能要望: [GitHub Issues](https://github.com/HOgishima/naistQmd/issues)
- プルリクエスト: [CONTRIBUTING.md](docs/CONTRIBUTING.md)の手順に従ってください

## 不具合報告

不具合や改善提案があれば、Issueで報告してください。
