# Verification Architecture: reality-gate (Phase 4.5 REALITY GATE)

Companion to `.vcsdd/features/reality-verifier/specs/verification-architecture.md` (the
existing feature this one extends). Read that file first. Read `behavioral-spec.md`'s
"Iteration history" and "Threat-model closure" sections first — this file's proof-obligation
table is organized by that same closure table (now 17 rows: 1-11 and 14-15 CLOSED, 17
MITIGATED/empirically-gated, 12/13/16 explicitly OPEN — see behavioral-spec.md for exactly
why each open row cannot be, and is not claimed to be, closed).

## Purity Boundary Map

- **Pure Core** (`skills/self/lib/reality-verdict-schema.mjs`, extended in place):
  - `FINDING_CATEGORIES` — frozen array, 7 entries (REQ-001). Pure data.
  - `isKnownCategory(category)` — unchanged pure lookup.
  - `validateVerdictShape(verdict)` — unchanged pure structural validator; deliberately never
    touched by this feature's provenance work (it validates SHAPE, never provenance).
  - `canonicalizeUrl(url)` *(new, REQ-004/013, closure row 14)* — pure: lowercases
    scheme+host, strips a default port (`:443` for https, `:80` for http), strips query
    string and fragment entirely, normalizes a trailing slash on a non-root path away (but
    keeps a bare `/` for the root path), and upgrades `http:` to `https:` for comparison
    purposes only. Any OTHER difference (path segments, host, or a redirect target) is
    deliberately NOT normalized away — two URLs differing in anything but scheme/port/
    trailing-slash/query/fragment canonicalize to DIFFERENT values. Total, deterministic, no
    I/O, no exceptions (a malformed URL canonicalizes to a fixed sentinel that can never equal
    a well-formed one, so malformed input fails closed rather than throwing).
  - `hashRealityClaim(realityClaim)` *(new, REQ-008/013, closure row 15)* — pure: serializes
    `realityClaim` via a canonical (sorted-key, whitespace-free) JSON stringify, then
    `sha256` hex digest (Node's built-in `crypto` module — CPU-bound, no I/O, mirrors the
    plugin's own `computeContentDigest`/`crypto.createHash` precedent already used in
    `vcsdd-state.js` for sprint-contract digests, VERIFIED by reading that file — this is an
    established, in-repo pattern for "pure enough to unit test" hashing, not a new idiom).
    Deterministic: identical `realityClaim` content (regardless of key order in the source
    file) always yields the identical hash; any content difference always yields a different
    hash (verified by property test, not merely assumed).
  - `validateArtifactProvenance(verdict, capturedArtifacts, claimType, requiredArtifactCount,
    claimedUrls)` *(closure rows 1-4, 6-8, 14)* — pure function; deliberately specified as an
    open, growable set of independent conditions rather than a fixed step count (a prior
    iteration's "5-step contract" framing was itself read, correctly, as an implicit
    completeness claim that was false):
    - **Citation presence** (row 1): collects every candidate citation — `findings[].evidence`
      where `filePath` matches the artifact-trail path shape, PLUS `evidenceReviewed[]`
      entries whose `location` matches the same shape (both scanned; neither is a second
      unguarded door). Zero candidates for a public-artifact `claimType` ⇒ violation,
      unconditionally, before any resolution logic runs.
    - **Resolution — identity** (rows 2-4): each deduplicated (by `(passId, seq)`, row 7)
      candidate must resolve to a REAL row in `capturedArtifacts` with `tool ===
      "public_artifact_snapshot"`, matching `passId`, `ts >=` the pass's start time.
    - **Resolution — URL** (row 14, new): `canonicalizeUrl(row.requestedUrl) ===
      canonicalizeUrl(oneOf(claimedUrls))` AND `canonicalizeUrl(row.finalUrl) ===` that SAME
      canonical value. A citation failing either half is rejected exactly as if it did not
      resolve at all — this closes both outright URL substitution (a different, real, public
      page cited instead of the claimed one) and a redirect off the claimed artifact (login
      wall, interstitial, profile-root) even when `httpStatus` is a bare `200`.
    - **Resolution — status** (row 8): `httpStatus` in `[200,299]` (or tool-level success flag
      true for a headless-browser-variant row).
    - **Count** (rows 6/7): distinct, fully-resolved (identity + URL + status all pass)
      citations `>= requiredArtifactCount`.
    - On ANY violation: returns a NEW verdict (never mutates inputs) with `overallVerdict:
      "FAIL"` and an added `post_not_publicly_visible` finding naming the specific shortfall
      (`no_citation` / `wrong_tool` / `no_matching_row` / `wrong_pass` / `stale_row` /
      `url_mismatch` / `redirect_off_artifact` / `duplicate_citation` / `insufficient_count` /
      `non_2xx_status`). Otherwise returns the input verdict unchanged (fresh reference).
  - `decideConvergenceGate(state, realityClaim)` *(closure rows 11, 15)* — pure:
    `blocked: false` iff (`state.gates.reality?.verdict === "PASS"` OR
    (`state.gates.reality?.verdict === "SKIP"` AND `realityClaim?.claimType === "none"`)) AND
    `hashRealityClaim(realityClaim) === state.gates.reality?.details?.realityClaimHash`;
    `blocked: true` in every other case, INCLUDING a hash mismatch of any kind (the claim
    file changed since the gate was recorded, in either direction) and `realityClaim` being
    `null`/malformed (fail-closed, never inferred `"none"` by absence). Shared,
    byte-identical, between `.githooks/pre-push`'s new section and
    `skills/self/verify-reality-gate.mjs`.
  - `buildVerdictTrailPath(stateDir, loopName)` *(REQ-006)* — unchanged.
  - `buildVerdictTrailLine(verdict, resultPath, timestampMs)` *(REQ-006)* — unchanged.
  - `buildArtifactTrailPath(stateDir, passId)` *(REQ-012)* — unchanged.
- **Effectful Shell**:
  - `.claude/agents/reality-verifier.md` — prompt content checked mechanically; actual
    reasoning is an LLM call, out of unit-test scope.
  - `skills/self/reality-verify-spawn.sh` — threads `claim-type`/`pass-id`/
    `required-artifact-count`/`claimed-urls` into the spawned task text; refuses to spawn
    (non-zero exit) for a public-artifact `claim-type` with no URL supplied at all.
  - `skills/self/scripts/public_artifact_snapshot.py` *(REQ-012)* — effectful: real network
    fetch, real file append; structurally incapable of authenticated access.
  - The gate script (`skills/self/vcsdd-reality-gate.mjs`) — effectful: reads
    `reality-claim.json` (never the verdict) for `claimType`/`requiredArtifactCount`/
    `claimedUrls`/`automatedVerification`, plus a mandatory per-invocation URL argument for a
    `caller-per-invocation` claim; refuses to invoke the verifier at all if a public-artifact
    claim has no URL to check; generates the pass id; spawns reality-verifier; reads
    `artifacts.jsonl`; calls `validateArtifactProvenance`; appends the verdict trail line;
    computes `hashRealityClaim` and stores it in `recordGate`'s `details`; propagates the
    backstop's actual output verbatim into `recordGate()`; refuses `reviewedBy: "verifier"`
    outright when `automatedVerification === false` (only `"human"` is legal for such a
    claim).
  - `.claude/commands/vcsdd-reality.md` — instructional command definition, not code.
  - `.githooks/pre-push`'s new "Reality Convergence Guard" section *(REQ-009, closure row
    10)* — effectful, reads current push-range content of `state.json`/`reality-claim.json`;
    decision is the pure `decideConvergenceGate` — AUTHORITATIVE among Claude-Code-independent
    mechanisms, but explicitly NOT a security boundary against an adversarial insider with
    shell access on the pushing worktree (closure row 16, FIND-F disposition — see
    behavioral-spec.md's verbatim-quoted reasoning).
  - `skills/self/tests/test_reality_convergence_guard.*` *(new, REQ-009, closure row 16
    discipline mitigation)* — a regression-lock test for the guard's own section, mirroring
    `test_cadence_evidence.py`/`test_cadence.py`'s existing pattern; triggered whenever the
    push range touches the guard section itself, `reality-verdict-schema.mjs`, or
    `verify-reality-gate.mjs`.
  - `.claude/settings.json`'s `hooks.PreToolUse` entry + `.claude/hooks/scripts/
    vcsdd-reality-gate-check.sh` — retained, explicitly non-authoritative convenience only.
  - `skills/self/verify-reality-gate.mjs` — effectful read, pure decision
    (`decideConvergenceGate`); used standalone and by the pre-push guard.

## Proof Obligations (organized by the behavioral-spec's threat-closure table)

| ID | Closure row | Description | Tier | Required | Tool |
|----|---|---|---|---|---|
| PROP-001..009 | — | Unchanged, inherited (category catalog, path helpers, base `validateVerdictShape` — re-verified against 7 categories) | — | true | (see base feature) |
| PROP-010 | 2 | `validateArtifactProvenance`: citation resolving to `tool !== "public_artifact_snapshot"` (fixture: `"cdp_nav_snapshot"`) ALWAYS yields `FAIL` | 1 | true | fast-check |
| PROP-011 | 3 | Citation resolving to NO row in `capturedArtifacts` ALWAYS yields `FAIL` | 1 | true | fast-check |
| PROP-012 | 4 | Citation with a foreign `passId` or pre-run `ts` ALWAYS yields `FAIL` | 1 | true | fast-check |
| PROP-013 | (positive control) | For ANY verdict where `requiredArtifactCount` distinct citations ALL resolve cleanly (right tool, right pass, fresh, **matching URL, no redirect**, 2xx), returns a value deep-equal to the input — extended this iteration to require the positive-control fixture include a real, matching `claimedUrls` entry, not merely "resolves on every OTHER axis" | 1 | true | fast-check |
| PROP-014 | (immutability) | Never mutates `verdict`/`capturedArtifacts` (deep-compared before/after, all branches) | 1 | true | fast-check |
| PROP-015 | — | `buildVerdictTrailPath`/`buildVerdictTrailLine`/`buildArtifactTrailPath`: deterministic, valid-JSON output | 1 | true | fast-check |
| PROP-016 | — | `canonicalizeUrl`: idempotent (`canonicalizeUrl(canonicalizeUrl(x)) === canonicalizeUrl(x)`); scheme/port/trailing-slash/query/fragment differences canonicalize equal; ANY path or host difference canonicalizes UNEQUAL, for arbitrary generated URL pairs | 1 | true | fast-check |
| PROP-017 | — | `.claude/agents/reality-verifier.md` prompt body contains, verbatim: all 7 category names, the `public_artifact_snapshot.py` invocation instruction using ONLY the supplied `claimedUrls` (never a model-derived URL), and the evidence-citation requirement | 0 | true | node:test (static content assertion) |
| PROP-018 / PROP-018b | 2 / 3 | Concrete example-based fixtures for PROP-010/011 | 1 | true | node:test |
| PROP-022 | 1 | `PASS` for a public-artifact `claimType` whose only evidence is `domExcerpt` (zero `filePath`/artifact-trail-shaped `location` anywhere), `requiredArtifactCount: 1` ⇒ ALWAYS `FAIL` with `post_not_publicly_visible`/`no_citation` (the named fix for FIND-A) | 1 | true | fast-check + node:test |
| PROP-023 | 6, 7 | `requiredArtifactCount: N` with fewer than `N` distinct resolved citations ⇒ `FAIL`; citing the same resolved row `k` times counts as 1 ⇒ `FAIL` when `k < N` distinct rows exist | 1 | true | fast-check + node:test |
| PROP-024 | 8 | Citation resolving to a real, correctly-tooled, fresh, distinct, correct-URL row whose `httpStatus` is outside `[200,299]` (fixture: `404`) ⇒ `FAIL` | 1 | true | fast-check + node:test |
| **PROP-028** | **14** | `validateArtifactProvenance`: a citation whose resolved row's `canonicalizeUrl(requestedUrl)` is NOT in `{canonicalizeUrl(u) for u in claimedUrls}` (fixture: a real, correctly-tooled, correctly-timed, 2xx row for a genuinely different, unrelated, real public URL) ALWAYS yields `FAIL`/`post_not_publicly_visible`/`url_mismatch` — the direct, named fix for FIND-D's exact exploit scenario | 1 | true | fast-check (random non-matching URL pairs) + node:test (exact FIND-D fixture: an unrelated real public page cited for an Instagram-post claim) |
| **PROP-029** | **14** | A citation whose `requestedUrl` DOES match `claimedUrls` but whose `finalUrl` canonicalizes to a DIFFERENT value (fixture: redirect to `/accounts/login/`, or to the account's profile root, both with `httpStatus: 200`) ALWAYS yields `FAIL`/`redirect_off_artifact` — proves a bare 200 status is never sufficient on its own | 1 | true | fast-check + node:test |
| **PROP-030** | **14** | `requiredArtifactCount: 2` with two citations that both resolve to the SAME matching `claimedUrls` entry (one URL cited twice, dressed as two "distinct" `(passId, seq)` pairs) does NOT satisfy a claim that actually requires 2 DIFFERENT claimed URLs ⇒ `FAIL` — a substitution-flavored variant of the count check, closing a padding path row 6/7's original fixtures did not explicitly cover | 1 | true | node:test (exact fixture: `claimedUrls` has 2 distinct URLs, only 1 is ever captured/cited, twice) |
| PROP-025 | 9 | Fixture-level test: the gate script's `recordGate` call always uses `validateArtifactProvenance`'s actual returned `overallVerdict`, never a hardcoded value | 0 | true | node:test (fixture harness, spy on `recordGate`) |
| PROP-026 | 11 | `decideConvergenceGate`: `SKIP` ⇒ `blocked: true` whenever `realityClaim.claimType !== "none"`; `blocked: false` only when `claimType === "none"` AND hash matches; `realityClaim` null/malformed ⇒ `blocked: true` regardless of `state` | 1 | true | fast-check |
| **PROP-031** | **15** | `decideConvergenceGate`: for ANY `state`/`realityClaim` pair where `hashRealityClaim(realityClaim) !== state.gates.reality?.details?.realityClaimHash`, `blocked === true` REGARDLESS of the stored `verdict` value (including a stored `"PASS"`) — the direct, named fix for FIND-E's both exploit variants (same-push downgrade AND stale-PASS-after-strengthening are both, structurally, "current claim hash != stored hash") | 1 | true | fast-check (random claim-content mutations between record-time and check-time) |
| PROP-027 | 10, 15, 16 | **Diff-aware** live-fire test: `.githooks/pre-push`'s Reality Convergence Guard, invoked directly against fixture push ranges, covering (a) `gates.reality` missing/FAIL ⇒ reject, (b) valid matching-hash `PASS` ⇒ accept, (c) **new**: a `PASS` recorded against an OLD `reality-claim.json` hash while the pushed range's final `reality-claim.json` differs (live-fire proof of FIND-E's exact same-push-downgrade scenario) ⇒ reject | 0 | true | bash test script invoking `.githooks/pre-push` directly with fixture args/files, including a fixture push range with 2 commits that change `reality-claim.json` mid-range |
| **PROP-032** | **16 (discipline mitigation)** | Regression-lock test: `skills/self/tests/test_reality_convergence_guard.*` exists and exits 0 when run directly; `.githooks/pre-push` itself is proven, by a live-fire fixture, to REJECT a push where the Reality Convergence Guard section OR `reality-verdict-schema.mjs`'s `decideConvergenceGate`/`hashRealityClaim` OR `verify-reality-gate.mjs` are touched in the push range AND this regression-lock test does not also pass in that same range — mirrors `.githooks/pre-push`'s existing `CADENCE_TOUCHED` trigger exactly | 0 | true | bash test invoking `.githooks/pre-push` with a fixture push range touching the guarded files |
| PROP-019 | (retained, demoted) | `.claude/hooks/scripts/vcsdd-reality-gate-check.sh`, invoked directly with fixture payload + fixture state, matches `decideConvergenceGate` — required for the convenience layer's OWN correctness, explicitly NOT a substitute for PROP-027/032 | 0 | true | bash/node test |
| PROP-020 | 13 (documents, does not close) | A real fresh `reality-verifier` spawn against a genuinely nonexistent public URL produces an on-disk FAIL verdict | 0 | true | manual/own-eyes run, evidence committed |
| **PROP-020b** | **14 (live proof)** | A real fresh `reality-verifier` spawn where `claimedUrls` names URL A (the intended claim) but the only real, capturable, public content is at a DIFFERENT real URL B produces an on-disk FAIL verdict — the live-run companion to PROP-028, distinct from PROP-020 (nothing exists) because this proves "something else, real, exists" is ALSO caught, not merely "nothing exists" | 0 | true | manual/own-eyes run, evidence committed under `.vcsdd/features/reality-gate/evidence/` |
| PROP-021 | — | `recordGate(feature, 'reality', 'SKIP'\|'PASS', 'verifier'\|'human', details)` completes without throwing against the plugin's REAL, unmodified schema validator | 0 | true | node:test against a throwaway fixture `.vcsdd/` directory |
| **PROP-033** | **17 (Phase-2a-gated)** | Once Phase 2a empirically records which structured signal distinguishes public-vs-not for Instagram (REQ-012), a fixture/live test feeds `public_artifact_snapshot.py` a real known-public Instagram post URL and a real known-removed/private one and asserts the two captured rows differ on that recorded signal. `required: true` ONLY once the signal is recorded; until then this PROP is `status: pending`, not silently dropped, and REQ-012's `automatedVerification: false` default (PROP-034) is what keeps the gate honest in the meantime | 0 | **true once Phase 2a records a signal; `pending` (not `skipped`) until then** | live fetch test against real Instagram URLs, per Phase 2a's chosen signal |
| **PROP-034** | **17 (mechanical, testable now)** | `reality-claim.json.automatedVerification === false` ⇒ any attempt to call `recordGate(..., 'verifier', ...)` for that feature/claim is refused (non-zero exit / explicit error) by the gate script; `recordGate(..., 'human', ...)` is permitted for the same claim. This is the RULE, testable independent of which platforms are actually proven diagnostic | 0 | true | node:test (fixture gate-script harness) |

Closure rows 12, 13, and 16 have no `required: true` PROP claiming to CLOSE them, by design —
row 16 has required PROPs (PROP-027/032) that mitigate it at the discipline-boundary level,
explicitly not claimed as closure. Manufacturing a PROP that pretends to close 12/13/16 would
itself be a false-PASS-shaped claim about this spec's own completeness — exactly the failure
mode this feature exists to prevent, now applied reflexively to this document.

## Verification Strategy

- **Tier 0**: agent-prompt content markers (PROP-017), the demoted hook's own live-fire
  behavior (PROP-019), the Reality Convergence Guard's diff-aware live-fire behavior
  (PROP-027, authoritative), its regression-lock test (PROP-032), the two live fail-closed
  proofs (PROP-020, PROP-020b), the real-schema call-through proof (PROP-021), the
  `automatedVerification` refusal rule (PROP-034, testable now), and the platform-
  diagnosability proof (PROP-033, Phase-2a-gated).
- **Tier 1** (`fast-check`): all pure functions — `validateArtifactProvenance` (PROP-010..014,
  PROP-022..024, PROP-028/029), `canonicalizeUrl` (PROP-016), `decideConvergenceGate`
  (PROP-026, PROP-031), and the path helpers (PROP-015) — get exhaustive-style property
  coverage. PROP-018/018b/023(b)/025/030 are named example-based fixtures for specific,
  concrete bypasses the behavioral-spec explicitly demands proof against.
- **Tier 2/3**: not used — no lightweight-formal-methods or memory-safety-critical core
  exists in this JS/bash/Python/markdown feature.

## What this architecture explicitly does NOT verify (by design)

- Whether reality-verifier's LLM judgment on a REAL claim is correct — validated only by real
  own-eyes spawns (PROP-020/020b), never automated unit tests.
- **Closure row 12**: artifact-trail forgery by a Bash-capable adversarial verifier. Explicitly
  accepted, inherited from `gig_reality_gate.py`/`cdp_nav_snapshot.py`'s identical gap.
- **Closure row 13**: TOCTOU. Inherent to any point-in-time verification system; REQ-006's
  trail makes a later re-check's dishonesty discoverable in hindsight, does not prevent it.
  This feature does not itself re-check previously-verified URLs on a later day (named,
  iteration-3-review-sourced caveat, not previously stated).
- **Closure row 16 (new)**: whether `.githooks/pre-push` can be bypassed by an agent with
  shell access on the pushing worktree (`--no-verify`, `chmod -x`, unsetting
  `core.hooksPath`, a stale pre-REQ-009 checkout). Explicitly, permanently OUT of what this
  feature claims to close — a local git hook is a discipline boundary against accident and
  drift, never a security boundary against an adversarial insider, per the orchestrator's
  ruling quoted verbatim in behavioral-spec.md. PROP-027/032 prove the guard's OWN logic is
  correct and self-consistent; neither proves, nor is claimed to prove, resistance to
  deliberate local tampering. The only defense named for this class (shared with row 12) is a
  fresh-context `reality-verifier` spawned from OUTSIDE the loop under test, plus recurring
  own-eyes/fresh-adversary review.
- **Closure row 17 (new)**: whether `public_artifact_snapshot.py`'s captured signal is
  actually diagnostic (distinguishes public-from-not) for a given platform is an EMPIRICAL
  fact this Phase-1c spec-writing session did not and could not establish (no live fetches
  were performed this session, and none should be — this is spec-only work). What IS verified
  at this phase is the RULE that an unproven platform can never silently produce an automated
  PASS (PROP-034); WHICH platforms are proven diagnostic, and by which signal, is explicitly
  deferred to a required Phase 2a empirical task, not hand-waved past this spec (PROP-033 is
  recorded as `pending`, not omitted, precisely so this deferral is visible and trackable
  rather than silent).
- Whether Claude Code composes project-level `.claude/settings.json` hooks additively with
  plugin-level `hooks.json` — remains an ASSUMPTION, now explicitly IRRELEVANT to correctness
  since REQ-009 does not rely on it (PROP-027's `.githooks/pre-push` wiring is authoritative
  regardless).
- Whether the plugin's own `validateConvergenceForCompletion` will ever natively understand
  `gates.reality` — out of scope; this feature is designed to be correct without that ever
  happening.
- Whether `gig_reality_verify.sh`'s independent pipeline should be migrated onto this
  feature's generalized spawn wrapper — explicitly out of scope.
- Whether a caller (a posting loop) that supplies `claimedUrls` is itself being honest about
  which URL it actually just posted to, versus citing some OTHER real URL it knows is public
  — explicitly out of scope, and explicitly no worse than the identical trust boundary
  `gig_reality_gate.py`'s fixed, caller-supplied `DEFAULT_GROUND_TRUTH_URLS` already has
  (VERIFIED). This feature verifies "is the claimed URL publicly live", not "did the caller
  honestly declare the URL it actually acted on" — a different-layer concern.
