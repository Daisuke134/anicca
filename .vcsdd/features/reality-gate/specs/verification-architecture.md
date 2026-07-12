# Verification Architecture: reality-gate (Phase 4.5 REALITY GATE)

Companion to `.vcsdd/features/reality-verifier/specs/verification-architecture.md` (the
existing feature this one extends). Read that file first — this one only documents what is
NEW or CHANGED. Read `behavioral-spec.md`'s "Iteration history" table first — this file's
proof-obligation table below reflects iteration-1's redesign (FIND-001..005), not the
original submission.

## Purity Boundary Map

- **Pure Core** (`skills/self/lib/reality-verdict-schema.mjs`, extended in place):
  - `FINDING_CATEGORIES` — frozen array, now 7 entries (REQ-001). Pure data.
  - `isKnownCategory(category)` — unchanged pure lookup, now checks against 7 entries.
  - `validateVerdictShape(verdict)` — unchanged pure structural validator; accepts the new
    category as any other (no special-casing needed inside this function — REQ-001). Not
    touched by the FIND-004 fix either: provenance citation reuses the EXISTING
    `evidence.filePath`+`lineRange` shape this function already validates — no new evidence
    key (`fetchMethod` or otherwise) is added anywhere.
  - `validateArtifactProvenance(verdict, capturedArtifacts, claimType)` *(new, replaces the
    rejected `enforceLoggedOutEvidence` design — REQ-003/004)* — pure function: for a
    public-artifact `claimType`, walks `verdict.findings[]` (and, for a `PASS`,
    `verdict.evidenceReviewed[]`) looking for entries whose `evidence.filePath` matches the
    artifact-trail path shape (REQ-012) and `evidence.lineRange` names a row index; resolves
    that citation against the `capturedArtifacts` array (an array of already-parsed row
    objects — the function itself never touches `fs`); if the citation does not resolve to a
    row satisfying `tool === "public_artifact_snapshot"` AND `passId` match AND `ts >=`
    the pass's start timestamp, returns a NEW verdict object (never mutates the input —
    immutability rule, `.claude/rules/coding-style.md`) with `overallVerdict: "FAIL"` and an
    added `post_not_publicly_visible` finding citing exactly which check failed
    (`no_matching_row` / `wrong_tool` / `wrong_pass` / `stale_row`); if every citation
    resolves cleanly, returns the input verdict unchanged (as a fresh object, not the same
    reference). **This is the direct fix for iteration-1 FIND-002**: the function's ONLY
    inputs are the verdict and an independently-read, structured array — it never inspects
    verdict prose for keywords, so a report that avoids naming "9222" no longer helps it
    bypass anything; the check is about which row exists, not which words appear.
  - `buildVerdictTrailPath(stateDir, loopName)` *(REQ-006)* — deterministic string join,
    mirrors `buildResultPath`'s existing pattern exactly (same normalization via
    `normalizeLoopName`), no I/O.
  - `buildVerdictTrailLine(verdict, resultPath, timestampMs)` *(REQ-006)* — pure: takes a
    validated verdict + its RESULT path + a timestamp and returns the exact JSON string to
    append (one line, no trailing content) — the actual `fs.appendFileSync` call lives in the
    effectful shell (the gate script), not here.
  - `buildArtifactTrailPath(stateDir, passId)` *(new, REQ-012)* — deterministic string join
    (`<stateDir>/reality-artifacts/<passId>/artifacts.jsonl`), mirrors the same pattern, no
    I/O.
  - The reality-gate convergence-decision function *(new, REQ-009, name TBD in Phase 2a, e.g.
    `decideConvergenceGate(state)`)* — pure: given a `state` object (already read from disk),
    returns `{blocked: boolean, reason?: string}` per the rule "blocked iff `currentPhase ===
    'complete'` and (`gates.reality` missing or `gates.reality.verdict === 'FAIL'`)". Both
    `verify-reality-gate.mjs` (the standalone backstop) and
    `vcsdd-reality-gate-check.sh` (the hook handler, via a thin Node/Bash shim) call this SAME
    function so the two enforcement layers can never disagree with each other by drifting
    independently.
- **Effectful Shell**:
  - `.claude/agents/reality-verifier.md` — prompt content is checked mechanically (frontmatter
    shape, required literal strings for the new category, the REQ-012 tool-invocation
    instruction, and the domExcerpt/status + URL evidence requirement); actual reasoning is
    an LLM call, out of unit-test scope (unchanged principle from the base feature).
  - `skills/self/reality-verify-spawn.sh` — extended to thread optional `claim-type` and
    `pass-id` args into the spawned task text; still effectful (tmux + `claude` process
    spawn); only the `REALITY_VERIFY_DRYRUN` seam is exercised by tests, same as before.
  - `skills/self/scripts/public_artifact_snapshot.py` *(new, REQ-012)* — effectful: performs
    a real network fetch (or spawns a fresh headless-browser process) and appends a real file
    row. Structurally incapable of authenticated access (no CDP client code path exists in
    this file at all — a Tier-0 grep-checkable guarantee, not a runtime behavior needing a
    property test).
  - The gate script (`skills/self/vcsdd-reality-gate.mjs`, exact name decided in Phase 2a) —
    effectful: generates the pass id, spawns reality-verifier (via the spawn wrapper), polls
    for the `RESULT` file, reads `artifacts.jsonl` for that pass id (the ONE effectful read
    that produces `capturedArtifacts`), calls the pure `validateArtifactProvenance` on
    whatever it reads, appends the verdict trail line, and calls the plugin's `recordGate()`
    with schema-legal values only (`'PASS'|'FAIL'|'SKIP'`, `reviewedBy: 'verifier'` —
    FIND-001 fix). Never itself performs Write/Edit-style source edits (REQ-010).
  - `.claude/commands/vcsdd-reality.md` — an instructional command definition (like the
    plugin's own `commands/vcsdd-adversary.md`), not code; its *content* (required steps
    present) is checked mechanically (Tier 0), its *execution* is effectful.
  - `.claude/settings.json`'s `hooks.PreToolUse` entry + `.claude/hooks/scripts/
    vcsdd-reality-gate-check.sh` *(REQ-009, path corrected per FIND-005)* — a `PreToolUse`
    hook is inherently effectful (inspects live tool-call payloads); its matching logic (does
    this Bash command look like a transition to `complete`) is a heuristic string check,
    mirrored directly from the plugin's own `vcsdd-gate-check.js` technique (VERIFIED by
    reading that file) — same tier of rigor the plugin itself uses for this class of check.
    Its DECISION once triggered is NOT heuristic — it calls the same pure
    `decideConvergenceGate(state)` the standalone backstop uses, after a real (effectful)
    `readState()`.
  - `skills/self/verify-reality-gate.mjs` *(REQ-009)* — effectful (reads `state.json` from
    disk) but its *decision logic* is the pure `decideConvergenceGate` — this is the one
    effectful-shell item in this feature that still gets full pure-core-style test coverage
    by factoring the read (effectful) from the decision (pure).

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-001..008 | Unchanged, inherited from `reality-verifier`'s verification-architecture.md (still apply to the extended module — the 6-category assumptions in PROP-004/006/007 must be re-verified against 7 categories, not re-derived) | — | true | (see base feature) |
| PROP-009 | `FINDING_CATEGORIES` contains exactly 7 entries including `post_not_publicly_visible`, and `isKnownCategory` returns true for all 7 and false for any string outside the set | 1 | true | node:test + fast-check |
| PROP-010 | `validateArtifactProvenance`: for ANY verdict citing an artifact row whose `tool !== "public_artifact_snapshot"` (fixture value: `"cdp_nav_snapshot"`, gig's real authenticated-tool name — the concrete stand-in for "captured from an authenticated context" the review demanded), the returned verdict ALWAYS has `overallVerdict === "FAIL"` and includes a `post_not_publicly_visible` finding, for arbitrary well-formed surrounding verdict content | 1 | true | fast-check (property test, generating random non-`public_artifact_snapshot` tool-name strings) |
| PROP-011 | `validateArtifactProvenance`: for ANY verdict citing a `filePath`+`lineRange` that resolves to NO row in `capturedArtifacts` (empty array, or a non-matching index), the returned verdict ALWAYS has `overallVerdict === "FAIL"` (the "no artifact at all" case the review named explicitly) | 1 | true | fast-check |
| PROP-012 | `validateArtifactProvenance`: for ANY verdict citing a row whose `passId` differs from the pass id supplied to the function, OR whose `ts` predates the supplied run-start timestamp, the returned verdict ALWAYS has `overallVerdict === "FAIL"` (stale/foreign-pass rejection) | 1 | true | fast-check |
| PROP-013 | `validateArtifactProvenance`: for ANY verdict where every citation resolves cleanly (matching `tool`, `passId`, fresh `ts`), the function returns a value deep-equal to the input (identity-preserving on the non-violating path — no false positives; supersedes iteration-1's PROP-011, which tested identity-preservation against absent *keywords* rather than present *valid provenance* — the redesign requires testing the positive case against REAL matching rows, not merely against text lacking banned words) | 1 | true | fast-check |
| PROP-014 | `validateArtifactProvenance` never mutates its input verdict object or the `capturedArtifacts` array (immutability — `coding-style.md`): both input references, deep-compared before/after the call, are unchanged regardless of which branch executes | 1 | true | fast-check |
| PROP-015 | `buildVerdictTrailPath`/`buildVerdictTrailLine`/`buildArtifactTrailPath`: deterministic for identical inputs; `buildVerdictTrailLine`'s output always parses as valid JSON containing `overallVerdict` and the given `resultPath` | 1 | true | fast-check |
| PROP-016 | `decideConvergenceGate(state)` returns `blocked: true` for every `state` object where `currentPhase === "complete"` and `gates.reality` is absent or `gates.reality.verdict === "FAIL"`, and `blocked: false` for every `state` object where `gates.reality.verdict` is `"PASS"` or `"SKIP"` (with any `details`), for arbitrary well-formed `state.gates` shapes | 1 | true | fast-check |
| PROP-017 | `.claude/agents/reality-verifier.md` prompt body contains, verbatim: all 7 category names, the exact `public_artifact_snapshot.py <passId> <seq> <label> <url>` invocation instruction for public-artifact claims, and the domExcerpt-or-status + URL evidence-citation requirement (`evidence.filePath`+`lineRange` into the artifact trail) | 0 | true | node:test (static content assertion, same technique as the base feature's PROP-007) |
| PROP-018 (negative test, REQ-004/007) | Feeding `validateArtifactProvenance` a fabricated PASS verdict citing a row produced by `"cdp_nav_snapshot"` (authenticated capture) deterministically yields FAIL — this is the concrete, CI-runnable proof that "a claim whose artifact was captured from an authenticated context... MUST FAIL", the exact obligation FIND-002 demanded | 1 | true | node:test (example-based, exact fixture from REQ-004) |
| PROP-018b (negative test, REQ-004/007) | Feeding `validateArtifactProvenance` a fabricated PASS verdict citing a `filePath`+`lineRange` with an EMPTY `capturedArtifacts` array (no artifact at all) deterministically yields FAIL | 1 | true | node:test (example-based) |
| PROP-019 | `.claude/hooks/scripts/vcsdd-reality-gate-check.sh`, invoked directly (not via Claude Code's runtime) with (a) a crafted tool-call payload resembling a transition-to-`complete` Bash command and (b) a fixture `state.json` with `gates.reality` missing/`FAIL`, returns a blocking result; invoked with the same payload but a fixture `state.json` with `gates.reality.verdict: "PASS"`, returns a non-blocking result. This is the LIVE-FIRE proof FIND-005 required in place of a static-content-only check, and it does not depend on whether Claude Code's hook composition actually invokes the script at runtime (that remains a separate, explicitly-flagged assumption below) | 0 | true | bash/node test script invoking the hook handler directly with fixture args |
| PROP-020 (negative test, REQ-007, live) | A real fresh `reality-verifier` spawn against a genuinely nonexistent public URL produces an on-disk FAIL verdict (own-eyes, not mocked — same non-mocking rule as the base feature's PROP-006/007 class, extended to a full end-to-end run) | 0 | true | manual/own-eyes run, evidence file committed under `.vcsdd/features/reality-gate/evidence/` |
| PROP-021 | `recordGate(feature, 'reality', 'SKIP', 'verifier', details)` and `recordGate(feature, 'reality', 'PASS', 'verifier', details)` both complete without throwing when run against the plugin's REAL, unmodified `vcsdd-schema.js` validator (not merely read-and-assert-by-eye against the schema text) — the direct fix-verification for FIND-001 | 0 | true | node:test, requiring the real plugin library against a throwaway fixture `.vcsdd/` state directory |

## Verification Strategy

- **Tier 0** (static/example-based, no formal proof needed): agent-prompt content markers
  (PROP-017), the hook handler's live-fire behavior (PROP-019 — upgraded from iteration-1's
  static-content-only PROP-016, per FIND-005), the one live fail-closed proof (PROP-020), and
  the real-schema call-through proof (PROP-021, per FIND-001) — these are documentation/
  definition artifacts, a script invoked directly with fixtures, an inherently-non-mockable
  LLM end-to-end run, or a direct call into an existing, already-tested third-party library —
  not algorithms this feature itself needs to formally prove.
- **Tier 1** (property tests via `fast-check`, already a repo devDependency — VERIFIED by
  reading `package.json`'s `devDependencies` and the existing
  `reality-verdict-schema.property.test.mjs`): all new pure functions
  (`validateArtifactProvenance`, `buildVerdictTrailPath`, `buildVerdictTrailLine`,
  `buildArtifactTrailPath`, `decideConvergenceGate`) get the same exhaustive-style property
  coverage the base feature already established. PROP-018/018b are the two exceptions left as
  example-based (concrete fixtures, as REQ-004/007 ask for as the specific named bypasses);
  property-test generalizations of them are not excluded but not required.
- **Tier 2**: not used — no lightweight formal-methods tool is warranted for functions this
  small, same reasoning as the base feature.
- **Tier 3**: not used — no memory-safety/concurrency-critical core exists in this JS/bash/
  Python/markdown feature.

## What this architecture explicitly does NOT verify (by design, extended from the base feature)

- Whether reality-verifier's LLM judgment on a REAL claim (e.g. a real Instagram post) is
  correct — same as the base feature, validated only by real own-eyes spawns (PROP-020), not
  automated unit tests, because mocking the judgment would itself be the "fake-green" failure
  mode this feature exists to catch.
- Whether a fully adversarial, Bash-capable agent could hand-forge a fake row into
  `artifacts.jsonl` without ever calling `public_artifact_snapshot.py` — explicitly
  acknowledged as a residual gap this feature does NOT close, because the pattern it mirrors
  (`gig_reality_gate.py`/`cdp_nav_snapshot.py`) has the identical gap and is already accepted
  project-wide (VERIFIED by reading both gig files; no additional forgery-proofing exists
  there either). Own-eyes/fresh-adversary review remains the final backstop against a fully
  adversarial agent for both patterns; this feature does not claim to solve a problem its own
  mirrored precedent does not solve.
- Whether the project-level `PreToolUse` hook (REQ-009) reliably intercepts EVERY possible
  Bash invocation that could transition a feature to `complete` — explicitly acknowledged as
  best-effort (heuristic text matching, same limitation the plugin's own
  `vcsdd-gate-check.js` already has for its Bash heuristics). PROP-019 proves the SCRIPT's
  decision logic is correct when invoked; it does not prove Claude Code always invokes it.
  The standalone `verify-reality-gate` script (PROP-016/021's `decideConvergenceGate`) is the
  authoritative check regardless.
- Whether Claude Code actually composes project-level `.claude/settings.json` `hooks`
  additively with plugin-level `hooks.json` for the same event — this remains an ASSUMPTION
  (not independently verified this session; PROP-019 tests the hook SCRIPT directly, not
  Claude Code's runtime composition of it). This is explicitly narrower than iteration-1's
  version of the same assumption: iteration-1 had NO mechanical check on the hook's own logic
  at all (its only "proof" was static file presence); this iteration proves the logic is
  correct (PROP-019) and isolates the remaining unknown to "does Claude Code invoke it",
  with the standalone backstop script as the unconditional fallback either way.
- Whether `gig_reality_verify.sh`'s independent pipeline should be migrated onto this
  feature's generalized spawn wrapper — explicitly out of scope (REQ-005 edge case): gig's
  auditor is a working, separately-verified pipeline; this feature does not touch it.
