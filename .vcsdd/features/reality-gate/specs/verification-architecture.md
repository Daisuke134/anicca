# Verification Architecture: reality-gate (Phase 4.5 REALITY GATE)

Companion to `.vcsdd/features/reality-verifier/specs/verification-architecture.md`. Read
`behavioral-spec.md`'s "Iteration history" and "Threat-model closure" sections first — this
file's proof-obligation table is organized by that same closure table (now 23 rows: 1-11,
14-15, 18-23 CLOSED; 17 MITIGATED; 12/13/16 explicitly OPEN). This iteration (6, a bounded,
scope-limited escalation grant per `escalations/escalation-01-spec-review.md`) is strictly
limited to FIND-M/N/O/P — see behavioral-spec.md's iteration-history row 5→6 disposition for
exactly what changed and why; every OTHER row/PROP in this file that is not touched by that
disposition is carried forward unchanged from iteration 5, which the fresh adversary
independently confirmed (FIND-H/I/J/K/L) as structurally, genuinely fixed.

## Purity Boundary Map

- **Pure Core** (`skills/self/lib/reality-verdict-schema.mjs`, extended in place):
  - `FINDING_CATEGORIES`, `isKnownCategory` — unchanged.
  - `validateVerdictShape(verdict)` *(extended this iteration)* — now also accepts
    `overallVerdict: "CANNOT_VERIFY"` as a legal third value alongside `PASS`/`FAIL` (the
    minimal, necessary extension to the BASE reality-verifier feature's own schema this
    iteration's 3-outcome design requires); a `CANNOT_VERIFY` verdict follows the SAME
    evidence-citation shape rules as `FAIL` (must cite what was checked, even if inconclusive)
    — this is the one place this iteration touches code shared with the base feature, kept to
    the minimum necessary.
  - `canonicalizeUrl(url)` — unchanged from iteration 5 (allowlist-only query stripping).
  - `computeContentFingerprint(content)` — unchanged.
  - `hashRealityClaim(realityClaim)` — unchanged.
  - `validateArtifactProvenance(verdict, capturedArtifacts, claimType, requiredArtifactCount,
    groundTruth, automatedVerification)` *(REDESIGNED this iteration — FIND-M/O fix,
    `automatedVerification` is now a PARAMETER of this function, not a precondition gating
    whether it is called)* — pure, returns one of `PASS`/`FAIL`/`CANNOT_VERIFY` per the fixed
    CONTRADICTION-vs-INCONCLUSIVE taxonomy (behavioral-spec.md REQ-004's table, reproduced
    here for the implementation's own reference):
    - CONTRADICTION violations (→ `FAIL`, checked FIRST, regardless of `automatedVerification`):
      `wrong_tool`, `no_matching_row`, `stale_row`, `url_mismatch`, `redirect_off_artifact`,
      `insufficient_count`, `duplicate_citation`, `server_confirmed_absent` (a genuine,
      server-returned non-2xx `httpStatus`), and, for `caller-per-invocation` claims,
      `not_on_fixed_surface`, `fingerprint_mismatch`, `precommit_not_before_action`.
    - INCONCLUSIVE violations (→ `CANNOT_VERIFY`, checked only if NO contradiction fired):
      `no_citation` (zero citations — reclassified this iteration, was `FAIL` before),
      `capture_network_error` (row records a network-level failure sentinel, never a real
      HTTP status — new, FIND-O), `capture_empty_body` (real 2xx, empty/near-empty body — new,
      FIND-O), and, checked LAST of all, `automated_verification_unproven` (everything else
      resolves cleanly, real 2xx, but `automatedVerification !== true`).
    - **CONTRADICTION (`artifact_trail_tampered`) — new, REQ-016/017, iteration 8 (FIND-U):** a
      row that EXISTS in the trail but whose `rowHmac` is absent / mis-signed / signed with a
      different pass's secret. This is positive evidence that the trail was written or modified
      by something other than the capture tool — it is NOT an absence of information and MUST
      NOT be classified INCONCLUSIVE. Without this row a lying loop can let the tool honestly
      capture a real 404 (a `FAIL`) and then corrupt those bytes with same-uid file access,
      laundering the `FAIL` into `CANNOT_VERIFY`. Forced by PROP-053 (tampered → `FAIL`) and
      PROP-054 (no row at all → `CANNOT_VERIFY`); the pair proves the two states are
      distinguishable.
    - If no violation of either class is found: returns the input verdict UNCHANGED
      (`PASS`), which requires `automatedVerification === true` to have been reachable at all
      (since `automated_verification_unproven` would otherwise have fired last).
    Never mutates inputs, never touches `fs`.
  - `enforceVerdict(rawVerdict, capturedArtifacts, claimType, requiredArtifactCount,
    groundTruth, automatedVerification)` *(REORDERED this iteration — the FIND-M fix, closure
    row 23)* — pure composition: (1) `validateVerdictShape(rawVerdict)` — malformed ⇒
    synthesize `CANNOT_VERIFY`/`malformed_verdict_shape` (an inconclusive condition: the
    checking apparatus's own output was unusable, not evidence of a lie — REJECTED iteration-5
    design: this used to synthesize `FAIL`, which is the wrong class per the ruling's own
    definition, "FAIL requires positive evidence of contradiction"); (2) if
    `rawVerdict.overallVerdict !== "PASS"`, return UNCHANGED (never second-guesses a raw
    `FAIL`/`CANNOT_VERIFY` the LLM itself already produced); (3) otherwise, for a
    public-artifact `claimType`, `validateArtifactProvenance(...)` UNCONDITIONALLY — reached
    regardless of `automatedVerification`, which is now consulted ONLY inside step (3), as its
    OWN last check. **Rejected design (iteration 5, do not reintroduce)**: running the
    `automatedVerification` refusal as a SEPARATE step BEFORE `validateArtifactProvenance` —
    this made the entire provenance backstop unreachable whenever `automatedVerification` was
    (correctly) `false`, producing a bare, indiscriminate `FAIL` for every claim on an
    unproven platform, with no distinction from a genuine contradiction. Returns the FINAL
    ENFORCED verdict, one of `PASS`/`FAIL`/`CANNOT_VERIFY`. The SOLE function either invocation
    path may treat a raw LLM verdict as accepted through.
  - `decideConvergenceGate(state, realityClaim)` — unchanged; still only ever consumes the
    schema-legal `PASS`/`FAIL`/`SKIP` mapping REQ-008 stores (`CANNOT_VERIFY` maps to a stored
    `verdict: "FAIL"` + `details.enforcementOutcome: "CANNOT_VERIFY"` before it ever reaches
    this function — see REQ-008).
  - `buildVerdictTrailPath`/`buildVerdictTrailLine`/`buildArtifactTrailPath` — unchanged; a
    NEW, analogous, minimal path helper for the human-review queue (REQ-010, e.g.
    `buildHumanReviewQueuePath(stateDir, loopName)`) is added, following the IDENTICAL pure
    pattern as `buildVerdictTrailPath` — deterministic, no I/O, unit-tested the same way.
- **Effectful Shell**:
  - `.claude/agents/reality-verifier.md` — LLM judgment, out of unit-test scope.
  - `skills/self/reality-verify-spawn.sh` *(EXTENDED this iteration — FIND-N fix, closure row
    22)* — unchanged blocking-spawn design from iteration 5, PLUS: `passId` generation is now
    INTERNAL to this script AND **UNPREDICTABLE** (FIND-Q fix, iteration 7 — orchestrator
    ruling). A time+PID scheme (`realityverify-$(date +%s)-$$`) is **REJECTED and forbidden**:
    the calling loop can derive it in advance (`bash "$SPAWN" & pid=$!` gives the parent the
    child's PID, and `date +%s` is a ~2-second search space), so it would let the loop under
    test pre-stage a forged `artifacts.jsonl` row under a passId it guessed — the exact
    pre-staging attack closure row 22 claims to close. Instead, `passId` MUST be drawn from a
    CSPRNG (e.g. `openssl rand -hex 16` / `uuidgen`, >= 128 bits of entropy) and the artifact
    trail directory MUST be created with an **exclusive** create that FAILS if the directory
    already exists (`mkdir` without `-p`). **A pre-existing directory at a freshly-drawn 128-bit
    CSPRNG name cannot be a collision or a stale leftover — it is proof that something observed or
    predicted the name and got there first. Per REQ-017's principle (positive evidence of tampering
    is a FACT, not an absence of facts) this yields `FAIL` / `artifact_trail_tampered`, NOT
    `CANNOT_VERIFY`** (corrected iteration 8 — an earlier draft of this line said `CANNOT_VERIFY`,
    which would have handed a watching loop the soft outcome it wants). Never silently reused.
    Both properties are load-bearing: entropy makes guessing infeasible, exclusive-create makes a lucky guess
    fail-closed instead of accepted. `passId` is still never read from any caller-facing
    argument or env var — the (former) `pass-id` positional argument is REMOVED from the
    accepted argument list entirely; on `CANNOT_VERIFY`, appends to the human-review queue (REQ-010) instead of
    invoking `self-fix.sh` — a distinct branch from the existing `FAIL`→`self-fix.sh` branch.
  - `skills/self/scripts/public_artifact_snapshot.py` *(edge cases specified, FIND-O fix)* —
    on a network-level failure, records the reserved `httpStatus` sentinel (never a real
    in-range code); on an empty body, records the real 2xx status with an empty/marked
    `domExcerpt` — both distinguishable, structurally, by `validateArtifactProvenance`'s
    taxonomy above.
  - `skills/self/reality-precommit.mjs` — unchanged.
  - The VCSDD gate script — unchanged wiring; `CANNOT_VERIFY` recording/routing rule mirrors
    the spawn wrapper's (REQ-008/010).
  - `.claude/commands/vcsdd-reality.md`, `.githooks/pre-push`'s guard section, `.claude/
    settings.json`'s `PreToolUse` entry — unchanged.
  - `$HOME/.openclaw/state/reality-needs-human-review-<loopName>.jsonl` *(new, minimal, REQ-010,
    closure row 23)* — an append-only jsonl queue, written only on `CANNOT_VERIFY`, following
    the IDENTICAL durability pattern REQ-006's verdict trail already establishes (no new
    subsystem, no new durability guarantee needed beyond what's already proven for that trail).

## Proof Obligations (organized by the behavioral-spec's threat-closure table; unchanged PROPs from iteration 5 are listed without re-derivation — only PROPs touched by FIND-M/N/O/P are elaborated)

| ID | Closure row | Path | Description | Tier | Required | Tool |
|----|---|---|---|---|---|---|
| PROP-001..021 | various | (i)+(ii) | **Unchanged from iteration 5** (category catalog, path helpers, base `validateVerdictShape`, `canonicalizeUrl`/PROP-016/041, prompt content, hash-mismatch PROP-031, live-fire PROP-027/032, real-schema PROP-021) — see prior iteration's table for full text; not reproduced here to keep this iteration's diff scoped to what actually changed, per the escalation ruling's "add no new scope" instruction | — | true | (unchanged) |
| **PROP-022** | **1** | **(i)+(ii)** | **RECLASSIFIED this iteration**: zero-citation `PASS` (domExcerpt-only) ⇒ `enforceVerdict` returns `overallVerdict: "CANNOT_VERIFY"`/`no_citation` — NOT `FAIL` as in iteration 5 (the ruling's own definition: absence of a diagnostic capture is inconclusive, not positive evidence of a lie). Still never a silent `PASS`; still blocks convergence identically via REQ-008's schema mapping | 1 | true | fast-check + node:test |
| PROP-023/024/028/029/030/035/036/037/041 | 6-8, 14, 19, 20 | (i)+(ii) | **Unchanged mechanism from iteration 5** — all remain CONTRADICTION-class, all still yield `FAIL`. Re-verified this iteration that each is tested with `automatedVerification: false` specifically (not only `true`), proving contradiction-detection does NOT depend on the flag (this is the direct, mechanical proof of REQ-011 scenario 3) | 1 | true | fast-check + node:test |
| PROP-025/039 | 9, 18 | (i)+(ii) | **PROP-039 updated fixtures this iteration**: `enforceVerdict`'s composition is unit-tested for (a) malformed shape → `CANNOT_VERIFY` (was `FAIL` in iteration 5, now corrected); (b) a raw verdict already `FAIL`/`CANNOT_VERIFY` passes through unchanged; (c) raw `PASS` + a contradiction present + `automatedVerification: false` → `FAIL` (contradiction checked BEFORE, and takes priority over, the automatedVerification gate — the direct proof that reordering did not weaken contradiction detection); (d) raw `PASS` + no contradiction + `automatedVerification: false` → `CANNOT_VERIFY`; (e) raw `PASS` + no contradiction + `automatedVerification: true` → `PASS` unchanged | 1 | true | fast-check + node:test |
| PROP-026/031 | 11, 15 | (i) only | Unchanged from iteration 5 | 1 | true | fast-check |
| PROP-027/032 | 10, 15, 16 | (i) only | Unchanged from iteration 5 | 0 | true | bash test |
| PROP-019 | — | (i) only | Unchanged from iteration 5 | 0 | true | bash/node test |
| PROP-020/020b | 13, 14 | (ii) | Unchanged from iteration 5 — both remain live, own-eyes proofs via the runtime path, both still `FAIL`-class (nonexistent URL; wrong-but-real URL) | 0 | true | manual/own-eyes run |
| PROP-033 | 17 | (i)+(ii) | **Status clarified this iteration (FIND-M part 4 fix)**: the Phase 2a diagnosability experiment is now a REQUIRED, SCHEDULED deliverable of this feature's own Phase 2a implementation (behavioral-spec.md REQ-012), not an optional/unscheduled future task. Acceptance criterion, stated exactly: "two captures (one real known-public Instagram post, one real known-removed/nonexistent Instagram post), materially different on a NAMED structured field the tool itself records — never DOM prose interpretation." If the direct post-URL fetch is not diagnostic, this PROP is satisfied instead by proving REQ-015's `fixedPublicSurfaceUrl`/`referencedArtifactIds` list-membership signal diagnostic (present vs. absent) — either satisfies this PROP; the spec names both as acceptable, per REQ-012's explicit fallback | 0 | **true as a Phase 2a deliverable of THIS feature; `status: pending` only in the sense that Phase 1c cannot itself run a live fetch — it is not optional, deferred, or "someone else's task"** | live fetch test against real Instagram URLs, per whichever signal Phase 2a records |
| PROP-034/038 | 17, 21 | (i)+(ii) | Unchanged from iteration 5 mechanism, but now understood correctly as testing the LAST check inside `validateArtifactProvenance` (REQ-004's reordered taxonomy), not a separate pre-step — the fixture shape is unchanged, only the composition it exercises is corrected | 1 | true | fast-check + node:test |
| **PROP-042** | **22** | **(i)+(ii)** | **NEW (FIND-N fix)**: `reality-verify-spawn.sh`'s artifact-trail directory is ALWAYS the script's own internally-generated `passId`, proven by a fixture/unit test that attempts to inject a caller-chosen value via every plausible channel (a `pass-id`-shaped positional argument, a `PASS_ID`/`passId`-named environment variable, or any other externally-suppliable input) and asserts NONE of them are honored — the directory used is always freshly generated inside the script, for every attempted injection channel | 1 | true | node/bash fixture harness driving the script's real passId-derivation code path |
| **PROP-043** | **23** | **(i)+(ii)** | **NEW (FIND-M fix, the central proof of this iteration)**: (a) a fixture with EVERY structural check clean (right tool/pass/URL/fixed-surface/fingerprint/count/status) and `automatedVerification: false` ⇒ `CANNOT_VERIFY`/`automated_verification_unproven`, proving the checks were actually reachable and executed (not merely "would have returned FAIL regardless"); (b) a COMPANION fixture identical to (a) except ALSO containing one contradiction (e.g. `url_mismatch`) ⇒ `FAIL`/`url_mismatch`, NOT `CANNOT_VERIFY` — proving contradiction detection is checked BEFORE, and takes priority over, the automatedVerification gate, so a dishonest loop cannot hide a real contradiction behind an unproven-platform excuse | 1 | true | fast-check (random combinations of contradiction-present/absent × automatedVerification true/false) + node:test (exact REQ-011 scenario-1 and scenario-3 fixtures) |
| **PROP-044** | **23** | **(i)+(ii)** | **NEW (FIND-O fix)**: a citation resolving to a row recording the network-error sentinel (never a real HTTP status) ⇒ `CANNOT_VERIFY`/`capture_network_error`, never `FAIL` and never treated as a resolvable citation for count purposes | 1 | true | fast-check + node:test |
| **PROP-045** | **23** | **(i)+(ii)** | **NEW (FIND-O fix)**: a citation resolving to a row with a real 2xx status but empty/near-empty `domExcerpt` ⇒ `CANNOT_VERIFY`/`capture_empty_body` | 1 | true | node:test |
| **PROP-046** | **23 (routing)** | **(i)+(ii)** | **RESTATED iteration 8 (FIND-V): this proves a SINGLE, FIRST `CANNOT_VERIFY` does NOT call `self-fix.sh`. It is NOT an unconditional no-self-fix rule — REQ-018/PROP-055 require that TWO CONSECUTIVE `CANNOT_VERIFY` verdicts DO escalate to `self-fix.sh`. The two are jointly satisfiable by one implementation and both are required.** **NEW (FIND-M part 2 fix)**: both `reality-verify-spawn.sh`'s and the gate script's post-enforcement logic contain, as two DISTINCT, grep-checkable code branches: `overallVerdict === "FAIL"` → calls `self-fix.sh`; `overallVerdict === "CANNOT_VERIFY"` → appends to the human-review queue and explicitly does NOT call `self-fix.sh` in that branch | 0 | true | grep-based static check + fixture harness confirming the correct branch executes for each of the 2 verdict values |
| **PROP-048** | **22 (FIND-Q fix)** | **(i)+(ii)** | **NEW (FIND-Q fix, iteration 7)**: `passId` unpredictability + tamper-evidence. Two required assertions: (a) the generated `passId` is drawn from a CSPRNG with >= 128 bits of entropy — a time+PID-derived value is a test FAILURE (a fixture that predicts `realityverify-$(date +%s)-$$` and finds it honored must fail the suite); (b) the artifact-trail directory is created with an EXCLUSIVE create — a fixture that pre-creates the directory (simulating a loop that guessed the passId and pre-staged a forged row) MUST cause the run to yield `FAIL` / `artifact_trail_tampered` (NOT `CANNOT_VERIFY` — a pre-existing dir at a 128-bit CSPRNG name is proof of observation/pre-staging, per REQ-017), never to reuse the directory and never to PASS | 0 | true | node/bash fixture harness driving the script's real passId-derivation + directory-creation code path |
| **PROP-047** | **18 (FIND-P fix — the missing PROP FIND-P named)** | **(i)+(ii) — BOTH callers' source files (FIND-R fix, iteration 7): the VCSDD gate script AND `skills/self/reality-verify-spawn.sh`, the runtime path. Scoping this check to the build-time gate script alone leaves the runtime customer — REQ-011's named first customer — with zero forcing check against shadow-reimplemented provenance logic, which is FIND-H reopening. "ONE module, TWO callers" must be proven on both callers or it is proven on neither.** | **NEW (FIND-P fix)**: a mechanical, grep-level static check (bookkeeping, not judgment — per the coordinator's own framing) scans **each caller's** source for definitions (not calls) of `canonicalizeUrl`, `validateArtifactProvenance`, `enforceVerdict`, `computeContentFingerprint`, `hashRealityClaim`, `decideConvergenceGate`, or any function body containing `httpStatus`/`referencedArtifactIds`/`contentHash` comparison logic, OUTSIDE `reality-verdict-schema.mjs`, and asserts ZERO matches — the direct, forcing proof for REQ-014's previously-unforced "zero duplicated provenance logic" acceptance criterion | 0 | true | grep/AST-based static check, run as part of the test suite |
| **PROP-049** | **12 (mitigation, REQ-016)** | **(i)+(ii)** | **NEW (FIND-S mitigation, iteration 7)**: a cited row with NO `rowHmac` is never counted as a valid capture (fixture: unsigned row → never `PASS`) | 0 | true | node fixture over `enforceVerdict` |
| **PROP-050** | **12 (mitigation, REQ-016)** | **(i)+(ii)** | **NEW**: a cited row whose `rowHmac` was computed under a DIFFERENT secret (simulating a forger who observed the `passId` but not the secret) is never counted as a valid capture | 0 | true | node fixture over `enforceVerdict` |
| **PROP-051** | **12 (mitigation, REQ-016)** | **(i)+(ii)** | **NEW**: the per-run HMAC secret never appears in the wrapper's argv, in any env var visible to the spawned loop/verifier, or anywhere under the artifact-trail directory (mechanical check — bookkeeping, not judgment) | 0 | true | grep/static check + process-args fixture |
| **PROP-052** | **12 (mitigation, REQ-016)** | **(i)+(ii)** | **NEW**: a VALID, correctly-signed row that CONTRADICTS the claim still yields `FAIL` — the signing layer must never become a new way to launder a contradiction into `CANNOT_VERIFY` | 0 | true | node fixture over `enforceVerdict` |
| **PROP-053** | **12 / 24 (REQ-017, FIND-U)** | **(i)+(ii)** | **NEW (FIND-U fix, iteration 8)**: a trail row whose bytes were MODIFIED AFTER signing (the exact FIND-U attack: honestly-captured real 404, then corrupted with same-uid file access) yields `FAIL` / `artifact_trail_tampered`. It MUST NOT yield `CANNOT_VERIFY`. This fixture IS the attack | 0 | true | node fixture: sign a row, mutate a byte, run `enforceVerdict` |
| **PROP-054** | **12 / 24 (REQ-017, FIND-U)** | **(i)+(ii)** | **NEW**: a trail with NO row at all for the claim yields `CANNOT_VERIFY` (paired with PROP-053, this proves "corrupted" and "absent" are distinguishable outcomes, not a shared fallback) | 0 | true | node fixture over `enforceVerdict` |
| **PROP-055** | **25 (REQ-018, FIND-V)** | **(i)+(ii)** | **NEW (FIND-V fix, iteration 8)**: TWO CONSECUTIVE `CANNOT_VERIFY` verdicts for the same loop fire a `self-fix.sh` escalation (fixture-level assertion on the escalation call, not on prose). Jointly satisfiable with PROP-046 (which covers only the FIRST one) | 0 | true | bash/node fixture asserting the escalation call |
| **PROP-056** | **25 (REQ-018, FIND-V)** | **(i)+(ii)** | **NEW**: a `CANNOT_VERIFY` pass's owner-facing report NEVER contains a verified/success framing and ALWAYS names why the read failed — every pass reports, silence is never an outcome | 0 | true | node fixture over the report renderer |

Closure rows 12, 13, and 16 have no `required: true` PROP claiming to CLOSE them — named,
accepted residual risk. Row 22 (FIND-N) and row 23 (FIND-M/O) are CLOSED this iteration, each
by the PROPs named above.

## Verification Strategy

- **Tier 0**: prompt content, demoted-hook logic, authoritative diff-aware pre-push proof +
  regression-lock, runtime-path live proofs (all unchanged from iteration 5), platform
  diagnosability (PROP-033, now explicitly a required Phase 2a deliverable, not merely
  "pending"), the runtime-path enforcement proof, and (new) the routing proof (PROP-046) and
  the no-duplicate-logic static check (PROP-047).
- **Tier 1** (`fast-check`): all pure functions, including the reordered
  `validateArtifactProvenance`/`enforceVerdict` (PROP-039/043) and the new capture-failure
  fixtures (PROP-044/045).
- **Tier 2/3**: not used.

## What this architecture explicitly does NOT verify (by design)

Unchanged from iteration 5 (closure rows 12, 13, 16, the hook-composition assumption, the
plugin's own convergence check never natively understanding `gates.reality`, `gig_reality_
verify.sh` migration, and the "loop honest about which URL it posted to BEYOND fixed-surface+
fingerprint" boundary) — none of those disclosures are affected by this iteration's scope
(FIND-M/N/O/P). One addition:

- **Whether a `CANNOT_VERIFY` outcome will, in practice, ever actually get resolved** (i.e.
  whether Phase 2a's diagnosability experiment, or a human reviewing the escalation queue,
  actually runs) — this feature specifies the MECHANISM (the queue, the required-but-not-yet-
  run PROP-033) but does not, and cannot from a Phase-1c spec, guarantee operational follow-
  through. This is analogous to (not the same as, but the same CLASS of limitation as) row 16's
  disclosure: a correctly-specified mechanism is not the same as a guarantee of its own
  execution in production. Named here explicitly rather than left implicit.
