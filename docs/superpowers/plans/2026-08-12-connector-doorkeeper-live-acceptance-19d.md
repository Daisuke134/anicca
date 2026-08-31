# Doorkeeper Official Live Acceptance Plan

> **For execution:** Use the already-loaded canonical launchd owner. Do not invoke provider scripts, browser actions, or a second executor manually.

**Goal:** Exercise the pushed Doorkeeper evidence-store, minimal-evidence, and Calendar-transport chain through one real production wake, accepting either a complete real `applied_bundle` or a truthful no-effect audit when no Calendar-free candidate exists.

**Architecture:** Trigger exact label `ai.anicca.mr-bot-connector-native` once with `launchctl kickstart`. The existing official `skills/connector/run.sh` owns the one browser rail, provider sequence, readback, Calendar, PNG, Telegram, durable state, cleanup, and terminal report. Observe append-only state and process lifecycle only.

**Tech Stack:** launchd, canonical Connector entrypoint, shared CDP `:9222`, gog Calendar, Telegram delivery, JSONL durable state.

## Preconditions and baseline

- Pushed clean HEAD `4032eea1e`, upstream ahead/behind `0/0`.
- Native label loaded, `not running`, runs `0`, 09:00 daily; healthcheck/healer-shadow/host-bridge all unloaded.
- Connector process `0`, lock absent, current CDP pages `4`.
- Durable baseline: bundles `13`, wake reports `132`, report deliveries `144`, actions `1448`.
- Provider audits Luma/Connpass/Peatix/Meetup/Doorkeeper/Eventbrite = `133/56/49/4/5/2`.
- Latest Doorkeeper audit = `100 discovered / 12 within window / 4 eligible / 0 Calendar-free / 0 selected`.

## Execution

1. Recheck pushed/clean, process 0, lock absent, label not running, and no concurrent owner.
2. Run exact one `launchctl kickstart gui/$(id -u)/ai.anicca.mr-bot-connector-native` without `-k`.
3. Watch the same label/process/state until terminal exit, with a hard observation bound of 12 minutes. Do not trigger a second wake.
4. Compare append-only counts and inspect the new wake/report/delivery/provider audits/bundle, then recheck process 0, lock absent, owned target cleanup, unrelated CDP page preservation, and legacy labels unloaded.

## Acceptance

- If a Calendar-free Doorkeeper candidate exists and provider readback is `registered`, require one exact lineage containing provider receipt/artifact, Calendar create plus independent readback, PNG SHA-256, positive Telegram message/photo IDs, and one durable Doorkeeper `applied_bundle`. Duplicate Submit/Calendar/Telegram effects must be 0 on recovery/reuse.
- If Doorkeeper again has Calendar-free `0`, accept only a durable truthful audit, Doorkeeper external write 0, normal continuation to Eventbrite, positive every-wake Telegram delivery, exact cleanup, and a terminal status that does not claim application success.
- Any missing dependency, ambiguous effect, duplicate owner, circuit-open before Doorkeeper, stale lock, leaked target, or success without complete bundle is failure and becomes the next repair slice. Do not weaken Calendar conflict or paid-event safety gates.
