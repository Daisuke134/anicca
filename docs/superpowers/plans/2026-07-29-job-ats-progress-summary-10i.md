# JOB-ATS-RESILIENCE-10I: Durable ATS Progress Summary

**Goal:** Make Order 10's real-application gate machine-readable without adding
provider-specific columns to the application ledger.

**Architecture:** Read the existing canonical application URL and current state
from SQLite, derive the ATS adapter with `job_search_loop.ats.detect_provider`,
and atomically replace one private `summary.v1.json` projection after every
terminal daily-pass path. The projection contains aggregate states and
Ashby/Workday coverage only; it contains no company, title, URL, email, or other
candidate data.

## Evidence and adopted practices

| Decision | Source | Core quote |
|---|---|---|
| Replace the projection atomically from a same-directory temporary file | [Python `os.replace`](https://docs.python.org/3/library/os.html#os.replace) | “the renaming will be an atomic operation” |
| Aggregate persisted application rows rather than model narration | [SQLite SELECT](https://www.sqlite.org/lang_select.html) | “A simple SELECT statement is an aggregate query if it contains either a GROUP BY clause or one or more aggregate functions” |
| Keep the public contract explicit and object-shaped | [JSON Schema object reference](https://json-schema.org/understanding-json-schema/reference/object) | “Objects are the mapping type in JSON. They map ‘keys’ to ‘values’.” |
| Use a same-directory tempfile plus `os.replace` so readers never see partial JSON | [agent-smith atomic JSON store](https://github.com/0x0pointer/agent-smith/blob/e6011c6cfe720cebd927e9577338b241a19fe99a/core/store.py) | “a concurrent reader … never sees a half-written file” |

Firecrawl search was attempted with three independent English/Japanese queries,
but the agent-owned token returned HTTP 401. GitHub code search and the official
Python, SQLite, and JSON Schema documentation supplied the fallback evidence;
no personal account was used.

## Contract

`$JOB_SEARCH_STATE_ROOT/summary.v1.json` is mode `0600` and contains:

```text
version: 1
day: YYYY-MM-DD
counts: aggregate current application states
model_route: configured provider name or "unconfigured"
ats_progress:
  required_adapters: [ashby, workday]
  confirmed_adapters: adapters with at least one current submitted application
  complete: true only when both required adapters are confirmed
  adapters: per-adapter durable submission-outcome counts, falling back to current
            state before a submission intent exists
```

The ledger remains provider-neutral. Adapter identity is derived from the
canonical URL only while building the read projection. A persisted
`submit_intents.status=submitted` remains confirmed after the application advances
to interview, offer, rejection, or another lifecycle state. `submit_unknown` never
counts as confirmed.

## TDD execution

- [x] Add a RED summary behavior test covering Ashby submitted, Workday
  submit-unknown, generic submitted, PII exclusion, and incomplete Order 10.
- [x] Add a RED CLI test proving atomic mode-`0600` output from a real temporary
  ledger.
- [x] Add a RED daily-runner integration test proving quota, budget-wait, and
  successful paths refresh the durable projection.
- [x] Implement the minimal ledger read, summary builder/writer/CLI, and runner
  wiring.
- [x] Run focused tests, then all 168 job-loop and 9 agent-runner tests.
- [ ] Update the design spec and record live projection evidence without
  changing Order 10 to completed.
- [ ] Push, wait for all required GitHub checks, merge, fast-forward the
  canonical worktree, kick the existing launchd loop, and verify the live
  projection and scheduler health.
