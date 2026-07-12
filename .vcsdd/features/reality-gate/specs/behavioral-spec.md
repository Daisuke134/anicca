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
| 2 (`reviews/spec-review-02.md`) | FAIL | FIND-001/003/004/005 **confirmed genuinely fixed**. New: FIND-A (blocking — zero-citation PASS never inspected), FIND-B (blocking — `gates.reality` wired to no real enforcement point), FIND-C (major — `claimType` provenance never pinned down) | Fixed in iteration 3: default-closed citation-count check (FIND-A); required `.githooks/pre-push` wiring (FIND-B); `reality-claim.json` committed claim declaration (FIND-C). |
| 3 (`reviews/spec-review-03.md`) | FAIL | FIND-A/B/C **confirmed genuinely fixed at the named mechanism**. New: FIND-D (blocking — cited artifact row's URL never checked against the actually-claimed URL; the LLM could cite a real, unrelated, public page and still PASS), FIND-E (blocking — `gates.reality`'s verdict never bound to a specific version of `reality-claim.json`; same-push claim-downgrade and stale-PASS-after-strengthening both reach a false PASS), FIND-F (blocking, downgraded by orchestrator ruling to a disclosed limit, not a fixable gap — local git hooks are not a security boundary against an adversarial insider with shell access), FIND-G (major — no proof that the capture tool's signal is actually diagnostic for the named first-customer platform) | Fixed in this iteration (4), below. FIND-D closed by binding citations to a caller-supplied, immutable claimed-URL set with strict canonical-URL/no-redirect matching. FIND-E closed by hash-binding `gates.reality` to the exact `reality-claim.json` content it was checked against. FIND-F reclassified, per explicit orchestrator ruling (quoted verbatim below), from "blocking bug" to "disclosed, structural limit of any local-hook mechanism" — the closure table gains an explicitly OPEN row naming it, alongside a required diff-aware live-fire proof and a regression-lock test for the guard's own discipline-boundary value. FIND-G closed by making platform diagnosability an explicit, empirically-gated precondition — no platform may receive an automated `PASS` from an unproven signal. |

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
ground truth it is graded against, without letting anything OTHER than a resolved,
independently-captured, correctly-scoped, correctly-URLed artifact citation ever produce a
convergence-accepted PASS, and without letting a recorded PASS outlive the exact claim
content it was checked against** (the pattern across all three review iterations so far:
closing one door the wrong way reopens the same underlying vulnerability class through the
next unguarded door — see "Threat-model closure" below for the complete, adversarially
re-enumerated list of doors, honestly including the ones this spec cannot close).

## Threat-model closure (read this section first — it is the spec's own completeness check)

Every identified path by which `gates.reality` (or a per-run verdict, REQ-006) could end up
`PASS` while the underlying artifact is NOT actually, publicly, currently visible, and how
each is closed. This table is itself a required artifact of this spec. It has already been
revised twice after fresh review found paths not originally listed (rows 14-17 below are new
in this iteration); a future iteration that finds an 18th path has found a spec defect, not
merely an implementation bug. Rows explicitly marked OPEN are not defects by themselves —
claiming a row is closed without a required proof obligation forcing it would be the defect.

| # | Path to a false PASS | Status | Closed by |
|---|---|---|---|
| 1 | Verdict cites NO artifact-trail row at all (`domExcerpt`-only prose, or a bare `evidenceReviewed` entry) | CLOSED | REQ-004: default-closed citation-presence check, unconditional, before any resolution logic. PROP-022. |
| 2 | Citation resolves to a row produced by an authenticated-capture tool (e.g. `cdp_nav_snapshot`) | CLOSED | REQ-004 `tool` check. PROP-010/018. |
| 3 | Citation resolves to no real row at all (fabricated `filePath`/`lineRange`) | CLOSED | REQ-004 row-existence check. PROP-011/018b. |
| 4 | Citation resolves to a real row, but from a different/stale pass (foreign `passId` or pre-run `ts`) | CLOSED | REQ-004 `passId`/`ts` check. PROP-012. |
| 5 | The LLM self-declares `claimType` to escape the strict check entirely | CLOSED | REQ-013: `claimType` sourced ONLY from committed, Phase-1c-reviewed `reality-claim.json`, never the verdict. |
| 6 | A claim cites 1 of N required public URLs and still gets `PASS` | CLOSED | REQ-004 `requiredArtifactCount` (mirrors gig's `REQUIRED_COUNT`). PROP-023. |
| 7 | The same real row is cited N times to pad the count | CLOSED | REQ-004 distinctness dedup by `(passId, seq)`. PROP-023. |
| 8 | A citation resolves cleanly but the row's `httpStatus` shows the fetch actually failed | CLOSED | REQ-004 deterministic status gate (`[200,299]`, structured field). PROP-024. |
| 9 | The gate script calls `recordGate(..., 'PASS', ...)` without propagating the backstop's actual (possibly downgraded) output | CLOSED | REQ-004/008 verbatim-propagation requirement. PROP-025. |
| 10 | `gates.reality` is recorded but nothing ever checks it before convergence | CLOSED | REQ-009: required `.githooks/pre-push` "Reality Convergence Guard" wiring, authoritative. PROP-027. |
| 11 | `gates.reality.verdict === "SKIP"` recorded for a feature/loop with a real claim, treated as convergence-sufficient | CLOSED | REQ-009/013: `SKIP` legal only when `reality-claim.json.claimType === "none"`. PROP-026. |
| **14** | **(FIND-D) A citation resolves cleanly — right tool, right pass, fresh, 2xx — but for a completely different (real, public, unrelated) URL than the one actually claimed; OR the row's `finalUrl` shows a redirect off the claimed artifact (a login wall, an interstitial, a profile-root/home redirect) that a bare 200 status would otherwise let through** | **CLOSED** | REQ-004/REQ-013's new **claimed-URL binding**: `claimedUrls` is a caller-supplied, LLM-never-touches-it, deterministic list (from `reality-claim.json` for a spec-time-known URL, or a mandatory per-invocation argument sourced from the posting loop's own record for a per-run URL — REQ-005). `validateArtifactProvenance` requires `canonicalizeUrl(row.requestedUrl) === canonicalizeUrl(oneOf(claimedUrls))` AND `canonicalizeUrl(row.finalUrl)` equal to that SAME canonical value — i.e. no meaningful redirect at all is tolerated, which structurally rejects login-wall/interstitial/root redirects along with outright URL substitution. PROP-028/029/030. |
| **15** | **(FIND-E) `gates.reality`'s stored verdict is never re-checked against the CURRENT `reality-claim.json` — a same-push claim-downgrade, or a claim later strengthened without re-verification, both ride a stale/mismatched PASS to convergence** | **CLOSED** | REQ-008/009's new **claim-hash binding**: `recordGate` always stores `details.realityClaimHash = hashRealityClaim(realityClaim)` (a pure, deterministic content hash of the EXACT `reality-claim.json` the verification was run against). `decideConvergenceGate` recomputes the hash of the CURRENT `reality-claim.json` on every check and treats ANY mismatch — from the file changing after the gate was recorded, in either direction (weakened or strengthened) — identically to "no gate recorded" (`blocked: true`), regardless of the stored `verdict` string. PROP-031. |
| **16** | **(FIND-F) An agent with shell access bypasses `.githooks/pre-push` entirely** (`--no-verify`, `chmod -x .githooks/pre-push`, `git config --unset core.hooksPath`, or checking out a stale pre-REQ-009 copy of the hook into the working tree before pushing) | **OPEN — disclosed, structural limit, not a fixable gap** | See "Local-hook trust boundary (FIND-F disposition)" below for the full, non-paraphrased reasoning. Mitigated (not closed) by: (a) a diff-aware live-fire proof (PROP-027, extended) that at least proves the guard's OWN logic is correct and exercises a claim-downgrade-within-the-push scenario; (b) a regression-lock test for the guard's own code (PROP-032, mirroring `test_cadence_evidence.py`/`test_cadence.py`) so an accidental or lazy same-commit rewrite of both the guard and its test is still caught; (c) the SAME backstop already named for row 12 — a fresh-context `reality-verifier` spawned from OUTSIDE the loop being verified, plus recurring own-eyes/fresh-adversary review — is the actual defense against an adversarial insider, never the hook itself. |
| **17** | **(FIND-G) The capture tool's structured signal (`httpStatus`/`domExcerpt`) may not actually distinguish "publicly visible" from "private/removed/shadowbanned" for a given platform** — if it doesn't, every other row in this table closes a door that was never the real door; the gate becomes theater for that platform | **MITIGATED — empirically gated, fail-closed when unproven** | REQ-012's new **diagnosability precondition**: Phase 2a MUST empirically establish, against real known-public and real known-removed/private URLs on the named first-customer platform (Instagram, REQ-011), which structured signal reliably distinguishes them, and record the finding. Until proven for a given platform, `reality-claim.json` for a claim on that platform MUST declare `automatedVerification: false`, and `gates.reality`/loop verdicts for it may ONLY be recorded via `reviewedBy: "human"` (own-eyes), never `"verifier"` (automated) — an unproven platform cannot silently produce an automated PASS. PROP-033 (once the signal is chosen) + the `automatedVerification` gate itself (PROP-034, testable now, independent of which platform/signal). |
| 12 | A fully adversarial, Bash-capable verifier hand-forges a fake row into `artifacts.jsonl` without ever calling `public_artifact_snapshot.py` | NOT closed — accepted, inherited residual risk | Identical, pre-existing gap in `gig_reality_gate.py`/`cdp_nav_snapshot.py`. Own-eyes/fresh-adversary review is the project-wide backstop, for both patterns and for row 16. |
| 13 | TOCTOU: the artifact is genuinely public at verification time but is taken down/shadowbanned immediately afterward | NOT closed — inherent to any point-in-time check | REQ-006's durable trail makes a later re-check's dishonesty discoverable in hindsight, not prevented. **Named caveat (from iteration-3 review, not previously stated):** this feature does not itself re-check previously-verified URLs on a later day; a takedown of an old post is only rediscovered if a LATER feature/loop chooses to re-verify it, which is out of this feature's scope and not assumed solved. |

Rows 12, 13, and 16 are OPEN by explicit, reasoned disclosure, not by omission. A row is only
ever removed from "open" by adding a required, `required: true` proof obligation that forces
it — never by argument alone.

### Local-hook trust boundary (FIND-F disposition — orchestrator's reasoning, not paraphrased)

> An agent with shell access can bypass ANY local git hook (`--no-verify`, `chmod -x`, unset
> `core.hooksPath`, stale checkout). Therefore a local hook is not a security boundary against
> an adversarial insider — it is a discipline boundary against accident and drift, and that is
> all we should claim for it. Pretending otherwise is exactly the kind of false assurance this
> feature exists to kill.

This is adopted as this feature's own position, verbatim. Concretely, this spec makes exactly
these claims about `.githooks/pre-push`'s Reality Convergence Guard (REQ-009) and no more:

- It WILL catch: a normal, non-adversarial `git push` of a feature whose `gates.reality` is
  missing, `FAIL`, an illegally-`SKIP`ped claim, or bound to a stale/mismatched
  `reality-claim.json` (rows 1-11, 14, 15) — the everyday, non-adversarial path by which this
  colony's own loops and self-fix passes actually operate.
- It WILL NOT catch: an agent that deliberately disables or routes around the hook before
  pushing (row 16) — this is structurally identical to row 12's already-accepted forgery risk
  (both require the SAME pre-existing capability, unrestricted Bash on the pushing worktree,
  that every loop in this colony already has by design) and is defended the same way: a
  fresh-context `reality-verifier` spawned from OUTSIDE the loop/session being verified
  (never the loop grading itself), plus recurring own-eyes/fresh-adversary review — never a
  local hook, for either row.
- The regression-lock test (PROP-032) does not change this boundary — it only prevents an
  ACCIDENTAL or lazy (non-adversarial) same-commit erosion of the guard and its own test
  together, the exact failure class `.githooks/pre-push`'s own pre-existing Cadence Contract
  Guard was built to catch (VERIFIED, `.githooks/pre-push:18-30`: "a code comment alone cannot
  stop a FUTURE commit from rewriting BOTH the guarded code AND its own regression-lock test —
  that is the exact failure class already proven once"). A determined adversarial bypass
  (row 16) does not run the regression-lock test at all, by definition, so the test is a
  discipline tool, not a security one, exactly like the hook it protects.

## Purity boundary analysis (top-level, elaborated per-requirement below)

- **Pure / deterministic core** (side-effect-free, unit- and property-testable):
  - the finding-category catalog and its validators (`FINDING_CATEGORIES`,
    `isKnownCategory`, `validateVerdictShape` in
    `skills/self/lib/reality-verdict-schema.mjs`) — extended, not replaced;
  - path/line derivation for the durable verdict trail (REQ-006) and the artifact trail
    (REQ-012);
  - `canonicalizeUrl(url)` (new, REQ-004/013, closure row 14) — deterministic URL
    normalization (scheme/host lowercased, default port stripped, query/fragment stripped,
    trailing slash normalized except for a bare root path), no I/O;
  - `hashRealityClaim(realityClaim)` (new, REQ-008/013, closure row 15) — deterministic
    canonical-JSON-then-sha256 content hash, no I/O beyond CPU-bound hashing (mirrors the
    plugin's own `computeContentDigest`/`crypto.createHash` precedent in `vcsdd-state.js`);
  - `validateArtifactProvenance(verdict, capturedArtifacts, claimType, requiredArtifactCount,
    claimedUrls)` (REQ-004) — the default-closed, count-aware, status-gated, URL-bound
    provenance backstop (closure rows 1-4, 6-8, 14);
  - `decideConvergenceGate(state, realityClaim)` (REQ-009/013) — the SKIP-aware,
    hash-bound convergence decision (closure rows 11, 15), shared byte-identical between the
    pre-push guard and the standalone backstop.
- **Effectful shell** (not unit-tested; verified only by real spawns / own-eyes review):
  - `.claude/agents/reality-verifier.md` — the LLM's own judgment when it actually reasons;
  - `skills/self/reality-verify-spawn.sh` — spawns a detached `claude` process; now also
    threads `claimed-urls` (REQ-005);
  - `skills/self/scripts/public_artifact_snapshot.py` (REQ-012) — the deterministic
    logged-out capture tool; performs a real network fetch and writes a real file;
  - the gate script — sources `claimType`/`requiredArtifactCount`/`claimedUrls` from
    `reality-claim.json` plus (for a per-invocation URL) a mandatory caller argument, never
    from the verdict; generates the pass id; spawns reality-verifier; reads the artifact
    trail; calls the pure backstop; appends the verdict trail line; computes
    `hashRealityClaim` and stores it in `recordGate`'s `details`; propagates the backstop's
    actual output verbatim into `recordGate()`;
  - `.claude/commands/vcsdd-reality.md` — instructional command definition, not code;
  - `.githooks/pre-push`'s new Reality Convergence Guard section (REQ-009) — the
    AUTHORITATIVE, Claude-Code-independent (but NOT adversarial-insider-proof — see FIND-F
    disposition above) enforcement point;
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
  `deepEqual` — this test itself must be updated to 7 names as part of this feature).
- `gig_reality_gate.py`/`gig_judge.py` do NOT import `FINDING_CATEGORIES` at all (VERIFIED) —
  not a consumer to preserve compatibility for.
**Acceptance Criteria**:
- `FINDING_CATEGORIES` in `skills/self/lib/reality-verdict-schema.mjs` contains exactly 7
  entries: the original 6 plus `post_not_publicly_visible`.
- `.claude/agents/reality-verifier.md`'s category section is updated to name and describe all
  7, verbatim category names matching the array.
- `validateVerdictShape()` accepts a finding with `category: "post_not_publicly_visible"`
  when it carries citeable evidence, and rejects it when the evidence is uncited.

### REQ-002: `post_not_publicly_visible` is used specifically for report-vs-public-reality gaps
**EARS**: WHEN a loop's report claims an artifact was published/posted/deployed AND
independent evidence shows the artifact does not exist at the claimed public location, is not
reachable, or is reachable only to the authenticated account owner (not the public) THE
SYSTEM SHALL emit a `post_not_publicly_visible` finding rather than force-fitting the gap into
`narrate_only_claim`.
**Edge Cases**:
- Content-mismatch at an otherwise-public URL: still `post_not_publicly_visible`, closest
  category; prompt MUST instruct preferring the most specific applicable category.
- Timeout/service down: fail-closed per REQ-007 of the reality-verifier spec.
**Acceptance Criteria**:
- The agent prompt gives at least one concrete example distinguishing `narrate_only_claim`
  from `post_not_publicly_visible`.

### REQ-003: Logged-out evidence MUST be independently captured, never the LLM's own prose, and its absence is itself a violation (closure rows 1, 5)
**EARS**: WHEN reality-verifier is asked to verify a claim of a *publicly visible* artifact
(a `claimType`, REQ-013, of `publish`/`post`/`deploy`) THE SYSTEM SHALL require that the
evidence backing any `PASS` — or backing the absence of a finding — for that claim was
produced by an independently-run, non-LLM-authored capture step (REQ-012's deterministic
tool) FOR THE EXACT CLAIMED URL (REQ-004/013's `claimedUrls`, closure row 14) and a
deterministic backstop (REQ-004), run on the verdict AFTER the LLM produces it and BEFORE it
is accepted by the caller, SHALL enforce this as a **default-closed** rule: the absence of a
qualifying, correctly-URLed citation is itself a violation, checked unconditionally.
**Rejected designs (do not reintroduce)**:
1. (iteration-1 FIND-002) substring-matching the verdict's own free-text evidence fields.
2. (iteration-2 FIND-A) validating only citations that already carry a `filePath` while
   silently ignoring `domExcerpt`-only evidence.
3. (iteration-3 FIND-D) validating that A citation resolves cleanly without checking it is
   FOR THE CLAIMED URL — accepting any real, correctly-tooled, correctly-timed, 2xx row as
   sufficient regardless of which URL it actually captured. The fix is not "trust the LLM to
   pick the right URL" — it is "the LLM never picks the URL at all" (REQ-013).
**Edge Cases**:
- A separate, unrelated logged-in check MAY still use the daily-driver CDP:9222 tab under
  existing shared-lock rules; ONLY the public-visibility check for the CLAIMED URL must go
  through REQ-012's tool, against `claimedUrls`, and be cited per REQ-004.
- `claimType`/`claimedUrls` are never sourced from the verdict object — see REQ-013.
- No public URL exists to check at all (claim omits it, or `claimedUrls` is empty for a
  public-artifact `claimType`): fail-closed — this is itself a caller bug (REQ-004 edge case:
  the gate script MUST refuse to invoke the verifier at all rather than let it derive one).
- Artifact-trail forgery (closure row 12) and local-hook bypass (closure row 16) are
  explicitly accepted, disclosed residual risk, not something this requirement closes.
**Acceptance Criteria**:
- `.claude/agents/reality-verifier.md` contains an explicit instruction: for any
  public-artifact claim, call `skills/self/scripts/public_artifact_snapshot.py <passId> <seq>
  <label> <url>` (REQ-012) once per URL in the SUPPLIED `claimedUrls` list (never a URL the
  model derives itself) — never a freeform CDP/curl invocation for this specific check — and
  to cite each resulting row in its verdict.
- `validateArtifactProvenance` (REQ-004) is unconditionally invoked by the gate script for
  every public-artifact-`claimType` verification, and its default-closed citation-count and
  URL-match checks run BEFORE (and independent of) any other logic — PROP-022 (zero-citation)
  and PROP-028/029 (wrong-URL/redirect) both pass without requiring anything else in the
  input to be correct first.

### REQ-004: Provenance backstop — default-closed, count-aware, status-gated, URL-bound, and verbatim-propagated (closure rows 1, 6, 7, 8, 9, 14)
**EARS**: WHEN reality-verifier emits `overallVerdict: "PASS"` (or omits a finding) for a
public-artifact claim THE SYSTEM SHALL require the deterministic backstop
`validateArtifactProvenance(verdict, capturedArtifacts, claimType, requiredArtifactCount,
claimedUrls)` to independently confirm ALL of the following before letting the verdict stand
unchanged; ANY failure downgrades the verdict to `overallVerdict: "FAIL"` with an added
`post_not_publicly_visible` finding citing exactly which check failed. This list is
deliberately NOT presented as a fixed step count (an earlier iteration's "5-step contract"
was itself read, correctly, as an implicit claim of completeness that turned out to be
false) — it is an open, growable set of independent, all-must-pass conditions:
- **Citation presence** (closure row 1): at least `requiredArtifactCount` DISTINCT
  `evidence.filePath`+`lineRange` (or `evidenceReviewed[].location` in the equivalent
  artifact-trail shape) citations are present in the verdict at all. Zero citations is
  itself a violation, checked first and unconditionally.
- **Resolution — tool/pass/time** (closure rows 2-4): each counted citation resolves to a
  REAL row in `capturedArtifacts` with `tool === "public_artifact_snapshot"`, matching
  `passId`, and `ts` at or after this run's start timestamp.
- **Resolution — URL identity** (closure row 14, new): the resolved row's `requestedUrl`,
  after `canonicalizeUrl()`, equals `canonicalizeUrl()` of ONE of the caller-supplied
  `claimedUrls` (never a URL the verdict itself asserts, never a URL the LLM derived) — a
  citation for a real, correctly-tooled, correctly-timed, 2xx row that is nonetheless for the
  WRONG URL is rejected exactly as if it did not exist.
- **Resolution — no redirect off the artifact** (closure row 14, new): the resolved row's
  `finalUrl`, after `canonicalizeUrl()`, is IDENTICAL to the same canonical value as
  `requestedUrl`/the matched `claimedUrls` entry — i.e. `canonicalizeUrl()` deliberately
  normalizes ONLY scheme-upgrade and trailing-slash differences, and treats ANY OTHER
  difference (a different path, host, or a redirect to a login/interstitial/profile-root
  page) as a mismatch, rejected by the same rule as URL substitution. This is intentionally
  the strictest safe default: a legitimately-redirecting canonical/short URL simply must be
  captured and cited at its final form, not its redirecting form — false rejections here are
  acceptable (fail-closed), false acceptances are not.
- **Distinctness** (closure row 7): citations deduplicated by `(passId, seq)` before counting.
- **Count** (closure row 6): distinct, fully-resolved citations `>= requiredArtifactCount`
  (a deterministic integer, mirroring `gig_reality_gate.py`'s `REQUIRED_COUNT` pattern).
- **Status gate** (closure row 8): every counted citation's row has `httpStatus` in
  `[200,299]` (or, for a headless-browser-variant row, its tool-level success flag true) — a
  structured, tool-written field, never prose interpretation.
`validateArtifactProvenance` never mutates its inputs and never touches `fs` itself.
**Edge Cases**:
- `requiredArtifactCount` is `0`/omitted for a public-artifact `claimType`: defaults to `1`,
  never `0` (would make the count check vacuous, reopening row 1).
- `claimedUrls` is empty/omitted for a public-artifact `claimType`: THE SYSTEM SHALL treat
  this as a caller bug and refuse to invoke the verifier at all (fail before spawn, not a
  vacuous pass — there is no safe default URL to substitute).
- Two entries in `claimedUrls` canonicalize to the same value (caller error, e.g. accidental
  duplicate): harmless — resolution matches "one of" the set, duplicates don't loosen
  anything.
- The gate script must call `recordGate` with the EXACT `overallVerdict`
  `validateArtifactProvenance` returned, never a separately-computed value (closure row 9) —
  proven at the gate-script level (REQ-008).
**Acceptance Criteria** (each is a required, `required: true` proof obligation — see
verification-architecture.md PROP-022..031):
- Zero-citation `PASS` (domExcerpt-only, `requiredArtifactCount: 1`) → `FAIL` (row 1,
  PROP-022).
- Citation from `"cdp_nav_snapshot"` → `FAIL` (row 2, PROP-010/018).
- Citation resolving to no row → `FAIL` (row 3, PROP-011/018b).
- Citation with foreign/stale `passId`/`ts` → `FAIL` (row 4, PROP-012).
- **Citation whose resolved row's `requestedUrl` canonicalizes to a URL NOT in `claimedUrls`
  (a real, public, unrelated page) → `FAIL` (row 14, PROP-028 — the direct, named fix for
  FIND-D's exact exploit scenario).**
- **Citation whose resolved row's `finalUrl` canonicalizes differently from its
  `requestedUrl`/the matched `claimedUrls` entry (a login-wall/interstitial/root redirect,
  even with `httpStatus: 200`) → `FAIL` (row 14, PROP-029).**
- **`claimedUrls` containing the SAME URL as `requestedUrl` twice via two different citations
  that both resolve does not let one citation "stand in" for a DIFFERENT required URL not
  actually captured — `requiredArtifactCount: 2` with two citations of the identical URL
  → `FAIL` (row 14, PROP-030, closes a substitution variant of row 6/7's count check).**
- `requiredArtifactCount: 2` with only 1 valid distinct citation → `FAIL` (row 6, PROP-023).
- `requiredArtifactCount: 2` with the SAME row cited twice → `FAIL` (row 7, PROP-023).
- Citation with `httpStatus: 404` → `FAIL` (row 8, PROP-024).
- Gate-script fixture-level test proves `recordGate`'s verdict argument always matches the
  backstop's actual returned `overallVerdict` (row 9, PROP-025).

### REQ-005: Generalized spawn wrapper — any claim type, deterministic count and URLs, backward compatible with the real existing caller
**EARS**: WHEN a caller needs to verify a real-world side-effect claim of any kind THE SYSTEM
SHALL provide `skills/self/reality-verify-spawn.sh` accepting `<loop-name>
<artifact-or-public-url> [claim-text] [claim-type] [pass-id] [required-artifact-count]
[claimed-urls]`, where `claimed-urls` is a comma-separated, caller-supplied, deterministic
list (REQ-004's `claimedUrls`) — for a public-artifact `claim-type`, THE SYSTEM SHALL source
it from the SAME value already used as `artifact-or-public-url` when only one URL is claimed
(so existing single-URL callers need no new argument), or from the new explicit
`claimed-urls` argument for a multi-URL claim; the loop making a NEW post SHALL supply the
real URL it received back from the platform at post time (its own deterministic record —
never a value the reality-verifier LLM is asked to guess or derive). Omitting `claim-type`
defaults to `earn` (pre-existing behavior) so that `skills/self/reality-verify-on-new-earn.sh`
— the one real existing caller (VERIFIED by `grep -rl reality-verify-spawn`) — continues to
work unchanged; omitting `pass-id` generates one deterministically; omitting
`required-artifact-count` for a public-artifact `claim-type` defaults to `1`.
**Edge Cases**:
- `claim-type` unrecognized: generic real-world-side-effect handling, no REQ-012 tool
  requirement (standalone loop-verification convention, REQ-011, has no VCSDD state).
- A public-artifact `claim-type` invocation supplies NO URL at all (neither
  `artifact-or-public-url` nor `claimed-urls`): THE SYSTEM SHALL refuse to spawn (error,
  non-zero exit) rather than let the verifier derive one — mirrors REQ-004's "no safe
  default URL" rule.
**Acceptance Criteria**:
- `test-reality-verify-spawn.sh`'s existing 3 assertion groups (A/B/C) still pass unchanged.
- A new DRYRUN assertion confirms `claim-type`, `pass-id`, `required-artifact-count`, and
  `claimed-urls` are all threaded into the spawned task text when provided, with documented
  defaults applied when omitted, and that omitting the URL entirely for a public-artifact
  `claim-type` causes a non-zero exit before any spawn.

### REQ-006: Durable per-loop verdict trail
**EARS**: WHEN a reality-verifier verdict is produced for loop `<L>` THE SYSTEM SHALL, in
addition to the existing single-shot `RESULT` json file, append exactly one JSON line to
`$HOME/.openclaw/state/reality-verdict-<L>.jsonl` containing at minimum the timestamp,
`overallVerdict`, `findings` (or a summary count), and the `RESULT` file path.
**Edge Cases**:
- Concurrent verdicts: append-only, never overwritten.
- File does not yet exist: created on first append.
**Acceptance Criteria**:
- `buildVerdictTrailPath(stateDir, loopName)` exists, deterministic, unit-tested.
- After a real (or fixture) run, `reality-verdict-<loop>.jsonl`'s last line parses as JSON
  matching the shape above.

### REQ-007: Negative test — fail-closed proof (a gate that cannot fail is not a gate)
**EARS**: WHEN reality-verifier's deterministic backstop (REQ-003/REQ-004) is given a FALSE
or unprovable claim THE SYSTEM SHALL produce `overallVerdict: "FAIL"` with at least one
finding, demonstrated by ALL of the following:
1. All of REQ-004's unit-test bypass fixtures (PROP-010..012, PROP-018/018b, PROP-022..031).
2. A real, live fresh `reality-verifier` spawn against a genuinely nonexistent public URL,
   producing an actual on-disk FAIL verdict (own-eyes, not mocked).
3. A real, live fresh `reality-verifier` spawn against a genuinely DIFFERENT (real, public,
   but not-the-claimed) URL, with `claimedUrls` correctly set to the intended (nonexistent-at-
   that-URL) claim, producing an actual on-disk FAIL verdict — the live-run proof of FIND-D's
   closure (closure row 14), distinct from proof #2 (which proves "nothing exists" is caught;
   this proves "something else, real, exists" is also caught).
**Edge Cases**:
- Nonexistent-artifact proof: unambiguous (random-UUID 404 path); retry once if flaky before
  treating network-down as proof (still fail-closed either way).
- Wrong-URL proof: the "other real URL" MUST be genuinely unrelated (e.g. this repo's own
  public landing page) so the negative result cannot be attributed to platform flakiness.
**Acceptance Criteria**:
- All REQ-004 bypass unit tests pass.
- Both live FAIL verdict artifacts (nonexistent-URL and wrong-URL) are committed under
  `.vcsdd/features/reality-gate/evidence/`, produced by actual Phase 2b/2c spawns, not
  fabricated by hand.

### REQ-008: VCSDD Phase 4.5 REALITY GATE — `vcsdd-reality` command, project-level (not plugin cache), schema-legal gate values, claim-hash-bound
**EARS**: WHEN a VCSDD feature has passed adversarial review (`gates['3'].verdict ===
'PASS'`) THE SYSTEM SHALL provide a `/vcsdd-reality` command that spawns a FRESH
`reality-verifier` instance, sources `claimType`/`requiredArtifactCount`/`claimedUrls`
EXCLUSIVELY from that feature's committed `reality-claim.json` (REQ-013 — never a CLI flag,
never the verdict object), and records the resulting verdict into `state.json` via
`recordGate(featureName, 'reality', verdict, reviewedBy, details)`, called ONLY with values
legal under the plugin's own, unmodified `schemas/vcsdd-state.schema.json` (VERIFIED,
`"verdict": {"enum": ["PASS","FAIL","SKIP"]}`, `"reviewedBy": {"enum":
["adversary","verifier","human"]}`), where `details` ALWAYS includes
`{claimType, requiredArtifactCount, claimedUrls, realityClaimHash:
hashRealityClaim(realityClaim)}` (closure row 15, new) — the deterministic content hash of
the EXACT `reality-claim.json` this verification ran against, so `decideConvergenceGate`
(REQ-009) never has to guess whether a later-modified claim file still matches a stored
verdict.
**Edge Cases**:
- Plugin cache updates do not affect this feature — no files live there.
- A feature with `claimType: "none"` (REQ-013): `/vcsdd-reality` records `gates.reality = {
  verdict: "SKIP", timestamp, reviewedBy: "human", details: { claimType: "none",
  realityClaimHash, reason } }`.
- A claim on a platform where diagnosability is unproven (REQ-012/closure row 17,
  `automatedVerification: false`): `/vcsdd-reality` MUST NOT record `reviewedBy: "verifier"`
  at all for that claim — only a `reviewedBy: "human"` (own-eyes) recording is legal.
**Acceptance Criteria**:
- Command file exists at `.claude/commands/vcsdd-reality.md` in THIS repo, not the plugin
  cache.
- The command's implementation instructions state, grep-checkably: "read `claimType`,
  `requiredArtifactCount`, `claimedUrls` from `reality-claim.json` — NEVER a command-line
  flag, NEVER the spawned verifier's own output" AND "always compute and store
  `realityClaimHash`".
- `gates.reality.details.realityClaimHash` is present and equals `hashRealityClaim` of the
  `reality-claim.json` content at recording time — proven by a fixture test.
- `recordGate(feature, 'reality', 'SKIP'|'PASS', 'verifier'|'human', {...})` calls all
  complete without throwing against the plugin's real, unmodified schema validator.
- A fixture-level test proves the gate script's `recordGate` call always uses the backstop's
  actual returned `overallVerdict` (closure row 9, PROP-025).

### REQ-009: Convergence requires the reality gate — 5 dimensions, hash-bound, enforced at a real, authoritative (but not adversarial-insider-proof — see FIND-F disposition), Claude-Code-independent point (closure rows 10, 11, 15, 16)
**EARS**: WHEN a feature attempts to reach VCSDD completion THE SYSTEM SHALL require, in
addition to the plugin's existing 4-dimension check (VERIFIED zero reference to
`gates.reality` in `validateConvergenceForCompletion`), that `decideConvergenceGate(state,
realityClaim)` returns `blocked: false`, where:
- `blocked: false` iff `gates.reality.verdict === "PASS"` AND
  `hashRealityClaim(realityClaim) === gates.reality.details.realityClaimHash` (closure row
  15, new — the recorded PASS must be for the EXACT current claim content, not merely SOME
  past claim content), OR (`gates.reality.verdict === "SKIP"` AND
  `realityClaim.claimType === "none"` AND the same hash match);
- `blocked: true` in every other case, including a hash mismatch of ANY kind (the claim file
  changed — weakened or strengthened — since the gate was recorded), `gates.reality` missing,
  `FAIL`, or an illegally-`SKIP`ped claim (closure row 11).
This decision SHALL be enforced by `.githooks/pre-push`'s new "Reality Convergence Guard"
section, mirroring the existing Cadence Contract Guard pattern (VERIFIED,
`.githooks/pre-push:18-30,75-96`; `core.hooksPath=.githooks` confirmed live via `.git/config`)
— the AUTHORITATIVE, Claude-Code-independent enforcement point, explicitly understood (per
the FIND-F disposition above) as a **discipline boundary against accident and drift, not a
security boundary against an adversarial insider with shell access**:
- For every commit in the push range, detect any `.vcsdd/features/*/state.json` part of the
  diff whose (post-push) content has `currentPhase: "complete"`; for each, run
  `decideConvergenceGate` (via `skills/self/verify-reality-gate.mjs`) against that file's
  CURRENT `gates.reality` plus the CURRENT (post-push) `reality-claim.json` — always current
  content, which is what makes the hash-binding check (row 15) actually fire for a same-push
  downgrade, without needing to separately diff `reality-claim.json`'s before/after; if
  `blocked: true` for any of them, abort the push (fail-closed, same `--no-verify` escape
  hatch already governed by CLAUDE.md HARD RULE #14, not redesigned here).
- A regression-lock test (`skills/self/tests/test_reality_convergence_guard.*`, mirroring
  `test_cadence_evidence.py`/`test_cadence.py`'s existing pattern) MUST run and exit 0
  whenever the push range touches `.githooks/pre-push`'s Reality Convergence Guard section,
  `skills/self/lib/reality-verdict-schema.mjs` (where `decideConvergenceGate`/
  `hashRealityClaim` live), or `skills/self/verify-reality-gate.mjs` — mirroring the Cadence
  Guard's own `CADENCE_TOUCHED` trigger pattern exactly (closure row 16's discipline-boundary
  mitigation, PROP-032).
- The `.claude/settings.json` `hooks.PreToolUse` entry + `.claude/hooks/scripts/
  vcsdd-reality-gate-check.sh` is RETAINED but explicitly, permanently labeled
  **non-authoritative**: best-effort convenience only; nothing relies on it for correctness.
**Edge Cases**:
- A pre-existing feature has no `reality-claim.json`: treated identically to `gates.reality`
  missing — `blocked: true`, never inferred as `"none"`.
- The guard only fires when a `state.json` transition to `complete` is part of the pushed
  diff — matches the Cadence Guard's own push-time (not commit-time) scope, an accepted,
  documented limitation.
- **Local-hook bypass (closure row 16)**: explicitly OUT of what this requirement claims to
  close — see the FIND-F disposition section above, adopted verbatim as this feature's own
  position.
**Acceptance Criteria**:
- `.githooks/pre-push` contains the new Reality Convergence Guard section, grep-checkable.
- Diff-aware live-fire test (PROP-027, extended): invokes `.githooks/pre-push` directly
  against fixture push ranges covering (a) `gates.reality` missing/FAIL → reject, (b) valid
  matching-hash `PASS` → accept, (c) a `PASS` recorded against an OLD `reality-claim.json`
  hash while the pushed range's final `reality-claim.json` content differs (the live-fire
  proof of FIND-E's exact same-push-downgrade scenario) → reject.
- `decideConvergenceGate` is unit-tested (property + example) for `blocked: true` on ANY
  `(state, realityClaim)` pair with a hash mismatch, regardless of stored `verdict`
  (PROP-031), and for the `SKIP`-legality rule (PROP-026).
- A regression-lock test for the guard's own section exists and is required to pass whenever
  the guarded files are touched (PROP-032).
- `.claude/settings.json`'s `PreToolUse` entry and/or its referencing prose contains the
  literal words "non-authoritative" / "best-effort" / "fast-fail convenience".

### REQ-010: reality-verifier stays read-only; FAIL escalates to self-fix, never self-repairs
**EARS**: WHEN the reality gate (REQ-008) records `overallVerdict: "FAIL"` THE SYSTEM SHALL
NOT permit the gate script or `reality-verifier` itself to edit any source/spec/test file;
instead it SHALL invoke `skills/self/self-fix.sh <loop-or-feature-name> "<blocker + hint>"`
(same escalation pattern `gig_reality_verify.sh` uses).
**Edge Cases**:
- `self-fix.sh` already running: its own dedupe/staleness logic applies; the gate script
  needs no separate dedupe.
- The gate script itself must remain free of `Write`/`Edit` tool usage.
**Acceptance Criteria**:
- No file this feature adds grants `reality-verifier.md` `Write` or `Edit` (frontmatter
  `tools` stays exactly `["Read", "Grep", "Glob", "Bash"]`).
- The gate script's FAIL path contains a literal call to `self-fix.sh` and does not itself
  invoke any file-editing operation.

### REQ-011: First customer / acceptance vehicle (documented, not implemented by this feature)
**EARS**: WHEN the growth-engine marketing loop claims it posted a video to Instagram THE
SYSTEM's reality gate SHALL be able to prove or disprove that claim via REQ-002's
`post_not_publicly_visible` category and REQ-003/004/012's independently-captured,
logged-out, count-and-status-gated, URL-bound public-URL check, using the exact same
`reality-verifier` agent and spawn wrapper — no growth-engine-specific verifier code needed.
This is a standalone loop-verification call (REQ-005): the growth-engine loop calls
`reality-verify-spawn.sh` directly, per run, with `claim-type`/`required-artifact-count`/
`claimed-urls` (the REAL post URL the loop itself received from Instagram at post time —
never something the verifier derives) supplied as deterministic CLI arguments each time — no
`state.json`, no `gates.reality`, no `SKIP`, no `reality-claim.json` (that file applies only
to the VCSDD-pipeline gate, REQ-008/009). A failed daily verification produces a `FAIL`
verdict + trail line and escalates via REQ-010.
**Edge Cases**: N/A — forward-compatibility statement, satisfied by REQ-001..004/012 being
general-purpose (claim-type- and URL-parameterized, not platform-hardcoded), subject to
REQ-012's diagnosability precondition (closure row 17) actually being proven for Instagram
before this loop is allowed to rely on an automated verdict.
**Acceptance Criteria**:
- Nothing in `.claude/agents/reality-verifier.md`, `reality-verdict-schema.mjs`,
  `reality-verify-spawn.sh`, or `public_artifact_snapshot.py` names "Instagram" or any single
  platform.
- The loop-verification-vs-VCSDD-gate distinction is stated explicitly in the gate script's
  own documentation.

### REQ-012: Deterministic logged-out capture tool — mirrors `cdp_nav_snapshot.py`, diverges on auth, and MUST be proven diagnostic before automated reliance (closure row 17, FIND-G)
**EARS**: WHEN reality-verifier (or the gate script) needs to check a public URL THE SYSTEM
SHALL provide `skills/self/scripts/public_artifact_snapshot.py <passId> <seq> <label> <url>`
— a deterministic, non-LLM script that performs the actual network fetch, structurally never
touches CDP port `9222`, and appends exactly one row to
`$HOME/.openclaw/state/reality-artifacts/<passId>/artifacts.jsonl` containing at minimum
`{ts, passId, seq, label, tool: "public_artifact_snapshot", requestedUrl, finalUrl,
httpStatus, domExcerpt}`, printing the artifact path (or `ERROR:<reason>`) to stdout — never
raising.
**Diagnosability precondition (new, FIND-G)**: THE SYSTEM SHALL NOT rely on this tool's
output for an AUTOMATED `PASS`/`FAIL` verdict on any given platform until Phase 2a has
empirically established — by actually fetching a real, currently-public post URL on that
platform AND a real, currently-removed/private/nonexistent post URL on the SAME platform, and
comparing the two captured rows — that at least one structured, deterministic field
(`httpStatus` difference, presence/absence of a specific meta-tag/JSON-LD field in
`domExcerpt`, or a specific redirect target in `finalUrl`) reliably differs between the two.
This finding MUST be recorded (e.g. `docs/reality-gate-platform-signals.md` or
`.vcsdd/features/reality-gate/evidence/`), naming the exact signal used, per platform.
**Honest current state (this session, Phase 1c, no live fetches performed)**: based on
general training knowledge, NOT independently verified this session, Instagram is commonly
reported to render a distinct "Sorry, this page isn't available" interstitial for
removed/private/nonexistent post URLs even when logged out, which — IF confirmed empirically
in Phase 2a — would be a plausible `domExcerpt`-text-based structural signal; a plain
`httpStatus` code is NOT expected to reliably differ (Instagram's SPA shell commonly returns
`200` regardless of whether the underlying post exists), so REQ-012's status-only gate (REQ-
004) alone is very unlikely to be sufficient for Instagram specifically. **If Phase 2a's
empirical check finds no plain-HTTP-fetch-observable signal reliably distinguishes the two
cases**, THE SYSTEM SHALL fall back, in order: (1) a headless-browser-rendered capture (fresh
incognito profile, never CDP:9222) checking for the same kind of DOM-text/meta-tag signal
post-render; (2) if even that is unreliable, a SECOND INDEPENDENT PUBLIC SURFACE as a
corroborating (not replacing) signal — e.g. querying whether the exact claimed URL is present
in a public search-engine index/cache, itself captured deterministically (its own `httpStatus`
+ presence/absence of the URL in returned results, not LLM-interpreted) and logged as an
additional `artifacts.jsonl` row; (3) if diagnosability remains unproven even after (1) and
(2), THE SYSTEM SHALL NOT claim automated verification capability for that platform at all —
see the `automatedVerification: false` rule below.
**`automatedVerification` gate (mechanical, not prose)**: `reality-claim.json` (REQ-013)
gains a `automatedVerification: boolean` field (default `true` for a platform Phase 2a has
proven diagnostic; MUST be explicitly set `false` for one that is not, or not yet, proven).
WHEN `automatedVerification === false` THE SYSTEM SHALL refuse (fail-closed, gate script
error, not a silent pass-through) any `recordGate(..., reviewedBy: "verifier", ...)` call for
that claim — only `reviewedBy: "human"` (an own-eyes recording, outside this feature's
automated path entirely) is legal. This is independent of, and testable without waiting for,
Phase 2a's actual empirical finding: the RULE ("unproven platform ⇒ automated verdicts are
refused") is proven now; WHICH platforms are proven diagnostic is a Phase 2a empirical fact,
not a Phase 1c spec claim.
**Exact mirror / exact divergence from `cdp_nav_snapshot.py`**: unchanged from the prior
iteration's table — connection (never `:9222` vs. gig's live `:9222`), what it proves
(public/logged-out vs. authenticated), evidence-row shape/location, failure handling,
scoping — all as previously specified; only the diagnosability precondition above is new.
**Edge Cases**:
- JS-rendering-required platforms: headless-browser variant preferred, per the fallback order
  above — no longer left as a bare, unproven "Phase 2a decides" deferral; it is now the
  explicitly-ordered fallback when the plain fetch is proven insufficient.
- Anti-bot 403s: captured as `httpStatus: 403`, rejected by REQ-004's status gate — an
  accepted false-negative risk, not special-cased into a pass.
**Acceptance Criteria**:
- `skills/self/scripts/public_artifact_snapshot.py` contains no reference to port `9222`.
- Its artifact rows live under a directory tree distinct from `~/gig/trajectory/` with a
  `tool` field distinct from `"cdp_nav_snapshot"`.
- Every row includes an `httpStatus` field.
- **New**: a fixture-level test proves the `automatedVerification: false` refusal rule: given
  `reality-claim.json.automatedVerification === false`, any attempt to call
  `recordGate(..., 'verifier', ...)` for that feature/claim is refused by the gate script
  (non-zero exit / explicit error), while `recordGate(..., 'human', ...)` is permitted
  (PROP-034 — testable now, independent of platform).
- **New, Phase 2a-gated**: once Phase 2a records which signal(s) work for Instagram, a
  fixture/live test (PROP-033) feeds the tool a real known-public and a real known-removed
  Instagram URL and asserts the two captured rows differ on the recorded signal — `required:
  true` once the signal is known; until then, `reality-claim.json` for any Instagram claim
  MUST set `automatedVerification: false`, enforced by PROP-034 above regardless.

### REQ-013: `reality-claim.json` — committed, spec-reviewed, deterministic claim declaration, now including claimed URLs and diagnosability (closure rows 5, 11, 14, 15, 17)
**EARS**: WHEN a VCSDD feature intends to be gated by `/vcsdd-reality` THE SYSTEM SHALL
require `.vcsdd/features/<name>/reality-claim.json`, authored during Phase 1a/1b, with shape:
```json
{
  "claimType": "publish|post|deploy|earn|none",
  "requiredArtifactCount": "<integer, omit or 1 if claimType is none>",
  "urlSource": "fixed|caller-per-invocation",
  "claimedUrls": "<string[], REQUIRED and non-empty if urlSource is fixed; omitted/empty if caller-per-invocation>",
  "automatedVerification": "<boolean, default true; MUST be false for an unproven platform, REQ-012>",
  "description": "<what real-world thing this claims, or why none exists>"
}
```
reviewed by the same Phase 1c fresh adversary that reviews `behavioral-spec.md`, and NEVER
writable by `reality-verifier` or by the gate script at runtime (read-only).
**EARS (claimType/URL provenance, closure rows 5, 14)**: `claimType`/`requiredArtifactCount`/
`claimedUrls` are sourced EXCLUSIVELY from `reality-claim.json` when `urlSource: "fixed"`
(e.g. a landing-page-deploy claim with a spec-time-known URL), or from `reality-claim.json`'s
`claimType`/`requiredArtifactCount`/`automatedVerification` PLUS a MANDATORY per-invocation
`claimed-urls` argument (REQ-005) sourced from the posting loop's OWN deterministic record —
NEVER from `verdict.claimType`/any LLM-derived value, and NEVER from an ad-hoc CLI flag for
`claimType` itself.
**EARS (SKIP legality, closure row 11)**: `SKIP` is convergence-sufficient ONLY when
`claimType === "none"`; otherwise `decideConvergenceGate` treats `SKIP` identically to `FAIL`.
**EARS (hash binding, closure row 15)**: every `recordGate` call for this gate stores
`hashRealityClaim(realityClaim)` in `details.realityClaimHash`; `decideConvergenceGate`
recomputes and compares on every check, treating any mismatch as `blocked: true`.
**Trust boundary this requirement does NOT close (stated explicitly, not hidden)**: this
requirement proves "the cited artifact is for the URL the CALLER declared as claimed" — it
does NOT prove "the caller's declared URL is honestly the URL it actually posted to" (e.g. a
dishonest or badly-drifted loop could, in principle, supply `claimed-urls` pointing at some
OTHER real post it knows is public, rather than the one it actually just attempted). This is
the SAME trust boundary `gig_reality_gate.py`'s fixed, caller-supplied
`DEFAULT_GROUND_TRUTH_URLS` already has (VERIFIED — gig trusts its own caller-supplied ground
truth URLs are honest ground truth, it does not separately re-derive them); this feature does
not claim to exceed that precedent's trust model, only to match it (whereas the REJECTED
iteration-3 design — letting the LLM derive its own URL — was materially WORSE than that
precedent, per FIND-D). Verifying the LOOP's own post-time record-keeping honesty is a
different-layer concern, out of this feature's scope.
**Edge Cases**:
- Claim genuinely changes mid-development: `reality-claim.json` MUST be updated and go back
  through Phase 1c review; the hash-binding mechanism (row 15) makes this MECHANICALLY
  enforced now, not merely prose, because any un-re-verified change immediately invalidates
  the stored hash match.
- Pre-existing feature with no `reality-claim.json`: `blocked: true`, never inferred `"none"`.
- Malformed `reality-claim.json`: fail-closed.
**Acceptance Criteria**:
- The `vcsdd-reality` command file and gate script documentation both state, grep-checkably,
  that `claimType`/`requiredArtifactCount`/`claimedUrls` come ONLY from `reality-claim.json`
  (plus the mandatory per-invocation URL argument for `caller-per-invocation` claims).
- Unit tests prove: (a) `SKIP` + `claimType: "publish"` → `blocked: true`; `SKIP` +
  `claimType: "none"` → `blocked: false` (PROP-026); (b) a hash mismatch between stored
  `details.realityClaimHash` and the current file's hash → `blocked: true` regardless of the
  stored `verdict` (PROP-031); (c) `automatedVerification: false` refuses a `'verifier'`-
  reviewed `recordGate` call (PROP-034).

## Non-functional requirements

- **Performance bound**: a `/vcsdd-reality` spawn is capped at 600s (mirrors
  `gig_reality_verify.sh`); on timeout, records `gates.reality = { verdict: "FAIL",
  reviewedBy: "verifier", details: { claimType, requiredArtifactCount, claimedUrls,
  realityClaimHash, reason: "timeout" } }` (fail-closed, never `SKIP`).
- **Security constraint**: no file added by this feature imports/calls a
  signing/keypair/private-key library.
- **Security constraint**: `validateArtifactProvenance`, `decideConvergenceGate`,
  `canonicalizeUrl`, `hashRealityClaim` have no network/file access.
- **Security constraint**: `public_artifact_snapshot.py` is structurally incapable of
  authenticated access — no CDP client code path, no cookie-jar loading path.
- **Security constraint**: `reality-claim.json` is never written by any component that also
  produces the verdict checked against it.
- **Disclosed limit (not a security constraint this feature satisfies)**: `.githooks/
  pre-push`'s enforcement is a discipline boundary, not a security boundary against an
  adversarial insider with shell access on the pushing worktree (closure row 16, FIND-F
  disposition, adopted verbatim). No claim in this spec should be read as contradicting this.

## Judgment vs determinism (anti-hardcoding discipline)

Per `~/.claude/rules/building-effective-ai-agents.md`: whether a report is "honest", whether a
finding fits `post_not_publicly_visible` vs `narrate_only_claim`, and whether a captured
`domExcerpt` at a confirmed-2xx, confirmed-correct-URL actually shows the claimed content are
JUDGMENT calls — the LLM makes them, guided by right-altitude prompt instructions, never by
keyword/regex classification. The things implemented as deterministic code in this feature
are, exhaustively: fixed category catalog membership; the artifact-provenance check (a
required NUMBER of DISTINCT, resolved, correctly-tooled, fresh, correctly-URLed,
non-redirected, 2xx-status rows — all structural lookups against independently-captured or
caller-declared data, never prose interpretation, never LLM-derived URLs); URL
canonicalization (a fixed normalization function, not a judgment about which URL is "right" —
the RIGHT URL is a caller-supplied fact this function never chooses); the claim-hash binding
(a content-equality check, not a judgment about whether a claim change was "reasonable"); the
SKIP/convergence decision; the `automatedVerification` refusal rule (a boolean lookup, not a
judgment about whether a platform is "probably fine"); jsonl path derivation; and gate
recording. Every one of iterations 1-3's rejected designs (substring-marker matching,
citation-presence-optional, and now URL-blind resolution) was the same underlying mistake at
a different granularity: treating the ABSENCE of a detected problem, or the mere PRESENCE of
*some* real evidence, as equivalent to AFFIRMATIVE proof of the SPECIFIC claimed fact. This
iteration's rule, stated once, generally: **a public-artifact `PASS` requires affirmative,
counted, resolved, fresh, correctly-URLed, non-redirected, correctly-tooled, 2xx-status proof
of the EXACT caller-declared claim, bound by content hash to the exact claim it was checked
against — never the mere absence of a caught violation, and never proof of SOME true fact
that happens to be adjacent to the claim.** If any future change accepts a `PASS`/`SKIP` on
the basis of what was NOT found wrong, what merely LOOKS like sufficient evidence without
being tied to the specific claimed fact, or a local-hook pass being mistaken for a security
guarantee against an adversarial insider, that is the anti-pattern this rule forbids.
