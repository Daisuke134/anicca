# 10f daily self-build evidence — real Day 1/7

## Result

Atomic 10f is started and remains pending at one distinct real day out of seven. The existing
feedback/error intake, `lm:type:self-heal` issue queue, and D0 fresh-agent worker are reused. No
second intake queue, agent, account, or deployment service is introduced.

The bounded daily runner adds:

- one exclusive mode-0600 lock, with dead-owner stale recovery and live-owner refusal;
- a 25-minute hard child deadline with process-group termination;
- one closed-schema, mode-0600 append-only JSONL receipt for every completed scheduled pass;
- exact issue/PR or allowlisted no-op/failure reason, with arbitrary provider text discarded;
- an atomic `seven-day-status.json` that counts only distinct consecutive `Asia/Tokyo` dates.

## Real provider and runtime readback

| Evidence | Readback |
|---|---|
| Day | `2026-07-24` (`1/7`, not done) |
| Source issue | [#1090](https://github.com/Daisuke134/life-manager/issues/1090), OPEN, `lm:type:self-heal` |
| Fresh-agent commit | `b649393c92203c30c0edb5a4c6c392ca8508042b` |
| Auto-created PR | [#1094](https://github.com/Daisuke134/life-manager/pull/1094), OPEN |
| Daily receipt | `outcome=pr_open`, `reason=pr_created`, `duration_ms=147499` |
| Telegram report | real message id `3390` |
| launchd | `ai.anicca.life-manager-dev`, `04:10`, program=`.../life-manager-dev-daily.js` |

The fresh worker observes RED before implementation, commits the minimal controlled-health
regression fix, and the caller independently passes the full test/eval/privacy gates before
opening PR #1094. The daily runner itself does not merge or deploy; blocked 10e cannot be bypassed.

## Verification

- Focused TDD: initial RED `0/3`; GREEN `7/7`.
- Corrective seven-day delegation test: RED `4/5`; GREEN `7/7`.
- Full `npm test`: exit `0`.
- Evals: calendar `21/21`, late `12/12`, context `12/12`, score `27/27`, intent `18/18`,
  mental `15/15`, physical `12/12`.
- Panel privacy: `api=177`, `browser=63`, `recipes=19`, `channels=9`.
- `shellcheck` passes and the installed plist passes `plutil -lint`.
- Changed-path gitleaks and added-line secret/PII scans report zero findings.

The timeout test starts a real child `sleep`, reaches the hard deadline, terminates its process
group, records `timed_out/hard_timeout`, and releases the exact lock. The stale-lock test uses a
real mode-0600 lock file: a dead stale PID is recovered, while a live PID is never stolen.

## Best-practice sources

- Apple, [Creating Launch Daemons and Agents](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html):
  “you can specify a calendar-based interval.” This is the basis for the single 04:10
  `StartCalendarInterval`.
- GitHub, [Control workflow concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency):
  “only a single job or workflow using the same concurrency group will run at a time.” The local
  exclusive lock applies the same single-owner invariant.
- Node.js, [File system API](https://nodejs.org/api/fs.html#fsappendfilepath-data-options-callback):
  “Asynchronously append data to a file, creating the file if it does not yet exist.” The ledger
  uses append semantics and never rewrites historical receipts.

## Remaining gate

Six additional distinct real dates must be produced by the installed loop. Duplicate same-day
runs, fixture dates, simulation, and backfill do not count. The loop writes its own seven-day
readiness status, so this session does not wait or mark the row done early.
