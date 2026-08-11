# Connector Meetup discovery-audit persistence plan

## Goal

Persist the existing privacy-safe five-count Meetup discovery audit so an official no-effect wake proves whether discovery observed, normalized, filtered, and Calendar-blocked candidates.

## Measured evidence

- Official wake `wake-698594817b79bbe91ab869a5` reused all current Peatix bundles, then executed Meetup provider discovery for 48,171 ms on the same owned rail. It returned no candidate and completed `existing_bundles_reused` with positive Telegram ID `11483`.
- `createMinimalProductionDependencies` already supplies `operations.recordMeetupDiscoveryAudit || noop`, but `createMinimalProductionOperations` exposes only Luma, Connpass, and Peatix audit writers. No Meetup audit file exists.
- Isolated default Meetup workflow with the real Calendar measured exactly `14/12/12/1/0` for observed/normalized/window/free-open/calendar-free and candidate count zero. The only strict free event overlaps an existing timed Connector Calendar event, so the skip is correct.

## Ponytail full gate

- Copy/tweak the existing Peatix aggregate-audit writer and reuse `safeDiscoveryAudit`, `append`, mode 0600, wake ID, and timestamp validation.
- Change only operations production/test. Add no provider query, browser action, candidate data, URL, title, event ID, Calendar logic, state schema version, retry, schedule, or new module.
- Persist aggregate integer counts only to `meetup-discovery-audits.jsonl`.

## Luna implementation slice

Luna owns only:

1. `apps/life-manager/lib/connector-minimal-operations.test.js`
2. `apps/life-manager/lib/connector-minimal-operations.js`

Soft target: 2 files; production +4–8 LOC; tests +30–45 LOC.

### RED

1. `recordMeetupDiscoveryAudit` is callable and writes exactly one mode-0600 JSONL row with schema version, wake ID, five counts, and exact recorded time.
2. Invalid monotonic counts reject without appending a second row.
3. Persisted bytes contain no URL, event ID, title, profile, ticket, auth, or private value.
4. Existing Luma/Connpass/Peatix audit and report/action operations remain unchanged.

### GREEN

- Add `meetup-discovery-audits.jsonl` beside the three existing files.
- Add one writer using the existing safe validator and exact timestamp.
- Export that writer in the frozen operations object; production factory already consumes it.

## Verification

- Operations focused RED/GREEN, then production, Meetup workflow, runner, evidence, Harness adjacent suites; syntax and diff checks.
- Fresh Sol review for aggregate-only privacy, monotonic validation, file mode/path, production consumption, and no behavior changes.
- Sol merges, updates SSOT, pushes both branches, then runs one schedule-unloaded official wake. Acceptance is a new Meetup audit row matching the official discovery lineage, positive every-wake report, and exact target cleanup.
