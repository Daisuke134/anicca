# Eventbrite Evidence Adapter Official Wake Plan

**Goal:** Exercise the pushed Eventbrite evidence-store, minimal-evidence, and Calendar-transport adapters through one canonical production wake without weakening candidate safety.

**Executor:** Existing loaded `ai.anicca.mr-bot-connector-native` only. Trigger once with `launchctl kickstart`; do not invoke provider/browser scripts or a second executor manually.

## Baseline

- Clean/pushed HEAD `9b79a8ad1`, upstream `0/0`.
- Native label loaded, not running, runs 1, daily 09:00; process 0; lock absent; CDP pages 4.
- Bundles 13, reports 133, report deliveries 145, actions 1492.
- Provider audits Luma/Connpass/Peatix/Meetup/Doorkeeper/Eventbrite = `134/57/50/4/6/3`.
- Latest Eventbrite audit was `188/0/0/0/0`; a real bundle is not predicted.

## Acceptance

1. Trigger exact one wake and watch the same label to terminal for at most 12 minutes.
2. If a new eligible Calendar-free Eventbrite candidate registers, require exact Eventbrite provider receipt/artifact, Calendar create/readback, PNG SHA, positive Telegram message/photo IDs, and one `applied_bundle` lineage.
3. If eligible remains 0, require truthful Eventbrite audit, Eventbrite external write 0, bundle count unchanged, positive every-wake Telegram delivery, no false success, process/lock/owned-target cleanup, unrelated CDP pages preserved, and legacy labels unloaded.
4. No second wake, schedule change, manual browser/provider action, paid-event gate weakening, or synthetic success.
