---
name: invest
description: Show the current Life Manager Investment Loop setup or account status.
user-invocable: true
---

# Investment Loop status

When the user invokes `/invest`, run this command exactly once:

```bash
python3 "$HOME/loops/current/skills/anicca-life-manager/scripts/investment_status.py"
```

Return its stdout verbatim. Do not add a greeting, explanation, profit promise, or `Codex:::` prefix.
The command is read-only. It reports the existing account-review and paper-loop receipts. If no account receipt
exists, its official Alpaca signup URL is the only onboarding action shown.
