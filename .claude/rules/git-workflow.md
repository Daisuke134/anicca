# Git Workflow

## Commit Format

`<type>: <description>` — Types: feat, fix, refactor, docs, test, chore, perf, ci

## PR Workflow

1. `git diff [base-branch]...HEAD` で全変更確認
2. 全コミット履歴を分析（最新だけ見ない）
3. PR summary + test plan 作成、`-u` flag で push

## Feature Flow

Plan（planner agent）→ TDD（RED→GREEN→REFACTOR、80%+ coverage）→ Review（code-quality-reviewer）→ Commit

## Semver

| 変更 | 例 |
|------|-----|
| バグ修正 | 1.0.8 → 1.0.9 |
| 新機能 | 1.0.8 → 1.1.0 |
| 破壊的 | 1.1.0 → 2.0.0 |

## Hotfix

release ブランチで修正 → dev に cherry-pick

## 壊れた Submodule

```bash
git rm --cached <path> && echo "<path>/" >> .gitignore && git commit -m "fix: remove broken submodule" && git push
```

## Prisma Migration

| Step | Command |
|------|---------|
| baseline | `DATABASE_URL="..." npx prisma migrate resolve --applied <name>` |
| deploy | `DATABASE_URL="..." npx prisma migrate deploy` |
| 反映 | main に push（Railway自動デプロイ） |

## リリース管理

| ルール | 内容 |
|--------|------|
| 作業場所 | 原則ワークツリー。ドキュメントのみdev直接可 |
| ブランチ作成 | dev→main後、mainからrelease/x.x.x |
| マージ | 絶対禁止。チェックリスト→ユーザーOK待ち |
| 並列開発 | Git Worktrees（worktree.md参照） |
