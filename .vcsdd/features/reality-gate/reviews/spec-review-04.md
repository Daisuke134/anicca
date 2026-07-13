# VCSDD Adversary — Phase 1c Spec Review (iteration 4 of 5)

Feature: `reality-gate` (mode: lean) — Phase 4.5 REALITY GATE
Reviewer: fresh-context adversary. Zero context from Builder, zero context from iterations 1-3's
reviewers or the orchestrator's FIND-F ruling beyond what is quoted verbatim on disk. Every
disposition below is independently re-derived from the files listed, not trusted from the spec's
own "CONFIRMED FIXED" / "VERIFIED" claims.

## Artifacts actually read (paths + line ranges)

- `.vcsdd/features/reality-gate/specs/behavioral-spec.md` (1-671, full file)
- `.vcsdd/features/reality-gate/specs/verification-architecture.md` (1-207, full file)
- `.vcsdd/features/reality-gate/reviews/spec-review-03.md` (1-401, full file — independently
  re-checked, not trusted)
- `.vcsdd/features/reality-gate/state.json` (1-39, full file)
- `.claude/agents/reality-verifier.md` (1-139, full file)
- `skills/self/lib/reality-verdict-schema.mjs` (1-128, full file — confirmed 6 categories currently)
- `skills/self/reality-verify-spawn.sh` (1-69, full file — confirmed CURRENT implementation is a
  detached, fire-and-forget `tmux new-session -d`; nothing reads the verdict back)
- `skills/self/reality-verify-on-new-earn.sh` (1-76, full file — the one real existing caller;
  confirmed it never reads the spawned verdict back either, only advances a cursor)
- `skills/earn/gig/scripts/gig_reality_gate.py` (1-119, full file)
- `skills/earn/gig/scripts/cdp_nav_snapshot.py` (1-152, full file)
- `skills/earn/gig/gig_judge.py` (1-80 read — `DEFAULT_GROUND_TRUTH_URLS` module-level constant)
- `.githooks/pre-push` (1-142, full file — Cadence Contract Guard precedent, `core.hooksPath`
  reference)
- `/Users/anicca/anicca/.git/config` (1-48, full file — confirmed `core.hooksPath = .githooks` live)
- `/Users/anicca/.claude/plugins/marketplaces/vcsdd-claude-code/schemas/vcsdd-state.schema.json`
  (1-107, full file)
- `/Users/anicca/.claude/plugins/marketplaces/vcsdd-claude-code/scripts/lib/vcsdd-state.js`
  (395-412, 1060-1180, 1730-1770 — `computeContentDigest`, `validateConvergenceForCompletion`,
  `validateState`, `recordGate`)
- `/Users/anicca/.claude/plugins/marketplaces/vcsdd-claude-code/agents/vcsdd-orchestrator.md:56`
  (`recordGate(featureName, '3', ...)`)
- `/Users/anicca/.claude/plugins/marketplaces/vcsdd-claude-code/agents/vcsdd-adversary.md:1-4`
  (tools frontmatter)
- `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-13-growth-engine-self-improving-
  promotion-skill-design.md` (1-40 — V0/G0/G1/G5 roadmap, confirms daily-loop wiring is a LATER
  feature (G1), not this one)
- `/Users/anicca/.claude/rules/building-effective-ai-agents.md` (full file)

No `manifest.json` scaffold exists for this scope; reviewed directly against the task brief, per
the convention iterations 1-3 already used.

---

## Disposition of iteration-3's blocking findings (independently re-verified)

### FIND-D (URL-blind resolution) — mechanism genuinely NEW and real, but see FIND-I below
`canonicalizeUrl`/`claimedUrls` binding (behavioral-spec.md:65 row 14, REQ-004 lines 239-252,
PROP-028/029/030 at verification-architecture.md:127-129) is a real, structural improvement over
iteration-3's total absence of URL checking: a citation for a real, correctly-tooled, fresh, 2xx row
that resolves to the WRONG URL, or that redirects off the claimed URL, is now caught. **However**,
this mechanism is (a) wired only into the gate script, never the standalone spawn path REQ-011
names as the acceptance vehicle (FIND-H below), and (b) trusts the caller-supplied `claimedUrls`
itself as ground truth with no independent tether to what was actually posted (FIND-I below) — the
underlying vulnerability class (self-reported claim accepted as sufficient) is narrowed, not closed,
for the feature's own named first customer.

### FIND-E (claim-file versioning) — **CONFIRMED FIXED**
`hashRealityClaim`/`decideConvergenceGate`'s hash-equality check (behavioral-spec.md:66 row 15,
REQ-008/009/013, PROP-031 required/tier-1/fast-check, PROP-027(c) required/tier-0/live-fire) is a
straightforward, deterministic, no-I/O content-hash comparison. I traced the exploit scenarios
iteration-3 named (same-push downgrade, stale-PASS-after-strengthening) and both are structurally
"current hash != stored hash" cases that `decideConvergenceGate`'s described logic
(verification-architecture.md:63-71) catches unconditionally, `blocked: true` regardless of the
stored verdict string. `recordGate`'s real implementation (`vcsdd-state.js:1734-1744`) merges
`details` only when the caller passes it; REQ-008's acceptance criteria require the gate script to
always pass `details.realityClaimHash`, and even a bug that omitted `details` would fail CLOSED (a
stale hash mismatches the current file and blocks), not open. No exploit found in this mechanism.

### FIND-F (local-hook bypass) — reclassified to OPEN, disposition adopted; judged for honesty below
No new gap found in the reclassification itself beyond what is analyzed under "Judgment on rows
12/13/16" below.

### FIND-G (platform diagnosability unproven) — mechanism real, but **scoped to the wrong code path** — see FIND-H below
`automatedVerification`/PROP-034 (behavioral-spec.md:68 row 17, REQ-012 lines 533-542) is a real,
testable-now refusal rule. But it refuses `recordGate(..., reviewedBy: "verifier", ...)` — a
VCSDD-state-only call. It provides **zero** protection for the path REQ-011 says the actual
Instagram-claim customer uses.

---

## Dimension 1: spec_fidelity — **FAIL**

### FIND-H (BLOCKING) — the ENTIRE deterministic backstop (REQ-004) and its `automatedVerification` refusal rule (REQ-012, closure row 17) are architecturally wired ONLY into the VCSDD gate script; REQ-011's own named acceptance vehicle explicitly bypasses that gate script, so none of this spec's 4 iterations of provenance-hardening protect the feature's actual first customer

The spec's own text is internally contradictory on this point:

- REQ-011 EARS (`behavioral-spec.md:474-478`): "THE SYSTEM's reality gate SHALL be able to prove or
  disprove that claim via REQ-002's `post_not_publicly_visible` category and REQ-003/004/012's
  independently-captured, logged-out, count-and-status-gated, URL-bound public-URL check."
- REQ-011 body (`behavioral-spec.md:479-484`): "This is a **standalone loop-verification call**
  (REQ-005): the growth-engine loop calls `reality-verify-spawn.sh` directly... **no `state.json`,
  no `gates.reality`, no `SKIP`, no `reality-claim.json`** (that file applies only to the
  VCSDD-pipeline gate, REQ-008/009)."
- REQ-003's own Acceptance Criteria (`behavioral-spec.md:216-220`): "`validateArtifactProvenance`
  (REQ-004) is **unconditionally invoked by the gate script** for every public-artifact-`claimType`
  verification" — REQ-003 itself, in its own acceptance bar, scopes the backstop's invocation to
  **the gate script**, not to `reality-verify-spawn.sh` or any standalone caller.
- `verification-architecture.md`'s Effectful Shell list confirms this is not a drafting slip:
  `skills/self/vcsdd-reality-gate.mjs` ("the gate script") is the ONLY component described as
  calling `validateArtifactProvenance` (`verification-architecture.md:83-92`, specifically line 88).
  `skills/self/reality-verify-spawn.sh`'s own described behavior (`verification-architecture.md:
  78-80`) is limited to threading arguments and refusing to spawn without a URL — no mention of
  waiting for, reading, or backstop-validating the verdict it produces.
- The CURRENT, real `reality-verify-spawn.sh` (`skills/self/reality-verify-spawn.sh:67`) confirms
  this is not hypothetical: it fires a **detached** `tmux new-session -d` and returns immediately.
  The one real existing caller, `reality-verify-on-new-earn.sh` (full file read), never reads the
  spawned verdict back either — it only advances a cursor file. Nothing in this feature's own text
  assigns ANY component the job of waiting for the standalone spawn's `RESULT` file and running
  `validateArtifactProvenance` against it.
- REQ-012's `automatedVerification` refusal rule (`behavioral-spec.md:533-542`) is described
  exclusively as refusing `recordGate(..., reviewedBy: "verifier", ...)` — a VCSDD-`state.json`-only
  function. The standalone path (REQ-011) never calls `recordGate` at all (REQ-011 says so itself:
  "no `gates.reality`"). So even the empirically-gated fail-closed mechanism this iteration built
  specifically to fix FIND-G (closure row 17 — "no proof the signal is diagnostic for Instagram") is
  **structurally incapable of firing** for the ONE platform (Instagram) and the ONE invocation
  pattern (standalone daily verification) this spec names as its actual acceptance vehicle.

**Concrete failure scenario**: the growth-engine loop (a future, separate feature per the
growth-engine roadmap doc's own G1 step, `docs/superpowers/specs/2026-07-13-growth-engine-...md:32`)
calls `reality-verify-spawn.sh <loop> <claimed-ig-url> "<claim>" post 1 <claimed-ig-url>` exactly as
REQ-005/REQ-011 specify. A fresh `reality-verifier` spawn runs, and — because REQ-012's own "Honest
current state" text (`behavioral-spec.md:515-522`) admits Instagram's plain `httpStatus` is
"very unlikely to be sufficient" and its SPA shell "commonly returns `200` regardless of whether the
underlying post exists" — the LLM could see a `200` status, a generic SPA shell `domExcerpt` it
doesn't recognize as a removal interstitial, and emit `overallVerdict: "PASS"` with a citation to a
real, fresh, correctly-tooled, correctly-URLed, `200`-status row. **Nothing in this spec's
architecture ever runs `validateArtifactProvenance` OR the `automatedVerification: false` refusal
against this verdict**, because nothing is wired to do so for this invocation path. The `PASS`
verdict is simply written to the `RESULT` file and the durable trail (REQ-006) and accepted as-is —
REQ-006's per-run verdict is explicitly named in this spec's own threat-model preamble
(`behavioral-spec.md:44`: "gates.reality (or a per-run verdict, REQ-006)") as in-scope for this
closure table, and this is a live, unclosed door to exactly that outcome for the feature's own named
customer.

`routeToPhase`: 1b — either (a) require a synchronous or polling caller-side wrapper (owned by THIS
feature, not deferred to G1) that reads the standalone spawn's `RESULT` file and applies
`validateArtifactProvenance` + the `automatedVerification` refusal rule before any per-run verdict
is treated as authoritative, with a required PROP proving it, or (b) explicitly narrow REQ-011's EARS
claim to state that NONE of REQ-003/004/012's protections apply to the standalone path yet, and stop
citing them in REQ-011's acceptance vehicle language — the current text overclaims what this spec
actually delivers for its own stated purpose.

### FIND-K (MAJOR) — `automatedVerification`'s schema default is fail-OPEN (`true`), inconsistent with every other default-closed choice in this spec

`reality-claim.json`'s shape (`behavioral-spec.md:578`): `"automatedVerification": "<boolean,
default true; MUST be false for an unproven platform, REQ-012>"`. Compare this to
`requiredArtifactCount`'s own edge case, three lines away in intent (`behavioral-spec.md:262-263`):
"`requiredArtifactCount` is `0`/omitted... defaults to `1`, never `0` (would make the count check
vacuous, reopening row 1)" — a deliberate fail-closed default choice. `automatedVerification`
defaulting to `true` means an author who simply forgets to set the field for a brand-new, unproven
platform gets automated-`PASS` eligibility by DEFAULT, not by explicit opt-in. The spec's only stated
protection against this is that `reality-claim.json` "reviewed by the same Phase 1c fresh adversary"
(REQ-013, `behavioral-spec.md:582`) will catch a missing/wrong value by human/adversary judgment —
but no `required: true` PROP anywhere (PROP-034 only tests the case where the field is EXPLICITLY
`false`) forces rejection of an omitted field for a `claimType !== "none"` claim. This is the same
"absence of a caught problem treated as proof" anti-pattern this spec's own closing section
(`behavioral-spec.md:661-671`) explicitly forbids, now present in its own schema default.

`routeToPhase`: 1b — default `automatedVerification` to `false` (fail-closed, mirroring
`requiredArtifactCount`'s own precedent in this same spec), or add a `required: true` PROP that
rejects a `reality-claim.json` with `claimType !== "none"` and `automatedVerification` omitted.

---

## Dimension 2: edge_case_coverage — **FAIL**

### FIND-I (BLOCKING) — `claimedUrls` for a `urlSource: "caller-per-invocation"` claim is supplied by the SAME loop whose honesty is being tested, with no independent tether to what was actually posted; the spec's own "VERIFIED" equivalence to `gig_reality_gate.py`'s precedent is factually wrong

REQ-013's own text (`behavioral-spec.md:596-607`) discloses this boundary and claims: "This is the
SAME trust boundary `gig_reality_gate.py`'s fixed, caller-supplied `DEFAULT_GROUND_TRUTH_URLS`
already has (**VERIFIED** — gig trusts its own caller-supplied ground truth URLs are honest ground
truth, it does not separately re-derive them)."

I read `gig_judge.py:26-31` directly: `DEFAULT_GROUND_TRUTH_URLS` is a **module-level, hardcoded,
spec-time-fixed Python list** — 4 Coconala dashboard URLs, identical on every single invocation,
regardless of what the gig loop under test actually did or claims to have done. The gig loop being
verified has **zero ability to choose or influence** which URLs get checked. This is the OPPOSITE
trust model from what this spec builds for `urlSource: "caller-per-invocation"`: there, per REQ-005
(`behavioral-spec.md:301-305`), "the loop making a NEW post SHALL supply the real URL it received
back from the platform at post time (its own deterministic record...)" — i.e., the exact loop being
graded for honesty chooses the ONE piece of evidence (the URL) that will be checked, every time,
per-claim. The spec's own "VERIFIED" label is applied to a claim that does not survive reading the
cited file — this is a false verification citation used to justify NOT closing a real gap.

**Concrete failure scenario**: a dishonest (or self-fix-degraded) growth-engine loop that never
actually posted the claimed video calls `reality-verify-spawn.sh growth-engine
https://instagram.com/p/SOME_OLD_REAL_POST_FROM_THE_SAME_ACCOUNT "posted new video X" post 1
https://instagram.com/p/SOME_OLD_REAL_POST_FROM_THE_SAME_ACCOUNT`. `SOME_OLD_REAL_POST` is genuinely
public, genuinely 2xx, genuinely fresh-fetched, genuinely matches `claimedUrls` (because the loop
supplied the SAME URL as both the target and the claim anchor) — `validateArtifactProvenance` (were
it even wired to this path, see FIND-H) would pass every deterministic check. The ONLY remaining
defense is `reality-verifier`'s own LLM judgment comparing `domExcerpt` content against `claim-text`
(REQ-002's content-mismatch edge case, `behavioral-spec.md:176-177`) — but this is explicitly,
correctly, left as ungoverned LLM judgment (per this spec's own "Judgment vs determinism" section),
and **no required PROP anywhere in the Proof Obligations table exercises this exact scenario**
(a caller-supplied `claimedUrls` entry that is real/public/fresh/correctly-tooled but for
demonstrably DIFFERENT content than the claim describes). PROP-020b tests the opposite direction
(verifier tries the CORRECT url, content is missing there) — not "the caller hands the verifier a
real-but-wrong url up front."

`routeToPhase`: 1b — remove the false "VERIFIED" equivalence claim (or replace with an honest
statement that this is materially weaker than gig's precedent), and add a required, `required: true`
live-fire PROP (mirroring PROP-020/020b) that supplies `claimedUrls` pointing at a real, public, but
CONTENT-UNRELATED artifact alongside a specific claim-text, and proves `reality-verifier` emits FAIL
via content-mismatch — without this, "the LLM will probably notice" is exactly the un-forced,
un-tested judgment call this spec elsewhere refuses to accept as sufficient.

### FIND-J (BLOCKING) — `canonicalizeUrl`'s query-string-stripping collapses distinct, query-identified artifacts to the same canonical value; PROP-016 requires this behavior, locking in the collision rather than catching it

`canonicalizeUrl` (`verification-architecture.md:17-25`) is specified to "strip[] query string and
fragment entirely," and PROP-016 (`verification-architecture.md:121`, tier 1, `required: true`)
mandates: "scheme/port/trailing-slash/query/fragment differences canonicalize equal; ANY path or
host difference canonicalizes UNEQUAL, for arbitrary generated URL pairs." For any platform whose
canonical resource identity lives in a query parameter rather than a path segment — the single most
common real-world example being YouTube (`youtube.com/watch?v=<video-id>`) — two DIFFERENT, real,
public videos canonicalize to the IDENTICAL value (`youtube.com/watch`) under this function. A
citation resolving to `youtube.com/watch?v=REAL_BUT_UNRELATED` would satisfy `claimedUrls =
["youtube.com/watch?v=THE_ACTUALLY_CLAIMED_VIDEO"]` after canonicalization, defeating
`validateArtifactProvenance`'s URL-identity check (row 14) entirely — the exact bypass class REQ-004
was rebuilt this iteration specifically to close.

This spec explicitly frames `canonicalizeUrl` and the whole REQ-001..004/012 stack as
**general-purpose, not platform-hardcoded** (REQ-011 edge case, `behavioral-spec.md:486-489`), and
the growth-engine design doc this feature exists to serve names YouTube as an explicit, near-term
target (`docs/superpowers/specs/2026-07-13-growth-engine-...md:36`, phase G5: "多媒体:
TikTok/YouTube/X/article への横展開"). For Instagram specifically today, post/reel URLs are
path-identified (`/p/<shortcode>/`, `/reel/<shortcode>/`), so this exact collision is not maximally
exploitable against the DAY-1 platform — but the mechanism as specified, and as MANDATED by a
required property test, is already broken for a platform this program's own roadmap plans to onboard
using the identical, unmodified `canonicalizeUrl` function, with no requirement anywhere to revisit
it before that onboarding.

`routeToPhase`: 1b — `canonicalizeUrl` must not unconditionally strip the query string; at minimum,
query parameters must be preserved and compared (sorted, for stability) rather than discarded, or
PROP-016 must be scoped/qualified to name which platforms' identity schemes this normalization is
actually safe for, with an explicit, `required: true` obligation blocking any query-identified
platform from being declared diagnostically proven (REQ-012) until the function is fixed.

---

## Dimension 3: implementation_correctness — **FAIL**

FIND-H and FIND-J are, under this dimension's Phase-1c bar ("are the requirements concrete enough to
be implemented unambiguously"), requirements that a Builder implementing EXACTLY as specified
produces schema-legal, fully-tested (against the spec's own tests) code that is nonetheless
trivially bypassable for the feature's own named customer (FIND-H: no code path even runs the
backstop; FIND-J: the backstop's own URL-identity check is proven, by its own required test, to
treat distinct query-identified resources as identical).

**What is genuinely correct, independently reverified**: `hashRealityClaim`/`decideConvergenceGate`
(FIND-E's fix), `recordGate`'s real merge behavior (`vcsdd-state.js:1734-1744`), and the schema
legality of `recordGate(featureName, 'reality', 'PASS'|'FAIL'|'SKIP', 'verifier'|'human', details)`
against the REAL, unmodified schema (`vcsdd-state.schema.json:37,39` — `verdict` enum and
`reviewedBy` enum both match exactly) all hold up under this fourth independent re-check.
`recordGate(featureName, '3', ...)` (`vcsdd-orchestrator.md:56`) confirms `gates['3']` — REQ-008's
precondition — is a real, existing gate key, not invented.

`routeToPhase`: 1b (same fixes as FIND-H/FIND-J above).

---

## Dimension 4: structural_integrity — **FAIL**

### FIND-L (MAJOR) — the architecture creates two invocation paths (gate script vs. standalone spawn) with radically different guarantees, and does not name or reuse a shared enforcement module between them, unlike its own `decideConvergenceGate` precedent

`verification-architecture.md:63-71` explicitly calls out `decideConvergenceGate` as "shared,
byte-identical, between `.githooks/pre-push`'s new section and `skills/self/verify-reality-gate.mjs`"
— a deliberate, named anti-drift design choice specifically to avoid two enforcement points
disagreeing. No equivalent design choice exists for `validateArtifactProvenance`: it is wired into
exactly one of the two invocation paths this same spec defines (REQ-005's standalone path and
REQ-008's gate-script path), with no shared "verify-and-gate" wrapper module named anywhere that both
paths could call. This is the same class of two-enforcement-points problem the spec correctly solved
for `decideConvergenceGate`, left unsolved for the (arguably more important, since it is the
first-customer-facing) `validateArtifactProvenance` backstop. This is scored here as a structural gap
(missing shared module / inconsistent enforcement boundary across the codebase this spec describes)
distinct from FIND-H's spec-fidelity framing of the same underlying issue.

**What is genuinely correct**: the pure/effectful purity boundary itself (`verification-architecture.
md:11-109`) is still cleanly drawn — `canonicalizeUrl`, `hashRealityClaim`, `validateArtifactProvenance`,
`decideConvergenceGate` are all correctly classified pure, no I/O, matching `reality-verdict-schema.
mjs`'s existing pattern (`skills/self/lib/reality-verdict-schema.mjs:1-9`'s own stated design intent).
No duplication of the category catalog; `FINDING_CATEGORIES` extension is additive-in-place. Naming
is consistent with existing conventions.

`routeToPhase`: 1b — name and require a single shared function (or explicitly document why none is
possible) that both the gate script and any standalone caller (including a future G1 feature) must
call before accepting a verdict.

---

## Dimension 5: verification_readiness — **FAIL**

The Proof Obligations table has a coverage gap that is a direct consequence of FIND-H: no
`required: true` PROP anywhere exercises the standalone spawn path's verdict being backstop-checked,
because nothing is specified to do that checking. PROP-016 (tier 1, `required: true`) actively
enshrines FIND-J's query-collapsing behavior as CORRECT ("scheme/port/trailing-slash/query/fragment
differences canonicalize equal... for arbitrary generated URL pairs") rather than catching it — a
proof obligation that proves the wrong property is worse than an absent one, because it will pass
green and read as evidence of safety. PROP-034 (`automatedVerification` refusal) is real and
testable now, but — per FIND-H — provably inapplicable to the one path (standalone, `recordGate`
never called) where REQ-012's own "Honest current state" text says the underlying risk (Instagram's
`httpStatus` not being diagnostic) is real TODAY, not hypothetically.

**What is genuinely correct**: PROP-031 (hash-mismatch always blocks, tier 1, fast-check) and
PROP-027(c) (live-fire same-push-downgrade rejection, tier 0) are real, required, and exercise actual
artifacts, not mocks — FIND-E's fix is verification-ready. PROP-010/011/012/022/023/024 remain
correctly required and unchanged in mechanism from iteration 2/3's already-confirmed fixes.

`routeToPhase`: 1b (same fixes as FIND-H/J/L above, plus a corrected PROP-016).

---

## Dimension: no-hardcoded-judgment — **PASS**

Re-checked `~/.claude/rules/building-effective-ai-agents.md`'s rule against the "Judgment vs
determinism" section (`behavioral-spec.md:644-671`) and every new deterministic component this
iteration adds: `canonicalizeUrl` (fixed normalization, not a judgment about which URL is "right" —
FIND-J's defect is a WRONG deterministic answer, not a smuggled-in judgment call), `hashRealityClaim`
(content-equality, no judgment), the `claimedUrls`/`automatedVerification` lookups (boolean/set
membership, not honesty judgment). No regex/keyword classification of "is this claim honest" was
added anywhere in this iteration's diff from iteration 3. This dimension remains where this spec's
problems are NOT.

---

## Closed-row audit table (my independent re-verification)

| # | Spec-claimed status | My finding | Verdict |
|---|---|---|---|
| 1-4, 6-9, 11 | CLOSED | Mechanism unchanged from iteration 2/3's already-confirmed fixes; re-spot-checked, no new gap found | genuinely CLOSED |
| 10 | CLOSED | `.githooks/pre-push`'s Cadence Guard precedent (lines 18-30, 75-96) is real and live (`core.hooksPath` confirmed); REQ-009's new section is specified analogously | CLOSED (for the gate-script path only — see row 17/FIND-H for the path this doesn't cover) |
| **14** | CLOSED | Real mechanism for the gate-script path (FIND-D genuinely narrowed). But (a) never wired to the standalone/REQ-011 path (FIND-H), (b) `claimedUrls` itself is an unverified, loop-supplied fact (FIND-I), (c) `canonicalizeUrl` collapses query-identified distinct resources (FIND-J) | **NOT actually closed** for the feature's own named customer |
| **15** | CLOSED | Verified: `hashRealityClaim`/`decideConvergenceGate` correctly, deterministically, fail-closed on any mismatch; PROP-031/PROP-027(c) both required and exercise real artifacts | genuinely CLOSED |
| **17** | MITIGATED | `automatedVerification`/PROP-034 real but refuses only `recordGate(...,'verifier',...)`, a call the standalone/REQ-011 path never makes; also defaults fail-OPEN (`true`) unless the author remembers to set `false` (FIND-K) | **NOT actually mitigated** for the feature's own named customer |
| 12 | OPEN (disclosed) | Confirmed identical, pre-existing gap in `gig_reality_gate.py`/`cdp_nav_snapshot.py`; honestly disclosed, not hidden | legitimately OPEN, honestly disclosed |
| 13 | OPEN (disclosed) | TOCTOU is inherent to any point-in-time check; the "we don't re-check old URLs" caveat is stated plainly | legitimately OPEN, honestly disclosed |
| 16 | OPEN (disclosed) | The FIND-F disposition's reasoning is sound (a local hook cannot be an adversarial-insider security boundary) and is honestly, verbatim-quoted, not hand-waved | legitimately OPEN, honestly disclosed — but see judgment below on whether it matters for THIS gate's actual customer |

---

## Falsifiability check (review task item 5)

There ARE real, required, live-fire proof obligations that force actual FAIL verdicts for the
NARROW scenarios this spec enumerates for the **gate-script/VCSDD path**: PROP-020/020b (real spawns
against nonexistent/wrong URLs), PROP-027 (real `.githooks/pre-push` invocation, including the new
same-push-downgrade fixture), PROP-031 (hash-mismatch property test), PROP-034 (`automatedVerification`
refusal). These are genuine, not stubbed.

However, for the feature's own declared first customer (REQ-011, the standalone Instagram-post daily
verification), **a lying or merely careless implementation can satisfy every acceptance criterion in
this entire spec while producing a false PASS**, via any of:
- FIND-H: the backstop is simply never invoked on this path — the raw, self-reported LLM verdict is
  the only output.
- FIND-I: even if wired, the caller (the very loop whose honesty is in question) supplies the
  `claimedUrls` value itself, with no required test proving content-mismatch detection catches a
  real-but-wrong self-supplied URL.
- FIND-J: `canonicalizeUrl`'s query-stripping is a live collision vector for any query-identified
  platform this general-purpose function is later pointed at (explicitly roadmapped, G5).

None of these three is exercised by any `required: true` proof obligation. Falsifiability holds for
the narrow, gate-script-scoped threat model this spec wrote tests against; it does NOT hold for the
threat model this spec's own preamble claims to have "completely, adversarially re-enumerated"
(`behavioral-spec.md:39-40`) for the actual, named acceptance vehicle.

---

## Judgment on rows 12/13/16 (review task item 3)

**Row 12 (artifact-trail forgery)**: Legitimate, honestly disclosed, matches a real pre-existing
precedent (`gig_reality_gate.py`/`cdp_nav_snapshot.py`). Not, by itself, disqualifying.

**Row 13 (TOCTOU)**: Legitimate, inherent to any point-in-time check, honestly disclosed with a named
caveat. Not disqualifying for a daily-cadence use case.

**Row 16 (local-hook bypass)**: The reasoning is sound and the disclosure is honest and thorough. But
my own finding (FIND-H) makes row 16 close to moot for THIS gate's actual first customer: REQ-011's
standalone path never touches `.githooks/pre-push`, `state.json`, or `gates.reality` at all — so
whether an adversarial insider can bypass the pre-push guard is irrelevant to whether the Instagram
loop's own daily claims are honestly checked. The disclosed risk (row 16) is real for the
VCSDD-pipeline-completion use case; it is not the reason this gate is unready for its stated first
customer. FIND-H/I/J are the reasons.

**My overall ship/no-ship judgment**: I would NOT ship this gate to the growth-engine's Instagram loop
(REQ-011) as currently specified. The four iterations of adversarial back-and-forth have built a
genuinely sophisticated, well-tested provenance backstop — but it protects a code path
(`/vcsdd-reality`, `gates.reality`, VCSDD-completion) that this spec's own REQ-011 says the actual
first customer does not use. For the ACTUAL first customer, the gate currently reduces to "trust the
fresh LLM's self-report," which is precisely the failure mode this entire feature (and the base
`reality-verifier` feature it extends) exists to prevent. This is not a case of "acceptable residual
risk, honestly disclosed" (like rows 12/13/16) — it is an unexamined, undisclosed gap between what
REQ-011's EARS claims ("SHALL be able to prove or disprove... via REQ-003/004/012's... check") and
what the architecture actually wires up, contradicted by REQ-003's own acceptance criteria
("unconditionally invoked by **the gate script**"). Rows 12/13/16 are honest disclosures this spec
should ship with; FIND-H/I/J are not disclosed anywhere and are the actual blockers.

---

## Overall Gate Verdict: **FAIL**

Blocking findings (must be fixed before Phase 1c can pass and Phase 2 can begin):

1. **FIND-H** — the entire REQ-004 deterministic backstop and REQ-012's `automatedVerification`
   fail-closed rule are wired exclusively into the VCSDD gate script (`recordGate`-calling path);
   REQ-011's own text says the feature's named first customer (the growth-engine Instagram loop) uses
   a standalone path that calls neither `recordGate` nor anything else that invokes
   `validateArtifactProvenance`. REQ-003's own acceptance criteria ("unconditionally invoked by the
   gate script") contradicts REQ-011's EARS claim that this protection applies to the standalone
   customer. A raw, unbackstopped LLM self-report is the only real output for REQ-011's use case as
   currently specified.
2. **FIND-I** — `claimedUrls` for a caller-per-invocation claim is supplied by the same loop whose
   honesty is under test, with no independent tether to what was actually posted; the spec's
   "VERIFIED" claim that this matches `gig_reality_gate.py`'s precedent is factually wrong
   (`gig_judge.py:26-31`'s `DEFAULT_GROUND_TRUTH_URLS` is a fixed, spec-time constant the loop under
   test cannot influence — the opposite trust model). No required PROP tests content-mismatch
   detection against a real-but-wrong, caller-self-supplied URL.
3. **FIND-J** — `canonicalizeUrl` strips query strings entirely; PROP-016 mandates this as correct.
   For any query-identified-resource platform (e.g. YouTube, explicitly named in this program's own
   G5 roadmap), two different real, public artifacts canonicalize identically, defeating the
   URL-identity check row 14 was built specifically to add. Not maximally exploitable against
   Instagram today (path-identified URLs), but broken, by a required test, for a platform this spec
   claims general-purpose coverage over and this program plans to onboard using the same function.

Major, non-blocking-but-must-be-tracked: **FIND-K** (`automatedVerification` defaults fail-open,
inconsistent with this spec's own fail-closed precedent for `requiredArtifactCount`), **FIND-L**
(no shared enforcement module between the two invocation paths, unlike `decideConvergenceGate`'s own
precedent for avoiding exactly this kind of drift).

Iteration-3's FIND-D, FIND-E, FIND-F, and FIND-G are each disposed of above, independently
re-verified against ground truth rather than taken on the spec's word: FIND-E is genuinely,
completely fixed. FIND-D, FIND-F, and FIND-G are each narrowed or reclassified in a way that is
individually defensible, but the SAME underlying vulnerability class this spec exists to close
(a self-reported real-world claim being accepted as sufficient) is reachable again through three
further, previously-unexamined doors — this time specifically through the doors this iteration
itself newly opened (`claimedUrls`, `canonicalizeUrl`, `automatedVerification`) rather than through
the doors it closed. Per this spec's own explicit, self-imposed bar (`behavioral-spec.md:47-50`,
"a future iteration that finds an 18th path has found a spec defect, not merely an implementation
bug"), that is exactly what this review found: three 18th-and-beyond paths, none accounted for in
the 17-row closure table.
