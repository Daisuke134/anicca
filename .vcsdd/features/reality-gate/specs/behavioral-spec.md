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

| Iteration | Verdict | Blocking findings | Disposition in this revision |
|---|---|---|---|
| 1 (`reviews/spec-review-01.md`) | FAIL | FIND-001 (recordGate enum crash), FIND-002 (backstop inspects the LLM's own prose instead of independently-captured evidence — the exact bypass this feature exists to close) | REQ-008/009 rewritten to use only schema-legal `recordGate` values (FIND-001, below). REQ-003/004 fully redesigned around a deterministic, non-LLM capture tool + provenance-based backstop, mirroring `gig_reality_gate.py`/`cdp_nav_snapshot.py` exactly, logged-out instead of logged-in (FIND-002, below, new REQ-012). FIND-003 (marker false-positive) is now moot — the new mechanism has no substring/keyword matching over free text at all. FIND-004 (`evidence.fetchMethod` phantom field) resolved by NOT inventing a new evidence field — provenance citation reuses the existing `evidence.filePath`+`lineRange` shape, pointing into the artifact trail file. FIND-005 (hook file path) fixed to match the ecosystem's real, observed convention (`.claude/settings.json` top-level `hooks` key + `.claude/hooks/scripts/*.sh`, confirmed by reading `anicca-project/.claude/settings.json`), and the live-fire hook-behavior check is now itself a required proof obligation (PROP-019), not prose only. |

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
ground truth it is graded against** (iteration-1 FIND-002's core lesson: a verifier whose
evidence check re-reads its own prose is not independent).

## Purity boundary analysis (top-level, elaborated per-requirement below)

- **Pure / deterministic core** (side-effect-free, unit- and property-testable):
  - the finding-category catalog and its validators (`FINDING_CATEGORIES`,
    `isKnownCategory`, `validateVerdictShape` in
    `skills/self/lib/reality-verdict-schema.mjs`) — extended, not replaced;
  - path/line derivation for the durable verdict trail (REQ-006) and the new artifact trail
    (REQ-012);
  - `validateArtifactProvenance(verdict, capturedArtifacts, claimType)` (REQ-003/004,
    replaces the rejected `enforceLoggedOutEvidence` design) — given a verdict AND an
    already-read array of independently-captured artifact rows, decides PASS/FAIL by
    matching citations against that array; takes the captured rows as a plain argument
    (never reads a file itself) so it stays pure — the effectful file read is a separate,
    explicit step in the gate script (mirrors `gig_reality_gate.py`'s own split between
    `count_evidence_rows` (effectful) and `gate_verdict` (pure)).
- **Effectful shell** (not unit-tested; verified only by real spawns / own-eyes review):
  - `.claude/agents/reality-verifier.md` — the LLM's own judgment when it actually reasons;
  - `skills/self/reality-verify-spawn.sh` — spawns a detached `claude` process;
  - `skills/self/scripts/public_artifact_snapshot.py` (REQ-012, new) — the deterministic
    logged-out capture tool; performs a real network fetch and writes a real file;
  - the gate script — calls the spawn wrapper, generates the pass id, reads the artifact
    trail file, calls the pure `validateArtifactProvenance`, appends the verdict trail line,
    calls the plugin's `recordGate()` (a real `writeState` file write);
  - `.claude/commands/vcsdd-reality.md` — instructional command definition, not code;
  - `.claude/settings.json`'s `hooks.PreToolUse` entry + `.claude/hooks/scripts/
    vcsdd-reality-gate-check.sh` (REQ-009) — inherently effectful (inspects live tool-call
    payloads), but its decision logic is unit-testable by invoking the script directly with
    fixture payloads (PROP-019), independent of whether Claude Code's hook composition
    actually fires it at runtime.

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

### REQ-003: Logged-out evidence MUST be independently captured, never the LLM's own prose (redesigned, closes FIND-002)
**EARS**: WHEN reality-verifier is asked to verify a claim of a *publicly visible* artifact
(the claim's declared type is `publish`/`post`/`deploy`, or the target is a public URL) THE
SYSTEM SHALL require that the evidence backing any `PASS` or any finding about that claim was
produced by an independently-run, non-LLM-authored capture step (REQ-012's deterministic
tool) that never uses an authenticated session — and a deterministic backstop, run on the
verdict AFTER the LLM produces it and BEFORE it is accepted by the caller, SHALL verify that
the cited evidence actually corresponds to a row that tool produced during THIS verification
pass, not merely that the LLM's own description avoids naming an authenticated tool.
**Rejected design (iteration-1 FIND-002)**: substring-matching the verdict's own free-text
`evidence`/`evidenceReviewed` fields for tokens like `"9222"`/`"daily-driver"` is explicitly
REJECTED — it only catches a report that happens to admit the violation in its own words, and
is silently bypassed by any report that observed an authenticated-session view but described
it in words that never mention how it was observed. This was iteration-1's exact BLOCKING
finding; the redesign below replaces it entirely, it does not patch around it.
**Edge Cases**:
- The same verification run also needs a logged-in check for something else (e.g. confirming
  an internal dashboard number) — that separate check MAY use the existing daily-driver
  CDP:9222 tab under the existing shared-lock rules (never duplicate/close the tab —
  `~/anicca/skills/earn/gig/scripts/cdp_lock.sh` is the established pattern for mutual
  exclusion with a loop's own core process); ONLY the public-visibility check itself must go
  through REQ-012's tool.
- The LLM navigates via CDP itself (Bash) instead of calling the required tool, then reports
  a `domExcerpt` that never mentions "9222"/"daily-driver": under the new design this is
  caught not because the words are absent, but because NO row in the independently-read
  artifact trail (REQ-012) corresponds to what the LLM cites — the backstop rejects any
  citation that does not resolve to a real row this pass produced (REQ-004).
- No public URL exists to check at all (claim omits it) — fail-closed: `FAIL` with
  `post_not_publicly_visible`, not silently skipped.
- A determined agent with Bash could, in principle, hand-forge a fake row into the artifact
  trail file without actually calling the capture tool (this residual risk is explicitly
  inherited from, and no worse than, the already-shipped `gig_reality_gate.py`/
  `cdp_nav_snapshot.py` pattern this feature mirrors — VERIFIED by reading both files; that
  pattern has the same theoretical gap and is accepted project-wide as "own-eyes /
  fresh-adversary review is the final backstop against a fully adversarial capable-of-Bash
  agent", not something this feature is required to solve that the pattern it mirrors does
  not already solve).
**Acceptance Criteria**:
- `.claude/agents/reality-verifier.md` contains an explicit instruction: for any
  public-artifact claim, call `skills/self/scripts/public_artifact_snapshot.py <passId> <seq>
  <label> <url>` (REQ-012) exactly, once per claimed public URL, using the pass id supplied in
  the task — never a freeform CDP/curl invocation of the model's own choosing for this
  specific check — and to cite the resulting row (`evidence.filePath` = the artifact trail
  path, `evidence.lineRange` = that row's line) in its verdict.
- `validateArtifactProvenance(verdict, capturedArtifacts, claimType)` exists in
  `skills/self/lib/reality-verdict-schema.mjs`: pure, takes the verdict plus an
  already-read array of captured-artifact row objects (never touches `fs` itself), and:
  - for a public-artifact `claimType`, rejects (downgrades to `FAIL` with an added
    `post_not_publicly_visible` finding) any `PASS` or finding whose cited
    `filePath`+`lineRange` does not resolve to a row present in `capturedArtifacts` with
    `tool === "public_artifact_snapshot"`;
  - is exercised by both example-based and property tests, including the specific bypass
    fixtures required by REQ-004's acceptance criteria.

### REQ-004: PASS evidence for public-artifact claims must resolve to a real captured-this-pass row (redesigned)
**EARS**: WHEN reality-verifier emits `overallVerdict: "PASS"` (or any finding) for a
public-artifact claim THE SYSTEM SHALL cite `evidence.filePath` (the artifact trail file,
REQ-012) and `evidence.lineRange` (the specific row), and the deterministic backstop
(REQ-003) SHALL independently re-read that exact row and confirm ALL of: (a) the row exists,
(b) `row.tool === "public_artifact_snapshot"` (never an authenticated-capture tool name),
(c) `row.passId` matches the pass id this verification run was given, (d) `row.ts` is at or
after this run's start timestamp (never a stale row left over from a previous, unrelated
pass reusing the same loop) — mirroring `gig_reality_gate.py`'s existing `count_evidence_rows`
(`pass_id` + `min_ts` scoping, VERIFIED by reading `gig_reality_gate.py:39-61`) exactly,
except our tool is logged-out where gig's `cdp_nav_snapshot.py` is logged-in.
**Edge Cases**:
- A cited row exists, matches the pass id, but its `tool` field is
  `"cdp_nav_snapshot"` (gig's real, already-existing AUTHENTICATED capture tool name) instead
  of `"public_artifact_snapshot"` — THE SYSTEM SHALL reject this exactly as if no row existed
  at all (`FAIL`, `post_not_publicly_visible`): this is the concrete, testable stand-in for
  "artifact captured from an authenticated context" the review demanded a proof obligation
  for (PROP-018 below).
- A cited row exists and passes all four checks, but its `httpStatus` is in the 400/500 range
  or its `domExcerpt` is empty/error-page content: the LLM's own judgment (not the backstop)
  is responsible for reading that row's content and concluding `post_not_publicly_visible`
  itself — the backstop's job is provenance (is this real, independently-captured, logged-
  out, this-pass evidence), not content interpretation (is the page actually showing the
  post) — that split keeps the deterministic layer a lookup, not a judgment, per
  `~/.claude/rules/building-effective-ai-agents.md`.
**Acceptance Criteria**:
- A unit test feeds `validateArtifactProvenance` a PASS verdict citing a row whose `tool` is
  `"cdp_nav_snapshot"` (simulating an authenticated-context capture) and asserts the result is
  `overallVerdict: "FAIL"` with a `post_not_publicly_visible` finding (closes the exact gap
  FIND-002 named: "a claim whose artifact was captured from an authenticated context...
  MUST FAIL").
- A unit test feeds it a PASS verdict citing a `filePath`+`lineRange` that resolves to no row
  in `capturedArtifacts` at all, and asserts the same rejection (closes "...or has no artifact
  at all... MUST FAIL").
- A unit test feeds it a PASS verdict citing a row whose `passId` does not match the current
  run's pass id (stale/foreign-pass row), and asserts the same rejection.

### REQ-005: Generalized spawn wrapper — any claim type, backward compatible with the real existing caller
**EARS**: WHEN a caller needs to verify a real-world side-effect claim of any kind (`earn`,
`publish`, `post`, `deploy`) THE SYSTEM SHALL provide `skills/self/reality-verify-spawn.sh`
accepting `<loop-name> <artifact-or-public-url> [claim-text] [claim-type] [pass-id]`, where
omitting `claim-type` defaults to `earn` (the pre-existing behavior) so that
`skills/self/reality-verify-on-new-earn.sh` — the one real existing caller (VERIFIED by
`grep -rl reality-verify-spawn` across the repo; `gig_reality_verify.sh`/`gig_judge.py` do
**not** call this script — see REQ-001 edge case) — continues to work with zero changes to
its 3-positional-argument invocation, and omitting `pass-id` (only meaningful for
public-artifact `claim-type`s) generates one deterministically (mirrors
`gig_reality_verify.sh`'s own `PASS_ID="realityverify-$(date +%s)-$$"` pattern, VERIFIED by
reading that script) so REQ-004's provenance scoping always has a pass id to key against.
**Edge Cases**:
- `claim-type` is an unrecognized string: THE SYSTEM SHALL treat it as a generic
  "real-world side-effect claim" (fall through to the general narrate-only/evidence rules,
  no REQ-012 tool requirement) rather than erroring, since the spawn wrapper does not itself
  validate claim semantics — that is the agentic layer's job.
- `claim-type` is a public-artifact type (`publish`/`post`/`deploy`) but `artifact-or-
  public-url` looks like a local filesystem path, not a URL: the spawned task text MUST still
  instruct "if this claim is about public visibility, find/derive the actual public URL
  yourself and check it via REQ-012's tool with THIS run's pass id" rather than silently
  treating a local path as sufficient evidence.
**Acceptance Criteria**:
- `test-reality-verify-spawn.sh`'s existing 3 assertion groups (A/B/C) still pass unchanged
  after this feature (regression baseline).
- A new DRYRUN assertion confirms a 4th `claim-type` argument and a 5th `pass-id` argument
  (auto-generated when omitted) are both threaded into the spawned task text when provided,
  and `claim-type` defaults to `earn` / `pass-id` defaults to an auto-generated value when
  omitted.

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
1. The three deterministic unit-test bypass fixtures required by REQ-004's acceptance
   criteria (authenticated-tool citation, no matching row, foreign/stale pass id) — these are
   the CI-runnable proof that the backstop itself cannot be fooled by prose alone.
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
- All three REQ-004 bypass unit tests pass (see REQ-004 acceptance criteria — repeated here
  because REQ-007 is what makes them a *required*, not optional, gate for this feature).
- A real, committed FAIL verdict json (or its jsonl line, REQ-006) exists under
  `.vcsdd/features/reality-gate/evidence/` (or `~/.openclaw/state/`, referenced by path) as
  the live-run artifact, produced by an actual spawn during Phase 2b/2c of this feature, not
  fabricated by hand.

### REQ-008: VCSDD Phase 4.5 REALITY GATE — `vcsdd-reality` command, project-level (not plugin cache), schema-legal gate values only (fixes FIND-001)
**EARS**: WHEN a VCSDD feature has passed adversarial review (plugin-internal phase `'3'`,
`gates['3'].verdict === 'PASS'`, VERIFIED by reading `scripts/lib/vcsdd-state.js`'s
`GATE_PREREQUISITES['5']`) THE SYSTEM SHALL provide a `/vcsdd-reality` command that spawns a
FRESH `reality-verifier` instance (zero context from the Builder/loop being verified, same
fresh-context discipline as `/vcsdd-adversary`) against that feature's own real-world
acceptance claim, and records the resulting verdict into the feature's `state.json` via the
plugin's own exported `recordGate(featureName, 'reality', verdict, reviewedBy, details)`
function, called ONLY with values legal under the plugin's own, unmodified
`schemas/vcsdd-state.schema.json` (VERIFIED, quoted verbatim):
```json
"verdict": { "type": "string", "enum": ["PASS", "FAIL", "SKIP"] },
...
"reviewedBy": { "type": "string", "enum": ["adversary", "verifier", "human"] },
```
i.e. `recordGate(featureName, 'reality', 'PASS'|'FAIL'|'SKIP', 'verifier', details)` — never
`'SKIPPED'` (iteration-1's exact crashing value) and never `'reality-verifier'` as
`reviewedBy` (also not in the enum) — `'verifier'` is the correct, already-existing enum
value for this role. `recordGate`'s `phase` parameter itself remains unconstrained by the
schema (VERIFIED: `state.gates` is `{"type":"object","additionalProperties": {...}}` with no
`enum` on the object's own keys — only the VALUES under each key are constrained by the
`verdict`/`reviewedBy` enums quoted above), so `'reality'` as the gate key is still fully
legal; only the enum VALUES needed correcting, not the key.
**Edge Cases**:
- The plugin is later updated and overwrites `/Users/anicca/.claude/plugins/cache/
  vcsdd-claude-code/vcsdd/1.0.0/` — THE SYSTEM SHALL NOT be affected, because none of this
  feature's files live under that cache path; `/vcsdd-reality`'s command file, its supporting
  script, and the (already-existing) `reality-verifier` agent all live under THIS repo's own
  `.claude/` and `skills/self/`, which a plugin update never touches.
- A feature has no obvious "real-world claim" to check (a pure library refactor with no
  side-effecting behavior): THE SYSTEM SHALL allow `/vcsdd-reality --skip
  "<reason>"` to record `gates.reality = { verdict: "SKIP", timestamp, reviewedBy: "human",
  details: "<reason>" }` — using the schema-legal `SKIP` value and `reviewedBy: "human"` (a
  human/orchestrator decision to skip is semantically a human review, not the automated
  verifier's own verdict) — explicitly rather than silently omitting the gate. REQ-009's
  convergence check treats an explicit, reasoned `SKIP` as satisfying the gate, but a MISSING
  `gates.reality` key never does.
**Acceptance Criteria**:
- Command file exists at `.claude/commands/vcsdd-reality.md` in THIS repo (`~/anicca`), not
  under the plugin cache path.
- After running it (or its Phase 2b/2c live proof, REQ-007), the active feature's
  `.vcsdd/features/<name>/state.json` contains a `gates.reality` object with `verdict`
  strictly one of `PASS`/`FAIL`/`SKIP` and `reviewedBy` strictly one of `adversary`/
  `verifier`/`human`, written via `recordGate()` (i.e. `state.json` is never hand-edited for
  this purpose — `history.jsonl` also gains a matching `gate_recorded` entry for `phase:
  "reality"`, which is `recordGate()`'s built-in behavior).
- A unit test (or a direct `require()` + call in a throwaway fixture state directory) proves
  `recordGate(feature, 'reality', 'SKIP', 'verifier', {...})` and `recordGate(feature,
  'reality', 'PASS', 'verifier', {...})` both complete without throwing against the plugin's
  real, unmodified `vcsdd-schema.js`/`vcsdd-state.schema.json` — i.e. the values this feature
  specifies are proven schema-legal by actually calling the real validator, not merely by
  reading the schema and asserting it by eye.

### REQ-009: Convergence requires the reality gate — 5 dimensions, not 4 (fixes FIND-005: real hook convention, live-fire proof required)
**EARS**: WHEN a feature attempts to reach VCSDD completion (`currentPhase: "complete"`) THE
SYSTEM SHALL require, in addition to the plugin's existing 4-dimension check (spec fidelity /
test coverage / implementation correctness / formal verification, enforced by the plugin's
own unmodified `validateConvergenceForCompletion`), that `gates.reality.verdict` is `PASS` or
`SKIP` (with a non-empty `details` reason, REQ-008 edge case) — never absent and never
`FAIL` — and this 5th-dimension check SHALL be enforced by project-level artifacts added to
THIS repo, following the ecosystem's REAL, observed, already-working convention for
project-level Claude Code hooks (VERIFIED by reading `/Users/anicca/anicca-project/
.claude/settings.json:48-144`: a top-level `"hooks"` key directly inside `.claude/
settings.json`, with matcher/handler entries pointing at shell scripts under
`.claude/hooks/scripts/*.sh` — there is **no** separate `.claude/hooks/hooks.json` file in
that convention; iteration-1's `.claude/hooks/hooks.json` path was WRONG — it copied the
*plugin's own internal packaging file shape*, a different mechanism, by mistake):
- `.claude/settings.json` (created fresh in this repo, which does not yet have one — VERIFIED
  by `ls .claude/` showing only `agents/`/`handovers/` before this feature) gains a
  `hooks.PreToolUse` entry matching `Bash`, pointing at
  `.claude/hooks/scripts/vcsdd-reality-gate-check.sh`.
- That script re-reads `state.json` for the active feature directly (not via heuristic
  Bash-command-text parsing alone) and blocks (non-zero exit / hook `blocked: true` response)
  when the command under review would transition the active feature to `complete` while
  `gates.reality` is missing or `FAIL`.
- A standalone, independently runnable backstop (`skills/self/verify-reality-gate.mjs`) is
  the AUTHORITATIVE check: it can be invoked manually or wired into this repo's existing
  `.githooks/pre-push`, and does not depend on Claude Code's hook system at all.
**Edge Cases**:
- Whether Claude Code actually invokes a project-level `.claude/settings.json` `PreToolUse`
  hook in addition to (not instead of) any plugin-level hook for the same tool/event is
  ASSUMED, not verified this session (no live fire test was run). THE SYSTEM SHALL therefore
  treat the hook SCRIPT's own correctness (does it decide PASS/FAIL correctly given a
  fixture payload + fixture `state.json`) as independently, mechanically provable
  (PROP-019, verification-architecture.md) REGARDLESS of whether Claude Code's runtime
  actually invokes it — narrowing the unverified surface from "does this whole mechanism
  work" to just "does Claude Code invoke project hooks", with the standalone backstop script
  as the fallback authoritative gate either way.
- A pre-existing feature (created before this gate existed) is mid-pipeline: THE SYSTEM SHALL
  NOT retroactively block phases 1-4 for it; the 5th-dimension requirement applies only at the
  `'complete'` transition, so older features simply need one `/vcsdd-reality` run before they
  can complete going forward.
**Acceptance Criteria**:
- `.claude/settings.json` exists in this repo with a `hooks.PreToolUse` entry referencing
  `.claude/hooks/scripts/vcsdd-reality-gate-check.sh`, matching the exact shape (top-level
  `hooks` key, matcher/hooks array, `type: "command"`) VERIFIED in
  `anicca-project/.claude/settings.json:59-69`.
- `verify-reality-gate.mjs` exits non-zero when a fixture `state.json` has `currentPhase:
  "complete"` and `gates.reality` missing/`FAIL`, and exits zero when `gates.reality.verdict`
  is `PASS` or `SKIP` — covered by a unit test using fixture `state.json` files (no live spawn
  needed).
- `vcsdd-reality-gate-check.sh` is directly invokable with a crafted fixture payload +
  fixture `state.json` and returns a blocking result for the FAIL/missing case and a
  non-blocking result for the PASS/SKIP case — this is PROP-019 (verification-architecture.md)
  and is `required: true`.

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
REQ-003/REQ-012's independently-captured, logged-out public-URL check, using the exact same
`reality-verifier` agent and `vcsdd-reality` gate this feature ships — no growth-engine-
specific verifier code is needed.
**Edge Cases**: N/A — this requirement is a forward-compatibility acceptance statement, not
new behavior; it is satisfied by REQ-001..REQ-004/REQ-012 being general-purpose (claim-type-
parameterized, tool-parameterized by URL not by platform), not hardcoded to Instagram or any
single platform.
**Acceptance Criteria**:
- Nothing in `.claude/agents/reality-verifier.md`, `reality-verdict-schema.mjs`,
  `reality-verify-spawn.sh`, or `public_artifact_snapshot.py` after this feature names
  "Instagram" or any single platform — the mechanism is general (Instagram is only ever an
  example in prose/comments, never a hardcoded string checked by logic), matching the
  anti-hardcoding rule in `~/.claude/rules/building-effective-ai-agents.md`.

### REQ-012: Deterministic logged-out capture tool (new — mirrors `cdp_nav_snapshot.py`, diverges on auth)
**EARS**: WHEN reality-verifier (or the gate script, for the negative-test proof) needs to
check a public URL THE SYSTEM SHALL provide `skills/self/scripts/public_artifact_snapshot.py
<passId> <seq> <label> <url>` — a deterministic, non-LLM script that performs the actual
network fetch, structurally never touches CDP port `9222` / the CloakBrowser daily-driver
session / any cookie jar, and appends exactly one row to
`$HOME/.openclaw/state/reality-artifacts/<passId>/artifacts.jsonl` containing at minimum
`{ts, passId, seq, label, tool: "public_artifact_snapshot", requestedUrl, finalUrl,
httpStatus, domExcerpt}`, printing the artifact file path (or `ERROR:<reason>`) to stdout —
never raising, so a failed capture is itself evidence (an unreachable/erroring fetch), not a
crashed run.
**Exact mirror / exact divergence from `cdp_nav_snapshot.py` (VERIFIED by reading
`skills/earn/gig/scripts/cdp_nav_snapshot.py` in full)**:
| aspect | `cdp_nav_snapshot.py` (gig, logged-in) | `public_artifact_snapshot.py` (this feature, logged-out) |
|---|---|---|
| connection | connects to the LIVE CDP `:9222` daily-driver tab (`get_tab()`, `ws://localhost:9222/devtools/page/<id>`) — reuses the authenticated session on purpose | MUST NOT open any `:9222` connection at all — a plain HTTP(S) client (`urllib.request`/`requests`, or a freshly-spawned headless browser process with an ephemeral/incognito profile that is never attached to an existing CDP session) with no cookie jar loaded from any profile |
| what it proves | "the authenticated account's view of this page, right now" | "what the public, logged-out internet sees at this URL, right now" |
| evidence row shape | `{ts, pass_id, seq, label, requested_url, url, title, action, navigated_ok, png}` under `~/gig/trajectory/<pass_id>/` | `{ts, passId, seq, label, tool, requestedUrl, finalUrl, httpStatus, domExcerpt}` under `~/.openclaw/state/reality-artifacts/<passId>/` — a distinct directory tree AND a distinct, structurally-checkable `tool` field name, so the two are never confusable by the provenance check (REQ-004) |
| failure handling | never raises; screenshot captured regardless of `navigated_ok` | never raises; `httpStatus`/error captured regardless of reachability (fail-closed evidence either way) |
| scoping | caller-side gate (`gig_reality_gate.py`) counts rows by `pass_id` + `min_ts`, independent of the judge's self-report | same scoping pattern, reused verbatim by `validateArtifactProvenance` (REQ-003/004) |
**Edge Cases**:
- The target URL requires JavaScript rendering to show real content (a client-side-rendered
  post page): a plain HTTP fetch's `domExcerpt` may show only a loading shell. THE SYSTEM
  SHALL prefer a headless-browser variant (fresh incognito profile, never CDP:9222) when the
  claim type is `publish`/`post`/`deploy` and the target platform is known to be JS-rendered,
  falling back to the plain HTTP fetch otherwise — this choice is itself deterministic (a
  fixed platform→method table, not an LLM judgment), decided in Phase 2a/2b implementation,
  not this spec.
- Rate limiting / bot-blocking on the public fetch (some platforms 403 logged-out requests
  from a bare `curl`): the resulting `httpStatus`/`domExcerpt` is still captured and is itself
  valid (if inconclusive) evidence — the LLM's judgment (not the tool) decides whether a 403
  means "not public" or "anti-bot false negative", and MUST say so explicitly rather than
  silently treating a 403 as proof of either.
**Acceptance Criteria**:
- `skills/self/scripts/public_artifact_snapshot.py` contains no import of, or reference to,
  port `9222` anywhere in its source (grep-checkable, mirrors REQ-010's "no Write/Edit"
  grep-checkable acceptance style).
- Its artifact rows live under a directory tree distinct from `~/gig/trajectory/` and carry a
  `tool` field distinct from `"cdp_nav_snapshot"`, so REQ-004's provenance check can reject
  cross-tool citation structurally, not by string-guessing.

## Non-functional requirements

- **Performance bound**: a `/vcsdd-reality` spawn is capped at the same order of magnitude as
  the existing `gig_reality_verify.sh` judge spawn (600s timeout) — the gate script MUST NOT
  block the caller indefinitely; on timeout it records `gates.reality = { verdict: "FAIL",
  reviewedBy: "verifier", details: "timeout" }` (fail-closed), never leaves the gate unset.
- **Security constraint**: no file added by this feature imports or calls a
  signing/keypair/private-key library (carried over from reality-verifier REQ-007) — this
  feature only extends categories/wiring, it does not touch on-chain read/write scope at all.
- **Security constraint**: `validateArtifactProvenance` and all other new pure functions have
  no network/file access, so they cannot be tricked by anything other than the verdict object
  and the already-independently-read `capturedArtifacts` array passed to them.
- **Security constraint**: `public_artifact_snapshot.py` (REQ-012) is structurally incapable
  of authenticated access — it has no CDP client code path and no cookie-jar loading code
  path at all, not merely a prompt instruction not to use one.

## Judgment vs determinism (anti-hardcoding discipline)

Per `~/.claude/rules/building-effective-ai-agents.md`: whether a report is "honest", whether a
finding fits `post_not_publicly_visible` vs `narrate_only_claim`, and whether a captured
`domExcerpt` actually shows the claimed content (vs. a soft-404/error page/anti-bot block) are
all JUDGMENT calls — the LLM (reality-verifier) makes them, guided by right-altitude prompt
instructions and concrete examples (REQ-002/REQ-004/REQ-012), never by keyword/regex
classification. The only things implemented as deterministic code in this feature are: the
fixed category catalog membership check (a lookup, not a judgment), the artifact-provenance
check (does a cited row exist, from the right tool, right pass, right time-window — a lookup
against independently-captured structured data, not an interpretation of prose or DOM
content), jsonl path derivation, and gate recording via the state library. Iteration-1's
rejected `enforceLoggedOutEvidence` design (substring-matching the LLM's own free text) was,
on reflection, itself a smaller instance of exactly this anti-pattern — a keyword rule
standing in for judgment/verification it could not actually perform — and its replacement
(REQ-003/004/012) is deliberately designed to check STRUCTURE (does this row exist, from this
tool, this pass) rather than CONTENT (does this text contain these words), which is the
correct place to draw the pure/agentic boundary. If any future change needs to decide "is
this claim actually honest" via a regex/keyword rule over free text instead of the LLM's own
reasoning, that is the anti-pattern this rule forbids and must be rejected in review.
