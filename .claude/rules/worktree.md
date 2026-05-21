# 並列開発ルール（Git Worktrees）

**原則ワークツリー。ドキュメント変更のみdev直接可。**

## 禁止

- 同じブランチで複数エージェント作業
- Worktreeなしで複数タスク並行

## フロー

```bash
git worktree add ../anicca-<task> -b feature/<task>  # 作成
cd ../anicca-<task>                                   # 作業
# 完了後
cd /path/to/anicca-project && git merge feature/<task>
git worktree remove ../anicca-<task> && git branch -d feature/<task>
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
