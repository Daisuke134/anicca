---
name: calendar-health-check
type: permanent
schedule: "0 4 * * 5"
schedule_ist: "09:30 IST every Friday"
timezone: Asia/Kolkata
purpose: Check content calendar health — ensure 14 days ahead pipeline
fire_once: false
auto_delete: false
status: active
---
# Calendar Health Check — Permanent
Fires every Friday at 09:30 IST.
Check: how many days of approved/scheduled content exist per platform.
< 14 days → advisory to owner with content suggestions.
THIS FILE MUST NEVER BE DELETED.
