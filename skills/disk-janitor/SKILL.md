---
name: disk-janitor
description: Sweeps disk hogs from local workspace every 3 hours. Targets known-disposable dirs (Remotion out/.cache, claude-harness task tempdir, /tmp scrape leftovers, sao-content-factory/output older than 2 days). Idempotent. Reports freed bytes to Slack #metrics. Cron 0 */3 * * * JST.
---

# Disk Janitor — Single Command Skill

You are an LLM running once via cron. Your only job: execute the bash orchestrator and emit its final stdout line.

## YOUR ENTIRE TASK (do not deviate)

```bash
bash ~/.openclaw/skills/disk-janitor/run.sh
```

Pass the final stdout line through unchanged. Cron delivery posts it to #metrics. Do not call Slack tools yourself.

## Targets (always-safe to delete)

- `~/anicca-project/sao-content-factory/remotion/out/` — re-renderable from src
- `~/anicca-project/sao-content-factory/remotion/.cache/` — re-buildable
- `~/anicca-project/sao-content-factory/assets/*/v*/output/` (>2d old)
- `~/anicca-project/sao-content-factory/assets/*/v*/broll/yt_full.mp4` (>2d, re-DL via yt-dlp)
- `~/anicca-project/sao-content-factory/assets/*/v*/bgm/bgm_*_full.mp3` (>2d, only if `bgm.mp3` already trimmed)
- `~/.openclaw/skills/sao-content-factory/output/*/` (>2d old per-day per-version videos)
- `/private/tmp/claude-501/**` task transcripts older than 1d
- `/private/var/folders/*/*/{X,C}/*code_sign_clone*/` Chrome.app clone orphans idle >60min (agent-{{profile.lateness.stakeholders.channel}}/playwright leak — historically the #1 disk eater at 41GB; Unix-safe even while Chrome runs)
- `/tmp/*.md`, `/tmp/x_thread_*.json`, `/tmp/sao_draft_*.json`, `/tmp/jobs.json.*` (any age — transient)
- `/private/tmp/claude-501/**` task transcripts older than 3h (115 crons spawn isolated sessions constantly)
- **macOS dev-tool caches (regenerable, the real hogs)**: `~/Library/Developer/Xcode/DerivedData/*`, `~/Library/Developer/CoreSimulator/Caches/*` + `simctl delete unavailable`, `~/Library/Caches/org.swift.swiftpm/*`, `~/Library/Caches/Homebrew/*`, `~/Library/Caches/{colima,Google,node-gyp,pip}/*`, `~/.npm/_cacache`, `~/.bun/install/cache`

Never touched: `~/Library/Caches/camoufox` (Camofox = main {{profile.lateness.stakeholders.channel}} stash), `~/.bun/bin` (nano-banana + CLIs), `node_modules/`, `.next/`, `state/`, `docs/`, `.git/`, `.env`.

## Safety net (tiered)

After the sweep: `<2GB free` → exit 4 (EMERGENCY alert to #metrics); `<5GB free` → ⚠️ warn line (exit 0); else 🧹 normal report. The old single 200MB threshold was uselessly low — cron `.output` writes hit ENOSPC long before that.

## Failure mode

If a delete fails or `df` reports < 200MB free after the sweep, exit non-zero with last 3 stderr lines so a human can intervene.
