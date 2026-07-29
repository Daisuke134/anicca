# OpenClaw Enabled Job Inventory

**Measured:** 2026-07-29 JST  
**Store:** `/Users/anicca/.openclaw/cron/jobs.json`

## Scheduler state

| Check | Result |
|---|---|
| OpenClaw cron feature | `enabled: true` |
| Entries in store | 316 |
| Entries with `enabled == true` | 92 |
| Enabled entries scheduled every calendar day or more frequently | 68 |
| `openclaw cron list --json` | 0 jobs |
| `nextWakeAtMs` | `null` |

Interpretation: the 92 rows below are enabled configuration entries, but the
OpenClaw scheduler currently exposes no runnable jobs and no next wake. They
must not be described as proven active executions. Separately, 40 relevant
macOS launchd labels are currently loaded for Larry, ReelClaw, Capafy,
article/writer, shared marketing, and financial-report work. Their most recent
exit statuses include both successes and failures, and several execute scripts
under `~/.openclaw`.

## All 92 enabled store entries

An empty timezone means the entry has no explicit timezone.

| # | Job | Cron | Timezone |
|---:|---|---|---|
| 1 | `daily-memory` | `15 23 * * *` | Asia/Tokyo |
| 2 | `larry-anicca-en-1` | `35 16 * * *` | Asia/Tokyo |
| 3 | `factory-bp-revenue` | `0 22 * * *` | Asia/Tokyo |
| 4 | `factory-bp-efficiency` | `20 22 * * *` | Asia/Tokyo |
| 5 | `factory-bp-internal` | `40 22 * * *` | Asia/Tokyo |
| 6 | `larry-strategy-updater` | `10 5 * * *` | Asia/Tokyo |
| 7 | `reelclaw-anicca-en-card-2` | `30 21 * * *` | Asia/Tokyo |
| 8 | `reelclaw-honne-ja-1` | `10 10 * * *` | Asia/Tokyo |
| 9 | `yangmun-monk-evening` | `30 8 * * *` | Asia/Tokyo |
| 10 | `anicca-music-daily` | `0 4 * * *` | Asia/Tokyo |
| 11 | `4.7-slideshow-morning` | `0 9 * * *` | Asia/Tokyo |
| 12 | `daily-letter-sender` | `40 6 * * *` | Asia/Tokyo |
| 13 | `weekly-fresh-letter` | `50 8 * * 0` | Asia/Tokyo |
| 14 | `aniccaai-dashboard-refresh` | `0 5 * * *` | Asia/Tokyo |
| 15 | `accelerator-application-monthly` | `0 12 1 * *` | Asia/Tokyo |
| 16 | `anicca-music-stockmusic-batch-daily` | `40 4 * * *` | Asia/Tokyo |
| 17 | `yangmun-monk-noon` | `30 12 * * *` | — |
| 18 | `copy-viral-format-factory-3day` | `13 4 * * *` | Asia/Tokyo |
| 19 | `anicca-meetup-discover-daily` | `15 9 * * *` | Asia/Tokyo |
| 20 | `anicca-meetup-apply-tokyo-weekly` | `0 9 * * *` | Asia/Tokyo |
| 21 | `anicca-meetup-apply-sf-monthly` | `10 12 * * 0` | Asia/Tokyo |
| 22 | `anicca-comedy-skit-deliver-daily` | `5 7 * * *` | Asia/Tokyo |
| 23 | `app-reviews-daily` | `25 8 * * *` | Asia/Tokyo |
| 24 | `jsps-application-monthly` | `5 13 1 * *` | Asia/Tokyo |
| 25 | `naist-deadline-ical` | `25 7 * * *` | Asia/Tokyo |
| 26 | `tuning-skills-nightly` | `5 2 * * *` | Asia/Tokyo |
| 27 | `naist-funds-apply` | `40 9 * * *` | Asia/Tokyo |
| 28 | `naist-course-register` | `15 10 * 4-5,10-11 1-5` | Asia/Tokyo |
| 29 | `naist-homework-submit` | `10 14 * * *` | Asia/Tokyo |
| 30 | `naist-gcal-sync` | `0 13 * * 1` | Asia/Tokyo |
| 31 | `anicca-comedy-ogiri-practice-daily` | `5 4 * * *` | Asia/Tokyo |
| 32 | `comedy-live-discover-monthly` | `20 9 1 * *` | Asia/Tokyo |
| 33 | `comedy-live-schedule-publish` | `50 11 * * 1` | Asia/Tokyo |
| 34 | `comedy-tiktok-cross-post-daily` | `0 16 * * *` | Asia/Tokyo |
| 35 | `comedy-tokyo-mic-apply-weekly` | `5 9 * * 3` | Asia/Tokyo |
| 36 | `anicca-recruit-comedy-weekly` | `35 11 * * 2` | Asia/Tokyo |
| 37 | `anicca-comedy-weekly-book` | `10 8 * * 1` | Asia/Tokyo |
| 38 | `anicca-dentist-quarterly` | `5 9 1 2,5,8,11 *` | Asia/Tokyo |
| 39 | `anicca-haircut-quarterly` | `10 9 15 3,6,9,12 *` | Asia/Tokyo |
| 40 | `comedy-booking-en-dais-SF-monthly` | `0 8 1 * *` | Asia/Tokyo |
| 41 | `anicca-corey-prog-seo-weekly` | `10 13 * * 2` | Asia/Tokyo |
| 42 | `anicca-corey-cold-email-daily` | `35 12 * * *` | Asia/Tokyo |
| 43 | `anicca-seo-rank-monitor-daily` | `35 6 * * *` | Asia/Tokyo |
| 44 | `anicca-corey-ai-seo-cron` | `0 13 * * *` | Asia/Tokyo |
| 45 | `anicca-corey-schema-markup-cron` | `45 13 1 * *` | Asia/Tokyo |
| 46 | `anicca-corey-page-cro-cron` | `0 15 * * 4` | Asia/Tokyo |
| 47 | `naist-homework-fetch` | `0 7 * * *` | Asia/Tokyo |
| 48 | `auto-research-e2e` | `0 1 * * *` | Asia/Tokyo |
| 49 | `comedy-sf-apply-weekly` | `30 12 * * 0` | Asia/Tokyo |
| 50 | `connpass-lt-apply-daily` | `30 9 * * *` | Asia/Tokyo |
| 51 | `anicca-heartbeat` | `0 */6 * * *` | Asia/Tokyo |
| 52 | `anicca-event-bot-trigger` | `23 * * * *` | — |
| 53 | `attention-tracker-6h` | `0 */6 * * *` | — |
| 54 | `anicca-stage-daily` | `0 21 * * *` | Asia/Tokyo |
| 55 | `anicca-gcal-heal` | `0 5,17 * * *` | — |
| 56 | `anicca-travel-fill` | `0 5 * * *` | — |
| 57 | `anicca-fuel-broker` | `17 * * * *` | — |
| 58 | `anicca-schedule-template` | `0 4 * * *` | — |
| 59 | `anicca-wallet-balance` | `0 6 * * *` | Asia/Tokyo |
| 60 | `anicca-earn-bounty` | `0 */2 * * *` | Asia/Tokyo |
| 61 | `anicca-arrival-mail` | `*/5 * * * *` | Asia/Tokyo |
| 62 | `anicca-cold-email-reply` | `17 * * * *` | — |
| 63 | `anicca-cold-email-send` | `37 9 * * *` | — |
| 64 | `anicca-product-growth` | `23 10 * * *` | — |
| 65 | `anicca-aie-consulting` | `23 12 * * 1` | Asia/Tokyo |
| 66 | `anicca-aie-product` | `37 16 * * 5` | Asia/Tokyo |
| 67 | `anicca-exec-guard` | `33 * * * *` | — |
| 68 | `anicca-mail-triage` | `7 * * * *` | Asia/Tokyo |
| 69 | `anicca-health` | `0 * * * *` | — |
| 70 | `anicca-cron-harvester` | `19 * * * *` | — |
| 71 | `anicca-watch-sweep` | `47 * * * *` | — |
| 72 | `anicca-night-fill` | `13 21 * * *` | Asia/Tokyo |
| 73 | `anicca-cron-auto-disable` | `11 3 * * *` | Asia/Tokyo |
| 74 | `anicca-pattern-promoter` | `31 4 * * *` | Asia/Tokyo |
| 75 | `anicca-backlink-reddit-weekly` | `0 10 * * 1,3,5` | Asia/Tokyo |
| 76 | `anicca-backlink-hn-biweekly` | `0 9 1-7,15-21 * 1` | Asia/Tokyo |
| 77 | `anicca-backlink-ih-weekly` | `0 11 * * 3` | Asia/Tokyo |
| 78 | `contra-daily` | `53 22 * * *` | — |
| 79 | `anicca-account-health-daily` | `30 10 * * *` | Asia/Tokyo |
| 80 | `anicca-postiz-health-daily` | `0 6 * * *` | Asia/Tokyo |
| 81 | `anicca-cron-doctor` | `0 3 * * *` | Asia/Tokyo |
| 82 | `anicca-booking-daily` | `0 6,18 * * *` | Asia/Tokyo |
| 83 | `anicca-capafy-daily-publish` | `0 9 * * *` | Asia/Tokyo |
| 84 | `anicca-credit-monitor` | `0 9 * * *` | Asia/Tokyo |
| 85 | `anicca-cfo-sync` | `0 5 1 * *` | Asia/Tokyo |
| 86 | `anicca-config-canary-daily` | `30 3 * * *` | Asia/Tokyo |
| 87 | `agentmemory-mcp-cleanup` | `*/30 * * * *` | Asia/Tokyo |
| 88 | `larry-anicca-ja-v2` | `30 8 * * *` | Asia/Tokyo |
| 89 | `anicca-life-ask` | `0 21 * * *` | — |
| 90 | `anicca-life-notify-scan` | `*/10 8-22 * * *` | Asia/Tokyo |
| 91 | `anicca-life-notify-poll` | `*/5 8-22 * * *` | Asia/Tokyo |
| 92 | `fastlane-affirmation-daily-post` | `0 8 * * *` | Asia/Tokyo |

## Revenue-relevant OpenClaw entries

| Family | Enabled store entries |
|---|---|
| Larry/slideshows | `larry-anicca-en-1`, `larry-strategy-updater`, `4.7-slideshow-morning`, `larry-anicca-ja-v2`, `copy-viral-format-factory-3day` |
| ReelClaw/video | `reelclaw-anicca-en-card-2`, `reelclaw-honne-ja-1` |
| Mobile metrics/reviews | `aniccaai-dashboard-refresh`, `app-reviews-daily`, `anicca-product-growth` |
| Capafy | `anicca-capafy-daily-publish` |
| Finance/earn | `factory-bp-revenue`, `factory-bp-efficiency`, `factory-bp-internal`, `anicca-wallet-balance`, `anicca-earn-bounty`, `anicca-credit-monitor`, `anicca-cfo-sync`, `contra-daily` |
| Life Manager | `anicca-life-ask`, `anicca-life-notify-scan`, `anicca-life-notify-poll` |

## ReelClaw/Larry launchd dependency

ReelClaw is still local and OpenClaw-dependent even though only two
ReelClaw-named entries appear in the OpenClaw store. macOS launchd separately
loads the broader production family.

| Family | launchd cadence observed |
|---|---|
| ReelClaw Anicca EN | card 11:00, 00:00, 17:23; widget 09:30, 07:00, 21:00 |
| ReelClaw Anicca JA | card 04:47, 12:00, 20:00; widget 08:00, 22:37, 16:00 |
| ReelClaw Honne EN | 07:00, 11:00, 20:30 |
| ReelClaw Honne JA | 08:30, 12:30, 21:30 |
| Larry Anicca EN/JA | multiple daily posts between 07:00 and 20:45 |
| Larry learning/library | strategy 05:10; library fill 03:00; library posts about 16:30 |

These launchd jobs call scripts or state in `~/.openclaw`,
`/Users/anicca/profitable-claude`, or other local paths. They are therefore
part of the migration scope even when OpenClaw cron itself is inert.
