# Skill Deduplication & Repo Unification Spec

**Date**: 2026-02-28
**Author**: Anicca
**Status**: ✅ 完了（）

---

## 実行結果

| # | タスク | 状態 |
|---|--------|------|
| 0a | MacBookの origin を anicca-products に変更 | ✅ 完了 |
| 0b | MacBookの未同期コミットをpush（rebase済み） | ✅ 完了 |
| 0c | Mac Miniで git pull（両方 36319bec で同期） | ✅ 完了 |
| 0d | Daisuke134/anicca privateリポの整理 | ⬜ ✅ 完了（devブランチ削除） |
| 1 | 壊れたsymlink削除 (.claude/skills/supabase) | ✅ 完了 |
| 2 | supabase .agent サブディレクトリ削除 | ✅ 完了 |
| 3 | ClawHub汎用 mobile-app-builder 削除 | ✅ 完了 |
| 4 | OpenClaw内の死んだ重複24個削除（77→53スキル） | ✅ 完了 |
| 5 | CLAUDE.md にMacBook用ルール追記 | ✅ 完了 |
| 6 | TOOLS.md にスキル管理ルール追記 | ✅ 完了 |
| 7 | git-auto-sync cron削除（Opus無駄遣い停止） | ✅ 完了 |
| 8 | MacBookにシステムcron git pull追加（5分ごと） | ✅ 完了 |
| 9 | MEMORY.md + TOOLS.md にtmux/syncルール記録 | ✅ 完了 |
| 10 | git commit & push | ✅ 完了 |

## DaisがMac MiniのCCを使うコマンド

```bash
# 既存セッション接続
ssh anicca@aniccanomac-mini-1 -t "/opt/homebrew/bin/tmux attach -t claude"

# 新規セッション
ssh anicca@aniccanomac-mini-1 -t "/opt/homebrew/bin/tmux new -s claude -c /Users/anicca/anicca-project"
```

## オリジナリティ: 0%
