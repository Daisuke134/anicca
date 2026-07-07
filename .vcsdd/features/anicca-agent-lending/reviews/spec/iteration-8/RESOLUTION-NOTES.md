# Resolution Notes — Phase 1c spec review, iteration 8

feature: `anicca-agent-lending` · mode: strict · review verdict: FAIL (2 findings — 1 critical, 1 major) ·
this revision resolves both. Files touched: `specs/behavioral-spec.md`, `specs/verification-architecture.md`.
Neither `state.json`, the reviews manifest, nor any verdict file was touched, per the task's own
constraint — only the two spec files were edited.

---

## FIND-701 (critical) — boundary bug: strict `>` makes a single max-size default untrippable

**Problem restated:** `evaluateOverallDefaultKillSwitch`'s absolute-loss branch checked
`totalRecentDefaultLossUsd > RECENT_DEFAULT_LOSS_THRESHOLD_USD` (strict greater-than), with
`RECENT_DEFAULT_LOSS_THRESHOLD_USD` deliberately set to `$5.00` — EQUAL to REQ-105's own `maxLoanUsd`. Since
no single loan under REQ-105's own ladder can ever exceed `$5.00`, a single bust-out default at the ladder's
own maximum size can NEVER, by itself, satisfy a strict `>` comparison against a threshold of the SAME value
— directly contradicting (a) the document's own stated design intent ("chosen here specifically so that ONE
single bust-out default at REQ-105's own maximum possible loan size ... is, BY ITSELF, already sufficient to
trip this signal"), (b) the requirement's own worked Edge Case (which computes `totalRecentDefaultLossUsd =
$5.00`, states it EQUALS the threshold, and asserts `paused:true`), and (c) PROP-114f's own fixture (the
revision's own headline dilution-defeat proof, which also asserts `paused:true` at exactly `$5.00`).

**Fix:** the comparison operator is corrected from strict `>` to `>=` everywhere it appears — a loss AT or
ABOVE the threshold now trips the pause. This makes the requirement's own already-stated design intent, its
own worked edge case, and PROP-114f's own fixture all internally consistent for the first time — none of the
three needed their own asserted values changed, only the operator.

**`specs/behavioral-spec.md` changes:**
- Top-of-file `revision:` metadata bumped from "iteration 7" to "iteration 8" (line 5), and the per-finding
  citation list extended to include `FIND-701..702` / `reviews/spec/iteration-8/RESOLUTION-NOTES.md`
  (lines 3-10).
- New `## Changelog (iteration 8 → current, this revision)` section inserted after the existing
  iteration-7 changelog table and before `## Background / rationale` (lines 106-115): documents both
  FIND-701 and FIND-702 in the SAME per-iteration changelog-table convention every prior iteration already
  uses.
- REQ-114's **"Kill-switch enforcement"** paragraph, lines **937-943** (the EARS clause itself): the third
  OR-condition rewritten from `` `(totalRecentDefaultLossUsd > RECENT_DEFAULT_LOSS_THRESHOLD_USD)` `` to
  `` `(totalRecentDefaultLossUsd >= RECENT_DEFAULT_LOSS_THRESHOLD_USD)` ``, with an inline note explaining the
  correction and citing FIND-701, the worked edge case, and PROP-114f (none of which needed their own values
  changed).
- No change was needed to the worked Edge Case (already asserted `paused:true` at exactly `$5.00`, now
  actually reachable) or to the Acceptance Criteria's PROP-114f fixture (same reason) — confirmed by grep,
  per the finding's own instruction that these did not need to change.

**`specs/verification-architecture.md` changes:**
- Purity Boundary Map row for `evaluateOverallDefaultKillSwitch`, line **29**: the restated formula corrected
  from `>` to `>=`, with the same inline correction note.
- PROP-114b row, line **136**: the THREE-condition pause-rule description's third condition corrected from
  `>` to `>=`, with the same inline correction note. The row's own existing fixture set (including the
  `totalRecentDefaultLossUsd:5.01` fixture isolating the third branch) required no changes — `5.01` already
  satisfies both `>` and `>=`.

A full grep of both spec files for `RECENT_DEFAULT_LOSS_THRESHOLD_USD` after the edit confirms these were the
ONLY two places the literal comparison operator appeared; every other occurrence in either file is either the
threshold's own numeric definition/rationale prose (behavioral-spec.md lines 880, 1010, 1017 areas) or a
fixture/edge-case value comparison, none of which restate the operator itself and none of which needed to
change.

---

## FIND-702 (major) — no Tier-0 binding check that the real append code sets `defaulted_ms`

**Problem restated:** `defaulted_ms` (the field REQ-114's `computeRecentDefaultLossUsd` depends on to
determine whether a given default falls within its own rolling window) was, before this revision, defined
only in prose (REQ-109's EARS clause) and exercised only via `computeRecentDefaultLossUsd`/
`computeOverallDefaultRateUsd`'s own pure-function fixtures (PROP-114e/PROP-114f), where `defaulted_ms` is
ALWAYS supplied as already-populated, hand-authored fixture data. No proof obligation anywhere in the
171-row (now 172-row) table structurally confirmed that REQ-109's own REAL, production default-detection/
append code path actually SETS this field when it appends a `"defaulted"` row — an implementation could pass
every stated PROP for REQ-109 and REQ-114 while the real append code silently omitted or mistyped this field,
permanently zeroing `totalRecentDefaultLossUsd` in production (since REQ-114's own fail-closed convention
treats a missing/malformed `defaulted_ms` as contributing `0`), making the ENTIRE new absolute-loss defense
this feature adds silently inert.

**Fix:** a new Tier-0 structural proof obligation, **PROP-109g**, mirroring PROP-105h's/PROP-106d's/
PROP-114c's own established "source-grep/control-flow read of the REAL, production code path — never a mock,
never a hand-authored fixture" pattern, requiring confirmation that the REAL, production effectful caller
that appends a `status:"defaulted"` row genuinely sets `defaulted_ms: Date.now()` on that row's own append
payload, and omits this field on every non-`"defaulted"` status-transition row.

**`specs/behavioral-spec.md` changes:**
- REQ-114's own `defaulted_ms` definition paragraph, lines **875-879** (inside the
  `computeRecentDefaultLossUsd` "Definition" paragraph): a forward cross-reference added, pointing to
  REQ-109's own new Tier-0 check (PROP-109g) for the real-code confirmation this prose definition alone
  cannot provide.
- REQ-109's own EARS clause, lines **2056-2060** (immediately after "A row whose `status` is NOT
  `\"defaulted\"` ... carries no `defaulted_ms` field."): a new sentence added, explicitly stating this
  prose definition is NOT sufficient proof that the real append code sets the field, and cross-referencing
  the new Tier-0 check (PROP-109g), mirroring PROP-105h's own "this mocked-caller fixture proves the
  function... it does NOT, by itself, prove the REAL, production code..." framing used elsewhere in this
  same document for REQ-106's kill-switch call sites.
- REQ-109's own Acceptance Criteria, new bullet added at lines **2175-2183** (after the existing PROP-109e
  bullet, before the section's closing `---`): the full binding statement of PROP-109g — a structural/Tier-0
  check confirming the REAL, production effectful caller that appends a `status:"defaulted"` row genuinely
  sets `defaulted_ms: Date.now()` on that row's own payload, and that no non-`"defaulted"` status-transition
  append includes this field, never accepting PROP-114e/PROP-114f's own hand-authored-fixture proofs as
  sufficient evidence for this specific binding fact.
- New `## Changelog (iteration 8 → current, this revision)` table (see FIND-701 section above, same edit)
  documents FIND-702 alongside FIND-701.

**`specs/verification-architecture.md` changes:**
- **New PROP-109g row** added to the Proof Obligations table, line **170** (immediately after PROP-109e,
  before PROP-110a): Tier 0, Required `true`, `REQ-109/REQ-114`. Description mirrors PROP-105h's/PROP-106d's/
  PROP-114c's own real-source-read discipline exactly; Tool/Method column specifies a source-grep or
  control-flow read of the real REQ-109 default-append call site confirming (a) its `appendChild` payload
  for a `status:"defaulted"` row includes `defaulted_ms: Date.now()` (or equivalent, set at append time,
  never backdated), and (b) no `appendChild` payload for an `"active"`/`"repaid"` status-transition row
  includes this field.
- "Verification tiers" Tier-0 paragraph, lines **53-56**: REQ-109's existing Tier-0 entry extended to also
  cite the new PROP-109g check.
- "Verification Strategy" Tier-0 bullet list, lines **193-195**: REQ-109's existing Tier-0 citation extended
  to also cite PROP-109g.
- Gate section item (5) (REQ-109's default handling), lines **389-399**: extended with an explicit adversary
  confirmation requirement — the REAL, production append call site (never a unit test in isolation, never a
  hand-authored fixture) must be confirmed, via direct control-flow read, to set `defaulted_ms` correctly;
  the adversary MUST NOT accept PROP-114e/PROP-114f's own pure-function fixtures as sufficient evidence for
  this specific binding fact, the SAME discipline PROP-105h/PROP-114c already establish for their own
  sibling call-site facts.

---

## Files touched (paths)

- `/Users/anicca/anicca-project/.vcsdd/features/anicca-agent-lending/specs/behavioral-spec.md`
- `/Users/anicca/anicca-project/.vcsdd/features/anicca-agent-lending/specs/verification-architecture.md`

No other file was modified. `state.json`, the reviews manifest, and verdict files were left untouched per
the task's own instruction.
