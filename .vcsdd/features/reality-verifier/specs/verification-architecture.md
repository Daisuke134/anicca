# Verification Architecture: reality-verifier

## Purity Boundary Map

- **Pure Core** (`skills/self/lib/reality-verdict-schema.mjs`):
  - `normalizeLoopName(loopName)` — deterministic, no side effects.
  - `buildResultPath(stateDir, loopName, timestampMs)` — deterministic string join, no I/O.
  - `isKnownCategory(category)` — pure lookup against a frozen array.
  - `validateVerdictShape(verdict)` — pure structural validation, no I/O, no randomness,
    fully formally verifiable by property tests (fast-check is already a devDependency of
    this repo).
- **Effectful Shell**:
  - `.claude/agents/reality-verifier.md` — the subagent's system prompt/definition. Its
    *content* is checked mechanically (frontmatter shape, required string markers), but its
    *behavior when actually reasoning* is inherently effectful/non-deterministic (an LLM
    call) and out of unit-test scope.
  - `skills/self/reality-verify-spawn.sh` — spawns a detached process (tmux + `claude`
    binary), reads env vars, writes marker files. Effectful; only the `REALITY_VERIFY_DRYRUN`
    seam (pure path derivation printed to stdout) is exercised by tests.
  - Runtime evidence-gathering the spawned reality-verifier instance performs (Bash/Read/Grep/
    Glob calls against ledgers, RPC endpoints, browser CLI) — effectful, happens only when
    Claude Code actually spawns the subagent; not simulated or mocked by this feature's test
    suite (mocking an LLM's tool-use loop would violate "no fake success" — the spec instead
    requires own-eyes manual verification, see Done criteria in doc27).

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-001 | `normalizeLoopName` is idempotent: `normalizeLoopName(normalizeLoopName(x)) === normalizeLoopName(x)` for any non-empty string `x` | 1 | true | fast-check (property test) |
| PROP-002 | `buildResultPath` never produces two different paths for the same `(stateDir, loopName, timestampMs)` input (determinism) and always produces different paths for different `timestampMs` given fixed `(stateDir, loopName)` | 1 | true | fast-check |
| PROP-003 | `validateVerdictShape` rejects every `overallVerdict==="FAIL"` object with an empty `findings` array, for any well-formed but findings-empty input | 1 | true | fast-check |
| PROP-004 | `validateVerdictShape` rejects every finding whose `category` is not a member of `FINDING_CATEGORIES`, for any string category outside the fixed set | 1 | true | fast-check |
| PROP-005 | `validateVerdictShape` rejects every `overallVerdict==="PASS"` object with empty `findings` AND empty/missing `evidenceReviewed` (anti-vague-PASS) | 1 | true | fast-check |
| PROP-006 | `.claude/agents/reality-verifier.md` frontmatter `tools` array contains exactly `Read`, `Grep`, `Glob`, `Bash` and never `Write`/`Edit` | 0 | true | node:test (static content assertion, not a formal proof — tier 0) |
| PROP-007 | `.claude/agents/reality-verifier.md` prompt body contains the REQ-003 boundary statement, the REQ-004 fresh-context/no-self-eval statement, all 6 REQ-005 category names verbatim, and the REQ-007 read-only RPC allow-list | 0 | true | node:test (static content assertion) |
| PROP-008 | `reality-verify-spawn.sh` under `REALITY_VERIFY_DRYRUN=1` prints a result path containing the normalized loop name and never spawns a `tmux`/`claude` process (no process left running after the call) | 0 | true | bash test script (`test-reality-verify-spawn.sh`, mirrors `test-self-fix.sh` pattern) |

## Verification Strategy

- **Tier 0** (no formal proof needed, static/example-based checks suffice): the two content
  markers on `reality-verifier.md` (PROP-006, PROP-007) and the dry-run seam of the spawn
  script (PROP-008). These are documentation/definition artifacts, not algorithms — asserting
  their required substrings/shape is the correct level of rigor.
- **Tier 1** (property tests / fast-check, since this repo already depends on `fast-check`):
  the four pure functions in `reality-verdict-schema.mjs` (PROP-001..005). Each is a small,
  total, side-effect-free function — ideal fast-check targets. Ranges: `loopName` generated as
  non-empty printable ASCII strings (`fc.string({minLength: 1})`), `timestampMs` as
  non-negative safe integers, `category` as arbitrary strings both inside and outside
  `FINDING_CATEGORIES`.
- **Tier 2**: not used. No lightweight formal-methods tool (TLA+, contracts-as-code beyond
  property tests) is warranted for functions this small; fast-check property tests already
  give the exhaustive-style guarantee needed for REQ-006's shape validator.
- **Tier 3**: not used. No safety-critical numeric/concurrency invariant exists in this
  feature that would justify Kani/CBMC-class strong formal proof; this is a JS/bash
  documentation+glue feature, not a memory-safety-critical core.

## What this architecture explicitly does NOT verify (by design)

- Whether reality-verifier's actual LLM judgment on a real report is *correct* — that is
  validated only by manual own-eyes runs against real prior incidents (clip/reddit/founder/
  connector/pm/Franklin cases listed in doc24's "Done" section), never by automated unit
  tests, because mocking the judgment would itself be exactly the "fake-green" failure mode
  this feature exists to catch.
- Whether the DETERMINISTIC layer (on-chain tx/balance) is correct — out of scope, already
  implemented elsewhere, explicitly not touched by this feature (REQ-008 edge case: no
  ledger/`earn-detect.mjs` file is modified).
