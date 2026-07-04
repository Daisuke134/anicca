# Slot: `self/coordinate` (status: live)

Built 2026-07-05 to close spec §5.1 Channel A (bot2bot info-sharing, #9/H6): wires the already-tested
`skills/_shared/lib/bot2bot.py` (post/poll/annotate_pr/auto_merge) into an actual `run_skill` slot so
instances can share and read strategy lessons, not just have the library sit unused.

## Contract
- Entrypoint: `run.sh`
- Args (`ANICCA_ARGS` JSON): `{"note": "<lesson>", "topic": "<earn-slot name>"}`. `note` present =
  share; absent = poll `topic`'s (default `"general"`) open lessons.
- Live E2E-verified 2026-07-05: a real `bot2bot-lesson` issue was filed and then read back via poll
  from the SAME process (see commit for the issue URL).
