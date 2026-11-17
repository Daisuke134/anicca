# Superpowers（obra/superpowers）採用メモ — 2026-11-17

本人の指示（2026-11-17）で、**obra/superpowers をチーム全員の標準スキルセット**として採用した。

- 導入（全エージェント共通・1コマンド）: `npx skills add obra/superpowers -g -y -a '*'`
- 収録は15スキル: using-superpowers / brainstorming / writing-plans / executing-plans / subagent-driven-development / dispatching-parallel-agents / test-driven-development / systematic-debugging / verification-before-completion / requesting-code-review / receiving-code-review / using-git-worktrees / finishing-a-development-branch / writing-skills / diagnosing-superpowers
- 正本は上流（obra/superpowers、MIT）。このリポの `skills/` にある自社スキルと重複する場合は **自社版を正とする**。2026-11-17 時点で、このリポの skills/（62件）と superpowers 15件に名前の重複は無い。
- 棚卸し・導入手順・状態の正本は anicca-ops `files/superpowers-adoption-2026-11-17.md`。
- チームの通信は全部 GitHub（anicca-ops）で行う。GitHub に無い会話は存在しないものとして扱う（周知: anicca-ops `team-outbox/muse/to-all-2026-11-17-superpowers-and-github-comms.md`）。
