---
name: alpaca-investment
description: Run one bounded Life Manager Alpaca investment pass and exit.
---

# Alpaca Investment

Run one paper-only investment pass. Observe official broker state before deciding, allow the model to choose
`TRADE` or `NO_TRADE`, enforce risk and duplicate fences in deterministic code, reconcile every uncertain effect
by stable client order ID, persist receipts outside the release, report the official result to Telegram, and
exit. Never describe paper P&L as revenue or silently switch to live capital.
