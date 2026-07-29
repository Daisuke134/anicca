# JOB-INBOX-MESSAGE-CHECKPOINT-10L: Follow-ups Inside Seen Threads

**Goal:** Replace permanent Gmail thread-level dedupe with immutable message-level
checkpoints so a later recruiter reply, assessment, or interview in an already-seen
thread is processed exactly once.

**Observed gap:** Production `inbox-seen.json` contains three thread IDs. Every
current thread has one message and zero messages newer than the checkpoint mtime, so
an exact migration can happen now without replay or loss. The current scanner drops
the whole thread forever, which would also drop any future message that Gmail adds
to that conversation.

## Evidence and adopted practices

| Decision | Source | Core quote |
|---|---|---|
| Dedupe messages, not the containing conversation | [Gmail API — Message](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages) | “The immutable ID of the message.” |
| Treat a thread as a container whose members can grow | [Gmail API — Thread](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.threads) | “A collection of messages representing a conversation.” / “The list of messages in the thread.” |
| Bootstrap once, then consume only later changes | [Gmail API — Synchronize clients](https://developers.google.com/workspace/gmail/api/guides/sync) | “Full synchronization is required the first time” and partial sync returns records newer than `startHistoryId`. |

Three direct English/Japanese implementation searches returned no reusable code.
The Gmail full/partial synchronization contract is therefore the closest primary
practice. This increment uses the existing bounded recent-thread query as its full
sync and immutable message IDs as the durable incremental checkpoint; a later
history-ID optimization must preserve the same contract.

## TDD execution

- [x] RED: prove a post-checkpoint message in a legacy-seen thread is currently
  dropped.
- [x] GREEN: expand selected recruiting threads into sanitized messages and emit
  only unseen immutable message IDs.
- [x] RED/GREEN: migrate legacy thread IDs using the checkpoint mtime so old
  messages are bootstrapped without hiding newer messages.
- [x] Require processed message IDs to be an exact subset of the current scan and
  require processed thread IDs to match their message-to-thread mapping.
- [x] Make deterministic confirmation reconciliation acknowledge only its exact
  message while future messages in the same thread remain visible.
- [x] Run all 176 job-loop and 10 runner tests plus OSS/PII/shell verification.
- [ ] Push, pass all GitHub checks, merge, sync the canonical checkout, and kick
  the existing inbox LaunchAgent.
- [ ] Prove the production v1→v2 checkpoint migration replays zero old messages,
  preserves zero current loss, and keeps later same-thread mail observable.
