---
name: anicca-report
description: |
  Daily 18:00 JST report + weekly Monday 09:00 report sent to the user via
  Gmail (= Polsia-style: earned / spent / wallet / runway / MRR / today did
  / pending). Gmail is the default because every onboarded user is OAuth'd
  there; Slack is optional.

  Composed entirely from local state — no LLM call required, so it survives
  fuel outages. The report is the single source of "what Anicca did" the
  user sees on Day N.
metadata:
  tags: report, daily, gmail
  requires:
    bins: [python3, gog]
    env: [GOG_ACCOUNT, GOG_KEYRING_PASSWORD]
---

# anicca-report

Daily ASCII report mailed to the user.

## Data sources

| where | what |
|---|---|
| `~/.openclaw/skills/cfo-core/data/anicca-cfo.json` | earned / spent / wallet / runway / MRR |
| `~/.openclaw/skills/anicca-life-manager/state/run.log` | lateness calls fired today |
| `~/.openclaw/skills/anicca-life-manager/state/active_call_loop.json` | call lock state |
| `gog calendar events list` next 24 h | tomorrow's events preview |

## Output

Subject (daily): `[Anicca] Day N: $X earned today, $Y spent — wallet $Z (R days runway)`
Subject (weekly): `[Anicca] Week N: net +$X, MRR Y, wallet healthy`

Body sections:
- Earned / Spent / Net (today)
- Wallet / Runway / MRR
- What I did (= lateness calls fired today with SID)
- Pending (= awaiting reply / blocked)
- Next 24h events preview

## Cron

- daily: `0 18 * * *` (= 18:00 JST)
- weekly: `0 9 * * 1` (= Monday 09:00)
