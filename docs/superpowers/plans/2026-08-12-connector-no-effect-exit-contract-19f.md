# Connector No-effect Exit Contract Plan

**Goal:** Keep `completed_no_effect` as a healthy, observable business outcome without misclassifying the native worker as failed.

## Measured failure

- Official wake `wake-7aef819a21c24d01047fb372` produced and delivered `completed_no_effect / existing_bundles_reused`.
- The same process exited `1`, so `run.sh` wrote `worker_failed` and launchd recorded `last exit code = 1`.
- All seven discovery rails ran. Current audits found eligible events but `calendar_free_count = 0`; no new registration, Calendar event, bundle, or user-page mutation occurred.
- The connector-owned page closed and the exact four pre-existing CDP pages survived.

## Contract

- `applied_bundle` and `completed_no_effect` are successful native process outcomes and exit `0`.
- `circuit_open`, malformed/absent results, and thrown errors remain non-zero.
- `run.sh` therefore writes `worker_finished` after a safe no-effect wake; it must not weaken application, evidence, Calendar, or Telegram gates.
- No provider workflow, candidate filter, 14-day window, external effect, launchd plist, or report vocabulary changes in this slice.

## TDD scope

- Production: `skills/connector/native-pass.js`, about 5–10 LOC.
- Test: `skills/connector/test/native-entrypoint.test.js`, about 15–35 LOC.
- Export one pure status-to-exit helper only if needed for a direct regression test; add no module, registry, dependency, or abstraction.

## Verification

1. RED proves current `completed_no_effect` mapping is non-zero.
2. GREEN proves `applied_bundle` and `completed_no_effect` map to `0`; `circuit_open`, malformed, and absent results map non-zero.
3. Run focused native entrypoint tests, Connector runner tests, syntax checks, and the full Connector test command already used by this repository.
4. Reload the existing plist and execute one official wake. Acceptance is `worker_finished`, launchd exit `0`, a delivered durable report, no new external effects when all candidates conflict, exact four-page restoration, and no lock.

## Grounding

- GNU Bash Exit Status: https://www.gnu.org/software/bash/manual/html_node/Exit-Status.html — “a command which exits with a zero exit status has succeeded.”
- Node.js Process: https://nodejs.org/api/process.html#processexitcode — omitted `process.exit()` code uses success code `0`; non-zero represents failure.
- launchd.plist(5): https://keith.github.io/xcode-man-pages/launchd.plist.5.html#SuccessfulExit — launchd distinguishes success using “an exit status of zero.”

