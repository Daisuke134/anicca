# Posting Targets

## Account Mapping

| Lang | Platform | Account | Integration ID |
|------|----------|---------|----------------|
| EN | TikTok | `anicca.en7` | `cmmtt62wq01lqn50yehk1f6dy` |
| EN | YouTube | `@anicca-ai` | `cmmzukbkw04ulp30yfvijrwio` |
| EN | Instagram | `anicca.ai` | `cmmzzg2es0539p30ycb94ayx0` |
| JA | TikTok | `aniccajp6` | `cmmytdj1101w1p30ytx8lj0fw` |
| JA | Instagram | `anicca.jp` | `cmmzujxpa04ujp30yxqpg1vci` |

## Postiz API

| Item | Value |
|------|-------|
| CLI | `/opt/homebrew/bin/postiz` v2.0.12 |
| API Key | `~/.config/mobileapp-builder/.env` → `POSTIZ_API_KEY` |
| Rate Limit | 30 req/hour |
| Auth Header | `Authorization: ${POSTIZ_API_KEY}` (NO Bearer prefix) |
| Per cron run | upload 6 + create 6 = 12 req |

## Per-Run Posting Matrix

| Lang | TikTok | YouTube | Instagram | Videos | Posts |
|------|--------|---------|-----------|--------|-------|
| EN | 3 | 3 | 3 | 3 | 9 |
| JA | 3 | — | 3 | 3 | 6 |
| **Total** | | | | **6** | **15** |
