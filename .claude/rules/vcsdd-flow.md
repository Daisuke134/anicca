---
paths: ["docs/superpowers/**"]
---

# 開発（GLVS の Build/Verify = VCSDD の実コマンド）

| GLVS | 呼ぶもの |
|---|---|
| Goal | brainstorming → writing-plans（spec を `docs/superpowers/specs/`、plan を `docs/superpowers/plans/`） |
| 分離 | worktree（`.worktrees/<feature>/`。ドキュメントのみ dev 直接可）→ `.claude/rules/worktree.md` |
| Build/Verify | `vcsdd-init`→`spec`→`spec-review`→`tdd`→`impl`→`adversary`→`harden`→`converge`。**実コマンドを呼んで state.json の phase を進める**。token 上限は global CLAUDE.md が正本 |
| 完了 | finishing-a-development-branch（テスト → push → worktree cleanup） |

仕事が確定した瞬間に spec 作成 + TaskCreate + commit&push を同じ turn で行う。spec に「任意/optional/推奨」は書かない（全て MUST）。終わっていない作業を completed と書かない。
実装レビューのゲート = `vcsdd-adversary`（fresh spawn、blocking 0 + 自分の E2E green）。codex-review は廃止。
