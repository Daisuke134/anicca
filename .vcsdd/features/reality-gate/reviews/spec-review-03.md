# VCSDD Adversary — Phase 1c Spec Review (iteration 3)

Feature: `reality-gate` (mode: lean) — Phase 4.5 REALITY GATE
Reviewer: fresh-context adversary (zero context from Builder, zero context from iterations 1-2's
reviewers — everything below is re-derived from disk, iteration-1/2's dispositions independently
re-checked, not trusted from their own claims).

Artifacts actually read (paths + line ranges), used as the basis for every finding/PASS below:

- `.vcsdd/features/reality-gate/specs/behavioral-spec.md` (1-641, full file)
- `.vcsdd/features/reality-gate/specs/verification-architecture.md` (1-154, full file)
- `.vcsdd/features/reality-gate/reviews/spec-review-01.md` (1-138, full file)
- `.vcsdd/features/reality-gate/reviews/spec-review-02.md` (1-292, full file)
- `.claude/agents/reality-verifier.md` (1-139, full file)
- `skills/self/lib/reality-verdict-schema.mjs` (1-128, full file — confirmed 6 categories currently, 62-65 `hasCiteableEvidence`)
- `skills/self/reality-verify-spawn.sh` (1-69, full file — confirmed current 3-positional-arg contract)
- `skills/earn/gig/scripts/gig_reality_gate.py` (1-118, full file)
- `skills/earn/gig/scripts/cdp_nav_snapshot.py` (1-151, full file — confirmed no `httpStatus` field, `navigated_ok` boolean instead)
- `skills/earn/gig/gig_judge.py` (1-160 read — `DEFAULT_GROUND_TRUTH_URLS`, `gate_verdict`, `build_verifier_prompt`)
- `skills/earn/gig/gig_reality_verify.sh` (grep-confirmed `REQUIRED_COUNT` derivation, lines 108-117)
- `.githooks/pre-push` (1-142, full file — Cadence Contract Guard precedent)
- `/Users/anicca/anicca/.git/config` (1-48, full file — confirmed `core.hooksPath = .githooks` live)
- `/Users/anicca/.claude/plugins/cache/vcsdd-claude-code/vcsdd/1.0.0/schemas/vcsdd-state.schema.json` (1-107, full file)
- `/Users/anicca/.claude/plugins/cache/vcsdd-claude-code/vcsdd/1.0.0/scripts/lib/vcsdd-state.js` (1-120, 210-280, 1050-1143, 1720-1800 — `GATE_PREREQUISITES` incl. `'5'`, `validateConvergenceForCompletion`, `recordGate`)
- `/Users/anicca/anicca-project/.claude/settings.json` (1-158, full file)
- `~/.claude/rules/building-effective-ai-agents.md` (full file, via system context)

No `manifest.json`/`reviews/spec/iteration-N/input` scaffold exists for this scope; reviewed
directly against the task brief, per the convention iterations 1-2 already used.

---

## Disposition of iteration-2's blocking findings (independently re-verified against ground truth)

### FIND-A (zero-citation PASS unguarded) — **CONFIRMED FIXED**
`behavioral-spec.md:194-260` (REQ-004) and `verification-architecture.md:21-43`
(`validateArtifactProvenance`'s described 5-step contract) now make citation-count-ever-present
check #1 unconditional and first: "at least `requiredArtifactCount` DISTINCT... citations are
present in the verdict at all. Zero citations is itself a violation." PROP-022
(`verification-architecture.md:98`) is a named, `required: true` fixture forcing exactly this case
(domExcerpt-only, zero `filePath`, `requiredArtifactCount:1`) to `FAIL`. Genuinely fixed — this is
a real, structural improvement over iteration-2's design.

### FIND-B (nothing forces the authoritative backstop to run) — **CONFIRMED FIXED AT THE DESIGN LEVEL, NEW GAP FOUND — see FIND-F below**
REQ-009 (`behavioral-spec.md:391-457`) now upgrades `.githooks/pre-push` wiring from optional prose
to a required acceptance criterion with a named live-fire PROP (PROP-027,
`verification-architecture.md:103`), independently confirmed against the real
`validateConvergenceForCompletion` (`vcsdd-state.js:1066-1143`, confirmed zero reference to
`gates.reality` anywhere in that function) and the real, working Cadence Contract Guard precedent
(`.githooks/pre-push:18-30,75-96`, confirmed by direct read). The specific mechanism iteration-2
named (optional-prose wiring) is genuinely closed. **However**, the live-fire proof this closure
relies on does not exercise every way this exact enforcement point can be defeated — see FIND-F.

### FIND-C (`claimType` provenance ambiguous) — **CONFIRMED FIXED AT THE DESIGN LEVEL, NEW GAP FOUND — see FIND-E below**
REQ-013 (`behavioral-spec.md:552-596`) now pins `claimType`/`requiredArtifactCount` to a committed,
Phase-1c-reviewed `reality-claim.json`, explicitly forbidding both LLM-self-declaration and
ad-hoc CLI override. The specific ambiguity iteration-2 named (verdict-object vs. caller-argument)
is genuinely resolved — there is now exactly one source of truth named in the text. **However**,
"the file exists and is the sole source" does not by itself prevent the file's *content* from being
changed without re-verification, and no mechanism in this iteration ties a recorded
`gates.reality: PASS` to the specific `reality-claim.json` content it was checked against — see
FIND-E.

---

## Dimension 1: spec_fidelity — **FAIL**

### FIND-E (BLOCKING) — `gates.reality`'s recorded verdict is never bound to a specific version of `reality-claim.json`; REQ-013's own closure claim for closure-row-5/FIND-C is not actually enforced end-to-end

`decideConvergenceGate(state, realityClaim)` (`verification-architecture.md:44-50`) is described,
completely, as: `blocked: false` iff `state.gates.reality?.verdict === "PASS"`, OR (`SKIP` AND
`realityClaim?.claimType === "none"`); `blocked: true` otherwise, including `realityClaim` being
null/malformed. Nowhere in this description, nor in REQ-009's acceptance criteria
(`behavioral-spec.md:441-457`, PROP-026 `behavioral-spec.md:450-453`/`verification-architecture.md:102`),
is `gates.reality`'s stored `details.claimType`/`details.requiredArtifactCount` (which REQ-008 does
require storing, `behavioral-spec.md:358-361`) ever compared against the **current**
`reality-claim.json`'s values. Two concrete, independent exploits follow directly:

**(a) Same-push downgrade.** A single commit/push can simultaneously (i) weaken
`reality-claim.json`'s `claimType` from `"post"` to `"none"` and (ii) set `state.json`'s
`currentPhase: "complete"` with `gates.reality: {verdict: "SKIP"}`. The pre-push Reality
Convergence Guard (REQ-009) reads the file content **at push time**, i.e. the new, weakened
`reality-claim.json` — sees `claimType === "none"`, legalizes `SKIP`, and the push succeeds. The
feature's real original claim (a public Instagram post, per REQ-011's acceptance vehicle) was never
independently verified. REQ-013's edge case says a changed `claimType` "MUST... go back through
Phase 1c review" (`behavioral-spec.md:574-578`) — this is **prose only**; no PROP or acceptance
criterion in this spec checks that a `reality-claim.json` diff was itself gated by a fresh Phase-1c
review before being accepted at push time. PROP-026 tests `decideConvergenceGate` against a single,
static `(state, realityClaim)` pair, never a push that *changes* `realityClaim` in the same range.

**(b) Stale PASS after strengthening.** REQ-013's own edge case explicitly permits
`reality-claim.json` to be updated later (e.g. `requiredArtifactCount` raised from 1 to 5, or
`claimType` changed from `"none"` to `"post"`). A `gates.reality: {verdict: "PASS", details:
{requiredArtifactCount: 1}}` recorded against the OLD, weaker claim remains sufficient forever
after, because `decideConvergenceGate` only inspects `verdict`, never `details` against the current
file. A feature can converge claiming 5 required public artifacts while its only recorded PASS ever
verified 1.

Both scenarios reach "successful convergence/push while the claimed artifact is not publicly
visible" — directly on point for this review's mandate. This is a genuine, un-tested reopening of
the exact vulnerability class (self-reported/unenforced claims treated as sufficient) that this
iteration's own stated purpose (`behavioral-spec.md:17`: "this iteration deliberately closes the
vulnerability **class**... not each individual instance") explicitly commits to closing.

`routeToPhase`: 1b — `decideConvergenceGate` (or the pre-push guard around it) must compare
`gates.reality`'s recorded `details` (or a content hash of `reality-claim.json` at PASS-recording
time, stored alongside the gate) against the CURRENT `reality-claim.json` on every push, and treat
any mismatch (weakened `claimType`, raised `requiredArtifactCount` not yet re-verified) as
`blocked: true`. A new, named, `required: true` PROP must exercise a push range where
`reality-claim.json` differs between the pushed range's start and end.

---

## Dimension 2: edge_case_coverage — **FAIL**

### FIND-D (BLOCKING) — `validateArtifactProvenance` never checks that the cited artifact-trail row's URL corresponds to the actually-claimed artifact; claim-URL substitution is not an enumerated edge case anywhere in REQ-002/003/004/012/013

The complete, described 5-step contract of `validateArtifactProvenance`
(`verification-architecture.md:21-43`) checks: citation presence, dedup by `(passId, seq)`,
resolution (`tool`/`passId`/`ts`/`httpStatus`), count, and pass-through. **At no step is the
resolved row's `requestedUrl`/`finalUrl` (REQ-012's own row shape, `behavioral-spec.md:517-519`)
compared against anything the claim asserts.** REQ-004's full acceptance-criteria bypass-fixture
list (`behavioral-spec.md:236-259`) enumerates exactly 7 bypass fixtures (zero-citation, wrong-tool,
no-matching-row, foreign/stale pass, under-count, duplicate-citation, non-2xx-status) and never a
"cited row is for the wrong URL" fixture. `reality-claim.json`'s schema (REQ-013,
`behavioral-spec.md:555-557`: `{claimType, requiredArtifactCount, description}`) has **no
structured URL field at all** — `description` is free text. Meanwhile REQ-005's edge case
(`behavioral-spec.md:281-285`) explicitly delegates URL derivation entirely to the LLM: "if this
claim is about public visibility, find/derive the actual public URL yourself."

**Concrete failure scenario**: reality-verifier is asked to verify "posted video X to Instagram
publicly," `requiredArtifactCount: 1`. It calls
`public_artifact_snapshot.py <passId> 1 check https://instagram.com/p/SOME_OTHER_ALREADY_PUBLIC_POST`
(a genuinely public, unrelated, older post from the same account — or even the account's public
profile homepage) — this is a real, correctly-tooled, correct-pass, fresh, 2xx-status row.
`validateArtifactProvenance` has no way to know this is the wrong URL: it resolves cleanly, the
count is satisfied, and the verdict is returned unchanged as `PASS`. `gates.reality = PASS` while
the actually-claimed video was never posted or is genuinely shadowbanned.

This is **not** equivalent to the spec's own accepted-open row 12 (Bash-capable forgery of
`artifacts.jsonl`): no forgery is required, no adversarial intent is required — an honest, non-lying
verifier that simply fetches the wrong (but real) URL, through drift, laziness, or a
misunderstanding of which of several account posts is "the" claimed one, produces an undetectable
false PASS. The spec's own claimed mirror (`behavioral-spec.md:213-215`, "mirrors
`gig_reality_gate.py`'s REQUIRED_COUNT pattern") is materially weaker here than what it claims to
copy: gig's `DEFAULT_GROUND_TRUTH_URLS` (`gig_judge.py:26-31`) is a **fixed, caller-supplied,
platform-dashboard URL set known in advance** — the judge is instructed to visit those exact 4 URLs
in order and cannot substitute a different one, because gig's ground truth never depends on a
per-claim, LLM-derived URL. `reality-gate`'s claim structure (a new post at a URL only the LLM can
derive, per claim) has no equivalent fixed anchor, so borrowing gig's "just count independently
captured rows" mechanism without also borrowing (or replacing with an equivalent for) gig's
fixed-URL-list precondition reopens exactly the self-report-trust gap this feature exists to close,
for the one input (the URL) that matters most.

`routeToPhase`: 1b — either (a) `reality-claim.json` must gain a structured, committed, Phase-1c-
reviewed field for the claimed public URL(s) (or a URL pattern/domain the resolved citation must
match), checked deterministically by `validateArtifactProvenance`, or (b) an explicit, reasoned
decision to leave URL-identity to LLM judgment must be stated and justified against the
"judgment vs determinism" section's own bar — currently the spec is silent, not deliberate, on this
point, and silence here is exactly the "absence of a caught problem treated as proof" anti-pattern
`behavioral-spec.md:631-635` says this iteration corrects.

### FIND-G (MAJOR) — no proof obligation validates that `public_artifact_snapshot.py`'s captured `domExcerpt` is diagnostic for the declared first-customer platform (Instagram, REQ-011)

REQ-012's edge case (`behavioral-spec.md:533-537`) defers the JS-render-vs-plain-fetch platform
routing decision to "a fixed platform→method table... decided in Phase 2a/2b implementation, not
this spec." Nothing in `verification-architecture.md`'s Proof Obligations table requires this table
to actually cover Instagram, or that a captured `domExcerpt` for Instagram structurally
distinguishes a public post from a private/removed/shadowbanned one. A plain-HTTP fetch (`urllib`/
`requests`, no JS execution) of an Instagram post URL commonly returns `httpStatus: 200` with a
near-identical SPA-bootstrap HTML shell **regardless of whether the post is public, private, or
deleted** — satisfying REQ-004's status gate while giving the LLM's own judgment no diagnostic
signal to work with. Since REQ-011 explicitly names Instagram as this feature's acceptance vehicle
("the growth-engine marketing loop... claims it posted a video to Instagram," `behavioral-spec.md:484-486`),
and this is the one edge case that would make the entire gate structurally unable to distinguish
public-from-not for its own named first customer, its absence from both the edge-case list and the
proof-obligation table is a real coverage gap, not a hypothetical one.

`routeToPhase`: 1b — REQ-012's platform→method table decision cannot be deferred past this spec for
a platform this spec itself names as the acceptance vehicle; at minimum a named, `required: true`
PROP must assert the captured `domExcerpt`/render path for an Instagram-shaped URL structurally
differs between a real public post and a private/removed one.

---

## Dimension 3: implementation_correctness — **FAIL**

FIND-D above is, under this dimension's own Phase-1c bar ("are the requirements concrete enough to
be implemented unambiguously"), a requirement that is concrete on every axis EXCEPT the one that
matters most (URL correspondence) — a Builder implementing `validateArtifactProvenance` exactly as
specified produces working, schema-legal, fully-tested code that is nonetheless trivially
bypassable by fetching the wrong (but real) URL, with zero test in the spec's own acceptance
criteria that would catch this at implementation time. This is scored here as well as under
edge_case_coverage because it is simultaneously "an edge case the spec never named" and "a
requirement not concrete enough to prevent an unambiguous, silent bypass."

**What is genuinely correct, independently reverified**: `recordGate(featureName, 'reality',
'PASS'|'FAIL'|'SKIP', 'verifier', details)` (REQ-008, `behavioral-spec.md:356-361`) uses values
legal against the REAL, unmodified schema — confirmed directly:
`vcsdd-state.schema.json:37` (`"verdict": {"enum": ["PASS","FAIL","SKIP"]}`) and `:39`
(`"reviewedBy": {"enum": ["adversary","verifier","human"]}`) both match. `recordGate`'s actual
implementation (`vcsdd-state.js:1734-1770`) is a straightforward merge-and-`writeState()`; nothing
about the REQ-008-specified call shape would throw. Genuinely fixed from iteration-1's FIND-001, and
this holds up under a third independent re-check.

`routeToPhase`: 1b (same fix as FIND-D above).

---

## Dimension 4: structural_integrity — **PASS**

Reviewed the purity boundary map in full (`verification-architecture.md:11-83`): the pure core
(`FINDING_CATEGORIES`, `isKnownCategory`, unchanged `validateVerdictShape`, new
`validateArtifactProvenance`, `decideConvergenceGate`, path-derivation helpers) is cleanly separated
from the effectful shell (agent prompt, spawn wrapper, `public_artifact_snapshot.py`, the gate
script, the command file, `.githooks/pre-push`'s new section, the demoted `PreToolUse` convenience
layer, `verify-reality-gate.mjs`). No duplication: REQ-001 extends the existing frozen category
array in place (confirmed the array currently has exactly 6 entries,
`reality-verdict-schema.mjs:14-21`, matching the spec's own premise that this iteration adds a
7th). `decideConvergenceGate` being explicitly shared, byte-identical, between the pre-push guard
and the standalone backstop (`verification-architecture.md:47-50`) is a genuine anti-drift design
choice — the same two-enforcement-layers-disagreeing risk this repo already avoided once with the
Cadence Contract Guard pattern. Naming is consistent with the base `reality-verifier` feature's
established conventions (`buildResultPath` → `buildVerdictTrailPath`/`buildArtifactTrailPath`).
`public_artifact_snapshot.py`'s structural incapacity for authenticated access (no CDP client code
path, confirmed by reading the real, analogous `cdp_nav_snapshot.py:32,36-44` which DOES connect to
`:9222`, and REQ-012's explicit divergence table showing the new tool must not) is a genuine
module-boundary property. FIND-D/E/G above are content-correctness and coverage defects in this
otherwise sound design, not module-boundary defects, and are scored under their respective
dimensions, not here.

---

## Dimension: no-hardcoded-judgment — **PASS**

Reviewed the "Judgment vs determinism" section (`behavioral-spec.md:618-641`) against
`~/.claude/rules/building-effective-ai-agents.md`'s rule ("No hardcoded judgment. The model
decides... Deterministic code only for tools + arithmetic + bookkeeping"). Every deterministic
component this spec adds is a structural backstop that can only make a verdict STRICTER, never a
content/honesty judgment: category-catalog membership (a fixed-array lookup), citation
count/dedup/tool/pass/timestamp/status checks (all reading structured fields the TOOL itself wrote,
never prose), the SKIP/convergence lookup (a committed-file lookup, not a judgment about honesty),
path derivation, and gate recording. `overallVerdict` content — whether a `domExcerpt` at a
confirmed-2xx URL actually shows the claimed post — is explicitly and correctly left to the LLM
(`behavioral-spec.md:622-624`). No regex/keyword classification of honesty exists anywhere in
either spec file. This dimension is not where this spec's problems are.

---

## Dimension 5: verification_readiness — **FAIL**

### FIND-F (BLOCKING) — REQ-009's framing of `.githooks/pre-push`'s bypass surface as solely the "logged/auditable" `--no-verify` flag is incomplete; the closure table has no entry for local hook tampering, and PROP-027's live-fire proof only exercises 2 static fixtures, never a diff-aware one

`.githooks/pre-push`'s own header comment (ground truth, lines 29-30) and `behavioral-spec.md:419-421`
both frame the accepted bypass as exclusively `--no-verify` ("governed by existing CLAUDE.md HARD
RULE #14," implicitly "logged/auditable via git, not a silent path" per the ground-truth file's own
justification for accepting it). Independently confirmed `core.hooksPath = .githooks` is live in
this repo's config (`/Users/anicca/anicca/.git/config:8`) — so the hook IS wired, closing the
narrow "hooksPath unconfigured" scenario this review was asked to check. But git's hook mechanism
runs whatever bytes are **on disk in the pushing worktree at push time** — not the version of the
hook script contained in the commits being pushed. Any of the following achieve a SILENT bypass
functionally identical to `--no-verify`, but with **zero trace** (no flag in shell history, no
`--no-verify` marker anywhere in the push):
- a local, uncommitted edit that no-ops the new "Reality Convergence Guard" section;
- `chmod -x .githooks/pre-push`;
- `git config --unset core.hooksPath` (or a worktree-local override);
- checking out an older commit of `.githooks/pre-push` (predating REQ-009's section) into the
  working tree while still pushing a `state.json` that reaches `currentPhase: "complete"`.

Every self-fix/build loop in this colony already has unrestricted Bash access to its own working
tree by design (this is the SAME access closure row 12 already accepts as a residual risk for
artifact forgery) — so this is at least as reachable as row 12, yet the 13-row closure table names
only row 12 (forgery) and row 13 (TOCTOU) as accepted residual risk. Per the spec's own stated bar
("a future iteration that finds a 13th path has found a spec defect, not merely an implementation
bug," `behavioral-spec.md:43-44`), an unlisted, reachable 14th class of bypass is exactly that: a
spec defect, not merely a residual-risk omission.

Compounding this: PROP-027 (`verification-architecture.md:103`) only requires 2 static fixture
invocations (missing/FAIL → reject; PASS+matching claim → accept) — it never exercises a push whose
range *changes* `reality-claim.json` (see FIND-E) or a push where `.githooks/pre-push` itself is
part of the diff being evaluated (a self-fix commit rewriting both the guard and its own test in the
same commit is the EXACT failure class the Cadence Contract Guard's own header comment says it
exists to prevent — `.githooks/pre-push:22-24` — yet REQ-009 does not require an analogous
regression-lock test for its own new section).

`routeToPhase`: 1b — name the local-hook-tampering bypass class explicitly in the closure table
(as an accepted residual risk, mirroring rows 12/13's honesty, OR mitigated if a mitigation is
judged in-scope), and add a `required: true` PROP that proves `.githooks/pre-push`'s own Reality
Convergence Guard section has a regression-lock test analogous to `test_cadence_evidence.py`/
`test_cadence.py`, so a future commit cannot silently rewrite both the guard and its test together.

---

## Falsifiability check (explicit answer to review task item 4)

There IS at least one required proof obligation that forces an actual FAIL verdict to fire
end-to-end for the narrowly-listed bypass fixtures: PROP-020 (a real, live, un-mocked
`reality-verifier` spawn against a genuinely nonexistent URL must produce an on-disk FAIL) and
PROP-027 (a live-fire invocation of `.githooks/pre-push` itself, not a mock, against a fixture push
range, both for the reject and accept cases) are both Tier 0, `required: true`, and both actually
exercise the real artifact (not a stub). This is genuine, real falsifiability for the scenarios the
spec enumerates.

However: a lying or merely careless implementation CAN trivially satisfy every listed acceptance
criterion in this spec (PROP-010..027 as written) while still producing a false `PASS`/successful
convergence, via any of FIND-D (wrong-URL citation), FIND-E (same-push claim downgrade or stale
PASS), or FIND-F (local hook tampering) — none of which any required PROP tests. So falsifiability
holds for the threat model this spec explicitly wrote proof obligations against, but does NOT hold
for the full threat model the "Threat-model closure" table claims to have completely enumerated
(11 closed + 2 accepted-open = 13 total) — this review has found 3 additional, reachable paths
(FIND-D, FIND-E, FIND-F) that are not accounted for anywhere in that table.

---

## Judgment on the 2 explicitly-open closure rows (review task item 5)

**Row 12 (artifact-trail forgery by a Bash-capable adversarial verifier)**: leaving this open is
**defensible as "not worse than the precedent it mirrors"** — `gig_reality_gate.py`/
`cdp_nav_snapshot.py` have the identical gap (confirmed by direct read), and closing it would
require genuine process/OS-level sandboxing (a different UID/container for `reality-verifier` vs.
the loop under test) that nothing else in this single-user, single-Mac-Mini colony architecture has
either. **But it is not sufficient to call the gate trustworthy for its named first customer.** This
colony has already experienced exactly this failure class once: `.githooks/pre-push`'s own Cadence
Contract Guard exists BECAUSE "a prior self-fix pass silently lowered [a cadence] bar" (ground truth,
`.githooks/pre-push:21`) — a documented precedent of a self-modifying, autonomous loop gaming its
own gate under exactly the kind of cadence/output pressure a growth-engine marketing loop (REQ-011's
stated customer) will be under by design. The spec's only stated mitigation ("own-eyes/fresh-adversary
review remains the final backstop... project-wide," `behavioral-spec.md:59`) is not tied to any
required cadence for this feature (no PROP requires periodic human/fresh-adversary spot-audit of
`artifacts.jsonl` for a claim type with real financial/reputational stakes). My judgment: leaving row
12 open is an honest, non-hidden disclosure and is acceptable for THIS spec to ship with, but the
combination of (a) this repo's own precedent of a loop gaming an unaudited gate under pressure and
(b) FIND-F's newly-found local-hook-tampering class means the REAL trust boundary for this gate is
"as trustworthy as this repo's git-hook-based enforcement generally is" — which the repo's own
history shows is not fully trustworthy without a recurring, independent spot-check this spec does
not require. I would not block Phase 1c on row 12 alone (it is honestly disclosed, inherited, and
out of this feature's reasonable scope), but I would treat "row 12 is open" as a reason the
growth-engine loop (this gate's first, named customer) should NOT be treated as fully autonomous on
reality-gate's word alone until a recurring spot-check requirement exists somewhere in this repo's
process (even if not in this spec).

**Row 13 (TOCTOU)**: legitimate to leave open, and does not make the gate worthless for a daily
posting claim. This is inherent to any point-in-time verification system, honestly disclosed, and
mitigated (not eliminated) by REQ-006's durable trail making a later takedown discoverable in
hindsight. One caveat worth naming explicitly (not blocking, since it's genuinely out of this
feature's scope per REQ-011's own framing): nothing in this spec, nor in the growth-engine feature
this one is designed for, requires RE-checking previously-verified URLs on a later day — each day's
verification is presumably about that day's NEW claim, so a takedown of a 3-day-old post would never
be re-discovered by this gate alone, only by the (out-of-scope) growth-engine loop choosing to
re-check old posts on its own initiative. This is fine to leave to a later feature, as the spec
itself frames it, but is worth naming so it is not silently assumed solved.

---

## Overall Gate Verdict: **FAIL**

Blocking findings (must be fixed before Phase 1c can pass and Phase 2 can begin):

1. **FIND-D** — `validateArtifactProvenance`'s complete, described 5-step contract never checks
   that a cited artifact-trail row's URL corresponds to the actually-claimed artifact. A real,
   correctly-tooled, correct-pass, fresh, 2xx-status citation for a completely unrelated (but real
   and public) URL satisfies every deterministic check in this spec and produces `gates.reality =
   PASS` while the claimed artifact is not visible. `reality-claim.json` has no structured URL
   field to anchor against, and URL derivation is explicitly delegated entirely to the LLM
   (REQ-005 edge case). This is materially weaker than the gig pattern this feature claims to
   mirror, whose ground-truth URLs are fixed and caller-supplied, never LLM-derived per claim.
2. **FIND-E** — `gates.reality`'s recorded verdict is never bound to a specific version of
   `reality-claim.json`. A single push can both weaken `reality-claim.json` (e.g. `claimType` →
   `"none"`) and flip `currentPhase` to `"complete"` in the same range, and the Reality Convergence
   Guard, which only reads current (post-push) file content, accepts it — REQ-013's own "must go
   back through Phase 1c review" rule is prose-only, mechanically unenforced. Separately, a
   previously-recorded `PASS` against a weaker claim (lower `requiredArtifactCount`) remains
   sufficient forever after the claim is legitimately strengthened, because `decideConvergenceGate`
   never compares stored `details` against current claim content.
3. **FIND-F** — REQ-009 frames `--no-verify` as the sole, "logged/auditable" bypass of the
   authoritative pre-push enforcement point, but git hooks run whatever bytes are on disk in the
   pushing worktree at push time; local, untracked edits/removal of the guard section, `chmod -x`,
   unsetting `core.hooksPath`, or checking out a stale pre-REQ-009 copy of the hook all achieve an
   identical, genuinely silent (zero-trace) bypass that the 13-row closure table never names as
   residual risk, despite being at least as reachable as the already-accepted row 12. PROP-027's
   live-fire proof also never exercises a push that changes `reality-claim.json` or
   `.githooks/pre-push` itself within the pushed range.

Non-blocking but must be tracked (MAJOR): **FIND-G** — no proof obligation validates that
`public_artifact_snapshot.py`'s captured evidence is actually diagnostic (distinguishes public from
private/removed) for Instagram, the platform this spec's own REQ-011 names as the acceptance
vehicle; the platform→method routing table is deferred past this spec with no required test tied to
it.

Iteration-2's FIND-A, FIND-B, and FIND-C are confirmed genuinely fixed at the mechanism level named
in each finding — independently re-verified against the real ground-truth files (schema, real
`validateConvergenceForCompletion`, real `.git/config`), not taken on the spec's or Builder's own
word (see "Disposition" section above). This iteration deliberately closed the vulnerability class
those findings named at the mechanisms iteration-2 pointed at; this review finds the SAME underlying
class (self-reported/unenforced claims accepted as sufficient for convergence) reopened through
three further, previously-unexamined doors (URL identity, claim-file versioning, and local
enforcement-point tampering), consistent with this spec's own stated pattern across all three
iterations so far: each fix closes the doors named, and each subsequent review finds the same class
reachable through doors not yet named. Per this spec's own explicit self-imposed bar
(`behavioral-spec.md:43-44`), that makes this iteration's threat-model-closure table incomplete, not
merely its implementation.
