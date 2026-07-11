# Changelog

All notable changes to **anicca-oss** are tracked here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) ·
Versioning: [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **lending: wired the lender's own EVM key into disbursement** (`skills/economy/lending/scripts/wake-gate.mjs`,
  lean VCSDD `lending-lender-key-wiring`) — `lending-orchestrator.mjs`'s `defaultDisburse` always
  called `payViaFacilitator({privateKey: deps.lenderPrivateKey, ...})`, but no production caller ever
  resolved/injected `deps.lenderPrivateKey`, so every real wake crashed at
  `privateKeyToAccount(undefined)` (live symptom: `loan_Franklin_1` stuck at status
  `disbursement_uncertain`). `runWakeGate` now resolves the LENDER's own key via
  `resolve-identity.mjs::resolveEvmPrivateKey({env})` (fail-closed — an unresolvable key refuses with
  `reason:"lender_private_key_unresolved"` BEFORE `executeLoanIssuanceAttempt` is ever called, never
  reaching `payViaFacilitator` with `undefined`) and also wires a real `deps.rpcUrl` (defaults to
  `https://mainnet.base.org`, overridable via `BASE_RPC_URL`) so a stuck row's own reconciliation
  lookup is genuinely reachable and no longer permanently blocks the lender. 8 new/updated
  `wake-gate.test.mjs` tests (RED confirmed against pre-fix code via `git stash`, then GREEN); full
  `anicca-agent-lending` suite 134/134 pass.

### Added

- **CI security gate** (`.github/workflows/sec-scan.yml`) — gitleaks 8.30.1 +
  TruffleHog (filesystem + git history, `--only-verified`) + Python
  `ast.parse` walk + `bash -n` walk + `unittest` discovery. Runs on every
  push to `main` and every PR.
- **Pipecat phone outbound regression suite** — 7 pure-stdlib tests
  covering `{name}` / `{ctx}` substitution, empty-name fallback, hard-rule
  preservation, route-trust block preservation, prompt size budget.

### Changed

- **Phone prompts trimmed 60 %** — lateness 3109 → 1373 chars (-55.8 %),
  wakeup 2062 → 653 chars (-68.3 %). Smaller system prompt = lower
  Gemini Live first-token latency.
- **Caller name is now read from `profile.identity.preferredName`** —
  no hardcoded names in any prompt. Falls back to `"friend"` if unset.
- **Location source: Telegram Live Location only** — OwnTracks daemon
  retired. Pipecat / lateness check / gcal departures all read the same
  `~/.openclaw/state/location/*.json` written by the Telegram bridge.
- **Quiet hours enforced** — wake-up + lateness calls suppressed between
  `profile.alarm.quietHoursStart` and `quietHoursEnd` regardless of
  calendar contents.

### Fixed

- **Routine events (sleep/wake/meditate/run/meal) no longer leak the user's
  current location into the destination** — explicit `home_address()`
  injection means the lateness loop will never say "leave the cafe for
  sleep" or fabricate a station name.
- **franklin2-daemon-identity impl iter1 fixes (FIND-001..003)** — `runtime/anicca-daemon.sh`'s new
  `is_franklin_instance()` classifier (which lets `franklin2`, `franklin3`, … route through the same
  brain/telemetry/wallet paths as the original `franklin` citizen) newly makes two effectful bodies
  reachable by a SECOND concurrently-running instance for the first time; both are now instance-aware:
  (1) `runtime/dashboard/telemetry-post-franklin.mjs`'s dashboard `host` label now derives from
  `ANICCA_INSTANCE` (`franklin`/unset → `"Franklin"`, backward-compat; `franklin2` → `"Franklin2"`; …)
  instead of a hardcoded literal, so two Franklin-family instances no longer report under the identical
  dashboard row name; (2) the franklin-branch telemetry `pkill -f` in `anicca-daemon.sh` step 3 is now
  scoped to `$ANICCA_HOME` (via a `--home "$ANICCA_HOME"` argv marker on the poster invocation), so a
  daemon restart of one Franklin-family instance can no longer kill another concurrently-running
  instance's in-flight poster process. (3) The 4 franklin-routing/plist/telemetry test files (18
  pre-existing + 1 new static + 5 new `telemetry-host-label.test.mjs` tests) are now wired into
  `runtime/loop/package.json`'s `test` script, so this regression protection runs under `npm test`/CI
  instead of requiring manual invocation (`npm test` baseline: 183 → 207, all green).

### Security

- gitleaks-action@v2 replaced with upstream MIT-licensed binary
  (the action moved to a paid licensing model).
- CI security gate runs both filesystem + git-history scans.
