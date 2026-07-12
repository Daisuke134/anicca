# Behavioral Spec: reality-gate (Phase 4.5 REALITY GATE, VCSDD pipeline extension)

Scope: `docs/superpowers/specs/2026-07-13-growth-engine-self-improving-promotion-skill-design.md`
§8b V0 / §8c (motivating gap analysis), in the `anicca-project` repo.
Builds on the already-shipped `reality-verifier` feature (see
`.vcsdd/features/reality-verifier/specs/behavioral-spec.md`) — this feature does NOT
re-implement reality-verifier; it (a) extends its category catalog and prompt from
money/ledger-only to any real-world side-effect claim, (b) generalizes its spawn wrapper,
(c) adds a durable per-loop verdict trail, (d) proves it is fail-closed with a real negative
test, and (e) wires it into VCSDD as a gate between adversarial review and formal hardening.

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
deployed, sent, earned).

## Purity boundary analysis (top-level, elaborated per-requirement below)

- **Pure / deterministic core** (side-effect-free, unit- and property-testable):
  - the finding-category catalog and its validators (`FINDING_CATEGORIES`,
    `isKnownCategory`, `validateVerdictShape` in
    `skills/self/lib/reality-verdict-schema.mjs`) — extended, not replaced;
  - path/line derivation for the new durable trail file;
  - the CDP-marker downgrade rule (REQ-003's deterministic backstop): given a verdict object
    + declared `fetchMethod`/claim-type, decide PASS-must-downgrade-to-FAIL — pure function
    of its inputs, no I/O.
- **Effectful shell** (not unit-tested; verified only by real spawns / own-eyes review):
  - `.claude/agents/reality-verifier.md` — the LLM's own judgment when it actually reasons;
  - `skills/self/reality-verify-spawn.sh` — spawns a detached `claude` process;
  - the new `vcsdd-reality` command + its gate-recording script — calls the plugin's
    `scripts/lib/vcsdd-state.js` `recordGate()` (a real file write via `writeState`);
  - the reality-verifier's own runtime Bash calls (curl / fresh-browser-context / RPC reads)
    when it actually gathers evidence.

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

### REQ-003: Logged-out enforcement for public-artifact checks (mechanically enforced, not prose-only)
**EARS**: WHEN reality-verifier is asked to verify a claim of a *publicly visible* artifact
(the claim's declared type is `publish`/`post`/`deploy`, or the target is a public URL) THE
SYSTEM SHALL perform that specific check with no authenticated session — a plain public
HTTP(S) fetch (e.g. `curl -s <url>`, no cookie jar) or a freshly-created, cookie-less browser
context — and SHALL NOT drive the CloakBrowser daily-driver tab (CDP port `9222`) for that
check, because a shadowbanned or failed post remains visible to the logged-in account owner
and a logged-in check therefore produces a false PASS.
**Edge Cases**:
- The same verification run also needs a logged-in check for something else (e.g. confirming
  an internal dashboard number) — that separate check MAY use the existing daily-driver
  CDP:9222 tab under the existing shared-lock rules (never duplicate/close the tab —
  `~/anicca/skills/earn/gig/scripts/cdp_lock.sh` is the established pattern for mutual
  exclusion with a loop's own core process); ONLY the public-visibility check itself is
  forbidden from using it.
- The LLM's own prompt instruction is not sufficient enforcement on its own (an LLM can be
  wrong or drift) — THE SYSTEM SHALL ALSO apply a deterministic, no-LLM backstop: any PASS or
  finding-evidence for a public-artifact claim whose `evidence.fetchMethod` (or equivalent
  tool-call trace) indicates it went through CDP port `9222` / the daily-driver session SHALL
  be programmatically downgraded to `overallVerdict: "FAIL"` with a
  `post_not_publicly_visible` finding citing the violation, mirroring
  `gig_reality_gate.py`'s existing pattern of never trusting a fresh judge's self-report on
  faith alone (deterministic evidence gate applied AFTER the LLM verdict, before the verdict
  is accepted by the caller).
- No public URL exists to check at all (claim omits it) — fail-closed: `FAIL` with
  `post_not_publicly_visible`, not silently skipped.
**Acceptance Criteria**:
- `.claude/agents/reality-verifier.md` contains an explicit, literal prohibition string
  naming CDP port `9222` / "daily-driver" for public-visibility checks, plus the required
  alternative (`curl -s`, fresh/incognito browser context).
- A pure function (name TBD in Phase 1b, e.g. `enforceLoggedOutEvidence(verdict, claimType)`)
  exists in the schema module that: given a verdict whose findings/evidenceReviewed entries
  reference `9222` or `daily-driver` for a `claimType` requiring public visibility, returns a
  downgraded verdict with `overallVerdict: "FAIL"`; given a verdict with no such reference,
  returns it unchanged. This function is pure (no I/O) and is exercised by both example-based
  and property tests.
- The gate script (REQ-008) always runs this backstop function on the raw verdict before
  calling `recordGate()` — the LLM's self-reported verdict is never the last word, matching
  the "own-eyes / never trust reports" project rule.

### REQ-004: PASS evidence requirements for public-artifact claims
**EARS**: WHEN reality-verifier emits `overallVerdict: "PASS"` for a public-artifact claim
THE SYSTEM SHALL require `evidenceReviewed` (or the relevant finding's `evidence`, for a FAIL)
to cite a `domExcerpt` and/or an HTTP status alongside the checked public URL, so a PASS is
never "I believe it posted" without a fetchable proof.
**Edge Cases**:
- `domExcerpt` alone with no URL, or a URL with no excerpt/status: both INVALID — a bare URL
  string is not evidence of what was actually observed there.
- HTTP 200 with an empty/error-page body (soft-404): the prompt MUST instruct the model to
  treat body content, not just status code, as the actual check; a soft-404 with HTTP 200 is
  still `post_not_publicly_visible`, not a PASS.
**Acceptance Criteria**:
- The agent prompt states the domExcerpt-or-status + URL requirement explicitly for
  public-artifact claims, as a specialization of the existing "cite filePath/txHash/
  domExcerpt" evidence rule (reality-verifier spec REQ-006).
- Existing money/ledger claims are UNAFFECTED — this requirement applies only when the claim
  type is a public-artifact type (REQ-005's `claim-type`), not to `earn`-type claims.

### REQ-005: Generalized spawn wrapper — any claim type, backward compatible with the real existing caller
**EARS**: WHEN a caller needs to verify a real-world side-effect claim of any kind (`earn`,
`publish`, `post`, `deploy`) THE SYSTEM SHALL provide `skills/self/reality-verify-spawn.sh`
accepting `<loop-name> <artifact-or-public-url> [claim-text] [claim-type]`, where omitting
`claim-type` defaults to `earn` (the pre-existing behavior) so that
`skills/self/reality-verify-on-new-earn.sh` — the one real existing caller (VERIFIED by
`grep -rl reality-verify-spawn` across the repo; `gig_reality_verify.sh`/`gig_judge.py` do
**not** call this script — see REQ-001 edge case) — continues to work with zero changes to
its 3-positional-argument invocation.
**Edge Cases**:
- `claim-type` is an unrecognized string: THE SYSTEM SHALL treat it as a generic
  "real-world side-effect claim" (fall through to the general narrate-only/evidence rules)
  rather than erroring, since the spawn wrapper does not itself validate claim semantics —
  that is the agentic layer's job.
- `claim-type` is a public-artifact type (`publish`/`post`/`deploy`) but `artifact-or-
  public-url` looks like a local filesystem path, not a URL: the spawned task text MUST still
  instruct "if this claim is about public visibility, find/derive the actual public URL
  yourself and check it logged-out" rather than silently treating a local path as sufficient
  evidence.
**Acceptance Criteria**:
- `test-reality-verify-spawn.sh`'s existing 3 assertion groups (A/B/C) still pass unchanged
  after this feature (regression baseline).
- A new DRYRUN assertion confirms a 4th `claim-type` argument is threaded into the spawned
  task text (visible via `REALITY_VERIFY_DRYRUN=1` output or a task-text dry-print seam) when
  provided, and defaults to `earn` when omitted.

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
- A pure path-derivation helper (e.g. `buildVerdictTrailPath(stateDir, loopName)`) exists,
  is deterministic, and is covered by a unit test (mirrors `buildResultPath`'s existing
  pattern).
- After a real (or test-fixture) verdict-producing run, `reality-verdict-<loop>.jsonl` exists
  and its last line parses as JSON matching the shape above.

### REQ-007: Negative test — fail-closed proof (a gate that cannot fail is not a gate)
**EARS**: WHEN reality-verifier (or its deterministic backstop, REQ-003) is given a FALSE
claim — an artifact/public URL that does not exist or is not public — THE SYSTEM SHALL
produce `overallVerdict: "FAIL"` with at least one finding, and this SHALL be demonstrated
twice: once as a deterministic unit test of the pure backstop function (REQ-003) fed a
synthetic bad verdict, and once as a REAL fresh reality-verifier spawn against a genuinely
nonexistent public URL, producing an actual FAIL verdict artifact on disk (own-eyes
verification — this second proof is NOT mocked, matching the reality-verifier
verification-architecture's existing rule that mocking the LLM's judgment would itself be a
fake-green failure).
**Edge Cases**:
- The chosen "nonexistent artifact" for the live proof must be unambiguous (e.g. a random-
  UUID Instagram/URL path that returns 404, or a `file://`-style path that never existed) so
  the negative result cannot be attributed to a flaky network condition; if the live check is
  genuinely inconclusive (network down), THE SYSTEM SHALL retry once before treating it as
  proof — fail-closed still applies (unreachable ground truth from the target service is
  itself also a FAIL, satisfying the acceptance vehicle either way).
**Acceptance Criteria**:
- A unit test in the schema module's test suite feeds the backstop function (or
  `validateVerdictShape` plus the new category) a fabricated PASS claiming visibility of a
  fictitious public URL with no real evidence, and asserts it is rejected/downgraded.
- A real, committed FAIL verdict json (or its jsonl line, REQ-006) exists under
  `.vcsdd/features/reality-gate/evidence/` (or `~/.openclaw/state/`, referenced by path) as
  the live-run artifact, produced by an actual spawn during Phase 2b/2c of this feature, not
  fabricated by hand.

### REQ-008: VCSDD Phase 4.5 REALITY GATE — `vcsdd-reality` command, project-level (not plugin cache)
**EARS**: WHEN a VCSDD feature has passed adversarial review (plugin-internal phase `'3'`,
`gates['3'].verdict === 'PASS'`, VERIFIED by reading `scripts/lib/vcsdd-state.js`'s
`GATE_PREREQUISITES['5']`) THE SYSTEM SHALL provide a `/vcsdd-reality` command that spawns a
FRESH `reality-verifier` instance (zero context from the Builder/loop being verified, same
fresh-context discipline as `/vcsdd-adversary`) against that feature's own real-world
acceptance claim, and records the resulting verdict into the feature's `state.json` via the
plugin's own exported `recordGate(featureName, 'reality', verdict, 'reality-verifier',
details)` function (VERIFIED: `recordGate`'s `phase` parameter is used only as a `state.gates[
phase]` object key with no restriction to the plugin's `VALID_PHASES` set — passing `'reality'`
is a fully supported use of the existing library, not a hack).
**Edge Cases**:
- The plugin is later updated and overwrites `/Users/anicca/.claude/plugins/cache/
  vcsdd-claude-code/vcsdd/1.0.0/` — THE SYSTEM SHALL NOT be affected, because none of this
  feature's files live under that cache path; `/vcsdd-reality`'s command file, its supporting
  script, and the (already-existing) `reality-verifier` agent all live under THIS repo's own
  `.claude/` and `skills/self/`, which a plugin update never touches.
- A feature has no obvious "real-world claim" to check (a pure library refactor with no
  side-effecting behavior): THE SYSTEM SHALL allow `/vcsdd-reality --skip
  "<reason>"` to record `gates.reality = { verdict: "SKIPPED", reason }` explicitly rather
  than silently omitting the gate — REQ-009's convergence check treats an explicit, reasoned
  `SKIPPED` as satisfying the gate, but a MISSING `gates.reality` key never does.
**Acceptance Criteria**:
- Command file exists at `.claude/commands/vcsdd-reality.md` in THIS repo (`~/anicca`), not
  under the plugin cache path.
- After running it (or its Phase 2b/2c live proof, REQ-007), the active feature's
  `.vcsdd/features/<name>/state.json` contains a `gates.reality` object with `verdict`
  (`PASS`/`FAIL`/`SKIPPED`) and a `timestamp`, written via `recordGate()` (i.e. `state.json`
  is never hand-edited for this purpose — `history.jsonl` also gains a matching
  `gate_recorded` entry for `phase: "reality"`, which is `recordGate()`'s built-in behavior).

### REQ-009: Convergence requires the reality gate — 5 dimensions, not 4
**EARS**: WHEN a feature attempts to reach VCSDD completion (`currentPhase: "complete"`) THE
SYSTEM SHALL require, in addition to the plugin's existing 4-dimension check (spec fidelity /
test coverage / implementation correctness / formal verification, enforced by the plugin's
own unmodified `validateConvergenceForCompletion`), that `gates.reality.verdict` is `PASS` or
an explicitly-reasoned `SKIPPED` (REQ-008 edge case) — never absent and never `FAIL` — and
this 5th-dimension check SHALL be enforced by project-level artifacts added to THIS repo
(a project-level `PreToolUse` hook under `.claude/hooks/`, additive to the plugin's own
`hooks.json` — Claude Code composes project-level and plugin-level hooks for the same event,
so both fire; ASSUMED from Claude Code's documented hook model, to be confirmed by an actual
end-to-end test in Phase 2b — plus a standalone, independently runnable `verify-reality-
gate` script as a deterministic backstop that can be invoked manually or wired into this
repo's existing `.githooks/pre-push`), never by editing the plugin cache.
**Edge Cases**:
- The project-level hook cannot reliably intercept the exact Bash invocation that performs
  the phase transition to `'complete'` (heuristic Bash-command-text matching, same technique
  `vcsdd-gate-check.js` already uses, is inherently best-effort) — THE SYSTEM SHALL treat the
  standalone backstop script as the authoritative, always-correct check (it re-reads
  `state.json` directly and does not depend on intercepting any particular tool call), and
  the hook as a fast-fail convenience layer only. A feature is not considered genuinely
  "done" per this project's honesty rules until the backstop script has been run and passed
  at least once after the reality gate was recorded.
- A pre-existing feature (created before this gate existed) is mid-pipeline: THE SYSTEM SHALL
  NOT retroactively block phases 1-4 for it; the 5th-dimension requirement applies only at the
  `'complete'` transition, so older features simply need one `/vcsdd-reality` run before they
  can complete going forward.
**Acceptance Criteria**:
- `.claude/hooks/hooks.json` exists in this repo with a `PreToolUse` entry that can block a
  Bash command recognizably transitioning the active feature to `complete` while
  `gates.reality` is missing or `FAIL`.
- A standalone script (e.g. `scripts/verify-reality-gate.js` or `skills/self/verify-reality-
  gate.mjs`) exits non-zero when the active (or a named) feature's `state.json` has
  `currentPhase: "complete"` and `gates.reality` missing/`FAIL`, and exits zero otherwise —
  covered by a unit test using fixture `state.json` files (no live spawn needed for this
  specific check, since it only reads a state object).

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
REQ-003's logged-out public-URL check, using the exact same `reality-verifier` agent and
`vcsdd-reality` gate this feature ships — no growth-engine-specific verifier code is needed.
**Edge Cases**: N/A — this requirement is a forward-compatibility acceptance statement, not
new behavior; it is satisfied by REQ-001..REQ-004 being general-purpose (claim-type-
parameterized), not hardcoded to Instagram or any single platform.
**Acceptance Criteria**:
- Nothing in `.claude/agents/reality-verifier.md`, `reality-verdict-schema.mjs`, or
  `reality-verify-spawn.sh` after this feature names "Instagram" or any single platform —
  the mechanism is general (Instagram is only ever an example in prose/comments, never a
  hardcoded string checked by logic), matching the anti-hardcoding rule in
  `~/.claude/rules/building-effective-ai-agents.md`.

## Non-functional requirements

- **Performance bound**: a `/vcsdd-reality` spawn is capped at the same order of magnitude as
  the existing `gig_reality_verify.sh` judge spawn (600s timeout) — the gate script MUST NOT
  block the caller indefinitely; on timeout it records `gates.reality = FAIL` with a
  `timeout` finding (fail-closed), never leaves the gate unset.
- **Security constraint**: no file added by this feature imports or calls a
  signing/keypair/private-key library (carried over from reality-verifier REQ-007) — this
  feature only extends categories/wiring, it does not touch on-chain read/write scope at all.
- **Security constraint**: the deterministic CDP-marker backstop (REQ-003) must itself be a
  pure function with no network/file access, so it cannot be tricked by anything other than
  the verdict object's own content.

## Judgment vs determinism (anti-hardcoding discipline)

Per `~/.claude/rules/building-effective-ai-agents.md`: whether a report is "honest", whether a
finding fits `post_not_publicly_visible` vs `narrate_only_claim`, and whether DOM content is a
soft-404 are all JUDGMENT calls — the LLM (reality-verifier) makes them, guided by
right-altitude prompt instructions and concrete examples (REQ-002/REQ-004), never by
keyword/regex classification. The only things implemented as deterministic code in this
feature are: the fixed category catalog membership check (a lookup, not a judgment), the
CDP-port-9222 evidence-marker backstop (parsing a fixed, structured field the LLM itself
wrote — not judging free-text content), jsonl path derivation, and gate recording via the
state library. If any future change needs to decide "is this claim actually honest" via a
regex/keyword rule instead of the LLM's own reasoning, that is the anti-pattern this rule
forbids and must be rejected in review.
