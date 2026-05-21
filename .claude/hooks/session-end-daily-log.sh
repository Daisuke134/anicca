#!/bin/bash

# セッション終了時に日報を自動保存するHook
# 入力: stdin経由でJSON（session_id, transcript_path, cwd, reason）

# JSONを読み込む
INPUT=$(cat)

# 日付を取得
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)

# 保存先ディレクトリ
MEMORIES_DIR="$HOME/Downloads/anicca-project/.claude/skills/agent-memory/memories/daily-logs"

# ディレクトリがなければ作成
mkdir -p "$MEMORIES_DIR"

# ファイルパス
LOG_FILE="$MEMORIES_DIR/${DATE}.md"

# transcript_pathを取得（オプション）
TRANSCRIPT_PATH=$(echo "$INPUT" | grep -o '"transcript_path"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*: *"//' | sed 's/"$//')

# 既存のファイルがあれば追記、なければ新規作成
if [ -f "$LOG_FILE" ]; then
    # 追記モード
    echo "" >> "$LOG_FILE"
    echo "---" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    echo "## セッション終了: $TIME" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    echo "_自動記録: セッションが終了しました。詳細は次回セッションで確認してください。_" >> "$LOG_FILE"
else
    # 新規作成
    cat > "$LOG_FILE" << EOF
---
summary: ${DATE}の作業ログ
created: ${DATE}
tags: [daily-log, auto-generated]
---

# ${DATE} 作業ログ

## セッション終了: $TIME

_自動記録: セッションが終了しました。詳細は次回セッションで確認してください。_

<!--
次回セッションで以下を追記:
- やったこと
- 学び・発見
- 課題・ブロッカー
- 明日やること
-->
EOF
fi

echo "Daily log saved to: $LOG_FILE"
