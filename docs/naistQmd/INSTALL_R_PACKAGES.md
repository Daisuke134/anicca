# Rパッケージのインストール方法

naistQmdテンプレートにはRコードチャンクが含まれているため、QuartoがRパッケージを必要とします。

## 最小限のインストール（推奨）

Rを使わない場合でも、QuartoがRコードチャンクを検出するため、最小限のパッケージをインストールする必要があります：

```bash
# Rを起動
R

# Rコンソールで以下を実行
install.packages(c("knitr", "rmarkdown"))

# 終了
q()
```

## 完全なインストール（Rを使う場合）

Rコードチャンクで使用するすべてのパッケージをインストールする場合：

```bash
R

# Rコンソールで以下を実行
install.packages(c("knitr", "rmarkdown", "kableExtra", "tidyverse", "psych", "gridExtra", "jtools", "ggsignif", "effsize"))

# apaTablesはGitHubからインストール
install.packages("remotes")
remotes::install_github("dstanley4/apaTables")

# 終了
q()
```

## インストール後の確認

```bash
cd /Users/cbns03/Downloads/anicca-project/naistQmd
quarto render paper.qmd
```

## 注意事項

- Rパッケージのインストールには時間がかかります（5-10分程度）
- インターネット接続が必要です
- Rがインストールされている必要があります（既にインストール済み: R 4.3.1）

