# PLAN #44 GITHUB-SYNC (B5) — ~/.agents と ~/.claude/skills の双方向 sync

発注: Fable(planner) → Sol(Codex builder, flow B)。2026-07-19。
前提: 両 dir は GitHub 化済（private repo Daisuke134/anicca-agents-skills = ~/.agents、Daisuke134/anicca-claude-skills = ~/.claude/skills。07-19 push 済）。目的 = phone(GitHub app/web) で編集した変更が Mac に自動反映され、Mac 側編集も自動 push される。

## Planner 決定（曲げるな）
- 車輪の再発明禁止: 汎用 sync daemon を書かない。**git pull --rebase --autostash → add -A → commit → push** の薄い script + launchd interval(30分) のみ。
- conflict は自動解決しない: rebase が conflict したら `git rebase --abort` して telegram (chat 8547730585, openclaw message send) に1行警告、次回へ。壊さないが黙らない。
- secret guard: commit 前に `git diff --cached --name-only` を pattern (.env|credentials|*.pem|secret.*|*.key) で検査、該当あれば commit 中止 + telegram 警告。~/.agents/skills/agmsg/db (messages.db 等の生 DB) は .gitignore へ（既に track 済なら `git rm --cached`）。
- 対象は2 repo のみ。~/.cloak 等は絶対に触らない。

## 要件（MUST）
R1: `~/.agents/skills/self-sync/sync.sh` 新規（両 repo を順に処理する1本。repo path と branch は配列で保持）。冪等・多重起動 guard（flock or pid file）。log は `~/.openclaw/logs/agents-skills-sync.log` に追記。
R2: launchd plist `ai.anicca.agents-skills-sync`（StartInterval 1800）を **生成する installer script**（`install.sh`）として同 dir に置く。launchctl bootstrap は Fable が実行（Sol は launchctl 禁止）。
R3: 上記 secret guard + conflict 処理 + agmsg db の gitignore/rm --cached を実装。
R4: テスト: bash -n 全 sh + sandbox repo（/tmp 配下に bare remote + 2 clone を作る自己完結 test script `test_sync.sh`）で (i) 双方向反映 (ii) conflict 時 abort+警告 stub (iii) secret 検出で commit 拒否、を実 git で検証し PASS/FAIL を stdout に出す。実 GitHub/実 telegram には触らない（telegram 送信は env TELEGRAM_STUB=1 で echo に差し替え可能に）。
R5: worktree 不要（~/.agents は repo そのもの）。新規 dir `~/.agents/skills/self-sync/` 内の新 file のみ作成。既存 file 変更は .gitignore と `git rm --cached`（agmsg db）だけ。git commit/push は Fable 担当 — Sol は file 作成と test 実行のみ。

## Done
1. `bash test_sync.sh` が 3 case とも PASS（Sol 実行、出力貼付）
2. bash -n PASS
3. agmsg で 'DONE #44' + 出力要約 + 作成 file 一覧（絶対 path）
質問: send.sh capafy sol-codex fable-main '<#44: 質問>'。
