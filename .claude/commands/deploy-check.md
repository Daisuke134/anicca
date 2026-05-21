---
description: Run test → build → device/simulator deployment check
model: haiku
---
# Deploy Check

Run the full deployment verification pipeline:

1. Use the Task tool to invoke the `deploy-checker` agent
2. The agent runs unit tests, Maestro E2E (if UI changed), and builds
3. Results are reported in table format
