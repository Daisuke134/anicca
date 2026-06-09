# daily-report

Hermes-native daily Anicca digest. Fires at 06:00 JST via `hermes cron`, reads local CFO + heartbeat + friction state, calls Hermes once for 3 substantive bullets (≤$0.01 budget), and sends via AgentMail from `anicca-genesis@agentmail.to`. Replaces the OpenClaw `anicca-report` skill for the Hermes runtime; the OpenClaw version remains co-resident until LAUNCH-GATE #341 flips ⑤d to Hermes-only. Wired by `docs/superpowers/plans/2026-06-04-daily-report.md`.
