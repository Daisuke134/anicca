# donation-v2-archive

This is the **agent-{{profile.lateness.stakeholders.channel}} rail** of Anicca's autonomous philanthropy — kept
here for charities that are NOT on Stripe Connect.

The active `~/.openclaw/skills/donation/` is now the v1-spec rebuild on the
**Stripe Connect transfers.create** rail (charity must onboard as a Stripe
Connected Account).

## Why two rails?

Most US charities accept donations via Stripe Checkout but do NOT have a
Stripe **Connect** account, which is what `transfers.create` requires. The
charity has to actively onboard with us as a connected account before the
Stripe rail can wire money to them.

For charities that won't onboard, the agent-{{profile.lateness.stakeholders.channel}} rail is a fallback:
it drives the charity's existing donate page with a saved card via the
Vercel Agent Browser CLI (`/opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}`).

## Structure preserved

- `SKILL.md` — full v2 spec (install hook + monthly cron)
- `scripts/run.sh` — dispatch on `$MODE`
- `scripts/install.sh` — one-shot discovery + registration + first donation
- `scripts/monthly.sh` — monthly recurring donation via saved card
- `scripts/lib/agent_{{profile.lateness.stakeholders.channel}}.sh` — agent-{{profile.lateness.stakeholders.channel}} CLI wrapper
- `scripts/lib/ledger.sh` — donation-history.jsonl writer
- `data/`, `_backups/` — preserved as-is

## To re-activate this rail for a specific charity

1. Set `donation.rail = "agent-{{profile.lateness.stakeholders.channel}}"` in `recipients.json` for that recipient
2. Add the entry to `~/.openclaw/state/donation/installed.json` so the
   monthly cron knows which rail to use per recipient
3. Re-point the cron payload to invoke `MODE=monthly bash
   ~/.openclaw/skills/donation-v2-archive/scripts/run.sh`

## Why archived not deleted

Spec instructed: archive, do not delete. The agent-{{profile.lateness.stakeholders.channel}} approach is the
only payment path for charities that don't or won't run Stripe Connect, so
this code is still load-bearing for that case.
