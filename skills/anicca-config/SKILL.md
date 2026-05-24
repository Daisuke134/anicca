---
name: anicca-config
description: The single source of truth writer for Anicca's per-user config. Use whenever the user gives personal info (work/personal {{profile.lateness.stakeholders.channel}}, home address, school/student id, social handle or account id, goals, payment processor id) or a new API key/token/secret. Routes EVERY write to the two canonical files — secrets to .env, personal data to identity/profile.json (schema-validated) — so config never scatters and never leaks. Other skills only READ (via _shared/lib/profile.sh); this skill is the only WRITER.
---

# anicca-config — the only writer of .env + profile.json

The contract (see `identity/README.md`): per-user data lives in exactly two
places, and **only this skill writes them**. This prevents config scatter and
keeps the OSS litmus true ("could publish right now without leaking creds").

| Kind of value | Goes to | Command |
|---|---|---|
| 🔑 secret (API key, token, password) | `$ANICCA_HOME/.env` | `bash scripts/set-env.sh KEY "value"` |
| 👤 personal ({{profile.lateness.stakeholders.channel}}, address, school, social id, goals) | `$ANICCA_HOME/identity/profile.json` | `python3 scripts/set-profile.py <dot.path> "value"` |
| 💳 payment | `profile.payment.stripeCustomerId` (NEVER raw card) | `python3 scripts/set-profile.py payment.stripeCustomerId "cus_…"` |

## When to use
The moment the user states a fact about themselves or hands over a credential,
**write it once to the canonical place** instead of remembering it ad-hoc or
hardcoding it in another skill.

## How
```bash
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"   # from .env

# personal data (validated against identity/profile.schema.json before write)
python3 ~/.openclaw/skills/anicca-config/scripts/set-profile.py {{profile.lateness.stakeholders.toField}} "you@work.com"
python3 ~/.openclaw/skills/anicca-config/scripts/set-profile.py identity.homeAddress "City, Country"
# arrays/objects via --json:
python3 ~/.openclaw/skills/anicca-config/scripts/set-profile.py social.tiktok --json '[{"handle":"x","postizIntegrationId":"cm..","purpose":"main","postMode":"draft"}]'

# secret
bash ~/.openclaw/skills/anicca-config/scripts/set-env.sh POSTIZ_API_KEY "…"
```

## Rules
1. `set-profile.py` validates the WHOLE profile against the schema and **refuses
   to write if invalid** (atomic, 0600). Add a field to the schema first if it's new.
2. `set-env.sh` upserts (no duplicate keys), keeps `.env` at 0600, never echoes the value.
3. Reading is NOT this skill's job — skills read via `_shared/lib/profile.sh`
   (`profile '.{{profile.lateness.stakeholders.toField}}'`) or `$ENV_VAR`.
4. Never write personal data or secrets anywhere else. One writer, two files.
