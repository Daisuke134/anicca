---
paths:
  - ".worktrees/**"
---

# 並列開発ルール（Git Worktrees）

**原則ワークツリー。ドキュメント変更のみdev直接可。**

## ★ 既定 = Claude Code 公式ネイティブ（車輪の再発明禁止・BP採用）

手動 `git worktree add/remove` は削除し忘れで蓄積 → disk 圧迫。代わりに**公式機能を使う**（出典: https://code.claude.com/docs/en/worktrees）:

| 場面 | 使うもの | 効果 |
|---|---|---|
| サブエージェントで並列実装 | Agent tool の `isolation: "worktree"` | 一時worktree自動作成、**変更なしなら自動削除**（蓄積しない） |
| 対話セッションで別作業 | `--worktree`/`-w` flag、または `EnterWorktree`/`ExitWorktree` tool | 隔離worktreeで作業 |
| env等の持ち込み | repo直下 `.worktreeinclude`（gitignore構文） | `.env`等を新worktreeへ自動コピー |
| 蓄積したworktree | `cleanupPeriodDays` 設定 + SessionStart hook の削除候補表示 | 古いものを自動/半自動GC |

**強制（prose でなく hook）**: `TaskCompleted` hook `exit 2` で spec/test/adversary-verdict が揃わない完了を拒否＝VCSDD全工程の機械的担保。`PreToolUse Edit|Write exit 2` で worktree外/spec無し編集をブロック。→ `.claude/hooks/` に実装。

## 禁止

- 同じブランチで複数エージェント作業
- Worktreeなしで複数タスク並行

## フロー

```bash
git worktree add .worktrees/<task> -b feature/<task>  # 作成
cd .worktrees/<task>                                   # 作業
# 完了後
cd /path/to/anicca-project && git merge feature/<task>
git worktree remove .worktrees/<task> && git branch -d feature/<task>
```

## Spec ルール

| ルール | 理由 |
|--------|------|
| 各Worktreeに独自Spec | 干渉回避 |
| 触るファイルをSpec境界に明記 | 同ファイル複数人触り防止 |
| Spec冒頭に開発環境セクション | ワークツリーパス、ブランチ、状態を記載 |

## バックエンド開発

| 状況 | デプロイ |
|------|---------|
| dev push | Railway自動デプロイ |
| Worktree push | 自動デプロイされない → `cd apps/api && railway up --environment staging` |

**複数エージェントのバックエンドデプロイは順番に。同時は上書きされる。**
