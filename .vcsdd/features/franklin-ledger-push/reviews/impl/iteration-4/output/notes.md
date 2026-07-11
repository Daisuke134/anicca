# impl-review iteration 4 — fresh-context adversary notes (expected closing, lean impl review)

Reviewed commit: 166f4274 (worktree `/Users/operator/anicca/.worktrees/ledger-push`).
External test evidence accepted as reported by thinker (no Bash available to this adversary
session): 221-222/223, the only failure being the pre-existing, previously-reproduced-on-baseline
`integration.test.mjs` ENOTEMPTY `/tmp` teardown race, unrelated to this feature. All 40
`test(...)` blocks in `ledger-publish.test.mjs` reportedly pass; independently confirmed the file
is wired into `package.json`'s official `test`/`test:unit` scripts (package.json:8-9), so this is
not an orphaned/unwired test file.

## iteration-3 findings disposition (re-verified independently, fresh-context)

- **FIND-001 (critical — `isProfitable()` unconditionally false on published earn lines)**: KILLED.
  Traced `projectEarnField()` (ledger-publish.mjs:317-344) field-by-field against
  `skills/_shared/lib/ledger.mjs::isProfitable()`'s actual requirements (ledger.mjs:51-64):
  `external`/`confirmed` are now preserved with a strict `typeof value === 'boolean'` guard (never
  coerced — a string `'true'` or numeric `1` is correctly dropped, test.mjs:266-273), `fill_tid`
  accepts a finite number or a `SETTLEMENT_ID_VALUE`-shaped string. The round-trip proof
  (test.mjs:218-264) genuinely imports the REAL `isProfitable` (`import { isProfitable } from
  '../../../skills/_shared/lib/ledger.mjs'`, test.mjs:33) and isolates all three chain paths
  (EVM tx+status, Solana sig+confirmed, Hyperliquid fill_tid+confirmed+chain) into separate test
  cases so the `||` in `evmOk || solOk || hlOk` cannot mask a broken path — this is a genuinely
  non-tautological, real-source-of-truth proof, not a re-implementation of the classifier's rules.
- **FIND-002 (major — `pushed=true` set unconditionally in the retry branch)**: KILLED. Re-read the
  retry branch (ledger-publish.mjs:736-762) line by line: `pushed = true` now appears exactly once
  in that branch, at line 755, immediately after the retry's own `git(['push', ...])` call, itself
  gated inside `if (result.pendingLineCount > 0)`. The new phantom-success test (test.mjs:629-659)
  is a strong proof: it makes the FIRST push call actually execute against real git (landing on
  origin) and THEN throw (simulating an ambiguous client-observed failure), asserts exactly one
  total push call is ever made, and asserts `result.pushed === false` for that cycle — the
  strongest possible test of "no push call issued ⇒ never misreport true", using real git rather
  than a call-sequence mock.
- **FIND-003 (sig only bare length/type check)**: KILLED. `SIG_VALUE =
  /^[1-9A-HJ-NP-Za-km-z]{64,88}$/` (ledger-publish.mjs:217) matches the exact base58 discipline
  `record-swap.mjs` writes and `tx`'s own `TX_HASH_VALUE` discipline. Test.mjs:282-289 proves a
  correct value round-trips, a same-length wrong-alphabet value is dropped, and a too-short value is
  dropped — genuine shape validation, not a bare length/type check.

## New-risk scan of this iteration's own diff (per task instructions)

- **`SETTLEMENT_ID_VALUE` (fill_tid string form) — NEW GAP, raised as this iteration's FIND-001.**
  The iter3→iter4 fix for the critical FIND-001 finding is otherwise clean, but its `fill_tid`
  string-acceptance branch (`/^[A-Za-z0-9:_-]{1,128}$/`) is broader than either `tx`'s or the new
  `sig`'s shape checks, is exempted from BOTH redaction layers (same treatment as `tx`/`sig`, but
  those two have tightly-bound real formats; this one does not), and is — per the code's own
  comment — never actually produced by any real writer in this repo today (`reconcile.py:144-148`
  always writes a JSON integer). This repeats the exact class of gap iter3's adversary already
  ruled BLOCKING for `sig` (a structured field with a too-permissive shape check bypassing
  redaction), just currently unreachable rather than actively populated. Traced the ENTIRE earn-
  ledger write path (`record.mjs` → `deriveLine`) and found no upstream validation that would
  reject a string-typed, secret-shaped `fill_tid` before it reaches the ledger file, so this is a
  real (if currently dormant) structural gap, not a hypothetical concern with no code path to it.
- **`MARKER_DEFAULTS` dead code — NEW MINOR GAP, raised as this iteration's FIND-002.** Declared at
  ledger-publish.mjs:372, zero call sites; `readMarker`'s own catch-block (line 389) hand-duplicates
  the identical literal instead of returning it. Low impact today (both literals are in sync) but a
  genuine, citable violation of "no unused code / no duplicated logic" — flagged per the mandatory
  dead-code check under structural_integrity.
- **Wiring placement**: re-verified `publishLedgerCycle()`'s call site in `index.mjs`'s `while
  (!shuttingDown) { await runOneWake(); ... }` loop (index.mjs:354-387) is still strictly AFTER
  `runOneWake()` returns, still wrapped in its own defense-in-depth try/catch, still passes
  `earnLedgerPath` via `defaultEarnLedgerPath(config)` and inspects `publishFailureStreak` to
  escalate via the existing `appendHarnessFailure` at streak>=5 (index.mjs:374-383) — no purity-
  boundary or wiring regression found.
- **Regression scan (test suite)**: re-read the full 758-line `ledger-publish.test.mjs` end to end.
  Every structural-safety test iteration-3's own notes.md described (leak test, shallow-clone test,
  lock-held/stale tests, publish-repo-loss divergence test, outside-writer divergence test, commit-
  failure recovery test, streak/reachability tests) is still present, unweakened, using real git
  against `file://` bare-repo fixtures exactly as before. Test count went from 34 (iter3) to 40
  (this iteration) — purely additive, consistent with the 6 new FIND-001/002/003 (iter3-numbering)
  fix-verification tests, no evidence of a deleted or simplified assertion anywhere.

## Test integrity spot-check (this iteration's new tests specifically)

- FIND-001d round-trip tests (test.mjs:218-264): real assertions against `JSON.parse(projectEarnLine(...))`
  output AND the real imported `isProfitable()` — not tautological, not a re-implementation.
- FIND-002d phantom-push test (test.mjs:629-659): uses real git for the actual push call (via
  `realGit(args, cwd)` before throwing), counts push calls via a closure variable, and asserts both
  the call count AND the flag — genuine, not mocked-away.
- FIND-003 sig-shape test (test.mjs:282-289): exercises a same-length-wrong-alphabet case
  specifically chosen to defeat a naive length-only check — genuine shape-validation proof.

## Procedural note

A PostToolUse hook fired after this session's `Write` calls stating "fablize gate observed a tool
failure. Do not report completion until it is fixed, isolated as a known baseline, or explicitly
documented." Both preceding `Write` tool calls in this session returned "File created successfully"
with no error surfaced to this adversary. No other tool call in this session returned an error.
Documenting per the hook's own instruction: this adversary session observed no actual tool failure
to isolate or fix; the hook's warning could not be attributed to any specific failed call in this
transcript.
