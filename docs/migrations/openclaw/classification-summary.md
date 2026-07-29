# OpenClaw runtime inventory — Order 2 classification summary

Source of truth: `docs/migrations/openclaw/runtime-inventory.json` (399 rows,
captured 2026-07-29, read-only). Classifier:
`apps/life-manager/scripts/classify-legacy-jobs.js` (deterministic; re-running
it against the checked-in inventory is a no-op, proven by
`apps/life-manager/scripts/classify-legacy-jobs.test.js`). Validation:
`cd apps/life-manager && npm run test:openclaw-classification` (9/9 pass).

## Counts per disposition

| Disposition | Rows | Rule |
|---|---:|---|
| migrate | 214 | enabled-or-loaded legacy loops assigned to a Life Manager family adapter (includes the 3 pre-classified Order 1 rows) |
| replace | 40 | machine-maintenance/monitoring jobs (monkey/watchdog/janitor/healthcheck/backup/cleanup) plus the OpenClaw gateway/ask/heartbeat core, replaced by Life Manager monitoring and scheduler |
| retire | 132 | 130 disabled-and-unloaded OpenClaw store rows, plus `probe-rollback-*` (stale one-off) and `com.anicca.daemon` (loaded-only residual; plist already disabled 2026-07-12/13) |
| retain-external | 13 | third-party/system services outside migration scope (vocabulary amendment, decided): homebrew services (cliproxyapi, ollama, tailscale), clawrouter, CodexBar, Google updater, GitHub Actions runner, token-optimizer dashboards, vineyard dashboard-sync, colima autostart, and 2 label-less plists |
| **total** | **399** | zero rows remain `unclassified`; all 269 enabled-or-loaded rows have a non-null owner |

## Counts per target family (migrate + replace)

| Target adapter / family | Rows | Examples |
|---|---:|---|
| life-manager-runtime | 56 | personal/life loops (booking, meetup, comedy career, travel, phone/telegram/slack transport), OpenClaw gateway+ask+heartbeat (replace), canonical life-manager launchd jobs |
| marketing-video-generation | 44 | larry-*, reelclaw-*, honne, watercolor, slideshow, clip-loop, music, yangmun, comedy posting |
| life-manager-monitoring | 36 | monkey/watchdog/janitor, healthchecks, backups, disk/net sentinels (all `replace`) |
| finance-x402 | 31 | x402-*, the402-*, autohedge, pm-* trading, stripe-revenue, sol-funding, usdc, taskmarket ledger |
| gig-loop | 15 | hf-gig-*, bounty, contra, job-search |
| writer-loop | 13 | writer-*, article-*, craft-train, auto-research |
| mail-loop | 11 | agentmail-*, cold-email, mail-triage, letters, outbound recruit |
| marketing-platform-observation | 9 | marketing-dashboard/metrics, connector reports, account/postiz health, app-reviews |
| franklin-loop | 9 | franklin loops, citizen image/MCP sidecars, citizen-refill |
| seo-loop | 8 | backlink-*, corey SEO/CRO/schema, seo-rank-monitor |
| school-loop | 7 | naist-*, jsps application |
| memory-maintenance | 6 | sync-memory, daily-memory, factory-bp-*, pattern-promoter |
| capafy-loop | 5 | capafy daily/goal/marketing/warmup/publish |
| financial-report-telegram | 3 | financial report (Order 1), ai.anicca.cfo-daily, cfo-sync |
| marketing-life-manager-daily | 1 | ai.anicca.life-manager-daily (Order 1, protected) |

## Special cases (classified per read-only inspection)

| Row | Finding | Disposition |
|---|---|---|
| `ai.anicca.cfo-daily` | plist is not `plutil`-parseable (unknown ampersand-escape at line 11) so the captured command is empty; text inspection shows a daily 06:00 job running `$HOME/.openclaw/skills/cfo-core/run-cfo.sh`; `launchctl list` reports the label loaded with last exit status 0 at classification time | migrate → financial-report-telegram (with `classification_note`) |
| `com.anicca.daemon` | loaded-only residual at capture: active plist was renamed to `.disabled` backups on 2026-07-12/13 (KeepAlive daemon for `$HOME/anicca/runtime/anicca-daemon.sh`); the label is no longer present in `launchctl` at classification time | retire (with `classification_note`) |

## Field conventions

| Field | Rule |
|---|---|
| owner | migrate/replace → `life-manager`; retire → `life-manager-migration`; retain-external → `system`; the 3 protected Order 1 rows keep `life-manager-runtime` |
| verify_command | set to `cd apps/life-manager && npm run test:runtime-adapters` only when the target adapter already exists in `apps/life-manager/config/loop-adapters.json`; otherwise `null` (never invented) |
| rollback_action | OpenClaw-store retire → "re-enable job in archived OpenClaw store from signed inventory"; launchd retire and all migrate/replace → "restore legacy scheduler entry from signed inventory"; retain-external → "none (outside migration scope)" |
| effect_class | publish for posting families, message for mail/financial report, none for internal loops; null for retire/retain-external |

No scheduler was loaded, unloaded, or modified during classification; all
inspection of `~/.openclaw` and launchd was read-only.
