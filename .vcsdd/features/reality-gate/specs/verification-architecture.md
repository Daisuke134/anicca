# Verification Architecture: reality-gate (Phase 4.5 REALITY GATE)

Companion to `.vcsdd/features/reality-verifier/specs/verification-architecture.md` (the
existing feature this one extends). Read that file first — this one only documents what is
NEW or CHANGED. Read `behavioral-spec.md`'s "Iteration history" and "Threat-model closure"
sections first — this file's proof-obligation table below is organized by the same 13-row
closure table (rows 1-11 CLOSED, rows 12-13 explicitly accepted residual), not by "iteration"
as before, because the coordinator's instruction after iteration 2 was to close the
vulnerability class, and the class-level view is the correct organizing structure now.

## Purity Boundary Map

- **Pure Core** (`skills/self/lib/reality-verdict-schema.mjs`, extended in place):
  - `FINDING_CATEGORIES` — frozen array, 7 entries (REQ-001). Pure data.
  - `isKnownCategory(category)` — unchanged pure lookup.
  - `validateVerdictShape(verdict)` — unchanged pure structural validator; not touched by
    this feature's evidence-provenance work at all (deliberately — it validates SHAPE, never
    provenance; `validateArtifactProvenance` is a separate, later pass specifically because
    conflating "well-formed" with "independently proven" was never the right layering).
  - `validateArtifactProvenance(verdict, capturedArtifacts, claimType, requiredArtifactCount)`
    *(closure rows 1-4, 6-8)* — pure function, five-step contract, default-closed:
    1. Collect every candidate citation in the verdict: `findings[].evidence` where
       `filePath` matches the artifact-trail path shape, PLUS `evidenceReviewed[]` entries
       whose `location` matches the same shape (both are checked — REQ-004's fix for FIND-A
       explicitly does not leave `evidenceReviewed`'s looser `{type,location,description}`
       shape as a second unguarded door next to `findings[].evidence`).
    2. Deduplicate candidates by `(passId, seq)`.
    3. Resolve each deduplicated candidate against `capturedArtifacts` (an array the caller
       already read from disk — this function never touches `fs`): must find a row with
       matching `passId`+`seq`, `tool === "public_artifact_snapshot"`, `ts >=` the pass's
       start time (passed in as part of `capturedArtifacts`'s scoping, or as a 5th argument —
       Phase 2a implementation detail), and `httpStatus` in `[200,299]`.
    4. If `claimType` is public-artifact-class (`publish`/`post`/`deploy`) or `earn`-with-a-
       declared-artifact, AND the count of candidates that resolved cleanly in step 3 is `<
       requiredArtifactCount` (this is true, vacuously, when there were zero candidates at
       all — closure row 1 — as well as when there were some but too few, or duplicates that
       deduplicated down below the threshold — closure rows 6/7) — the function returns a NEW
       verdict (never mutates the input, immutability rule) with `overallVerdict: "FAIL"` and
       an added `post_not_publicly_visible` finding naming the specific shortfall
       (`no_citation` / `wrong_tool` / `no_matching_row` / `wrong_pass` / `stale_row` /
       `duplicate_citation` / `insufficient_count` / `non_2xx_status`).
    5. Otherwise (enough distinct, resolved, fresh, correctly-tooled, 2xx-status citations
       exist), returns the input verdict unchanged (as a fresh object reference).
  - `decideConvergenceGate(state, realityClaim)` *(closure row 11)* — pure: `blocked: false`
    iff `state.gates.reality?.verdict === "PASS"`, OR (`state.gates.reality?.verdict ===
    "SKIP"` AND `realityClaim?.claimType === "none"`); `blocked: true` in every other case,
    INCLUDING `realityClaim` being `null`/malformed (fail-closed, never inferred as `"none"`
    by absence). Shared, byte-identical, between `.githooks/pre-push`'s new section and
    `skills/self/verify-reality-gate.mjs` (the standalone backstop), so the two enforcement
    layers cannot independently drift into disagreement.
  - `buildVerdictTrailPath(stateDir, loopName)` *(REQ-006)* — unchanged from iteration 2.
  - `buildVerdictTrailLine(verdict, resultPath, timestampMs)` *(REQ-006)* — unchanged.
  - `buildArtifactTrailPath(stateDir, passId)` *(REQ-012)* — unchanged from iteration 2.
- **Effectful Shell**:
  - `.claude/agents/reality-verifier.md` — prompt content checked mechanically (frontmatter
    shape, required literal strings for the 7 categories, the REQ-012 tool-invocation
    instruction including the `requiredArtifactCount`-many-calls instruction, and the
    domExcerpt/status + URL evidence requirement); actual reasoning is an LLM call, out of
    unit-test scope.
  - `skills/self/reality-verify-spawn.sh` — extended to thread `claim-type`/`pass-id`/
    `required-artifact-count` into the spawned task text; still effectful.
  - `skills/self/scripts/public_artifact_snapshot.py` *(REQ-012)* — effectful: real network
    fetch, real file append; structurally incapable of authenticated access (Tier-0
    grep-checkable, not a runtime property test).
  - The gate script (`skills/self/vcsdd-reality-gate.mjs`) — effectful: reads
    `reality-claim.json` (NEVER the verdict) for `claimType`/`requiredArtifactCount`
    (closure row 5), generates the pass id, spawns reality-verifier, reads `artifacts.jsonl`
    for that pass id, calls the pure `validateArtifactProvenance`, appends the verdict trail
    line, and calls `recordGate()` with the backstop's ACTUAL returned `overallVerdict`
    verbatim — proven at the fixture level (closure row 9, PROP-025), not merely asserted in
    prose.
  - `.claude/commands/vcsdd-reality.md` — instructional command definition, not code.
  - `.githooks/pre-push`'s new "Reality Convergence Guard" section *(REQ-009, closure row
    10)* — effectful (reads the push range + `state.json`/`reality-claim.json` files), but
    its DECISION is the pure `decideConvergenceGate` — AUTHORITATIVE, Claude-Code-independent.
  - `.claude/settings.json`'s `hooks.PreToolUse` entry + `.claude/hooks/scripts/
    vcsdd-reality-gate-check.sh` — retained, explicitly non-authoritative (best-effort
    fast-fail convenience only); its decision logic is still the same shared
    `decideConvergenceGate`, so even as a convenience layer it cannot disagree with the
    authoritative one.
  - `skills/self/verify-reality-gate.mjs` — effectful (reads `state.json`/
    `reality-claim.json`), decision is the pure `decideConvergenceGate`; used both standalone
    (manual invocation) and as the library the pre-push guard's new section calls.

## Proof Obligations (organized by the behavioral-spec's threat-closure table)

| ID | Closure row | Description | Tier | Required | Tool |
|----|---|---|---|---|---|
| PROP-001..009 | — | Unchanged, inherited from `reality-verifier`'s and earlier iterations' verification-architecture (category catalog, path helpers, base `validateVerdictShape` behavior — re-verified against 7 categories) | — | true | (see base feature) |
| PROP-010 | 2 | `validateArtifactProvenance`: ANY verdict citing a resolved row whose `tool !== "public_artifact_snapshot"` (fixture: `"cdp_nav_snapshot"`) ALWAYS yields `FAIL` | 1 | true | fast-check |
| PROP-011 | 3 | `validateArtifactProvenance`: ANY verdict whose citation resolves to NO row in `capturedArtifacts` ALWAYS yields `FAIL` | 1 | true | fast-check |
| PROP-012 | 4 | `validateArtifactProvenance`: ANY verdict citing a row with a foreign `passId` or pre-run `ts` ALWAYS yields `FAIL` | 1 | true | fast-check |
| PROP-013 | (positive control) | `validateArtifactProvenance`: for ANY verdict where `requiredArtifactCount` distinct citations ALL resolve cleanly (right tool, right pass, fresh, 2xx), the function returns a value deep-equal to the input (no false positives on the fully-satisfied path — this fixture MUST include real, matching rows; it is not merely "text lacking banned words", the iteration-1-era failure mode) | 1 | true | fast-check |
| PROP-014 | (immutability) | `validateArtifactProvenance` never mutates `verdict` or `capturedArtifacts` (deep-compared before/after, both branches) | 1 | true | fast-check |
| PROP-015 | — | `buildVerdictTrailPath`/`buildVerdictTrailLine`/`buildArtifactTrailPath`: deterministic, valid-JSON output (unchanged from iteration 2) | 1 | true | fast-check |
| PROP-017 | — | `.claude/agents/reality-verifier.md` prompt body contains, verbatim: all 7 category names, the `public_artifact_snapshot.py <passId> <seq> <label> <url>` invocation instruction (including "call it `requiredArtifactCount` times, once per required public URL"), and the evidence-citation requirement | 0 | true | node:test (static content assertion) |
| PROP-018 / PROP-018b | 2 / 3 | Concrete example-based fixtures for PROP-010/011 (kept as named, separately-fixtured obligations per REQ-004's explicit "authenticated tool" / "no artifact at all" bypass demands) | 1 | true | node:test (example-based) |
| **PROP-022** | **1** | `validateArtifactProvenance`: a `PASS` verdict for a public-artifact `claimType` whose ONLY evidence, across every `findings[].evidence` AND every `evidenceReviewed[]` entry, is `domExcerpt` (or an `evidenceReviewed` entry with no artifact-trail-shaped `location`) — i.e. **zero** qualifying citations — ALWAYS yields `overallVerdict: "FAIL"` with a `post_not_publicly_visible` finding whose detail is `no_citation`. This is the direct, named fix for FIND-A and MUST be tested with `requiredArtifactCount` as low as `1` (the weakest possible bar) to prove the rejection is not merely a side effect of an unmet count | 1 | true | fast-check (property: for ANY verdict content with zero filePath/location citations) + node:test (example fixture) |
| **PROP-023** | **6, 7** | `validateArtifactProvenance`: (a) `requiredArtifactCount: N` with fewer than `N` DISTINCT resolved citations ALWAYS yields `FAIL`; (b) citing the SAME resolved row `k` times counts as 1 toward the distinct total, not `k` — tested by a fixture with `requiredArtifactCount: 2` and the identical valid `(passId, seq)` cited twice, asserting `FAIL` | 1 | true | fast-check + node:test |
| **PROP-024** | **8** | `validateArtifactProvenance`: a citation that resolves to a real, correctly-tooled, fresh, distinct row whose `httpStatus` is outside `[200,299]` (fixture: `404`) is NOT counted toward `requiredArtifactCount` and, if it is the only citation, ALWAYS yields `FAIL` | 1 | true | fast-check (random non-2xx status generation) + node:test |
| **PROP-025** | **9** | Fixture-level test of the gate script's recording logic: given a `validateArtifactProvenance` call that downgrades a `PASS` to `FAIL`, the value the gate script passes to `recordGate`'s `verdict` argument is proven (by inspecting the actual call arguments in a fixture harness, e.g. a stub/spy on `recordGate`) to be `'FAIL'`, never a separately-sourced `'PASS'` | 0 | true | node:test (fixture harness around the gate script's recording function) |
| **PROP-026** | **11** | `decideConvergenceGate(state, realityClaim)`: for ANY `state` with `gates.reality.verdict === "SKIP"`, `blocked === true` whenever `realityClaim.claimType !== "none"`, and `blocked === false` only when `realityClaim.claimType === "none"`; ALSO `blocked === true` whenever `realityClaim` is `null`/missing/malformed, for ANY `state.gates.reality` value (fail-closed on missing claim declaration) | 1 | true | fast-check |
| **PROP-027** | **10** | Live-fire test: `.githooks/pre-push`'s new Reality Convergence Guard section, invoked directly with a fixture push range containing a `state.json` at `currentPhase: "complete"` and `gates.reality` missing/FAIL, exits non-zero; the same invocation with `gates.reality.verdict: "PASS"` and a matching `reality-claim.json` (`claimType` satisfied) exits zero. Mirrors the exact rigor level `.githooks/pre-push`'s own existing Cadence Contract Guard test pattern already establishes in this repo | 0 | true | bash test script invoking `.githooks/pre-push` directly with fixture args/files |
| PROP-019 | (retained, demoted) | `.claude/hooks/scripts/vcsdd-reality-gate-check.sh`, invoked directly with a fixture payload + fixture `state.json`/`reality-claim.json`, returns a blocking/non-blocking result matching `decideConvergenceGate` — kept as a required PROP for the convenience layer's OWN correctness, but explicitly NOT a substitute for PROP-027; the behavioral-spec's REQ-009 states this layer is non-authoritative regardless of this PROP's status | 0 | true | bash/node test script invoking the hook handler directly |
| PROP-020 | 13 (documents, does not close) | A real fresh `reality-verifier` spawn against a genuinely nonexistent public URL produces an on-disk FAIL verdict (own-eyes, not mocked) | 0 | true | manual/own-eyes run, evidence committed under `.vcsdd/features/reality-gate/evidence/` |
| PROP-021 | — | `recordGate(feature, 'reality', 'SKIP'\|'PASS', 'verifier', details)` completes without throwing against the plugin's REAL, unmodified schema validator | 0 | true | node:test, requiring the real plugin library against a throwaway fixture `.vcsdd/` directory |

Closure rows 12 and 13 have no corresponding `required: true` PROP, by design — they are
named, accepted residual risk (behavioral-spec.md's threat-closure table), not gaps this
feature's proof obligations claim to close. Manufacturing a PROP that pretends to close them
would itself be a false-PASS-shaped claim about this spec's own completeness.

## Verification Strategy

- **Tier 0** (static/example-based): agent-prompt content markers (PROP-017), the hook
  handler's own live-fire behavior (PROP-019, demoted-but-still-tested), the Reality
  Convergence Guard's live-fire behavior (PROP-027, the AUTHORITATIVE one), the one live
  fail-closed proof (PROP-020), and the real-schema call-through proof (PROP-021).
- **Tier 1** (property tests via `fast-check`, already a repo devDependency): all pure
  functions — `validateArtifactProvenance` (PROP-010..014, PROP-022..024),
  `decideConvergenceGate` (PROP-026), and the path helpers (PROP-015) — get exhaustive-style
  property coverage. PROP-018/018b/023(b)/025 are the named example-based fixtures the
  behavioral-spec explicitly demands as concrete, non-generalized proof of each specific
  bypass; property-test generalizations of them are not excluded but not required.
- **Tier 2/3**: not used, same reasoning as prior iterations — no lightweight-formal-methods
  or memory-safety-critical core exists in this JS/bash/Python/markdown feature.

## What this architecture explicitly does NOT verify (by design)

- Whether reality-verifier's LLM judgment on a REAL claim is correct — validated only by real
  own-eyes spawns (PROP-020), never automated unit tests (mocking the judgment would itself be
  the "fake-green" failure mode this feature exists to catch).
- **Closure row 12**: whether a fully adversarial, Bash-capable agent could hand-forge a fake
  row into `artifacts.jsonl` without calling `public_artifact_snapshot.py`. Explicitly
  accepted, inherited from `gig_reality_gate.py`/`cdp_nav_snapshot.py`'s identical gap
  (VERIFIED by reading both). Own-eyes/fresh-adversary review is the project-wide backstop for
  this class of risk, for both patterns; this feature does not claim to exceed the security
  model of the pattern it deliberately mirrors.
- **Closure row 13**: TOCTOU between a genuine point-in-time PASS and a later takedown/
  shadowban. Inherent to any point-in-time verification system; REQ-006's durable trail makes
  a later re-check's dishonesty *discoverable in hindsight*, it does not prevent the gap from
  existing at all.
- Whether Claude Code actually composes project-level `.claude/settings.json` `hooks`
  additively with plugin-level `hooks.json` for the same event — remains an ASSUMPTION,
  narrowed exactly as in iteration 2 (PROP-019 tests the script's own logic, not Claude Code's
  runtime composition) — but this assumption is now explicitly IRRELEVANT to correctness,
  because REQ-009 no longer relies on it: PROP-027's `.githooks/pre-push` wiring is the
  authoritative enforcement point regardless of whether the `PreToolUse` hook ever fires.
- Whether the plugin's own `validateConvergenceForCompletion` will ever be extended (by a
  future plugin release) to natively understand `gates.reality` — out of scope; this feature
  is explicitly designed to be correct WITHOUT that ever happening, since REQ-008's edge case
  forbids depending on plugin-cache changes at all.
- Whether `gig_reality_verify.sh`'s independent pipeline should be migrated onto this
  feature's generalized spawn wrapper — explicitly out of scope (REQ-005 edge case).
