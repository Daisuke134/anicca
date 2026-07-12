# Behavioral Spec: reality-gate (Phase 4.5 REALITY GATE, VCSDD pipeline extension)

Scope: `docs/superpowers/specs/2026-07-13-growth-engine-self-improving-promotion-skill-design.md`
§8b V0 / §8c (motivating gap analysis), in the `anicca-project` repo.
Builds on the already-shipped `reality-verifier` feature (see
`.vcsdd/features/reality-verifier/specs/behavioral-spec.md`) — this feature does NOT
re-implement reality-verifier; it (a) extends its category catalog and prompt from
money/ledger-only to any real-world side-effect claim, (b) generalizes its spawn wrapper,
(c) adds a durable per-loop verdict trail, (d) proves it is fail-closed with real negative
tests, and (e) wires it into VCSDD as a gate between adversarial review and formal hardening.

## Iteration history (Phase 1c)

| Iteration | Verdict | Findings | Disposition |
|---|---|---|---|
| 1 (`reviews/spec-review-01.md`) | FAIL | FIND-001 (recordGate enum crash), FIND-002 (backstop inspected the LLM's own prose instead of independently-captured evidence) | Fixed in iteration 2: schema-legal `recordGate` values; `validateArtifactProvenance` replacing prose-keyword-matching with structural, independently-read-artifact-trail provenance checks. |
| 2 (`reviews/spec-review-02.md`) | FAIL | FIND-001/003/004/005 **confirmed genuinely fixed** by independent re-verification. New: FIND-A (blocking — zero-citation PASS is never inspected, the exact FIND-002 threat through an unguarded second door), FIND-B (blocking — `gates.reality` is wired to no real enforcement point; the plugin's own convergence check has zero awareness of it), FIND-C (major — `claimType` provenance never pinned down, LLM could self-declare its way out of the strict check) | Fixed in this iteration (3), below — see "Threat-model closure" section and the per-requirement changes. This iteration deliberately closes the vulnerability **class** (self-reported/unenforced claims accepted as sufficient), not each individual instance, per explicit coordinator instruction after iteration 2. |

## Purpose (non-negotiable framing, carried over from reality-verifier)

VCSDD's existing agents each see only part of the truth:

| agent | tools (VERIFIED by reading agent frontmatter) | sees | cannot see |
|---|---|---|---|
| `vcsdd-adversary` (plugin, `agents/vcsdd-adversary.md`) | Read, Write, Edit, Grep, Glob | spec/code/test-output files on disk | **no Bash — cannot execute anything or drive a browser; "tests are green" is a file it reads** |
| `vcsdd-verifier` (plugin, phase 5 formal hardening) | Read, Write, Edit, Bash, Grep, Glob | property-test/fuzz/security/purity artifacts | scoped to formal proof, not real-world side effects |
| `reality-verifier` (`.claude/agents/reality-verifier.md`, this repo) | Read, Grep, Glob, **Bash**, no Write/Edit | the actual logged-out DOM / on-chain state / ledger files | cannot repair anything (correctly — repair is `self-fix.sh`'s job) |

Only `reality-verifier` can see ground truth in the real world. This feature makes it a
first-class gate in the pipeline instead of an optional side-script, and generalizes its
"did we earn honestly" framing to "is any claimed real-world side effect honest" (posted,
deployed, sent, earned) — **without letting the verifier's own self-written report become the
ground truth it is graded against, and without letting anything OTHER than a resolved,
independently-captured, correctly-scoped artifact citation ever produce a convergence-
accepted PASS** (iteration-2's core lesson: closing one door the wrong way just reopens the
same underlying vulnerability class through the next unguarded door — see "Threat-model
closure" below for the complete, adversarially-enumerated list of doors and how each is shut).

## Threat-model closure (read this section first — it is the spec's own completeness check)

Every possible path by which `gates.reality` (or a per-run verdict, REQ-006) could end up
`PASS` while the underlying artifact is NOT actually, publicly, currently visible, and how
each is closed. This table is itself a required artifact of this spec — a future iteration
that finds a 13th path has found a spec defect, not merely an implementation bug.

| # | Path to a false PASS | Status | Closed by |
|---|---|---|---|
| 1 | Verdict cites NO artifact-trail row at all (`domExcerpt`-only prose, or a bare `evidenceReviewed` entry) — the exact hole FIND-A named | **CLOSED** | REQ-004: `validateArtifactProvenance` is *default-closed* — for a public-artifact `claimType`, a `PASS` (or any finding suppressing a violation) with **zero** qualifying artifact-trail citations is unconditionally forced to `FAIL`, checked BEFORE any per-citation resolution logic runs, not as a side effect of it. |
| 2 | Citation resolves to a row produced by an authenticated-capture tool (e.g. `cdp_nav_snapshot`) | CLOSED (iter. 2, unchanged) | REQ-004 `tool` check — PROP-010/018. |
| 3 | Citation resolves to no real row at all (fabricated `filePath`/`lineRange`) | CLOSED (iter. 2, unchanged) | REQ-004 row-existence check — PROP-011/018b. |
| 4 | Citation resolves to a real row, but from a different/stale pass (foreign `passId` or pre-run `ts`) | CLOSED (iter. 2, unchanged) | REQ-004 `passId`/`ts` check — PROP-012. |
| 5 | The LLM self-declares `claimType` as something outside the public-artifact class (or the generic fallback) to escape the strict check entirely — FIND-C | **CLOSED** | REQ-013: `claimType` is never read from the verdict object; it is sourced ONLY from `reality-claim.json`, a committed, Phase-1a/1b-authored, Phase-1c-adversary-reviewed declaration file the LLM never writes and the gate script never lets it override. |
| 6 | A claim cites 1 of N required public URLs and still gets `PASS` | **CLOSED** | REQ-004 `requiredArtifactCount` (mirrors gig's `REQUIRED_COUNT`) — a deterministic, caller-supplied integer; the backstop requires that many DISTINCT resolved citations, not merely "at least one". |
| 7 | The same real row is cited N times to pad the count above | **CLOSED** | REQ-004 distinctness requirement — citations are deduplicated by `(passId, seq)` before counting against `requiredArtifactCount`. |
| 8 | A citation resolves cleanly (right tool/pass/time) but the row's own `httpStatus` shows the fetch actually failed (4xx/5xx) or the tool-level fetch itself errored | **CLOSED** | REQ-004 status-gate — the backstop deterministically rejects any counted citation whose `httpStatus` is outside `[200,299]` (or whose capture-tool `ok`/equivalent flag is false); this is a structured field the TOOL wrote, not prose interpretation, so it stays on the deterministic side of the judgment/determinism boundary. |
| 9 | The gate script itself calls `recordGate(..., 'PASS', ...)` without actually propagating `validateArtifactProvenance`'s (possibly downgraded) output | **CLOSED** | REQ-004 new acceptance criterion + PROP-023: the gate script's recording call is proven, by a fixture-level test, to always pass through the backstop function's actual returned `overallVerdict`, never a separate/hardcoded value. |
| 10 | `gates.reality` is recorded correctly but nothing ever checks it before a feature converges (plugin unaware, `PreToolUse` hook composition unverified, standalone backstop merely "can be" run) — FIND-B | **CLOSED** | REQ-009: required wiring into `.githooks/pre-push` (this repo's own already-proven, Claude-Code-independent "Cadence Contract Guard" pattern) as the AUTHORITATIVE enforcement point, with a live-fire proof obligation (PROP-024). The `PreToolUse` hook is explicitly demoted to a best-effort, non-authoritative fast-fail convenience layer only. |
| 11 | `gates.reality.verdict === "SKIP"` is recorded for a feature/loop that DOES have a real public-artifact claim (capture errored, or `--skip` misused), and `SKIP` is treated as convergence-sufficient | **CLOSED** | REQ-009/REQ-013: `SKIP` is convergence-sufficient **only** when `reality-claim.json` declares `claimType: "none"`. For every other `claimType`, `decideConvergenceGate` and the pre-push guard treat `SKIP` identically to `FAIL` — regardless of the literal stored value or any `--skip` invocation reason. This is an explicit rule, not left to interpretation (the coordinator's own stated position, adopted verbatim: "for a loop that claims a public artifact, SKIP must NOT be sufficient to converge"). |
| 12 | A fully adversarial, Bash-capable verifier hand-forges a fake row into `artifacts.jsonl` (fabricating `tool`/`passId`/`ts`/`httpStatus`) without ever calling `public_artifact_snapshot.py` | **NOT closed by this feature — explicitly accepted, inherited residual risk** | Identical, pre-existing gap in the already-shipped `gig_reality_gate.py`/`cdp_nav_snapshot.py` pattern this feature mirrors (VERIFIED by reading both files — no forgery-proofing exists there either). This feature does not claim to solve a problem its own mirrored precedent does not solve; own-eyes/fresh-adversary review remains the final backstop against a fully adversarial agent, project-wide, for both patterns. |
| 13 | TOCTOU: the artifact is genuinely public at verification time but is taken down/shadowbanned immediately afterward | **NOT closed by this feature — inherent to any point-in-time check** | Every real-world verification system (including gig's) has this property; not a bypass this design introduces. Mitigated only by REQ-006's durable trail making a later re-check's honesty history inspectable, not by preventing the gap from existing. |

Paths 12 and 13 are named, not hidden, per the explicit requirement that a complete spec must
be able to enumerate its own residual risk rather than imply zero risk exists.

## Purity boundary analysis (top-level, elaborated per-requirement below)

- **Pure / deterministic core** (side-effect-free, unit- and property-testable):
  - the finding-category catalog and its validators (`FINDING_CATEGORIES`,
    `isKnownCategory`, `validateVerdictShape` in
    `skills/self/lib/reality-verdict-schema.mjs`) — extended, not replaced;
  - path/line derivation for the durable verdict trail (REQ-006) and the artifact trail
    (REQ-012);
  - `validateArtifactProvenance(verdict, capturedArtifacts, claimType, requiredArtifactCount)`
    (REQ-004) — the default-closed, count-aware, status-gated provenance backstop (closure
    table rows 1-4, 6-8);
  - `decideConvergenceGate(state, realityClaim)` (REQ-009/013) — the SKIP-aware convergence
    decision (closure table row 11), shared byte-identical between the pre-push guard and the
    standalone backstop.
- **Effectful shell** (not unit-tested; verified only by real spawns / own-eyes review):
  - `.claude/agents/reality-verifier.md` — the LLM's own judgment when it actually reasons;
  - `skills/self/reality-verify-spawn.sh` — spawns a detached `claude` process;
  - `skills/self/scripts/public_artifact_snapshot.py` (REQ-012) — the deterministic
    logged-out capture tool; performs a real network fetch and writes a real file;
  - the gate script — sources `claimType`/`requiredArtifactCount` from `reality-claim.json`
    (REQ-013, never from the verdict), generates the pass id, spawns reality-verifier, reads
    the artifact trail, calls the pure backstop, appends the verdict trail line, and
    propagates the backstop's actual output verbatim into `recordGate()` (closure table
    row 9);
  - `.claude/commands/vcsdd-reality.md` — instructional command definition, not code;
  - `.githooks/pre-push`'s new Reality Convergence Guard section (REQ-009) — the
    AUTHORITATIVE, Claude-Code-independent enforcement point;
  - `.claude/settings.json`'s `hooks.PreToolUse` entry + `.claude/hooks/scripts/
    vcsdd-reality-gate-check.sh` (REQ-009) — explicitly demoted to best-effort convenience.

## Requirements

### REQ-001: `post_not_publicly_visible` finding category added, catalog stays backward compatible
**EARS**: WHEN reality-verifier checks a claim about a publicly-visible artifact (a post, a
deployed page, a published article) THE SYSTEM SHALL be able to emit a finding whose
`category` is exactly `post_not_publicly_visible`, distinct from the existing 6 money/ledger
categories, and existing consumers of `FINDING_CATEGORIES` (the schema's own
`validateVerdictShape`, and any code that reads the frozen array) SHALL continue to accept
every one of the original 6 categories unchanged.
**Edge Cases**:
- A consumer hardcodes a length-6 expectation of `FINDING_CATEGORIES` (VERIFIED: the current
  test `reality-verdict-schema.test.mjs` asserts the catalog is EXACTLY the 6 names via
  `deepEqual` — this test itself must be updated to 7 names as part of this feature; it is
  not "backward compatibility that must be preserved unchanged", it is the one place that
  must change deliberately).
- `gig_reality_gate.py`/`gig_judge.py` do NOT import `FINDING_CATEGORIES` at all (VERIFIED by
  reading `skills/earn/gig/scripts/gig_reality_gate.py` and `gig_reality_verify.sh` — gig's
  auditor is a fully separate, independent report-blind pipeline with its own verdict shape;
  it is unaffected by this change and is not a consumer to preserve compatibility for).
**Acceptance Criteria**:
- `FINDING_CATEGORIES` in `skills/self/lib/reality-verdict-schema.mjs` contains exactly 7
  entries: the original 6 plus `post_not_publicly_visible`.
- `.claude/agents/reality-verifier.md`'s "6 finding categories" section is updated to name
  and describe all 7, verbatim category names matching the array.
- `validateVerdictShape()` accepts a finding with `category: "post_not_publicly_visible"`
  when it carries citeable evidence, and rejects it when the evidence is uncited (same rule
  as every other category — REQ-006 of the reality-verifier spec, unchanged).

### REQ-002: `post_not_publicly_visible` is used specifically for report-vs-public-reality gaps
**EARS**: WHEN a loop's report claims an artifact was published/posted/deployed AND
independent evidence shows the artifact does not exist at the claimed public location, is not
reachable, or is reachable only to the authenticated account owner (not the public) THE
SYSTEM SHALL emit a `post_not_publicly_visible` finding rather than force-fitting the gap into
`narrate_only_claim` (which is for actions with NO evidence trail at all, not actions with
evidence that contradicts public visibility).
**Edge Cases**:
- The artifact exists publicly but with different content than claimed (e.g. wrong caption):
  this is a content-mismatch, not an invisibility finding — still `post_not_publicly_visible`
  is the closest category unless a more specific mismatch category is added later; the prompt
  MUST instruct the model to prefer the most specific applicable category and never suppress
  a finding for lack of a perfect-fit category name.
- Artifact URL check times out or the destination service itself is down (not a login issue):
  fail-closed per REQ-007 of the reality-verifier spec (unreachable ground truth = FAIL), the
  finding still uses `post_not_publicly_visible` since visibility could not be confirmed.
**Acceptance Criteria**:
- The agent prompt gives at least one concrete example distinguishing
  `narrate_only_claim` (no evidence attempted/found) from `post_not_publicly_visible`
  (evidence attempted, artifact confirmed absent/inaccessible/shadowbanned).

### REQ-003: Logged-out evidence MUST be independently captured, never the LLM's own prose, and its absence is itself a violation (closure rows 1, 5)
**EARS**: WHEN reality-verifier is asked to verify a claim of a *publicly visible* artifact
(a `claimType`, REQ-013, of `publish`/`post`/`deploy`) THE SYSTEM SHALL require that the
evidence backing any `PASS` — or backing the absence of a finding — for that claim was
produced by an independently-run, non-LLM-authored capture step (REQ-012's deterministic
tool), and a deterministic backstop (REQ-004), run on the verdict AFTER the LLM produces it
and BEFORE it is accepted by the caller, SHALL enforce this as a **default-closed** rule: the
absence of a qualifying citation is itself a violation, checked unconditionally, never merely
the absence of a detected problem among citations that happen to be present.
**Rejected designs (do not reintroduce)**:
1. (iteration-1 FIND-002) substring-matching the verdict's own free-text `evidence`/
   `evidenceReviewed` fields for tokens like `"9222"`/`"daily-driver"` — catches only a
   report that admits the violation in its own words.
2. (iteration-2 FIND-A) validating only citations that already carry a `filePath` — silently
   ignores (treats as a non-issue) any `PASS`/finding whose evidence is `domExcerpt`-only or
   a generic `evidenceReviewed` entry with no `filePath` at all, which `hasCiteableEvidence`
   (unmodified, `reality-verdict-schema.mjs:62-65`) accepts as fully sufficient on its own.
   The fix is NOT "also scan `domExcerpt` text for something" (that regresses to rejected
   design 1's class) — it is "require a resolvable artifact-trail citation to exist at all
   before a `PASS`/silence is legal", independent of what any prose field says.
**Edge Cases**:
- The same verification run also needs a logged-in check for something else (e.g. confirming
  an internal dashboard number) — that separate check MAY use the existing daily-driver
  CDP:9222 tab under the existing shared-lock rules (never duplicate/close the tab —
  `~/anicca/skills/earn/gig/scripts/cdp_lock.sh` is the established pattern for mutual
  exclusion with a loop's own core process); ONLY the public-visibility check itself must go
  through REQ-012's tool and be cited per REQ-004.
- `claimType` itself is never sourced from the verdict object (closure row 5) — see REQ-013;
  REQ-003's "public-artifact claim" trigger condition is always the deterministic,
  committed/caller-supplied `claimType`, never anything the LLM asserts about its own claim.
- No public URL exists to check at all (claim omits it) — fail-closed: `FAIL` with
  `post_not_publicly_visible`, not silently skipped.
- A determined agent with Bash could, in principle, hand-forge a fake row into the artifact
  trail file without actually calling the capture tool — explicitly named and accepted as
  closure-table row 12 (inherited from `gig_reality_gate.py`/`cdp_nav_snapshot.py`'s identical
  gap, not newly introduced here, and not something this feature claims to solve).
**Acceptance Criteria**:
- `.claude/agents/reality-verifier.md` contains an explicit instruction: for any
  public-artifact claim, call `skills/self/scripts/public_artifact_snapshot.py <passId> <seq>
  <label> <url>` (REQ-012) once per required public URL (REQ-004's `requiredArtifactCount`),
  using the pass id supplied in the task — never a freeform CDP/curl invocation of the
  model's own choosing for this specific check — and to cite each resulting row
  (`evidence.filePath` = the artifact trail path, `evidence.lineRange` = that row's line) in
  its verdict.
- `validateArtifactProvenance` (REQ-004) is unconditionally invoked by the gate script for
  every public-artifact-`claimType` verification, and its default-closed citation-count check
  runs BEFORE (and independent of) its per-citation resolution checks — proven by a unit test
  ordering assertion or, equivalently, by PROP-022 (zero-citation fixture) passing without
  requiring any citation to be present in the input at all.

### REQ-004: Provenance backstop — default-closed, count-aware, status-gated, and verbatim-propagated (redesigned again — closure rows 1, 6, 7, 8, 9)
**EARS**: WHEN reality-verifier emits `overallVerdict: "PASS"` (or omits a finding) for a
public-artifact claim THE SYSTEM SHALL require the deterministic backstop
`validateArtifactProvenance(verdict, capturedArtifacts, claimType, requiredArtifactCount)` to
independently confirm ALL of the following before letting the verdict stand unchanged; ANY
failure downgrades the verdict to `overallVerdict: "FAIL"` with an added
`post_not_publicly_visible` finding citing exactly which check failed:
1. **Citation presence (closure row 1)**: at least `requiredArtifactCount` DISTINCT
   `evidence.filePath`+`lineRange` (or `evidenceReviewed[].location` in the equivalent
   artifact-trail shape) citations are present in the verdict at all. Zero citations is
   itself a violation — this check runs first and unconditionally, not as a side effect of
   resolving citations that happen to exist.
2. **Resolution (closure rows 2-4, unchanged from iteration 2)**: each counted citation
   resolves to a REAL row in `capturedArtifacts` with `tool === "public_artifact_snapshot"`,
   matching `passId`, and `ts` at or after this run's start timestamp.
3. **Distinctness (closure row 7)**: citations are deduplicated by `(passId, seq)` before
   being counted toward `requiredArtifactCount` — citing the same row twice counts once.
4. **Count (closure row 6)**: the number of DISTINCT, resolved citations is `>=
   requiredArtifactCount` (a deterministic integer supplied by the caller — REQ-005/013,
   mirroring `gig_reality_gate.py`'s `REQUIRED_COUNT` pattern, VERIFIED by reading
   `gig_reality_verify.sh`'s `REQUIRED_COUNT=$(...len(DEFAULT_GROUND_TRUTH_URLS))` derivation
   — never an LLM-decided number).
5. **Status gate (closure row 8)**: every counted citation's row has `httpStatus` in
   `[200,299]` (or, for a headless-browser-variant row, its tool-level success flag is true) —
   this reads a STRUCTURED FIELD THE TOOL ITSELF WROTE, not prose interpretation, so it stays
   deterministic (the LLM's judgment is still what decides whether the CONTENT at a
   confirmed-2xx URL actually shows the claimed post — the backstop only gates reachability,
   never content).
`validateArtifactProvenance` never mutates its inputs (immutability rule) and never touches
`fs` itself (the `capturedArtifacts` array is always pre-read by the effectful gate script).
**Edge Cases**:
- A cited row exists, matches the pass id, but its `tool` field is `"cdp_nav_snapshot"` (gig's
  real, existing AUTHENTICATED capture tool name): rejected exactly as if no row existed
  (closure row 2).
- `requiredArtifactCount` is 0 or omitted by a buggy caller for a public-artifact `claimType`:
  THE SYSTEM SHALL treat this as a caller bug and default to `1` (never `0` — a
  `requiredArtifactCount` of `0` would make check 4 vacuous and reopen closure row 1), so the
  minimum bar for a public-artifact claim can never be configured away to nothing.
- The gate script must call `recordGate` with the EXACT `overallVerdict` `
  validateArtifactProvenance` returned, never a separately-computed or hardcoded value
  (closure row 9) — this is proven at the gate-script level, not just the pure-function
  level, by REQ-008's own acceptance criteria.
**Acceptance Criteria** (each is a required, `required: true` proof obligation in
verification-architecture.md — see PROP-022..026):
- A unit test feeds `validateArtifactProvenance` a `PASS` verdict with `requiredArtifactCount:
  1` and `findings`/`evidenceReviewed` containing ONLY `domExcerpt` (no `filePath` anywhere),
  and asserts `overallVerdict: "FAIL"` with `post_not_publicly_visible` (closure row 1,
  PROP-022 — this is the specific, named fix for FIND-A).
- A unit test feeds it a `PASS` citing a row from `"cdp_nav_snapshot"` (closure row 2,
  PROP-010/018, unchanged).
- A unit test feeds it a `PASS` citing a `filePath`+`lineRange` resolving to no row (closure
  row 3, PROP-011/018b, unchanged).
- A unit test feeds it a `PASS` citing a row with a foreign/stale `passId`/`ts` (closure row
  4, PROP-012, unchanged).
- A unit test feeds it `requiredArtifactCount: 2` with only 1 valid distinct citation, and
  asserts `FAIL` (closure row 6, PROP-023).
- A unit test feeds it `requiredArtifactCount: 2` with the SAME valid row cited twice, and
  asserts `FAIL` (closure row 7, PROP-023 — same obligation as the count check, since
  dedup-then-count is one combined rule).
- A unit test feeds it a `PASS` citing a resolved, correctly-tooled, fresh, distinct row whose
  `httpStatus` is `404`, and asserts `FAIL` (closure row 8, PROP-024).
- A fixture-level test of the gate script's recording call proves it always passes through
  `validateArtifactProvenance`'s actual returned `overallVerdict`, tested by constructing a
  scenario where the backstop downgrades a `PASS` to `FAIL` and asserting the value the gate
  script would hand to `recordGate` is `'FAIL'`, not the LLM's original `'PASS'` (closure row
  9, PROP-025).

### REQ-005: Generalized spawn wrapper — any claim type, deterministic count, backward compatible with the real existing caller
**EARS**: WHEN a caller needs to verify a real-world side-effect claim of any kind (`earn`,
`publish`, `post`, `deploy`) THE SYSTEM SHALL provide `skills/self/reality-verify-spawn.sh`
accepting `<loop-name> <artifact-or-public-url> [claim-text] [claim-type] [pass-id]
[required-artifact-count]`, where omitting `claim-type` defaults to `earn` (the pre-existing
behavior) so that `skills/self/reality-verify-on-new-earn.sh` — the one real existing caller
(VERIFIED by `grep -rl reality-verify-spawn` across the repo; `gig_reality_verify.sh`/
`gig_judge.py` do **not** call this script — see REQ-001 edge case) — continues to work with
zero changes to its 3-positional-argument invocation; omitting `pass-id` generates one
deterministically (mirrors `gig_reality_verify.sh`'s own `PASS_ID` pattern); omitting
`required-artifact-count` for a public-artifact `claim-type` defaults to `1` per REQ-004's
edge case (never `0`).
**Edge Cases**:
- `claim-type` is an unrecognized string: THE SYSTEM SHALL treat it as a generic
  "real-world side-effect claim" (fall through to the general narrate-only/evidence rules,
  no REQ-012 tool requirement) rather than erroring, since the spawn wrapper does not itself
  validate claim semantics — that is the agentic layer's job. (For the VCSDD-gate invocation
  path specifically, REQ-013 makes `claim-type` a committed, reviewed value rather than an
  ad-hoc CLI string — this generic wrapper-level default remains for the standalone
  loop-verification calling convention, REQ-011, which has no VCSDD state at all.)
- `claim-type` is a public-artifact type but `artifact-or-public-url` looks like a local
  filesystem path, not a URL: the spawned task text MUST still instruct "if this claim is
  about public visibility, find/derive the actual public URL yourself and check it via
  REQ-012's tool with THIS run's pass id" rather than silently treating a local path as
  sufficient evidence.
**Acceptance Criteria**:
- `test-reality-verify-spawn.sh`'s existing 3 assertion groups (A/B/C) still pass unchanged
  after this feature (regression baseline).
- A new DRYRUN assertion confirms `claim-type`, `pass-id`, and `required-artifact-count` are
  all threaded into the spawned task text when provided, with the documented defaults
  (`earn`, auto-generated, `1`) applied when omitted.

### REQ-006: Durable per-loop verdict trail
**EARS**: WHEN a reality-verifier verdict is produced for loop `<L>` THE SYSTEM SHALL, in
addition to the existing single-shot `RESULT` json file, append exactly one JSON line to
`$HOME/.openclaw/state/reality-verdict-<L>.jsonl` containing at minimum the timestamp,
`overallVerdict`, `findings` (or a summary count), and the `RESULT` file path, so a loop's
honesty history is inspectable over multiple days without needing to keep every individual
timestamped RESULT file.
**Edge Cases**:
- Two verdicts for the same loop arrive concurrently (two spawns racing): both lines MUST be
  appended (append-only, `O_APPEND`-safe write), never overwritten — this is the same
  durability property `earn-ledger.jsonl`/`audit-reality.jsonl` already rely on elsewhere in
  this repo.
- The jsonl file does not yet exist for a loop: created on first append, not required to
  pre-exist.
**Acceptance Criteria**:
- A pure path-derivation helper (`buildVerdictTrailPath(stateDir, loopName)`) exists, is
  deterministic, and is covered by a unit test (mirrors `buildResultPath`'s existing
  pattern).
- After a real (or test-fixture) verdict-producing run, `reality-verdict-<loop>.jsonl` exists
  and its last line parses as JSON matching the shape above.

### REQ-007: Negative test — fail-closed proof (a gate that cannot fail is not a gate)
**EARS**: WHEN reality-verifier's deterministic backstop (REQ-003/REQ-004) is given a FALSE
or unprovable claim THE SYSTEM SHALL produce `overallVerdict: "FAIL"` with at least one
finding, demonstrated by ALL of the following, none of which may be skipped:
1. All of REQ-004's unit-test bypass fixtures (PROP-010..012, PROP-018/018b, PROP-022..025) —
   the CI-runnable proof that the backstop cannot be fooled by prose, under-citation,
   duplicate citation, non-2xx status, or a mispropagated verdict.
2. A real, live fresh `reality-verifier` spawn against a genuinely nonexistent public URL,
   producing an actual on-disk FAIL verdict (own-eyes, not mocked — matching the
   reality-verifier verification-architecture's existing rule that mocking the LLM's judgment
   would itself be a fake-green failure).
**Edge Cases**:
- The chosen "nonexistent artifact" for the live proof must be unambiguous (e.g. a random-
  UUID path that returns 404) so the negative result cannot be attributed to a flaky network
  condition; if the live check is genuinely inconclusive (network down), THE SYSTEM SHALL
  retry once before treating it as proof — fail-closed still applies (unreachable ground
  truth from the target service is itself also a FAIL, satisfying the acceptance vehicle
  either way).
**Acceptance Criteria**:
- All REQ-004 bypass unit tests pass.
- A real, committed FAIL verdict json (or its jsonl line, REQ-006) exists under
  `.vcsdd/features/reality-gate/evidence/` (or `~/.openclaw/state/`, referenced by path) as
  the live-run artifact, produced by an actual spawn during Phase 2b/2c of this feature, not
  fabricated by hand.

### REQ-008: VCSDD Phase 4.5 REALITY GATE — `vcsdd-reality` command, project-level (not plugin cache), schema-legal gate values only
**EARS**: WHEN a VCSDD feature has passed adversarial review (plugin-internal phase `'3'`,
`gates['3'].verdict === 'PASS'`, VERIFIED by reading `scripts/lib/vcsdd-state.js`'s
`GATE_PREREQUISITES['5']`) THE SYSTEM SHALL provide a `/vcsdd-reality` command that spawns a
FRESH `reality-verifier` instance (zero context from the Builder/loop being verified, same
fresh-context discipline as `/vcsdd-adversary`), sources `claimType`/`requiredArtifactCount`
EXCLUSIVELY from that feature's committed `reality-claim.json` (REQ-013 — never from a CLI
flag chosen ad hoc at invocation time, and never from the verdict object), and records the
resulting verdict into the feature's `state.json` via the plugin's own exported
`recordGate(featureName, 'reality', verdict, reviewedBy, details)` function, called ONLY with
values legal under the plugin's own, unmodified `schemas/vcsdd-state.schema.json` (VERIFIED,
quoted verbatim):
```json
"verdict": { "type": "string", "enum": ["PASS", "FAIL", "SKIP"] },
...
"reviewedBy": { "type": "string", "enum": ["adversary", "verifier", "human"] },
```
i.e. `recordGate(featureName, 'reality', 'PASS'|'FAIL'|'SKIP', 'verifier', details)`, where
the `'PASS'|'FAIL'` value passed is ALWAYS the verbatim `overallVerdict` the backstop
(REQ-004) returned (closure row 9) and `details` ALWAYS includes `{claimType,
requiredArtifactCount}` sourced from `reality-claim.json` so downstream convergence checks
(REQ-009) never need to re-read the claim file to know whether `SKIP` is legal for this
feature.
**Edge Cases**:
- The plugin is later updated and overwrites `/Users/operator/.claude/plugins/cache/
  vcsdd-claude-code/vcsdd/1.0.0/` — THE SYSTEM SHALL NOT be affected, because none of this
  feature's files live under that cache path.
- A feature genuinely has no real-world claim to check (a pure library refactor): its
  `reality-claim.json` declares `claimType: "none"` at Phase 1a/1b (REQ-013) — this is
  authored and adversary-reviewed as part of the spec, not chosen at gate-invocation time —
  and `/vcsdd-reality` records `gates.reality = { verdict: "SKIP", timestamp, reviewedBy:
  "human", details: { claimType: "none", reason } }`.
**Acceptance Criteria**:
- Command file exists at `.claude/commands/vcsdd-reality.md` in THIS repo (`~/anicca`), not
  under the plugin cache path.
- The command's implementation instructions explicitly state: "read `claimType` and
  `requiredArtifactCount` from `.vcsdd/features/<name>/reality-claim.json` — NEVER accept
  them as a command-line flag, and NEVER read them from the spawned verifier's own output" —
  grep-checkable in the command file.
- After running it (or its Phase 2b/2c live proof, REQ-007), the active feature's
  `.vcsdd/features/<name>/state.json` contains a `gates.reality` object with `verdict`
  strictly one of `PASS`/`FAIL`/`SKIP`, `reviewedBy` strictly one of `adversary`/`verifier`/
  `human`, and `details.claimType` matching `reality-claim.json`'s declared value — written
  via `recordGate()` (never hand-edited).
- A unit test proves `recordGate(feature, 'reality', 'SKIP', 'verifier', {claimType:
  "none", ...})` and `recordGate(feature, 'reality', 'PASS', 'verifier', {claimType:
  "publish", ...})` both complete without throwing against the plugin's real, unmodified
  `vcsdd-schema.js`/`vcsdd-state.schema.json`.
- A fixture-level test proves the gate script's `recordGate` call always uses
  `validateArtifactProvenance`'s actual returned `overallVerdict`, never a hardcoded/optimistic
  value (closure row 9, PROP-025).

### REQ-009: Convergence requires the reality gate — 5 dimensions, not 4, enforced at a real, authoritative, Claude-Code-independent point (closure rows 10, 11)
**EARS**: WHEN a feature attempts to reach VCSDD completion (`currentPhase: "complete"`) THE
SYSTEM SHALL require, in addition to the plugin's existing 4-dimension check (VERIFIED by
directly reading `validateConvergenceForCompletion`, `vcsdd-state.js:1066-1125`, which
contains **zero** reference to `gates.reality` anywhere and will never be edited to add one —
REQ-008's own edge case forbids touching the plugin cache), that `decideConvergenceGate(state,
realityClaim)` returns `blocked: false`, where that decision is:
- `blocked: false` iff `gates.reality.verdict === "PASS"`, OR (`gates.reality.verdict ===
  "SKIP"` AND `realityClaim.claimType === "none"`);
- `blocked: true` in every other case, including: `gates.reality` missing entirely,
  `gates.reality.verdict === "FAIL"`, AND `gates.reality.verdict === "SKIP"` while
  `realityClaim.claimType !== "none"` (closure row 11 — **SKIP is never sufficient to
  converge for a feature/loop that has a real public-artifact or earn claim; only a genuine,
  resolved `PASS`, or an explicit `claimType: "none"` declaration made at spec time, can
  satisfy this gate**).
This decision SHALL be enforced by an AUTHORITATIVE, Claude-Code-independent mechanism —
this repo's existing `.githooks/pre-push` "Cadence Contract Guard" pattern (VERIFIED by
reading `.githooks/pre-push:18-30,75-96` in full: an already-proven, git-level, `core.
hooksPath=.githooks`-wired enforcement point that exists specifically because "a code
comment alone cannot stop a FUTURE commit from rewriting BOTH the guarded code AND its own
regression-lock test", and because this repo has no PR/CI infra) — NOT merely a Claude Code
`PreToolUse` hook, whose composition with the plugin's own hooks is unverified:
- `.githooks/pre-push` gains a new, analogously-named "Reality Convergence Guard" section,
  mirroring the Cadence Contract Guard's structure exactly: for every commit in the push
  range, detect any `.vcsdd/features/*/state.json` that is part of the diff and whose
  (post-push) content has `currentPhase: "complete"`; for each such file, run
  `decideConvergenceGate` (via `skills/self/verify-reality-gate.mjs`, REQ-004's shared pure
  function) against that exact file plus its sibling `reality-claim.json`; if `blocked: true`
  for any of them, abort the push (fail-closed, same `--no-verify` documented escape hatch
  the Cadence Contract Guard already uses — governed by existing CLAUDE.md HARD RULE #14, not
  redesigned by this feature).
- The `.claude/settings.json` `hooks.PreToolUse` entry + `.claude/hooks/scripts/
  vcsdd-reality-gate-check.sh` (VERIFIED against the real, observed project-hook convention,
  `anicca-project/.claude/settings.json:48-69`) is RETAINED but explicitly, permanently
  labeled **non-authoritative**: a best-effort fast-fail convenience layer only, whose
  composition with the plugin's own hooks is an acknowledged, unverified assumption. Nothing
  in this spec relies on it for correctness.
**Edge Cases**:
- A pre-existing feature (created before this gate existed) has no `reality-claim.json` at
  all: `decideConvergenceGate` SHALL treat a missing `reality-claim.json` identically to
  `gates.reality` missing — `blocked: true` — never inferring `claimType: "none"` by absence,
  because that would silently reopen closure row 11 for every feature that predates this one.
  Such features need one `/vcsdd-reality` run (which itself requires authoring
  `reality-claim.json` first, REQ-013) before they can converge going forward.
- The Reality Convergence Guard only fires when a `state.json` transition to `complete` is
  literally part of the pushed diff — a feature that reaches `complete` purely in a local,
  never-pushed state is not caught until it IS pushed; this matches the Cadence Contract
  Guard's own scope (push-time, not commit-time) and is an accepted, documented limitation,
  not a silent gap (git push is the last point before any of this repo's work becomes visible
  to another instance/loop, matching this repo's "no PR/CI infra" constraint).
**Acceptance Criteria**:
- `.githooks/pre-push` contains a new section, analogous in structure/header-comment style to
  the existing Cadence Contract Guard, that detects a pushed `state.json` reaching
  `currentPhase: "complete"` and runs `verify-reality-gate.mjs` against it — grep-checkable.
- A live-fire test invokes `.githooks/pre-push` directly (as `git push` would) against a
  fixture push range containing a `state.json` with `currentPhase: "complete"` and
  `gates.reality` missing/FAIL, and asserts the hook exits non-zero (push rejected); the same
  test with `gates.reality.verdict: "PASS"` (and a matching `reality-claim.json`) asserts exit
  zero. This is `required: true` (PROP-024 in verification-architecture.md).
- `decideConvergenceGate(state, realityClaim)` is unit-tested (property + example) to return
  `blocked: true` for every `(state, realityClaim)` combination where `realityClaim.
  claimType !== "none"` and `gates.reality.verdict !== "PASS"` — including the `SKIP` case
  explicitly (closure row 11, PROP-026).
- `.claude/settings.json` exists with a `hooks.PreToolUse` entry as described, and its own
  section header/comment (or the command file/spec prose referencing it) contains the literal
  words "non-authoritative" / "best-effort" / "fast-fail convenience" so no future reader
  mistakes it for the enforcement point.

### REQ-010: reality-verifier stays read-only; FAIL escalates to self-fix, never self-repairs
**EARS**: WHEN the reality gate (REQ-008) records `overallVerdict: "FAIL"` THE SYSTEM SHALL
NOT permit the gate script or `reality-verifier` itself to edit any source/spec/test file to
"fix" the failure; instead it SHALL invoke `skills/self/self-fix.sh <loop-or-feature-name>
"<blocker + concrete fix hint derived from the FAIL findings>"` (the same escalation pattern
`gig_reality_verify.sh` already uses when its own gate produces `verdict:false` — VERIFIED by
reading `gig_reality_verify.sh` step 6), so repair remains the sole responsibility of a
separate, full-power Sonnet fixer process, never the read-only verifier.
**Edge Cases**:
- `self-fix.sh` is already running for the same loop/feature (its own dedupe/staleness logic,
  VERIFIED present in `self-fix.sh`'s existing `tmux has-session`/age-check block) — the gate
  script's escalation call is itself idempotent-safe because `self-fix.sh` already
  short-circuits on a recent, still-progressing fixer; the gate script does not need its own
  separate dedupe.
- The gate script itself must remain free of `Write`/`Edit` tool usage where it runs inside a
  Claude Code session (i.e. it is implemented as a plain Bash/Node script invoked via `Bash`,
  not as logic embedded in an agent granted Write/Edit).
**Acceptance Criteria**:
- No file this feature adds grants `reality-verifier.md` `Write` or `Edit` (frontmatter
  `tools` stays exactly `["Read", "Grep", "Glob", "Bash"]`, unchanged from the existing
  feature — regression check).
- The gate script's FAIL path contains a literal call to `self-fix.sh` (grep-checkable) and
  does not itself invoke any file-editing operation.

### REQ-011: First customer / acceptance vehicle (documented, not implemented by this feature)
**EARS**: WHEN the growth-engine marketing loop (a separate, later feature per §8b G0/G1 of
the motivating spec) claims it posted a video to Instagram THE SYSTEM's reality gate SHALL be
able to prove or disprove that claim via REQ-002's `post_not_publicly_visible` category and
REQ-003/REQ-004/REQ-012's independently-captured, logged-out, count-and-status-gated
public-URL check, using the exact same `reality-verifier` agent and spawn wrapper this
feature ships — no growth-engine-specific verifier code is needed. This is a **standalone
loop-verification call** (REQ-005), not a VCSDD-feature convergence gate: the growth-engine
loop calls `reality-verify-spawn.sh` directly, per run, with `claim-type`/`required-
artifact-count` supplied as deterministic CLI arguments each time — it has no `state.json`,
no `gates.reality`, no `SKIP` concept, and no `reality-claim.json` (REQ-013 applies only to
the VCSDD-pipeline gate, REQ-008/009). A failed daily verification for the loop produces a
`FAIL` verdict + trail line (REQ-006) and escalates via REQ-010; it does not block anything
"converging" because a recurring loop has no convergence state to block.
**Edge Cases**: N/A — this requirement is a forward-compatibility acceptance statement, not
new behavior; it is satisfied by REQ-001..REQ-004/REQ-012 being general-purpose (claim-type-
parameterized, tool-parameterized by URL not by platform), not hardcoded to Instagram or any
single platform.
**Acceptance Criteria**:
- Nothing in `.claude/agents/reality-verifier.md`, `reality-verdict-schema.mjs`,
  `reality-verify-spawn.sh`, or `public_artifact_snapshot.py` after this feature names
  "Instagram" or any single platform.
- The distinction above (loop-verification calls never touch `reality-claim.json`/`SKIP`/
  convergence; only the VCSDD-gate path does) is stated explicitly in the gate script's own
  documentation/header comment, so a future reader cannot conflate the two invocation
  contexts and accidentally apply SKIP-for-convergence reasoning to a plain loop call (or vice
  versa).

### REQ-012: Deterministic logged-out capture tool (mirrors `cdp_nav_snapshot.py`, diverges on auth)
**EARS**: WHEN reality-verifier (or the gate script, for the negative-test proof) needs to
check a public URL THE SYSTEM SHALL provide `skills/self/scripts/public_artifact_snapshot.py
<passId> <seq> <label> <url>` — a deterministic, non-LLM script that performs the actual
network fetch, structurally never touches CDP port `9222` / the CloakBrowser daily-driver
session / any cookie jar, and appends exactly one row to
`$HOME/.openclaw/state/reality-artifacts/<passId>/artifacts.jsonl` containing at minimum
`{ts, passId, seq, label, tool: "public_artifact_snapshot", requestedUrl, finalUrl,
httpStatus, domExcerpt}` (REQ-004's status gate reads `httpStatus` directly from this row),
printing the artifact file path (or `ERROR:<reason>`) to stdout — never raising, so a failed
capture is itself evidence (an unreachable/erroring fetch, `httpStatus` absent or set to a
sentinel), not a crashed run.
**Exact mirror / exact divergence from `cdp_nav_snapshot.py` (VERIFIED by reading
`skills/earn/gig/scripts/cdp_nav_snapshot.py` in full)**:
| aspect | `cdp_nav_snapshot.py` (gig, logged-in) | `public_artifact_snapshot.py` (this feature, logged-out) |
|---|---|---|
| connection | connects to the LIVE CDP `:9222` daily-driver tab (`get_tab()`, `ws://localhost:9222/devtools/page/<id>`) — reuses the authenticated session on purpose | MUST NOT open any `:9222` connection at all — a plain HTTP(S) client (`urllib.request`/`requests`, or a freshly-spawned headless browser process with an ephemeral/incognito profile that is never attached to an existing CDP session) with no cookie jar loaded from any profile |
| what it proves | "the authenticated account's view of this page, right now" | "what the public, logged-out internet sees at this URL, right now" |
| evidence row shape | `{ts, pass_id, seq, label, requested_url, url, title, action, navigated_ok, png}` under `~/gig/trajectory/<pass_id>/` | `{ts, passId, seq, label, tool, requestedUrl, finalUrl, httpStatus, domExcerpt}` under `~/.openclaw/state/reality-artifacts/<passId>/` — a distinct directory tree AND a distinct, structurally-checkable `tool` field name |
| failure handling | never raises; screenshot captured regardless of `navigated_ok` | never raises; `httpStatus`/error captured regardless of reachability (fail-closed evidence either way; REQ-004 rejects non-2xx) |
| scoping | caller-side gate (`gig_reality_gate.py`) counts rows by `pass_id` + `min_ts`, independent of the judge's self-report | same scoping, plus count (`requiredArtifactCount`) and distinctness, reused verbatim by `validateArtifactProvenance` (REQ-004) |
**Edge Cases**:
- The target URL requires JavaScript rendering to show real content: THE SYSTEM SHALL prefer
  a headless-browser variant (fresh incognito profile, never CDP:9222) when the claim type is
  public-artifact-class and the target platform is known to be JS-rendered, falling back to
  the plain HTTP fetch otherwise — a fixed platform→method table, not an LLM judgment,
  decided in Phase 2a/2b implementation, not this spec.
- Rate limiting / bot-blocking (some platforms 403 logged-out requests from a bare `curl`):
  captured as `httpStatus: 403`, which REQ-004's status gate treats as a violation (outside
  `[200,299]`) — a legitimate false-negative risk for anti-bot-protected platforms, explicitly
  accepted: the LLM's judgment may note this in its findings as a caveat, but the deterministic
  gate does not special-case 403 into a pass, because doing so would reopen a path for a
  genuinely-blocked (and possibly genuinely-absent) artifact to be waved through.
**Acceptance Criteria**:
- `skills/self/scripts/public_artifact_snapshot.py` contains no import of, or reference to,
  port `9222` anywhere in its source (grep-checkable).
- Its artifact rows live under a directory tree distinct from `~/gig/trajectory/` and carry a
  `tool` field distinct from `"cdp_nav_snapshot"`.
- Every row includes an `httpStatus` field (integer, or an explicit error sentinel on total
  fetch failure) so REQ-004's status gate always has a value to check.

### REQ-013: `reality-claim.json` — committed, spec-reviewed, deterministic claim declaration (new — closes FIND-C and the SKIP question, closure rows 5, 11)
**EARS**: WHEN a VCSDD feature intends to be gated by `/vcsdd-reality` (REQ-008) THE SYSTEM
SHALL require that feature's Builder to author `.vcsdd/features/<name>/reality-claim.json`
during Phase 1a/1b, with shape `{claimType: "publish"|"post"|"deploy"|"earn"|"none",
requiredArtifactCount: <integer, omit or 1 if claimType is "none">, description: "<what
real-world thing this feature's acceptance vehicle claims, or why none exists>"}`, and this
file SHALL be treated as spec content: reviewed by the same Phase 1c fresh adversary that
reviews `behavioral-spec.md`, and NEVER writable by `reality-verifier` (no `Write`/`Edit`
grant, REQ-010) or by the gate script at runtime (the gate script only READS it).
**EARS (claimType provenance, closure row 5)**: WHEN the gate script or
`validateArtifactProvenance` needs `claimType`/`requiredArtifactCount` THE SYSTEM SHALL source
them EXCLUSIVELY from `reality-claim.json` — NEVER from `verdict.claimType` or any other field
the verifier LLM's own output populates, and NEVER from a CLI flag chosen ad hoc at
`/vcsdd-reality` invocation time (which would let a orchestrator, not just the LLM, silently
downgrade a feature's strictness without it being visible in reviewed spec content).
**EARS (SKIP legality, closure row 11)**: WHEN `decideConvergenceGate` (REQ-009) evaluates
whether `SKIP` is convergence-sufficient THE SYSTEM SHALL treat `reality-claim.json`'s
`claimType` as the SOLE source of truth: `claimType === "none"` makes `SKIP` legal;
`claimType` set to anything else (`publish`/`post`/`deploy`/`earn`) makes `SKIP` ALWAYS
equivalent to `FAIL` for convergence purposes, regardless of the literal stored
`gates.reality.verdict` string or any `--skip` invocation's stated reason.
**Edge Cases**:
- A feature's real-world claim genuinely changes mid-development (e.g. a feature originally
  scoped as a pure refactor grows a real side effect): `reality-claim.json` MUST be updated
  and MUST go back through Phase 1c review before `/vcsdd-reality`/convergence will accept the
  new `claimType` — it is spec content, governed by the same change-control as
  `behavioral-spec.md`, not a runtime-mutable config file.
- A pre-existing feature (predates this requirement) has no `reality-claim.json`: treated
  identically to `claimType` being unknown/unresolved — `decideConvergenceGate` blocks
  (REQ-009 edge case) rather than defaulting to `"none"`.
- `reality-claim.json` itself is malformed/unparseable: fail-closed — `blocked: true`, never
  silently treated as `claimType: "none"`.
**Acceptance Criteria**:
- The `vcsdd-reality` command file (REQ-008) and the gate script's documentation both state,
  grep-checkably, that `claimType`/`requiredArtifactCount` come ONLY from
  `reality-claim.json`.
- `reality-claim.json` is listed among the artifacts `/vcsdd-spec-review`'s Phase 1c review
  manifest covers for this feature going forward (a documentation/process requirement on this
  spec itself — `reality-gate`'s own `reality-claim.json`, once authored in Phase 2a, is the
  first instance of this rule being followed).
- A unit test proves: for a fixture `state` with `gates.reality.verdict: "SKIP"` and a
  fixture `realityClaim` with `claimType: "publish"`, `decideConvergenceGate` returns
  `blocked: true`; for the same `state` but `realityClaim.claimType: "none"`, it returns
  `blocked: false` (PROP-026, closure row 11 — the coordinator's stated position, adopted as
  an explicit, tested rule, not left as prose).

## Non-functional requirements

- **Performance bound**: a `/vcsdd-reality` spawn is capped at the same order of magnitude as
  the existing `gig_reality_verify.sh` judge spawn (600s timeout) — the gate script MUST NOT
  block the caller indefinitely; on timeout it records `gates.reality = { verdict: "FAIL",
  reviewedBy: "verifier", details: { claimType, requiredArtifactCount, reason: "timeout" } }`
  (fail-closed, never `SKIP`), never leaves the gate unset.
- **Security constraint**: no file added by this feature imports or calls a
  signing/keypair/private-key library (carried over from reality-verifier REQ-007).
- **Security constraint**: `validateArtifactProvenance`, `decideConvergenceGate`, and all
  other new pure functions have no network/file access, so they cannot be tricked by anything
  other than their explicit arguments.
- **Security constraint**: `public_artifact_snapshot.py` (REQ-012) is structurally incapable
  of authenticated access — no CDP client code path and no cookie-jar loading code path at
  all, not merely a prompt instruction not to use one.
- **Security constraint**: `reality-claim.json` is never written by any component that also
  produces the verdict being checked against it (REQ-013) — the same separation-of-duties
  principle that keeps `reality-verifier` read-only (REQ-010) applied to the claim
  declaration itself.

## Judgment vs determinism (anti-hardcoding discipline)

Per `~/.claude/rules/building-effective-ai-agents.md`: whether a report is "honest", whether a
finding fits `post_not_publicly_visible` vs `narrate_only_claim`, and whether a captured
`domExcerpt` at a confirmed-2xx URL actually shows the claimed content are all JUDGMENT
calls — the LLM (reality-verifier) makes them, guided by right-altitude prompt instructions
and concrete examples (REQ-002/REQ-004/REQ-012), never by keyword/regex classification. The
things implemented as deterministic code in this feature are, exhaustively: the fixed
category catalog membership check; the artifact-provenance check (does a required NUMBER of
DISTINCT, resolved, correctly-tooled, fresh, 2xx-status rows exist — all structural lookups
against independently-captured data, never prose interpretation); the SKIP/convergence
decision (a lookup against a committed, spec-reviewed `claimType`, never the verdict); jsonl
path derivation; and gate recording via the state library. Both iteration-1's rejected
substring-marker design and iteration-2's rejected citation-presence-optional design were, in
hindsight, the same underlying mistake at different granularities: treating the ABSENCE of a
detected problem as equivalent to the PRESENCE of a proof. This iteration's rule is the
correction, stated once, generally: **a public-artifact `PASS` requires affirmative, counted,
resolved, fresh, correctly-tooled, 2xx-status proof — never the mere absence of a caught
violation** — and every requirement in this spec that touches evidence (REQ-003/004/012/013)
is a specific application of that one general rule, not a standalone patch. If any future
change needs to decide "is this claim actually honest" via a regex/keyword rule over free
text, or accepts a `PASS`/`SKIP` on the basis of what was NOT found wrong rather than what WAS
affirmatively proven right, that is the anti-pattern this rule forbids and must be rejected in
review.
