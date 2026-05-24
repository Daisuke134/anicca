# Cron Scheduling Patterns

Common scheduling patterns for AI workflow automation.

## Basic Patterns

| Pattern | Schedule | Description |
|---------|----------|-------------|
| Every hour | `0 * * * *` | Hourly execution |
| Every day at 9am | `0 9 * * *` | Daily morning |
| Every Monday 9am | `0 9 * * 1` | Weekly start |
| First of month | `0 9 1 * *` | Monthly report |
| Every 6 hours | `0 */6 * * *` | Periodic check |

## Use Case Patterns

### Content Distribution
```yaml
schedule: "0 10,14,18 * * *"  # 10am, 2pm, 6pm
timezone: "Asia/Shanghai"
task: "Publish scheduled content"
```

### Data Sync
```yaml
schedule: "*/30 * * * *"  # Every 30 minutes
task: "Sync data from API"
```

### Report Generation
```yaml
schedule: "0 18 * * 5"  # Friday 6pm
task: "Generate weekly report"
```

### Monitoring
```yaml
schedule: "*/15 * * * *"  # Every 15 minutes
task: "Check service health"
```

## OpenClaw Cron Syntax

Use the `cron` skill to create scheduled tasks:

```json
{
  "name": "daily-{{profile.lateness.stakeholders.channel}}-check",
  "schedule": { "kind": "cron", "expr": "0 9 * * *" },
  "payload": { "kind": "agentTurn", "message": "Check inbox and summarize" },
  "sessionTarget": "isolated"
}
```

## Timezone Considerations

- Default timezone: UTC
- Specify timezone in schedule: `{"kind": "cron", "expr": "0 9 * * *", "tz": "Asia/Shanghai"}`
- Common timezones:
  - `Asia/Shanghai` (Beijing, +8)
  - `America/New_York` (EST, -5)
  - `Europe/London` (GMT)
