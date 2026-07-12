# Verification Architecture: reality-gate (Phase 4.5 REALITY GATE)

Companion to `.vcsdd/features/reality-verifier/specs/verification-architecture.md`. Read
`behavioral-spec.md`'s "Iteration history" and "Threat-model closure" sections first — this
file's proof-obligation table is organized by that same closure table (now 21 rows: 1-11,
14-15, 18-21 CLOSED; 17 MITIGATED/empirically-gated; 12/13/16 explicitly OPEN). Every row
below states which invocation path(s) it protects — (i) build-time VCSDD gate, (ii) runtime
standalone loop — because iteration 4's own review found that a mechanism protecting only (i)
while REQ-011 requires (ii) is not closed, regardless of how well-tested it is for (i).

## Purity Boundary Map

- **Pure Core** (`skills/self/lib/reality-verdict-schema.mjs`, extended in place):
  - `FINDING_CATEGORIES`, `isKnownCategory`, `validateVerdictShape` — unchanged from the base
    feature except the 7th category; `validateVerdictShape` deliberately never touched by any
    provenance work (shape vs. provenance stay separate layers).
  - `canonicalizeUrl(url)` *(closure rows 14, 20 — REDESIGNED this iteration, FIND-J fix)* —
    pure: lowercases scheme+host, strips default port, upgrades `http:`→`https:` for
    comparison, normalizes trailing slash on a non-root path, strips the fragment. For the
    QUERY STRING: parses into key-value pairs, removes ONLY keys in a fixed, small, explicit
    tracking-parameter allowlist (`utm_source`, `utm_medium`, `utm_campaign`, `utm_term`,
    `utm_content`, `fbclid`, `igshid`, `gclid`, `ref`, `ref_src`), then sorts the REMAINING
    keys alphabetically and re-includes them in the canonical value — i.e. `?v=A&utm_source=x`
    and `?utm_source=y&v=A` canonicalize identically (both → `?v=A`), but `?v=A` and `?v=B`
    canonicalize to DIFFERENT values (iteration-3's design discarded the ENTIRE query string,
    which silently equated these). This is the safe default for an unknown platform: when in
    doubt, PRESERVE (over-strict, more false rejections) rather than DISCARD (over-permissive,
    false acceptances) — the same fail-closed posture as every other check in this feature.
    Total, deterministic, no I/O, no exceptions (malformed input → a fixed sentinel that never
    equals a well-formed value).
  - `computeContentFingerprint(content)` *(new, closure row 19)* — pure: NFC-normalizes and
    trims `content`, then `sha256` hex digest. No I/O.
  - `hashRealityClaim(realityClaim)` *(closure row 15)* — unchanged: canonical-JSON-then-sha256
    content hash, mirrors the plugin's own `computeContentDigest` precedent (VERIFIED,
    `vcsdd-state.js:395-412`).
  - `validateArtifactProvenance(verdict, capturedArtifacts, claimType, requiredArtifactCount,
    groundTruth)` *(closure rows 1-4, 6-8, 14, 19, 20 — EXTENDED this iteration)* — pure,
    open/growable condition set:
    - citation presence (row 1), identity resolution (rows 2-4), URL-identity + no-redirect
      via the redesigned `canonicalizeUrl` (rows 14, 20), status gate (row 8), distinctness +
      count (rows 6-7) — all as previously specified, `groundTruth.claimedUrls` is the locator
      set matched against.
    - **NEW, only when `groundTruth.mode === "caller-per-invocation"`**: a SEPARATE citation
      resolving to `groundTruth.fixedPublicSurfaceUrl` must be present (same identity/status
      rules) whose `referencedArtifactIds` contains the locator's canonical identifier (row
      19, `not_on_fixed_surface` violation otherwise); the locator row's `contentHash` must
      equal `groundTruth.precommit.contentFingerprint` (row 19, `fingerprint_mismatch`
      otherwise); `groundTruth.precommit.ts` must be strictly earlier than the capturing
      pass's start `ts` (row 19, `precommit_not_before_action` otherwise).
    - On ANY violation: returns a NEW verdict (never mutates inputs) with `overallVerdict:
      "FAIL"` and an added `post_not_publicly_visible` finding naming the specific shortfall.
      Otherwise returns the input unchanged (fresh reference).
  - `enforceVerdict(rawVerdict, capturedArtifacts, claimType, requiredArtifactCount,
    groundTruth, automatedVerification)` *(new, closure rows 18, 21 — the FIND-H/K/L fix)* —
    pure composition, in order: `validateVerdictShape(rawVerdict)` (malformed ⇒ synthesize a
    `FAIL` verdict, never pass malformed data further) → `automatedVerification`-refusal
    (`automatedVerification !== true` — including `undefined`, FIND-K's fail-closed default ⇒
    a synthesized `FAIL`/refusal result, never a silent automated PASS) →, for a
    public-artifact `claimType`, `validateArtifactProvenance(...)`. Returns the FINAL,
    ENFORCED verdict. This is the ONLY function either invocation path may treat a raw LLM
    verdict as accepted through — by construction, there is no remaining "did the caller
    propagate the result correctly" question (closure row 9 is now trivially true: the
    function's return value IS what gets recorded, full stop).
  - `decideConvergenceGate(state, realityClaim)` *(closure rows 11, 15)* — unchanged: hash-
    bound, SKIP-aware VCSDD convergence decision, shared between the pre-push guard and the
    standalone backstop.
  - `buildVerdictTrailPath`/`buildVerdictTrailLine`/`buildArtifactTrailPath` — unchanged.
- **Effectful Shell**:
  - `.claude/agents/reality-verifier.md` — LLM judgment, out of unit-test scope.
  - `skills/self/reality-verify-spawn.sh` *(REDESIGNED, closure row 18)* — was a detached
    `tmux new-session -d` (fire-and-forget, nothing read the result — VERIFIED by reading the
    CURRENT real file, iteration-4 review's own citation); now a BLOCKING `claude -p
    "$TASK" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" --output-format
    text` invocation under `timeout 600` (mirrors `gig_reality_verify.sh`'s own real, working
    blocking-judge pattern, VERIFIED), after which THIS SAME SCRIPT reads the `RESULT` file +
    `artifacts.jsonl`, calls `enforceVerdict`, and appends the ENFORCED result to REQ-006's
    trail — the single call site through which every runtime verdict passes, for every caller.
  - `skills/self/scripts/public_artifact_snapshot.py` *(extended, REQ-015)* — effectful: real
    network fetch; now also populates `contentHash`/`referencedArtifactIds` fields (extraction
    mechanics Phase-2a/platform-specific, per closure row 17's existing diagnosability-gating
    pattern).
  - `skills/self/reality-precommit.mjs` *(new, closure row 19)* — effectful: append-only jsonl
    write of `{ts, loopName, contentFingerprint}`, called by a posting loop BEFORE it posts.
  - The VCSDD gate script (`skills/self/vcsdd-reality-gate.mjs`) *(REDESIGNED, closure row
    18)* — effectful: calls `reality-verify-spawn.sh` (subprocess) or `require()`s
    `enforceVerdict` directly for an already-enforced verdict — contains NO parallel
    reimplementation of provenance-checking logic (grep-checkable); layers only
    `hashRealityClaim` + `recordGate` on top.
  - `.claude/commands/vcsdd-reality.md` — instructional, not code.
  - `.githooks/pre-push`'s Reality Convergence Guard section — effectful read, pure decision
    (`decideConvergenceGate`); AUTHORITATIVE for path (i) only, explicitly not
    adversarial-insider-proof (closure row 16).
  - `skills/self/tests/test_reality_convergence_guard.*` — regression-lock test, mirrors
    `test_cadence_evidence.py`/`test_cadence.py`.
  - `.claude/settings.json`'s `hooks.PreToolUse` entry — retained, non-authoritative.
  - `skills/self/verify-reality-gate.mjs` — effectful read, pure decision; standalone +
    library for the pre-push guard.

## Proof Obligations (organized by the behavioral-spec's threat-closure table; path column shows which invocation path(s) each PROP actually exercises)

| ID | Closure row | Path | Description | Tier | Required | Tool |
|----|---|---|---|---|---|---|
| PROP-001..009 | — | (i)+(ii) | Unchanged, inherited (category catalog, path helpers, base `validateVerdictShape`) | — | true | (see base feature) |
| PROP-010 | 2 | (i)+(ii) | Citation from `"cdp_nav_snapshot"` (via `enforceVerdict`) ⇒ `FAIL` | 1 | true | fast-check |
| PROP-011 | 3 | (i)+(ii) | Citation resolving to no row (via `enforceVerdict`) ⇒ `FAIL` | 1 | true | fast-check |
| PROP-012 | 4 | (i)+(ii) | Foreign `passId`/stale `ts` (via `enforceVerdict`) ⇒ `FAIL` | 1 | true | fast-check |
| PROP-013 | (positive control) | (i)+(ii) | For ANY verdict where `requiredArtifactCount` distinct citations ALL resolve cleanly (tool, pass, fresh, matching URL post-`canonicalizeUrl`, no redirect, 2xx) AND (for `caller-per-invocation`) fixed-surface + fingerprint + precommit-ordering ALL pass, `enforceVerdict` returns the verdict unchanged | 1 | true | fast-check |
| PROP-014 | (immutability) | (i)+(ii) | Never mutates inputs, all branches | 1 | true | fast-check |
| PROP-015 | — | (i)+(ii) | Path helpers deterministic, valid JSON | 1 | true | fast-check |
| **PROP-016/PROP-041** | **14, 20** | **(i)+(ii)** | **REDESIGNED (FIND-J fix)**: (016) `canonicalizeUrl` is idempotent; scheme/port/trailing-slash/fragment/allowlisted-tracking-param differences canonicalize equal; ANY path/host/non-allowlisted-query difference canonicalizes UNEQUAL. (041) Two distinct, real, query-identified artifacts differing ONLY in a non-allowlisted param (fixture: `?v=A` vs `?v=B`, mirrors YouTube's real identity scheme) canonicalize to DIFFERENT values and a citation for one does NOT satisfy `claimedUrls` naming the other — the direct fix for FIND-J's exact collision | 1 | true | fast-check (random URL-pair generation, including query-identified fixtures) + node:test |
| PROP-017 | — | (i)+(ii) | Prompt contains 7 categories, tool-invocation instruction (ground-truth-supplied URLs only), evidence-citation requirement | 0 | true | node:test |
| PROP-018/018b | 2/3 | (i)+(ii) | Example fixtures for PROP-010/011 | 1 | true | node:test |
| PROP-022 | 1 | (i)+(ii) | Zero-citation `PASS` (domExcerpt-only) ⇒ `FAIL`/`no_citation` | 1 | true | fast-check + node:test |
| PROP-023 | 6, 7 | (i)+(ii) | Under-count / duplicate-row padding ⇒ `FAIL` | 1 | true | fast-check + node:test |
| PROP-024 | 8 | (i)+(ii) | Non-2xx status ⇒ `FAIL` | 1 | true | fast-check + node:test |
| PROP-025 | 9 | (i)+(ii) | Subsumed by PROP-039 this iteration: `enforceVerdict`'s return value is definitionally what gets recorded — retained as the gate-script-level fixture check that `recordGate`'s argument equals that return | 0 | true | node:test |
| PROP-026 | 11 | (i) only | `SKIP` legality vs. `claimType` | 1 | true | fast-check |
| PROP-027 | 10, 15, 16 | (i) only | Diff-aware `.githooks/pre-push` live-fire: missing/FAIL ⇒ reject; matching-hash PASS ⇒ accept; stale-hash same-push-downgrade ⇒ reject | 0 | true | bash test invoking the real hook |
| PROP-028 | 14 | (i)+(ii) | Real, public, unrelated-URL citation ⇒ `FAIL`/`url_mismatch` (the named fix for FIND-D) | 1 | true | fast-check + node:test (exact FIND-D fixture) |
| PROP-029 | 14 | (i)+(ii) | Redirect off the artifact (login-wall/interstitial, HTTP 200) ⇒ `FAIL`/`redirect_off_artifact` | 1 | true | fast-check + node:test |
| PROP-030 | 14 | (i)+(ii) | Same URL cited twice does not satisfy a 2-distinct-URL requirement ⇒ `FAIL` | 1 | true | node:test |
| PROP-031 | 15 | (i) only | ANY hash mismatch ⇒ `blocked: true` regardless of stored `verdict` | 1 | true | fast-check |
| PROP-032 | 16 (discipline mitigation) | (i) only | Regression-lock test for the guard's own section; live-fire rejection when guarded files touched without a passing regression-lock test in range | 0 | true | bash test |
| PROP-019 | (retained, demoted) | (i) only | Convenience-layer hook script matches `decideConvergenceGate`, NOT a substitute for PROP-027/032 | 0 | true | bash/node test |
| PROP-020 | 13 (documents, doesn't close) | (ii) — live proof MUST run via `reality-verify-spawn.sh`, not only the gate script (FIND-H requirement) | Real fresh spawn, genuinely nonexistent URL ⇒ on-disk `FAIL` | 0 | true | manual/own-eyes run via the RUNTIME path, evidence committed |
| PROP-020b | 14 (live proof) | (ii), same runtime-path requirement as PROP-020 | Real fresh spawn, `claimedUrls` names URL A, only real content is at unrelated real URL B ⇒ on-disk `FAIL` | 0 | true | manual/own-eyes run via the RUNTIME path |
| PROP-021 | — | (i)+(ii) | `recordGate('reality','SKIP'\|'PASS','verifier'\|'human',...)` doesn't throw against the real, unmodified schema | 0 | true | node:test |
| PROP-033 | 17 (Phase-2a-gated) | (i)+(ii) — once required, the fixture applies to `enforceVerdict`, reachable from both | Instagram known-public vs. known-removed capture rows differ on the recorded signal AND `referencedArtifactIds`/`contentHash` extraction works | 0 | **true once Phase 2a records a signal; `pending` until then** | live fetch test |
| PROP-034 | 17 (mechanical, testable now) | (i)+(ii) — tests `enforceVerdict` directly, shared | `automatedVerification === false` (explicit) ⇒ `enforceVerdict` refuses an automated-verdict outcome for that claim; `reviewedBy: "human"` recording remains legal at the CALLER level | 0 | true | node:test |
| **PROP-035** | **19** | **(i)+(ii)** | `enforceVerdict`: locator resolves cleanly, IS on the fixed surface, but `contentHash !== groundTruth.precommit.contentFingerprint` (fixture: a real, old, unrelated post from the same account cited as the new claim) ⇒ `FAIL`/`fingerprint_mismatch` — the direct, named fix for FIND-I's exact exploit scenario | 1 | true | fast-check (random fingerprint mismatches) + node:test (exact FIND-I fixture) |
| **PROP-036** | **19** | **(i)+(ii)** | `enforceVerdict`: locator resolves cleanly and is otherwise correct, but NO citation for `groundTruth.fixedPublicSurfaceUrl` is present, OR its `referencedArtifactIds` does not include the locator ⇒ `FAIL`/`not_on_fixed_surface` | 1 | true | fast-check + node:test |
| **PROP-037** | **19** | **(i)+(ii)** | Distinct fingerprint-mismatch fixture: fresh, correctly-URLed, on-the-fixed-surface citation whose extracted content nonetheless differs from the precommitted fingerprint (content drift, not merely "an old post") ⇒ `FAIL`/`fingerprint_mismatch` | 1 | true | node:test |
| **PROP-038** | **21** | **(i)+(ii)** | `automatedVerification` OMITTED (not explicitly `false`) for `claimType !== "none"` ⇒ `enforceVerdict` refuses exactly as the explicit-`false` case (PROP-034) — the distinct fixture FIND-K's own critique demanded | 1 | true | fast-check (random claim objects with the field absent) + node:test |
| **PROP-039** | **18** | **(i)+(ii)** | `enforceVerdict` is unit-tested as the COMPOSITION of `validateVerdictShape` → `automatedVerification`-refusal → `validateArtifactProvenance`, proving each stage's rejection propagates through to the final return (a shape-invalid input never reaches the provenance check and still yields `FAIL`; an `automatedVerification:false` input never reaches the provenance check either and still yields refusal, not a silent PASS) | 1 | true | fast-check + node:test |
| **PROP-040** | **18** | **(ii) — the FIND-H-required runtime-path proof** | Fixture test: a stubbed verifier RESULT file (no live LLM call needed for this specific test) whose raw content would be `overallVerdict: "PASS"`, run through `reality-verify-spawn.sh`'s OWN post-spawn logic with a fixture `capturedArtifacts`/`groundTruth` that `enforceVerdict` would downgrade to `FAIL`, asserts the trail line THE SCRIPT ITSELF appends is `FAIL` — proving the runtime path actually rejects a verdict the module rejects, not merely "the module could reject it if called" | 0 | true | node/bash fixture harness driving `reality-verify-spawn.sh`'s real post-spawn code path with a stubbed RESULT file |

Closure rows 12, 13, and 16 have no `required: true` PROP claiming to CLOSE them — named,
accepted residual risk, not gaps this feature's proof obligations claim to close.

## Verification Strategy

- **Tier 0**: prompt content (PROP-017), demoted-hook logic (PROP-019), authoritative
  diff-aware pre-push proof (PROP-027) + its regression-lock (PROP-032), the runtime-path
  live proofs (PROP-020/020b — now REQUIRED to run via `reality-verify-spawn.sh`, not the gate
  script, per FIND-H), real-schema call-through (PROP-021), platform diagnosability
  (PROP-033, Phase-2a-gated), and the runtime-path enforcement proof (PROP-040).
- **Tier 1** (`fast-check`): all pure functions — `validateArtifactProvenance`
  (PROP-010..014, PROP-022..024, PROP-028/029, PROP-035/036), `canonicalizeUrl`
  (PROP-016/041), `enforceVerdict` (PROP-039), `decideConvergenceGate` (PROP-026, PROP-031),
  the `automatedVerification` default (PROP-038), and path helpers (PROP-015) — get
  exhaustive-style property coverage. PROP-018/018b/030/037 are named example-based fixtures
  for specific, concrete bypasses this spec explicitly demands proof against.
- **Tier 2/3**: not used.

## What this architecture explicitly does NOT verify (by design)

- Whether reality-verifier's LLM judgment on a REAL claim is correct — validated only by real
  own-eyes spawns (PROP-020/020b, now required via the runtime path specifically).
- **Closure row 12**: artifact-trail (and, as of this iteration, precommit-record) forgery by
  a Bash-capable adversarial verifier/loop. Explicitly accepted, inherited from
  `gig_reality_gate.py`/`cdp_nav_snapshot.py`'s identical gap, EXTENDED (not newly created) to
  cover the new precommit record: a fully coordinated forgery of both the precommit and the
  artifact trail is the same class of risk, not a new one REQ-015 introduces.
- **Closure row 13**: TOCTOU. Inherent; REQ-006's trail makes it discoverable in hindsight
  only.
- **Closure row 16**: local git hook bypass. Explicitly, permanently a discipline boundary,
  never a security boundary against an adversarial insider (FIND-F disposition, quoted
  verbatim in behavioral-spec.md). Relevant only to path (i) — REQ-011's runtime customer
  never touches this mechanism at all, so this limitation was never why the gate was unready
  for its stated first customer (iteration-4 review's own judgment, adopted).
- **Closure row 17**: platform diagnosability, INCLUDING the new `referencedArtifactIds`/
  `contentHash` extraction — an EMPIRICAL fact Phase 1c spec-writing did not and could not
  establish (no live fetches this session). The RULE (unproven ⇒ no automated verdict, on
  EITHER path — FIND-H's fix makes this true for both now) is verified now (PROP-034/038);
  WHICH platforms are proven, by which signal/extraction, is deferred to a required Phase 2a
  task (PROP-033, `pending`).
- Whether Claude Code composes project-level `.claude/settings.json` hooks additively with
  plugin-level `hooks.json` — remains an ASSUMPTION, explicitly IRRELEVANT to correctness
  since REQ-009 does not rely on it.
- Whether the plugin's `validateConvergenceForCompletion` will ever natively understand
  `gates.reality` — out of scope, and this feature is designed to be correct without it.
- Whether `gig_reality_verify.sh`'s independent pipeline should migrate onto this feature's
  spawn wrapper — explicitly out of scope.
- Whether a `caller-per-invocation` loop is honest about which URL it actually posted to,
  BEYOND what the fixed-surface-appearance + pre-committed-fingerprint checks (REQ-015) can
  establish — a fully coordinated, simultaneous forgery of the precommit record AND the
  artifact trail is not detectable by this feature and is explicitly folded into closure row
  12's already-accepted residual risk, not claimed as newly solved by REQ-015. REQ-015 closes
  the SPECIFIC, concrete exploit iteration-4's review demonstrated (an honest-looking, real,
  but wrong URL) — it does not claim to close full adversarial forgery, which no
  file-content-only check can, for the same reason row 12 was never claimed closed.
