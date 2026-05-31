# SKILL_CATALOG — install individual Anicca skills into your existing harness

You already run OpenClaw, Hermes, or Claude-P with your own
CONSTITUTION / SOUL / persona, and you don't want the full anicca-oss
distro. Good — you can pull in just the skills you want.

This is the **Phase E** install path from the master spec — works
alongside (not on top of) your existing setup.

---

## Catalog

| Skill | Purpose | Hard deps | Soft deps |
|---|---|---|---|
| `anicca-life-manager` | wake-call + lateness + RELENTLESS state machine | Twilio, Gemini API, Pipecat phone daemon, Telegram bot daemon, gog | — |
| `anicca-travel-fill` | insert 🚆 移動 blocks between location-changing events | gog, Google Maps API | profile.identity.homeAddress |
| `anicca-gcal-heal` | PATCH empty event.location fields (15-min) | gog | profile.identity.homeAddress |
| `anicca-report` | daily 18:00 + weekly Mon 09:00 Gmail digest | gog, cfo state file | Slack token |
| `anicca-fuel-broker` | hourly runway-low / self-fund / first-payout mailer | gog, cfo state file | wallet address |
| `anicca-schedule-template` | default-day filler for empty calendars | gog | profile.alarm.wakeTime |
| `anicca-goal-learner` | weekly proactive drift report vs ideal_state[] | gog | profile.identity.goals.ideal_state |
| `anicca-payout-wallet` | Tier 3 payout = USDC direct to user wallet | cdp CLI | broker.payout_destination |

Each skill is standalone — no skill depends on another at runtime. They
all expect `~/.openclaw/.env` for shared secrets and
`~/.openclaw/identity/profile.json` for the user profile.

---

## OpenClaw

```bash
openclaw skill install \
  https://github.com/Daisuke134/anicca-oss \
  --path skills/anicca-life-manager

openclaw cron create \
  --name anicca-life-manager \
  --cron "*/5 * * * *" \
  --message "exec で次を実行: bash ~/.openclaw/skills/anicca-life-manager/scripts/run.sh"
```

Repeat for each skill in the catalog. The cron schedule for each is
documented at the top of its `SKILL.md`.

---

## Hermes

```bash
hermes skill install \
  github.com/Daisuke134/anicca-oss#skills/anicca-life-manager
```

(Hermes uses its own cron registration; consult Hermes docs for the
exact verb. The skill's `cron.toml` (if present) declares the schedule.)

---

## Claude-P

There is no per-skill loader for Claude-P (claude -p). Instead, point
your heartbeat script at the skill's `run.sh`:

```bash
# in your heartbeat-beat.sh
bash "$HOME/.openclaw/skills/anicca-life-manager/scripts/run.sh"
```

Or symlink the skill into your existing skills dir:

```bash
ln -sf $PWD/anicca-life-manager ~/.openclaw/skills/anicca-life-manager
```

---

## What stays yours

When you install only individual skills:

- Your CONSTITUTION.md is untouched
- Your SOUL.md is untouched
- Your existing persona / agent identity is untouched
- These skills are mannequins inside YOUR harness — they don't claim a
  voice, they just execute their narrow job

The Anicca personality only manifests if you opt into installing the
Pipecat phone bot daemon (`outbound/bot.py`), which has its own
system_instruction. If you don't install that, your existing voice
agent answers the lateness-mode dialout instead.

---

## Removing a skill

```bash
openclaw cron disable <cron-id>
rm -rf ~/.openclaw/skills/anicca-<name>
```

State directories are deleted along with the skill. The shared `.env`
and `profile.json` are preserved (they belong to you).
