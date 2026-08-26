---
name: connector
description: Fill a rolling 28-day calendar with verified Tokyo events, prioritizing Luma, safe connpass discovery, and lightning talks.
---

# Connector

Use this skill when a user wants Life Manager to discover, rank, register, calendar, and report relevant events.

Read [README.md](README.md) before installation and [WORKER-CONTRACT.md](WORKER-CONTRACT.md) before changing runtime behavior. Keep one hourly native owner. Prefer YC hackathons, open lightning talks, AI, crypto, then startup events. Luma is actionable; connpass remains a read-only official-API source followed by a Telegram action handoff unless explicit provider permission is recorded.

Never package credentials, identity files, browser state, runtime state, or provider receipts. Never claim registration without provider readback, Calendar readback, Telegram provider IDs, and a durable evidence bundle.
