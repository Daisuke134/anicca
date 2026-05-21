# NLP2 Assignments Solution

## 概要

このディレクトリには、NLP2の課題（Questions 1-10）を解くためのスクリプトが含まれています。

## セットアップ

### 1. 必要なライブラリのインストール

```bash
pip install -r requirements.txt
```

### 2. スクリプトの実行

```bash
python generate_report.py
```

このスクリプトは以下の処理を行います：
- Questions 1-2: text0の単語トークン数とタイプ数をカウント
- Questions 3-5: llm-jp-3.1-1.8bトークナイザーでの分析
- Questions 6-8: Qwen/Qwen3-1.7Bトークナイザーでの分析
- Questions 9-10: ACL 2015と2025の論文分析

結果は `NLP2_report_format.txt` に保存されます。

## 注意事項

### Questions 9-10について

- ACL 2025の論文数は**4547**で計算します（訂正後の値）
- Question 10のキーワード検索では、"POS"は単語として検索します（"XPOS"や"Decompositional"は除外）
- ACL論文の取得には時間がかかる可能性があります

### 実行時間

- Questions 1-8: 数秒〜数分（トークナイザーのダウンロード時間を含む）
- Questions 9-10: 数分〜10分以上（ACL論文の取得時間による）

## ファイル構成

- `NLP2_assignments_20251112.ipynb`: 元の課題ノートブック
- `generate_report.py`: 全質問を解いてレポートを生成するスクリプト
- `solve_assignments.py`: 詳細な分析結果を表示するスクリプト
- `NLP2_report_format.txt`: レポートフォーマット（実行後に回答が書き込まれる）
- `requirements.txt`: 必要なPythonパッケージのリスト

