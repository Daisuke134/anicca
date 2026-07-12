# VCSDD Adversary — Phase 1c Spec Review (iteration 5 of 5, FINAL)

Feature: `reality-gate` (mode: lean) — Phase 4.5 REALITY GATE
Reviewer: fresh-context adversary. Zero context from Builder, zero context from iterations 1-4's
reviewers beyond what is quoted verbatim on disk. Every disposition below is independently
re-derived from the files listed, not trusted from the spec's own "CLOSED"/"CONFIRMED FIXED"
claims.

## Artifacts actually read (paths + line ranges)

- `.vcsdd/features/reality-gate/specs/behavioral-spec.md` (1-613, full file, this worktree)
- `.vcsdd/features/reality-gate/specs/verification-architecture.md` (1-192, full file, this worktree)
- `.vcsdd/features/reality-gate/reviews/spec-review-04.md` (1-441, full file — independently
  re-checked, not trusted)
- `/Users/anicca/anicca/skills/self/lib/reality-verdict-schema.mjs` (1-129, full file — confirmed
  CURRENT implementation has 6 categories, no `canonicalizeUrl`/`enforceVerdict`/
  `validateArtifactProvenance`/`hashRealityClaim`/`computeContentFingerprint`/
  `decideConvergenceGate` yet — all of REQ-004/013/014/015 describe code not yet written, which is
  expected/correct for a Phase 1c spec review)
- `/Users/anicca/anicca/skills/self/reality-verify-spawn.sh` (1-69, full file — confirmed CURRENT
  implementation is still the detached `tmux new-session -d`; nothing reads the verdict back)
- `/Users/anicca/anicca/skills/self/reality-verify-on-new-earn.sh` (1-76, full file — the one real
  existing caller, confirmed 3-positional-arg invocation `bash "$SPAWN" "$loop" "$ledger" "$claim"`)
- `/Users/anicca/anicca/skills/self/__tests__/test-reality-verify-spawn.sh` (1-34, full file —
  confirmed the real A/B/C assertion groups REQ-005 claims must keep passing)
- `/Users/anicca/anicca/.claude/agents/reality-verifier.md` (1-139, full file)
- `/Users/anicca/anicca/skills/earn/gig/gig_reality_verify.sh` (1-203, full file — confirmed
  `PASS_ID="realityverify-$(date +%s)-$$"` is generated INSIDE this script, lines 100-105, never
  accepted as a caller argument)
- `/Users/anicca/anicca/skills/earn/gig/scripts/gig_reality_gate.py` (1-119, full file)
- `/Users/anicca/anicca/skills/earn/gig/scripts/cdp_nav_snapshot.py` (1-152, full file)
- `/Users/anicca/anicca/skills/earn/gig/gig_judge.py` (1-228, full file — confirmed
  `DEFAULT_GROUND_TRUTH_URLS` is a module-level, hardcoded, spec-time-fixed Python constant,
  lines 26-31, matching REQ-015's own "rejected design" description of it)
- `/Users/anicca/anicca/.githooks/pre-push` (1-142, full file — confirmed NO Reality Convergence
  Guard section exists yet; only the eval-loop gate + Cadence Contract Guard exist today, which is
  expected — REQ-009 describes a section to be ADDED)
- `/Users/anicca/anicca/.git/config` (line 8 — confirmed `hooksPath = .githooks` live)
- `/Users/anicca/.claude/plugins/marketplaces/vcsdd-claude-code/schemas/vcsdd-state.schema.json`
  (1-107, full file — confirmed `gates.<phase>.verdict` enum `["PASS","FAIL","SKIP"]` at line 37,
  `reviewedBy` enum `["adversary","verifier","human"]` at line 39, `details` accepts an object)
- `/Users/anicca/.claude/plugins/marketplaces/vcsdd-claude-code/scripts/lib/vcsdd-state.js`
  (279, 390-412, 1066-1180, 1720-1849 — confirmed `computeContentDigest` (406-408, the precedent
  REQ-013's `hashRealityClaim` claims to mirror), `validateConvergenceForCompletion` (1066-1143,
  confirmed **zero** reference to `gates.reality` anywhere in its body — REQ-009's "VERIFIED"
  claim about the plugin's existing 4-dimension check holds), `recordGate` (1734-1770, signature
  and merge behavior match REQ-008's call pattern)
- `~/.claude/rules/building-effective-ai-agents.md` (full file, via system context)

No `manifest.json` scaffold exists for this scope; reviewed directly against the task brief and
the ground-truth file list given, matching the convention iterations 1-4 already used.

---

## Disposition of iteration-4's blocking findings (independently re-verified against the CURRENT spec text)

### FIND-H (backstop wired only into the gate script) — **mechanism now genuinely reaches both paths, but see the NEW finding below (FIND-M) for why the mechanism is inert for path (ii) in its actual production configuration**

REQ-014 (`behavioral-spec.md:494-531`) introduces `enforceVerdict`, and REQ-003's acceptance
criteria (`behavioral-spec.md:198-206`) now explicitly require it be invoked unconditionally by
BOTH `reality-verify-spawn.sh` AND the gate script, replacing the iteration-3 language that FIND-H
correctly identified as scoping the check to "the gate script" alone. REQ-005 (`:274-310`)
redesigns `reality-verify-spawn.sh` to be BLOCKING and to call `enforceVerdict` unconditionally
before any trail append, with a dedicated, required, tier-0 fixture proof (PROP-040,
`verification-architecture.md:135`) that specifically tests the SCRIPT's own post-spawn logic
downgrades a stubbed PASS to FAIL when `enforceVerdict` would. This is a real, structural fix to
the exact contradiction FIND-H found between iteration-4's REQ-003 and REQ-011 — independently
re-verified, not taken on the spec's word. **However**, see FIND-M below: the fix correctly wires
`enforceVerdict` into both paths, but `enforceVerdict`'s own internal composition order means the
now-correctly-wired backstop never actually executes for the feature's own named production
customer, which is a materially different, previously-unexamined failure mode from what FIND-H
described.

### FIND-I (`claimedUrls` as unverified self-supplied ground truth) — mechanism genuinely NEW and structurally sound, but its execution is gated by the same defect as FIND-M below, and a second, independent bypass survives (FIND-N)

REQ-015 (`:533-566`) correctly replaces the false "VERIFIED matches gig" equivalence claim
(confirmed false in iteration 4's review and independently re-confirmed here by reading
`gig_judge.py:26-31` myself: `DEFAULT_GROUND_TRUTH_URLS` is fixed, spec-time, never
loop-influenced) with a fixed-public-surface + pre-committed-fingerprint design. The rejected-design
section (`:544-551`) explicitly and correctly states this history. This is a genuine, honest fix to
the citation itself. The underlying exploit (a loop citing its own old, real, unrelated post) is now
structurally addressed IF the mechanism runs — but see FIND-M (it structurally will not run for
Instagram, the named customer, given `automatedVerification`'s required default) and FIND-N (the
`pass-id` design weakens the row-12 residual-risk boundary this same requirement otherwise tightens
for `reality-claim.json` and the precommit record).

### FIND-J (`canonicalizeUrl` collapsing query-identified resources) — **genuinely fixed**

The redesigned `canonicalizeUrl` (`verification-architecture.md:17-30`, `behavioral-spec.md:104-112`)
strips only a fixed, small, declared tracking-parameter allowlist and preserves/sorts every other
query parameter. I traced the exact FIND-J fixture (`?v=A` vs `?v=B`) through the described logic:
since `v` is not in the allowlist (`utm_*`, `fbclid`, `igshid`, `gclid`, `ref`, `ref_src`), it is
preserved and the two canonicalize to different values — the collision is closed. PROP-016/PROP-041
(`verification-architecture.md:110`) is a real, required, tier-1 property test naming this exact
fixture. One minor residual noted below (FIND-O, minor).

### FIND-K (`automatedVerification` fail-open default) — **genuinely fixed as a default**, but see FIND-M for why fixing the default does not fix the customer-facing problem

`reality-claim.json`'s schema (`behavioral-spec.md:465`) now defaults `automatedVerification` to
`false`, and PROP-038 (`verification-architecture.md:133`, required, tier 1) is a real,
distinctly-fixtured proof that an OMITTED field is refused identically to an explicit `false`. This
closes FIND-K's narrow complaint (an author who forgets the field no longer gets silent automated
PASS eligibility). It does not address — and was never meant to address — the deeper, previously
unexamined consequence analyzed under FIND-M below.

### FIND-L (no shared enforcement module between the two paths) — **genuinely fixed architecturally**, one gap remains (FIND-P)

REQ-014 names `enforceVerdict` as the ONE shared, pure composition both paths must call, mirroring
`decideConvergenceGate`'s own precedent (which I independently confirmed exists and is correctly
described: `verification-architecture.md:64-66`). REQ-014's acceptance criteria require the gate
script contain "zero duplicated provenance-checking logic — grep-checkable." This is a sound design.
See FIND-P below: this specific acceptance criterion has no corresponding required proof obligation
in the Proof Obligations table.

---

## Dimension 1: spec_fidelity — **FAIL**

### FIND-M (BLOCKING, NEW) — `enforceVerdict`'s own specified composition order gates the ENTIRE REQ-004 provenance backstop behind `automatedVerification === true`; REQ-012 requires this flag to stay `false` for Instagram (the feature's own, only named production customer) until an unscheduled future task proves diagnosability — so REQ-011's EARS claim ("SHALL prove or disprove") is false for the feature's actual production configuration: the gate can only ever emit synthesized `FAIL`, never a genuine `PASS`, and REQ-010 unconditionally routes every such `FAIL` to `self-fix.sh`

REQ-014's EARS (`behavioral-spec.md:494-504`) specifies `enforceVerdict` as "composed of, in
order: (1) `validateVerdictShape`... (2) the `automatedVerification` refusal rule (REQ-012/013,
default `false`); (3), for a public-artifact `claimType`, `validateArtifactProvenance(...)`."
Only step (3) is scoped with "for a public-artifact claimType" — step (2) is stated without that
qualifier, and REQ-012's own text confirms it is meant to gate the whole pipeline, not merely a
`recordGate`-level label: "`enforceVerdict` refuses (fail-closed, explicit error, never silent) to
produce an accepted verdict via `reviewedBy: "verifier"`-equivalent automated processing unless
`automatedVerification === true` EXPLICITLY" (`behavioral-spec.md:435-440`).
`verification-architecture.md:53-63` confirms the identical strict "in order" composition and adds:
"malformed ⇒ synthesize a `FAIL` verdict, never pass malformed data further... `automatedVerification`-refusal... ⇒ a synthesized `FAIL`/refusal result, never a silent automated PASS."

Read together with REQ-012's own "Honest current state" (`behavioral-spec.md:428-434`): "no
AUTOMATED verdict on any platform until Phase 2a empirically proves... a structured signal reliably
differs" and, specifically for Instagram, "per general, unverified training knowledge, Instagram's
plain `httpStatus` is unlikely to be diagnostic... Fallback... if still unproven,
`automatedVerification` STAYS at its `false` default (FIND-K) — never manually overridden to `true`
without the Phase 2a evidence." REQ-011's own edge case (`behavioral-spec.md:406-408`) admits this
directly: the standalone path is "subject to REQ-012/013's `automatedVerification` precondition
(default `false`) actually being flipped `true` for Instagram only after Phase 2a proves it
diagnostic" — but **Phase 2a is not scheduled, required, or gated as a prerequisite anywhere in this
spec's Requirements or Acceptance Criteria** for REQ-011 to be considered satisfied, and the
operational consequence of leaving `automatedVerification` at its (correct, mandated) default is
never analyzed.

**Concrete failure scenario**: the growth-engine loop posts a genuinely real Instagram video, then
calls `reality-verify-spawn.sh growth-engine <real-ig-url> "<claim>" post 1 <pass-id> 1
<real-ig-url> <fixed-surface-url> <fingerprint> <precommit-ts>` exactly as REQ-005/REQ-011 specify.
`reality-claim.json.automatedVerification` is `false` (its required, default, and — per REQ-012's
own instruction — *correct* value for an unproven platform). `enforceVerdict` reaches step (2),
synthesizes `FAIL`, and **never executes `validateArtifactProvenance` at all** — none of REQ-004's
citation/URL/fixed-surface/fingerprint checks (rows 1-9, 14, 19, 20), the very mechanism this
spec's five iterations of adversarial review were fought over, ever runs for this claim. REQ-010
(`behavioral-spec.md:382-390`) then unconditionally requires `self-fix.sh <name> "<blocker+hint>"`
be invoked. This repeats identically on every single future invocation, for a genuinely healthy,
honestly-posting loop, indefinitely — there is no described mechanism, override, or human-review
path for the standalone runtime customer (REQ-011 explicitly states path (ii) has "no `state.json`,
no `gates.reality`, no `SKIP`" — i.e., none of path (i)'s `reviewedBy: "human"` escape valve exists
for path (ii) either). `self-fix.sh` is out of scope for this feature and its behavior for a
permanently-recurring, non-actionable "the platform isn't proven diagnostic yet" blocker is not
examined anywhere in this spec.

This is not merely a documentation gap: it means a Builder implementing this spec EXACTLY as
written produces a reality gate that, for its own stated first and only customer, in its own
mandated default configuration, can prove the claim FALSE but can never prove it TRUE — the EARS
text at REQ-011 ("SHALL prove or disprove that claim") is only half-true by construction, and this
half-truth is never disclosed as a limitation anywhere the way rows 12/13/16 are.

`routeToPhase`: 1b — either (a) explicitly require Phase 2a's diagnosability proof (PROP-033) as a
blocking prerequisite before REQ-011 is considered complete/deployed for Instagram, with the
operational consequence (permanent FAIL / `self-fix.sh` escalation until then) disclosed as a
named, accepted limitation the way rows 12/13/16 are, or (b) give the standalone path an explicit,
`reviewedBy`-equivalent human-override channel so an unproven-platform claim can still reach a
human decision instead of an unconditional, indefinitely-recurring `self-fix.sh` escalation, or
(c) narrow REQ-011's EARS claim to state plainly that automated PASS is impossible for any
platform until its Phase 2a proof lands, and that until then the gate's only output is `FAIL`
+ escalation, with the resulting operational cost (constant escalation noise for a healthy loop)
named and accepted, not left implicit in a parenthetical edge case.

---

## Dimension 2: edge_case_coverage — **FAIL**

### FIND-N (BLOCKING, NEW) — `pass-id` is specified as a positional CLI argument the CALLER of `reality-verify-spawn.sh` supplies; REQ-011 names the loop-under-test itself as that caller, unlike `gig_reality_verify.sh`'s own precedent (which this spec repeatedly claims to mirror) that generates `pass_id` internally and never accepts it externally — this widens row 12's disclosed residual risk rather than merely inheriting it

REQ-005's EARS (`behavioral-spec.md:274-280`) specifies the accepted argument list as `<loop-name>
<artifact-or-public-url> [claim-text] [claim-type] [pass-id] [required-artifact-count]
[claimed-urls] [fixed-public-surface-url] [content-fingerprint] [precommit-ts]` — `pass-id` is
positional argument #5, supplied by whoever invokes the script. REQ-011 (`behavioral-spec.md:392-416`)
names the growth-engine loop itself as that invoker ("the growth-engine loop calls
`reality-verify-spawn.sh` directly"). I independently read the actual precedent this spec claims to
mirror: `gig_reality_verify.sh:100-105` generates `PASS_ID="realityverify-$(date +%s)-$$"` **inside
the calling script itself**, with an explicit design comment: "The SAME pass_id is embedded in the
prompt and used later by the evidence gate — the judge never chooses its own pass_id." Critically,
in gig's design, the entity that chooses `pass_id` (`gig_reality_verify.sh`, an independent auditor)
is never the same entity whose honesty is under test (the gig core loop). In this spec's design, the
entity that supplies `pass-id` (per REQ-005's own argument list) and the entity under test (per
REQ-011) are the SAME loop.

Neither REQ-012 (`behavioral-spec.md:417-452`) nor the NFR section (`:568-586`) states any write
protection on the `.../reality-artifacts/<passId>/artifacts.jsonl` directory or the `passId`
namespace itself — contrast this with the NFR's explicit, narrower protection: "`reality-claim.json`
and the precommit record are never written by any component that also produces the verdict checked
against them" (`:581-582`). `artifacts.jsonl` and the `passId` directory it lives under are
conspicuously absent from that sentence, despite being exactly analogous ground-truth anchors.

**Concrete failure scenario**: a Bash-capable growth-engine loop (already a granted capability for
any autonomous cron loop in this codebase, per the colony architecture this repo documents
elsewhere) pre-selects a `pass-id`, pre-writes a forged, fresh, correctly-shaped `artifacts.jsonl`
row under `~/.../reality-artifacts/<chosen-pass-id>/artifacts.jsonl` (matching tool, matching
`requestedUrl`/`finalUrl`, `httpStatus: 200`, a fabricated but plausible `domExcerpt`), THEN calls
`reality-verify-spawn.sh growth-engine <fake-claim-url> "<claim>" post 1 <chosen-pass-id> ...` — the
citation-identity checks (rows 2-4, matching `tool`/`passId`/`ts`) are satisfied by the loop's own
forgery without the fresh verifier's real capture tool ever needing to run, or even if it does run
and add more (real) rows to the same directory, the pre-planted forged row remains available to be
cited. This is the same CLASS of risk row 12 already discloses ("Bash-capable verifier hand-forges a
fake `artifacts.jsonl` row"), but row 12's own framing implicitly assumes the *verifier* is the
adversarial party with Bash access — this scenario shows the *loop under test itself*, via a
caller-suppliable `pass-id`, can pre-stage the forgery before the verifier is even spawned, which is
a materially easier and more deterministic attack than an adversarial verifier having to forge
evidence live during its own review. This degrades, rather than merely inherits, row 12's disclosed
scope, and is not named anywhere in the closure table or the "What this architecture explicitly does
NOT verify" section.

`routeToPhase`: 1b — generate `pass-id` internally inside `reality-verify-spawn.sh` (mirroring
`gig_reality_verify.sh`'s own precedent exactly, since this spec elsewhere claims to mirror it),
never accept it as a caller-suppliable argument; if a caller-suppliable `pass-id` is kept for some
other stated reason, explicitly fold this specific, easier attack into row 12's disclosure with its
own named scenario, rather than leaving it unexamined.

### FIND-O (MINOR) — `public_artifact_snapshot.py`'s behavior on network timeout / connection failure / empty response body is unspecified

REQ-012's Edge Cases (`behavioral-spec.md:441-442`) cover anti-bot 403s and JS-rendering platform
preference, but never state what `httpStatus`/`domExcerpt` value the tool records (or whether it
appends a row at all) when the underlying fetch times out, the connection is refused, or the
response body is empty. REQ-007's timeout edge case (`:331-332`) addresses only the OUTER
`reality-verifier` LLM spawn's 600s cap, not this INNER tool's own network call. Given `httpStatus
in [200,299]` is the sole status gate (row 8), an unspecified sentinel value on network failure
(e.g., accidentally `0`, `null`, or an in-range placeholder) could either correctly fail-close (most
likely, given the pattern in the existing `cdp_nav_snapshot.py` precedent, which returns an
`ERROR:` string without appending a trajectory row on hard failure) or accidentally fail-open,
entirely depending on an implementation detail this spec does not pin down. Not blocking because the
existing sibling tool's own precedent strongly suggests the safe behavior (no row appended on hard
failure, which correctly fails the "citation resolves to no real row" check, row 3) — but this spec
should say so explicitly rather than leave it to be inferred from a different tool's convention.

---

## Dimension 3: implementation_correctness — **FAIL**

Under this dimension's Phase-1c bar ("are the requirements concrete enough to be implemented
unambiguously, without producing something that fails its own stated purpose when implemented
exactly as written"): FIND-M shows a Builder implementing REQ-005/010/011/012/014 exactly as
specified produces a reality gate that, for its own production configuration, structurally cannot
ever emit a genuine automated `PASS` for its own named customer — this is not an ambiguity bug, it
is a specified, deterministic consequence of the composition order the spec itself mandates.
FIND-N shows REQ-005's `pass-id` argument, implemented exactly as specified, hands the loop under
test a caller-suppliable knob that materially eases forging its own evidence.

**What is genuinely correct, independently reverified**: `canonicalizeUrl`'s redesign (FIND-J's
fix) is unambiguous and correctly specified — I traced the exact fixture and it produces the
correct, non-colliding result. `hashRealityClaim`/`decideConvergenceGate` (unchanged from
iteration 4's already-confirmed fix) remain sound: `recordGate`'s real merge behavior
(`vcsdd-state.js:1734-1744`) and the schema legality of `recordGate(featureName, 'reality',
'PASS'|'FAIL'|'SKIP', 'verifier'|'human', details)` against the real, unmodified schema
(`vcsdd-state.schema.json:37,39`) both hold up under this fifth independent re-check.
`validateConvergenceForCompletion` (`vcsdd-state.js:1066-1143`, full body read) is independently
reconfirmed to contain zero reference to `gates.reality`, matching REQ-009's "VERIFIED" citation.

`routeToPhase`: 1b (same fixes as FIND-M/N above).

---

## Dimension 4: structural_integrity — **FAIL**

### FIND-P (MAJOR, NEW) — REQ-014's own acceptance criterion "gate script contains zero duplicated provenance-checking logic — grep-checkable" has no corresponding proof obligation in the Proof Obligations table

I scanned every row of `verification-architecture.md`'s Proof Obligations table (PROP-001 through
PROP-041, lines 101-136) for anything testing duplicate-logic absence in the gate script. None
exists. Every OTHER acceptance criterion in REQ-004/005/008/012/013/014/015 maps to a named,
`required: true` PROP (grep-checkable pattern this spec itself relies on throughout — see e.g.
PROP-040 for the analogous "runtime path actually calls `enforceVerdict`" claim). This one
acceptance criterion — arguably the load-bearing structural claim that makes FIND-L's fix real
rather than aspirational — is asserted in prose only, with no forcing mechanism scheduled anywhere.
Given this same spec's own closing rule ("a mechanism that only reaches one path is, for the other
path, exactly as if it did not exist" — extended here: an acceptance criterion with no proof
obligation is, for verification purposes, exactly as if it were not required at all), this is a
real, previously-unexamined inconsistency in an otherwise carefully cross-referenced spec.

**What is genuinely correct**: the purity boundary itself remains cleanly drawn
(`verification-architecture.md:11-98`) — every new pure function (`canonicalizeUrl`,
`computeContentFingerprint`, `hashRealityClaim`, `validateArtifactProvenance`, `enforceVerdict`,
`decideConvergenceGate`) is correctly classified with no I/O, matching the existing
`reality-verdict-schema.mjs` design intent I independently confirmed by reading the current 129-line
file. `enforceVerdict`'s naming and its position as the sole shared composition point is a sound,
non-duplicative design choice in principle (FIND-L's core fix is real); FIND-N's `pass-id` argument
design is the one place this iteration introduces an inconsistency with an established sibling
precedent (`gig_reality_verify.sh`) without justification.

`routeToPhase`: 1b — add a required, tier-0, grep-based PROP for the "no duplicated provenance logic
in the gate script" acceptance criterion.

---

## Dimension 5: verification_readiness — **FAIL**

FIND-P (missing PROP) is directly a verification-readiness gap. Additionally: given FIND-M's
composition-order finding, PROP-020b and PROP-035/036/037 (the "live spawn"/fixture proofs that the
URL-mismatch and fingerprint checks "fire for real") can only be exercised by a TEST fixture that
sets `automatedVerification: true` for its own claim object — which is legitimate for a unit/fixture
test, but it means **no proof obligation anywhere in this table demonstrates that the intended
production configuration (Instagram, `automatedVerification: false` by mandated default) can ever
reach `validateArtifactProvenance` at all.** The table proves the mechanism works in isolation; it
never proves the mechanism is reachable in the configuration this feature will actually ship in for
its own named customer. This is a real coverage gap that FIND-M's structural finding exposes: a
proof obligation that only ever tests a bypassed/relaxed configuration is not proof the intended
one works.

**What is genuinely correct**: PROP-016/041 (canonicalizeUrl fix), PROP-031/PROP-027 (hash-mismatch
and live-fire convergence guard, unchanged and sound from iteration 4's confirmed fix), and
PROP-038/034 (automatedVerification refusal, correctly required and correctly fixtured for what
they test) all remain real, required, and correctly scoped to what they individually claim to prove.

`routeToPhase`: 1b (same fixes as FIND-M/N/P above).

---

## Dimension: no-hardcoded-judgment — **PASS**

Re-checked `~/.claude/rules/building-effective-ai-agents.md`'s rule against the "Judgment vs
determinism" section (`behavioral-spec.md:588-612`) and every new deterministic component this
iteration adds or redesigns: `canonicalizeUrl`'s tracking-parameter allowlist is a fixed, declared,
structural normalization (not a judgment about which URL is "the real one"); `computeContentFingerprint`
is a pure hash; the fixed-surface/`referencedArtifactIds`/precommit-ordering checks are structural
lookups against independently-captured or pre-committed data, never prose interpretation;
`automatedVerification`'s refusal is a boolean gate, not a judgment call. No regex/keyword
classification of "is this claim honest" was added anywhere in this iteration's diff. This
dimension remains where this spec's problems are NOT, across all five iterations.

Evidence: `behavioral-spec.md:588-612` (full "Judgment vs determinism" section, read in full);
`verification-architecture.md:11-98` (Purity Boundary Map, read in full, cross-checked against
`skills/self/lib/reality-verdict-schema.mjs:1-129`, the current real file, for consistency of
design intent).

---

## Closed-row audit table (my independent re-verification)

| # | Spec-claimed status | My finding | Verdict |
|---|---|---|---|
| 1-9, 11 | CLOSED | Mechanism (`validateArtifactProvenance` sub-checks) is real and correctly specified in isolation — BUT see row 14/19/20 below: for path (ii)'s actual production configuration, this mechanism never executes at all (FIND-M) | mechanism sound, **execution gated off / inert for path (ii) as configured — not disclosed as such** |
| 10 | CLOSED | `.githooks/pre-push`'s Cadence Guard precedent (lines 18-30, 75-96) is real and live (`core.hooksPath` reconfirmed); no "Reality Convergence Guard" section exists yet in the current file — expected for Phase 1c, REQ-009 specifies what must be added | CLOSED (design is correctly specified; nothing implemented yet, which is correct for this phase) |
| 14, 19, 20 | CLOSED | `canonicalizeUrl` fix (FIND-J) and fixed-surface/fingerprint mechanism (FIND-I) are both genuinely, structurally sound in isolation. Same caveat as rows 1-9: gated off for path (ii)'s production configuration by FIND-M; row 19 additionally weakened by FIND-N's `pass-id` design | mechanisms sound, **same execution-gating caveat, plus FIND-N's independent weakening** |
| 15 | CLOSED | Verified again (5th independent check): `hashRealityClaim`/`decideConvergenceGate`/`recordGate` all correctly, deterministically, fail-closed on any mismatch | genuinely CLOSED |
| 17 | MITIGATED | `automatedVerification`'s default is now correctly fail-closed (FIND-K fixed) and the refusal rule is real and shared (FIND-H fixed for wiring) — but FIND-M shows the refusal rule's OWN correct fail-closed behavior, combined with the honest admission Instagram cannot be proven diagnostic without an unscheduled Phase 2a task, produces a gate that can never legitimately PASS for its named customer, a consequence this row's "MITIGATED — empirically gated, fail-closed when unproven" framing presents as fully resolved rather than as a new, disclosed, indefinite operational limitation | **mechanically correct, but its consequence for the named customer is undisclosed** |
| 12 | OPEN (disclosed) | Confirmed identical, pre-existing gap in `gig_reality_gate.py`/`cdp_nav_snapshot.py` — but FIND-N shows this row's real-world scope is WIDER this iteration (caller-suppliable `pass-id`) than the disclosure states | legitimately OPEN, **disclosure is now incomplete, not merely accepted** |
| 13, 16 | OPEN (disclosed) | Unchanged from iteration 4's independent re-verification; reasoning sound, disclosure honest and thorough | legitimately OPEN, honestly disclosed |

---

## Falsifiability check (review task item 5)

Real, required, live-fire proof obligations exist that force actual FAIL verdicts for the specific,
narrow fixture scenarios this spec enumerates: PROP-020/020b (nonexistent/wrong-URL spawns),
PROP-027 (live `.githooks/pre-push` fixtures), PROP-031/038 (hash-mismatch, automatedVerification
omission), PROP-035/036/037 (fingerprint/fixed-surface mismatches, as fixtures). These are genuine.

However, per FIND-M: **no proof obligation anywhere demonstrates the gate can ever reach a genuine
`PASS` for its own named production customer in that customer's actual, mandated default
configuration.** A gate whose only reachable outcome, for its stated first customer, is `FAIL`, is
falsifiable in the narrow sense the review brief asks about (item 5: "name a REQUIRED proof
obligation that forces an actual end-to-end FAIL to fire" — yes, several exist and are real) but
fails the SPIRIT of the same check: a verifier that cannot ever legitimately say PASS for its real
customer is exactly as broken, for that customer, as one that cannot ever say FAIL — and this
asymmetry is not examined by this spec's own falsifiability framing, which only ever worried about
the false-PASS direction.

---

## Judgment on rows 12/13/16 (review task item 3)

**Row 12**: Reasoning legitimate and precedented, but FIND-N shows this iteration's own new
`pass-id` design widens the real-world scope of this disclosed risk beyond what the disclosure
states — the disclosure needs updating, not merely retained verbatim.

**Row 13**: Unchanged, legitimate, honestly disclosed, inherent to any point-in-time check.

**Row 16**: Unchanged, legitimate, honest, sound reasoning (quoted verbatim, not paraphrased).

**My overall ship/no-ship judgment (first customer: the IG-posting marketing loop, REQ-011)**: I
would **NOT** ship this gate to the growth-engine's Instagram loop as currently specified. Five
iterations of adversarial review have now produced a genuinely well-designed, correctly-composed,
shared-module architecture (`enforceVerdict`) with a materially improved provenance backstop
(fixed-surface + fingerprint + precommit ordering, non-colliding URL canonicalization) — this is
real, substantive progress over iteration 4, and FIND-H/I/J/K/L are each honestly, structurally
fixed, not merely reworded. But the very discipline this spec correctly applied to closing those
four findings (a real, fail-closed default for `automatedVerification`) has a consequence this
iteration never examined: for the one platform and one invocation pattern this entire feature
exists to serve, the gate's own specified composition makes a genuine `PASS` structurally
unreachable until an unscheduled, unrequired Phase 2a task completes — meaning, deployed exactly as
written, the growth-engine loop would receive a `FAIL` + `self-fix.sh` escalation on every single
legitimate daily post, forever, with no described human-override channel for that path. This is not
"acceptable residual risk, honestly disclosed" like rows 12/13/16 — it is, like FIND-H before it, an
unexamined gap between REQ-011's EARS claim ("SHALL prove or disprove") and what the architecture
this same spec specifies actually delivers for its own named customer.

---

## Overall Gate Verdict: **FAIL**

Blocking findings (must be fixed before Phase 1c can pass and Phase 2 can begin):

1. **FIND-M** — `enforceVerdict`'s specified composition order (`behavioral-spec.md:494-504`,
   `verification-architecture.md:53-63`) gates the entire REQ-004 provenance backstop behind
   `automatedVerification === true`; REQ-012 requires this to remain `false` for Instagram
   (`behavioral-spec.md:428-434`) until an unscheduled Phase 2a task proves diagnosability
   (`behavioral-spec.md:406-408, 444-452`) — so the gate can only ever emit `FAIL` for its own
   named, only production customer, triggering an unconditional, indefinitely-recurring
   `self-fix.sh` escalation (REQ-010) with no described override for that path, contradicting
   REQ-011's EARS claim that the standalone customer is now "actually protected... SHALL prove or
   disprove."
2. **FIND-N** — `pass-id` is specified (`behavioral-spec.md:274-280`) as a caller-suppliable CLI
   argument, and REQ-011 names the loop under test as that caller — deviating, without
   justification, from the `gig_reality_verify.sh` precedent this spec repeatedly claims to mirror
   (`gig_reality_verify.sh:100-105`, which generates `pass_id` internally, never from the caller),
   letting the loop under test pre-select the `passId` its own pre-planted `artifacts.jsonl` forgery
   must match — a materially easier variant of row 12's disclosed risk, left unexamined and
   unincorporated into that row's disclosure.

Major, non-blocking-but-must-be-tracked: **FIND-P** (REQ-014's "zero duplicated provenance logic in
the gate script" acceptance criterion has no corresponding required proof obligation anywhere in
the Proof Obligations table), **FIND-O** (minor — `public_artifact_snapshot.py`'s network-failure/
timeout/empty-body behavior is unspecified).

Minor: **FIND-O** (see above, listed at minor severity within edge_case_coverage); the
`canonicalizeUrl` allowlist's unconditional stripping of `ref`/`ref_src` across all future,
unnamed platforms is a narrower, speculative echo of FIND-J's original collision class, noted but
not blocking given no named platform exhibits it today.

Iteration-4's FIND-H, FIND-I, FIND-J, FIND-K, and FIND-L are each independently re-verified above
as genuinely, structurally fixed by this iteration's REQ-013/014/015 and the redesigned
`canonicalizeUrl` — this is real progress, not restated language. This iteration's own two new
blocking findings (FIND-M, FIND-N) are, per this spec's own explicit, self-imposed bar
(`behavioral-spec.md:49-52`: "A future review that finds a 22nd path has found a spec defect"),
exactly a 22nd and 23rd path — found specifically through the doors this iteration itself newly
opened (`enforceVerdict`'s composition order, `pass-id`'s caller-suppliable argument), the same
pattern iteration 4 itself named for its own findings against iteration 3's fixes.
