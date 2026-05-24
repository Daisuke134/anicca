---
name: tiktok-ad-tracker-monitor
description: Track TikTok ad activity and monitor advertiser changes using PipiAds tools for TikTok ad discovery and Facebook-based monitoring workflows.
metadata:
  openclaw:
    requires:
      env:
        - PIPIADS_API_KEY
      bins:
        - npm
    install:
      command: npm
      args:
        - install
        - -g
        - "pipiads-mcp-server@1.0.3"
    primaryEnv: PIPIADS_API_KEY
    emoji: "📊"
    homepage: https://www.pipiads.com
    mcpServers:
      pipiads:
        command: pipiads-mcp-server
        env:
          PIPIADS_API_KEY: "{{PIPIADS_API_KEY}}"
---

# TikTok Ad Tracker & Monitor

Use this skill to research TikTok ads and manage ongoing monitoring workflows.

## Setup

1. Visit the official website at [https://pipiads.com/](https://pipiads.com/) to view real-time dashboard data and product UI.
2. Visit [https://www.pipispy.com/](https://www.pipispy.com/) to get your API key and manage billing/recharge.
3. Set the environment variable: `PIPIADS_API_KEY`

## When to Use

- Find trending TikTok ads, recurring creatives, and long-running winners
- Track advertiser changes over time with monitor tasks
- Review monitored ads, landing pages, products, and copy changes
- Analyze creative hooks, angles, engagement, and delivery duration

## When NOT to Use

- The user only wants Facebook-only ad library research
- The user wants TikTok Shop product/store analytics without ad research
- The user wants general market research outside PipiAds data

## Core Tools

### TikTok Ad Research
- `search_ads` — Search ads and narrow to TikTok with platform filters
- `get_ad_detail` — Inspect a specific ad in detail
- `search_advertisers` — Find advertisers behind TikTok campaigns
- `get_advertiser_detail` — Inspect advertiser details

### Monitoring
- `search_fb_advertisers` — Find advertiser entry points for monitor setup
- `create_monitor_task` — Create a monitoring task
- `list_monitor_tasks` — List existing monitor tasks
- `get_monitor_task_detail` — View task details
- `get_monitor_board` — Review monitoring dashboard
- `get_monitor_realtime_overview` — Real-time task overview
- `get_monitor_daily_overview` — Daily performance overview
- `get_monitor_ad_list` — Review monitored ads
- `get_monitor_ad_detail` — Review a monitored ad in detail
- `get_monitor_latest_products` — See newly found products
- `get_monitor_landing_page_list` — Review landing pages
- `cancel_monitor_task` — Stop a monitoring task

## Recommended Workflow

1. Start with `search_ads` and constrain to TikTok, region, and time range.
2. Use `get_ad_detail` to inspect the strongest creatives.
3. If the user wants ongoing tracking, find the advertiser and use `create_monitor_task`.
4. Use monitor overview and ad list tools to review changes over time.

## Cost Awareness

Each API call consumes credits from your PipiAds account:
- **List/Search**: 1 credit per result returned
- **Detail**: 1 credit per request (free if queried within 3 days)

Prefer narrow TikTok searches before creating broad monitor workflows.
