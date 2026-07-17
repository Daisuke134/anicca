# profitable-claude 単一 repo 化: clip loop 移設プラン

出典: sutando 実コード読解 (github.com/sonichi/sutando、2026-07-17 clone) + profitable-claude 現状 tree (github.com/Daisuke134/profitable-claude) + `~/anicca/skills/earn/clip/clip-cli.sh` の copy note。

## 結論 (核心)
**profitable-claude は既に正しいアーキテクチャを持っている。** `bin/ceo-run.sh` + `launchd/ai.anicca.ceo-runner.plist` = OS-launchd `StartInterval` が bash entrypoint を直接叩く形。これは今 live で動いている clip loop (`launchd ai.anicca.clip-loop-aiclipsvault` → `~/anicca/skills/earn/clip/clip_pass.sh`) と**同じパターン**。
→ 移設 = **ファイル copy + path 再指定**であって、アーキテクチャ発明ではない。
→ sutando の tmux-core + native CronCreate + Swift menubar app スタックは**再現しない**（compiled Swift binary と特定 long-lived session に縛られた Cron primitive に依存、この用途には overkill）。

## sutando から学んだ事 (参考、採用しないもの含む)
- claude-p パターン: `claude --name X --dangerously-skip-permissions -- "/schedule-crons"` を named tmux session で起動。recurring driver は OS cron でなく Claude Code **native CronCreate** で `*/5 * * * *` → `/proactive-loop` を登録。passes 間は tmux 内で idle。→ **我々は OS-launchd を使う（既存 live と同じ）ので不採用。**
- skills 配置: sutando は repo `skills/<name>/SKILL.md` を `skills/install.sh` で `$CLAUDE_CONFIG_DIR/skills/` に symlink。CLAUDE_CONFIG_DIR は workspace-scoped (`${WORKSPACE_DIR}/.claude-sutando`)。→ **profitable-claude は project-scoped `.claude/skills/<name>/` を repo root に直接 commit する標準方式（Claude Code が cwd 内で自動読込、install step 不要）。こちらが simple、採用。**
- self-heal 3層: (a) start-cli.sh が毎回 idempotent に生存確認/attach/heal、(b) health-check.py --recover-core が wedged 検知→restart→opus escalate、(c) launchd KeepAlive supervisor。+ core-input-watch が `/login` 等の blocked-on-input を owner channel へ escalate。→ **我々の clip-healthcheck.sh + launchd で相当機能。**
- state/secrets: `.env`/`*.local.json` gitignored、workspace は in-repo だが gitignored、repo に state を一切 commit しない。→ **同じ方針: ~/.cloak, ~/clips, ~/.openclaw/.env は repo 外のまま。**

## Copy-manifest (`~/anicca/skills/earn/clip/` → `profitable-claude/skills/clip/`)
```
clip_pass.sh run.sh producer.sh monitor.sh self_heal.py warm_step.py count_posts.py
reel_verify.py verify_posted_quality.py _instance_paths.sh clip-healthcheck.sh clip-cli.sh
scripts/{bio_step.py,burn_captions.py,export_camofox_cookies.py,instagrapi_post.py,
         measure_dollar.py,pipeline.py,verify_clip.sh}
tests/*
```
共有 deps (clip_pass.sh/clip-cli.sh が参照、clip-local でない):
- `~/anicca/skills/browser/` → `profitable-claude/skills/browser/` (CloakBrowser session/lease、全 step の hard dep)
- `~/anicca/skills/report/loop-report.sh` + `lib/` → `profitable-claude/skills/report/` (Telegram/mail 報告 step)
- `~/anicca/skills/self/self-improve/clip/evaluator.py` (+ `lib/weekly_compare.py`) → `profitable-claude/skills/self-improve/clip/`
- `~/.claude/skills/{ig-account-create,ig-reels-poster,ig-account-warmer}/` → `profitable-claude/.claude/skills/{同}/` (STARTUP prompt から live `/slash-command` で呼ばれる = `.claude/skills/` に置く)

Launchd: `bin/clip-run.sh` (= `bin/ceo-run.sh` と同 shape の thin dispatcher、既存 clip_pass.sh/clip-cli.sh を wrap) + `launchd/ai.anicca.clip-runner.plist` (= `ai.anicca.ceo-runner.plist` を模倣)。

## Gaps (単なる copy でない、埋める必要あり)
1. profitable-claude `CLAUDE.md` は今 `@.claude/active-team.md` (generic ccteams) のみ = earn loop への言及ゼロ。clip loop の存在 + state 所在を書く section が要る (今は `~/anicca-project/CLAUDE.md` の colony table だけが知っている)。
2. `_instance_paths.sh` は `ANICCA_INSTANCE`/`ANICCA_HOME` gate で path 解決 (今 franklin1 の `~/.blockrun` 等を指す)。PC に移すと「PC の home は何か」を決める設計判断が要る (機械 copy でない)。
3. CLIProxyAPI auth fallback (`~/.cli-proxy-api-key`、local proxy :8317) は headless core の OAuth refresh 前提 = machine-level 外部依存として文書化 (sutando の `.env.example` GEMINI_API_KEY 相当、repo が提供できるものでない)。
4. secrets/state は今のまま repo 外: `~/.cloak/*.json`, `~/.openclaw/.env`, `~/clips/{reflection.jsonl,playbook.json,clip-metrics.jsonl}`。変更不要、`profitable-claude/.gitignore` が local scratch を覆うか確認のみ。
5. 新 orchestration 機構は不要。`bin/ceo-run.sh` パターンで足りる = 純粋な file-migration + path re-pointing。

## 順序
★投稿 (#2) が動いてから移設 (#8) に着手★。投稿が回る前に repo を動かしても映すものが無い。
