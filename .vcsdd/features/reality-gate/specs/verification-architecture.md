# Verification Architecture: reality-gate (Phase 4.5 REALITY GATE)

Companion to `.vcsdd/features/reality-verifier/specs/verification-architecture.md` (the
existing feature this one extends). Read that file first — this one only documents what is
NEW or CHANGED.

## Purity Boundary Map

- **Pure Core** (`skills/self/lib/reality-verdict-schema.mjs`, extended in place):
  - `FINDING_CATEGORIES` — frozen array, now 7 entries (REQ-001). Pure data.
  - `isKnownCategory(category)` — unchanged pure lookup, now checks against 7 entries.
  - `validateVerdictShape(verdict)` — unchanged pure structural validator; accepts the new
    category as any other (no special-casing needed inside this function — REQ-001).
  - `enforceLoggedOutEvidence(verdict, claimType)` *(new, REQ-003)* — pure function:
    inspects `verdict.findings[].evidence` and `verdict.evidenceReviewed[]` string fields for
    a fixed marker set (`"9222"`, `"daily-driver"`, `"cloakbrowser"` case-insensitive) when
    `claimType` is in `{"publish","post","deploy"}`; if found, returns a NEW verdict object
    (never mutates the input — immutability rule) with `overallVerdict: "FAIL"` and an added
    `post_not_publicly_visible` finding citing the violating evidence field; otherwise returns
    the input verdict unchanged (by value, still a fresh object per the immutability rule in
    `.claude/rules/coding-style.md`). No fs/network access — pure string inspection.
  - `buildVerdictTrailPath(stateDir, loopName)` *(new, REQ-006)* — deterministic string join,
    mirrors `buildResultPath`'s existing pattern exactly (same normalization via
    `normalizeLoopName`), no I/O.
  - `buildVerdictTrailLine(verdict, resultPath, timestampMs)` *(new, REQ-006)* — pure: takes
    a validated verdict + its RESULT path + a timestamp and returns the exact JSON string to
    append (one line, no trailing content) — the actual `fs.appendFileSync` call lives in the
    effectful shell (the gate script), not here, so the *shape* of what gets written is fully
    unit-testable without touching disk.
- **Effectful Shell**:
  - `.claude/agents/reality-verifier.md` — prompt content is checked mechanically (frontmatter
    shape, required literal strings for the new category + logged-out prohibition); actual
    reasoning is an LLM call, out of unit-test scope (unchanged principle from the base
    feature).
  - `skills/self/reality-verify-spawn.sh` — extended to thread an optional 4th `claim-type`
    arg into the spawned task text; still effectful (tmux + `claude` process spawn); only the
    `REALITY_VERIFY_DRYRUN` seam is exercised by tests, same as before.
  - The new gate script (`skills/self/vcsdd-reality-gate.mjs` or `.sh`, exact name decided in
    Phase 2a) — effectful: spawns reality-verifier (via the spawn wrapper), polls for the
    `RESULT` file, calls the pure `enforceLoggedOutEvidence` backstop on whatever it reads,
    appends the verdict trail line (`fs.appendFileSync`), and calls the plugin's
    `recordGate()` (which itself performs a `writeState` — a real file write). This script is
    the ONLY place the deterministic backstop's output gets persisted; it never itself
    performs Write/Edit-style source edits (REQ-010).
  - `.claude/commands/vcsdd-reality.md` — an instructional command definition (like the
    plugin's own `commands/vcsdd-adversary.md`), not code; its *content* (required steps
    present) is checked mechanically (Tier 0), its *execution* is effectful.
  - `.claude/hooks/hooks.json` + its handler script (REQ-009) — a `PreToolUse` hook is
    inherently effectful (inspects live tool-call payloads); its matching logic (does this
    Bash command look like a transition to `complete`) is a heuristic string check, mirrored
    directly from the plugin's own `vcsdd-gate-check.js` technique (VERIFIED by reading that
    file) — same tier of rigor the plugin itself uses for this class of check (Tier 0,
    example-based, not formally proved, and explicitly best-effort per REQ-009's edge case).
  - `verify-reality-gate` backstop script (REQ-009) — effectful (reads `state.json` from
    disk) but its *decision logic* (given a state object, PASS or FAIL) is trivially
    extractable as a pure function and IS unit-tested that way (see PROP-011 below) — this is
    the one effectful-shell item in this feature that still gets full pure-core-style test
    coverage by factoring the read (effectful) from the decision (pure).

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-001..008 | Unchanged, inherited from `reality-verifier`'s verification-architecture.md (still apply to the extended module — the 6-category assumptions in PROP-004/006/007 must be re-verified against 7 categories, not re-derived) | — | true | (see base feature) |
| PROP-009 | `FINDING_CATEGORIES` contains exactly 7 entries including `post_not_publicly_visible`, and `isKnownCategory` returns true for all 7 and false for any string outside the set | 1 | true | node:test + fast-check |
| PROP-010 | `enforceLoggedOutEvidence`: for ANY verdict whose evidence text contains a `9222`/`daily-driver`/`cloakbrowser` marker AND `claimType` is a public-artifact type, the returned verdict ALWAYS has `overallVerdict === "FAIL"` and `findings.length >= 1` with at least one `post_not_publicly_visible` entry (never silently passes a logged-in check for a public claim) | 1 | true | fast-check (property test, generating random marker placement across `evidence`/`evidenceReviewed` fields) |
| PROP-011 | `enforceLoggedOutEvidence`: for ANY verdict whose evidence text contains NONE of the markers, the function returns a value deep-equal to the input (identity-preserving on the non-violating path — no false positives) | 1 | true | fast-check |
| PROP-012 | `enforceLoggedOutEvidence` never mutates its input verdict object (immutability — `coding-style.md`): the original object reference, deep-compared before/after the call, is unchanged regardless of which branch executes | 1 | true | fast-check |
| PROP-013 | `buildVerdictTrailPath`/`buildVerdictTrailLine`: deterministic for identical inputs, and `buildVerdictTrailLine`'s output always parses as valid JSON containing `overallVerdict` and the given `resultPath` | 1 | true | fast-check |
| PROP-014 | The reality-gate convergence decision function (factored out of `verify-reality-gate`, REQ-009) returns FAIL for every `state` object where `currentPhase === "complete"` and `gates.reality` is absent or `gates.reality.verdict === "FAIL"`, and returns PASS for every `state` object where `gates.reality.verdict` is `"PASS"` or `"SKIPPED"` (with a non-empty `reason`), for arbitrary well-formed `state.gates` shapes | 1 | true | fast-check |
| PROP-015 | `.claude/agents/reality-verifier.md` prompt body contains, verbatim: all 7 category names, the CDP-port-`9222`/daily-driver prohibition string for public-artifact checks, and the domExcerpt-or-status + URL evidence requirement for public-artifact PASS verdicts | 0 | true | node:test (static content assertion, same technique as the base feature's PROP-007) |
| PROP-016 | `.claude/hooks/hooks.json` is present and its `PreToolUse` matcher/handler references the same `gates.reality` field name used by `recordGate()`/PROP-014 (no drift between the hook's check and the backstop script's check) | 0 | true | node:test (static content assertion / import-and-compare) |
| PROP-017 (negative test, REQ-007) | Feeding the pure backstop (PROP-010's function) a fabricated PASS verdict for a nonexistent public URL with a `9222`-tagged evidence entry deterministically yields FAIL — this is the CI-runnable half of the fail-closed proof | 1 | true | node:test (example-based, exact fixture from REQ-007) |
| PROP-018 (negative test, REQ-007, live) | A real fresh `reality-verifier` spawn against a genuinely nonexistent public URL produces an on-disk FAIL verdict (own-eyes, not mocked — same non-mocking rule as the base feature's PROP-006/007 class, extended to a full end-to-end run) | 0 | true | manual/own-eyes run, evidence file committed under `.vcsdd/features/reality-gate/evidence/` |

## Verification Strategy

- **Tier 0** (static/example-based, no formal proof needed): agent-prompt content markers
  (PROP-015), hook-content consistency (PROP-016), and the one live fail-closed proof
  (PROP-018) — same rationale as the base feature: these are documentation/definition
  artifacts or an inherently-non-mockable LLM end-to-end run, not algorithms.
- **Tier 1** (property tests via `fast-check`, already a repo devDependency — VERIFIED by
  reading `package.json`'s `devDependencies` and the existing
  `reality-verdict-schema.property.test.mjs`): all new pure functions
  (`enforceLoggedOutEvidence`, `buildVerdictTrailPath`, `buildVerdictTrailLine`, the
  convergence-decision function) get the same exhaustive-style property coverage the base
  feature already established for `normalizeLoopName`/`buildResultPath`/
  `validateVerdictShape`. PROP-017 is the one exception left as example-based (a single
  concrete fixture is what REQ-007 asks for as the "CI-runnable half"; a property version is
  not excluded but not required).
- **Tier 2**: not used — no lightweight formal-methods tool is warranted for functions this
  small, same reasoning as the base feature.
- **Tier 3**: not used — no memory-safety/concurrency-critical core exists in this JS/bash/
  markdown feature.

## What this architecture explicitly does NOT verify (by design, extended from the base feature)

- Whether reality-verifier's LLM judgment on a REAL claim (e.g. a real Instagram post) is
  correct — same as the base feature, validated only by real own-eyes spawns (PROP-018), not
  automated unit tests, because mocking the judgment would itself be the "fake-green" failure
  mode this feature exists to catch.
- Whether the project-level `PreToolUse` hook (REQ-009) reliably intercepts EVERY possible
  Bash invocation that could transition a feature to `complete` — explicitly acknowledged as
  best-effort (heuristic text matching, same limitation the plugin's own
  `vcsdd-gate-check.js` already has for its Bash heuristics). The standalone
  `verify-reality-gate` script (PROP-014) is the authoritative check; the hook is a
  convenience fast-fail layer only, not the sole enforcement mechanism.
- Whether Claude Code actually composes project-level `.claude/hooks/hooks.json` additively
  with plugin-level `hooks.json` for the same event — this is currently an ASSUMPTION (not
  independently verified this session; no plugin-cache edit was made or tested to confirm
  it). Phase 2b/2c of this feature MUST include one real end-to-end check (fire a matching
  Bash command and observe both hooks' effects) before this requirement is considered
  verified; if the assumption is false, REQ-009's hook layer degrades gracefully to
  "convenience-only, non-blocking" and the standalone backstop script remains the sole
  authoritative gate (already designed to not depend on the hook).
- Whether `gig_reality_verify.sh`'s independent pipeline should be migrated onto this
  feature's generalized spawn wrapper — explicitly out of scope (REQ-005 edge case): gig's
  auditor is a working, separately-verified pipeline; this feature does not touch it.
