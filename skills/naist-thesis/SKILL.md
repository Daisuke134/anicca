---
name: naist-thesis
description: [DEPRECATED v1 — replaced by ~/.openclaw/skills/naist/ unified v2; this stub is kept for ledger continuity] 論文テキスト・LaTeXファイルを校正し一人称表現・参考文献整合性・可読性スコアをSlackに投稿する。Use when user says 「論文を校正して」「thesis.texを見て」「一人称チェックして」「参考文献確認して」or any thesis review request.
---

# {{profile.education.institution}} Thesis Reviewer

LaTeX論文をチェックし、指摘事項と可読性スコアを#ai-<username>に投稿する。

## 実行コマンド

```bash
export PATH=/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:$PATH
cd /Users/anicca/.openclaw/skills/naist-thesis

# ファイルを指定して校正
node scripts/thesis.js /path/to/thesis.tex

# テキストを直接渡す
node scripts/thesis.js "We propose a novel method..."

# DRY_RUN（Slack投稿なし・テスト用）
DRY_RUN=1 node scripts/thesis.js "We propose a novel method..."

# テスト
npm test
```

## スクリプト構成

| ファイル | 役割 |
|---------|------|
| `scripts/review.js` | 一人称チェック・参考文献整合性・単語数・スコア計算 |
| `scripts/thesis.js` | エントリーポイント。入力→校正→Slack投稿 |
| `scripts/utils/slack.js` | openclaw message send ラッパー |

## チェック項目

| チェック | 説明 |
|---------|------|
| 一人称表現 | "we propose" "I believe" "our method" 等を行番号付きで指摘 |
| 参考文献整合性 | \cite{}で引用されているが\bibitem{}にないキー（逆も） |
| 単語数 | 現在語数・目標までの残り語数 |
| 可読性スコア | 平均文長ベースの0-100スコア |

## 出力例

```
📝 *論文校正レポート* — chapter3.tex

📊 可読性スコア: 73/100
📏 文字数: 12,847語（目標20,000語まで: あと7,153語）

⚠️ 指摘事項: 3件

[1] [L47] 一人称表現 "we propose" → "This thesis proposes..." 等に変更
[2] [Smith2023] が本文で引用されているが参考文献リストに存在しない
[3] 参考文献 [Chen2022] が本文で引用されていない

内訳: 一人称表現 1件 / 参考文献整合性 2件
```

## Cronなし（オンデマンドのみ）

Aniccaが「thesis.texを校正して」等のSlackメッセージを受信したとき自動実行。

## 投稿先 Slack チャンネル

レポートは問い合わせ元のチャンネルに返す。問い合わせ元が分からない場合は `~/.openclaw/state/naist/<slug>/slack_channel.txt` を読む。両方とも無ければ `#metrics` (`{{profile.channels.reportChannel}}`) に投稿。
