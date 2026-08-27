---
name: anicca-monkey-watchdog
description: |
  Out-of-band launchd watchdog — monitors 3 openclaw monkeys
  (doctor / janitor / conformity)。 24h 内 success run 無し → Slack alert
  + 即 fire 試行。 launchd 自体 が macOS 起動時 自動 load される為、
  openclaw gateway down でも 動く (= 循環依存 回避)。
  Reference pattern: Netflix Atlas (= Simian Army external monitor)。
metadata:
  type: meta-monitor
  responsibility: monitor_monkeys
  runtime: launchd
  schedule: "0 4 * * *"
  pin_to_infra: true
  do_not_delete: true
---
