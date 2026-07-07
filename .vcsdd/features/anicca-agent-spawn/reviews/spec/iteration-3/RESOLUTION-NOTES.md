# Resolution Notes — spec review iteration-3 (FIND-201..206)

**feature**: anicca-agent-spawn · **mode**: strict · **日付**: 2026-07-07

All 6 iteration-3 findings resolved as targeted edits to `specs/behavioral-spec.md` and
`specs/verification-architecture.md`. Both files' header revision lines and changelog sections were
updated to iteration 3 (`behavioral-spec.md:1-6,35-49`; `verification-architecture.md:1-12`) per the
files' own established changelog convention.

Real source files re-read to ground every design decision below (no guessing): `~/anicca/skills/self/
spawn/lib/ledger.js`, `~/anicca/skills/self/spawn/lib/child-spec.js` (full file, not just lines 16-34),
`~/anicca/skills/self/spawn/lib/__tests__/child-spec.test.js`, `~/anicca/skills/self/spawn/lib/
spawn-decision.js`, `~/anicca/skills/self/spawn/run.sh`, `~/anicca/identity/genesis.md`, `~/anicca/
install.sh`. Also checked for a pre-existing colony-wide constitution file (`~/.openclaw/CONSTITUTION.md`
exists but is Dais's private automaton-specific instance, never cloned onto a cloud-deployed child per
REQ-303's own `git clone` of the OSS repo) — `~/anicca/identity/genesis.md` is the correct, actually-
shipped canonical file (per `install.sh:78-93`'s own comment: "Canonical hustle genesis lives at
identity/genesis.md in the repo; ship it verbatim").

---

## FIND-201 (critical) — active_since/bootstrap_failed location contradiction

**Fix**: ledger.js is now the pinned, sole canonical owner of `status`/`active_since`; `citizens.json`
never carries either field. REQ-101 gains an explicit two-step candidate-assembly process ending in a
new pure join function, `filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays})
→ citizens[]`, that cross-references REQ-105's registry against `ledger.js`'s rows (matched by
`id`===`child_id`) before `computeColonySurplusUsd` ever runs.

- `behavioral-spec.md:146-202` — REQ-101's EARS rewritten into the explicit two-step read (registry) +
  join (`filterProductiveCitizens` against ledger.js) process; new edge case (malformed
  `active_since` on an `"active"` row) added; new Acceptance Criterion for the join function added.
- `behavioral-spec.md:1135-1195` — REQ-402's EARS rewritten: `active_since` pinned as a ledger.js row
  field set by REQ-305 at activation; exclusion from REQ-101's aggregation stated to run EXCLUSIVELY
  through `filterProductiveCitizens`; Acceptance Criteria updated to read `active_since`/`status`
  from ledger.js, never the registry.
- `behavioral-spec.md:958-983` (REQ-305 EARS) and `:1046-1053` (REQ-305 Acceptance Criteria) — REQ-305
  now explicitly sets `active_since` on the ledger row the moment a child is marked `"active"`.
- `behavioral-spec.md:105-107,109-110` (Purity boundary analysis overview table: "Colony citizen
  registry", "Colony surplus aggregation", "Spawn ledger append" rows) — updated to state the
  registry/ledger split and cite the new join function.
- `verification-architecture.md:20-21` (Purity Boundary Map: `citizens.json` row updated; new
  `filterProductiveCitizens` row inserted) and `:35` (ledger.js row updated with `status`/
  `active_since` ownership note).
- `verification-architecture.md:107` — new proof obligation **PROP-101d** (`filterProductiveCitizens`
  correctness, Tier 1).
- `verification-architecture.md:152` — **PROP-402c** rewritten to describe the ledger.js-sourced flag
  read through the join, not a second registry-resident flag.
- `verification-architecture.md:57,68-69,194,213-214,255-256,264,352` — Verification tiers/Strategy
  narrative and Gate items (1a split into 1a + new **1b**, and item (10)) updated to reference the
  join function and ledger.js ownership.

## FIND-202 (major) + FIND-205 (medium) — HOME field missing + unresolved $HOME template

**Fix**: REQ-105's record shape gains a new `homeDir: string` field (an already-resolved absolute
HOME path, for REQ-403's audit) and `telemetryPath` is redefined to be an ALREADY-RESOLVED absolute
path at seed/append time — never an unresolved `$HOME` template requiring a runtime substitution step.

- `behavioral-spec.md:397-413` — REQ-105's field-shape prose rewritten: `telemetryPath` redefined as
  already-resolved; new `homeDir` field added and documented, including the explicit note that both
  of today's citizens legitimately share `homeDir=/Users/anicca` this increment (expected, not a bug,
  per REQ-106).
- `behavioral-spec.md:417-441` — the literal seed JSON example rewritten: both entries' `telemetryPath`
  changed from `"$HOME/.automaton/state/telemetry.json"` / `"$HOME/.blockrun/state/telemetry.json"` to
  resolved absolute paths (`/Users/anicca/.automaton/...`, `/Users/anicca/.blockrun/...`), and a new
  `"homeDir": "/Users/anicca"` field added to both; explanatory paragraph appended after the JSON block
  (`behavioral-spec.md:440-441`).
- `behavioral-spec.md:461-467` (REQ-105 Acceptance Criteria) — field list updated to include `homeDir`;
  new criterion added asserting neither `telemetryPath` nor `homeDir` ever contains a `$HOME`/
  `$ANICCA_HOME` substring.
- `behavioral-spec.md:1230-1234` (REQ-403 Acceptance Criteria) and `:1207-1209` (REQ-403 EARS) —
  rewritten to read `HOME` directly from the registry's `homeDir` field, never derived from
  `telemetryPath`.
- `behavioral-spec.md:1046-1049` (REQ-305) — appended registry record's `telemetryPath`/`homeDir`
  fields specified as already-resolved.
- `behavioral-spec.md:126` (Purity boundary table, "Balance/telemetry reads" row) — clarified that
  `run.sh`'s `$HOME`-relative notation is a shell-level convenience describing the same physical file,
  never implying the registry's own JSON field is a template string.
- `verification-architecture.md:20,29,30,37` (Purity Boundary Map: `citizens.json`,
  `readCitizenBalances`, `resolve-identity.mjs`, audit-script rows) — all updated to reference the
  pre-resolved `telemetryPath`/new `homeDir` field.
- `verification-architecture.md:122-123` — new proof obligations **PROP-105e** (no `$HOME`/
  `$ANICCA_HOME` substring anywhere in `citizens.json`) and **PROP-105f** (`homeDir` present, never
  passed to `isSelfFunded()`).
- `verification-architecture.md:106` — **PROP-105a**'s field-shape description updated to include
  `homeDir`.
- `verification-architecture.md:154` — **PROP-403b**'s method updated to read `homeDir` from the
  registry.
- `verification-architecture.md:178-180,198,255-256,332` — Verification tiers/Strategy and Gate items
  (1a), (11) updated accordingly.

## FIND-203 (major) — dangling REQ-402 → REQ-102 data flow

**Fix**: removed the promise that `children_bootstrap_failed` is "fed to REQ-102's next gate
evaluation." Replaced with an explicit descope: recorded for observability only, with a
structurally-checkable non-effect on REQ-102's pinned signature/behavior.

- `behavioral-spec.md:1156-1163` (REQ-402 EARS) — third paragraph rewritten from "SHALL feed this
  outcome to REQ-102's NEXT gate evaluation... as a bookkeeping count" to the descope language: "SHALL
  record this outcome... for observability ONLY... SHALL NOT be passed as a parameter to, or otherwise
  change the behavior of, REQ-102's `decideColonySpawn`."
- `behavioral-spec.md:1193-1195` (REQ-402 Acceptance Criteria) — new criterion: a structural/Tier-0
  check confirms `decideColonySpawn`'s signature/behavior are byte-identical regardless of bootstrap
  failures.
- `verification-architecture.md:170` — new proof obligation **PROP-402d** (structural, Tier 0: no
  `childrenBootstrapFailed` parameter anywhere in the diff; identical gate output with/without
  failures).
- `verification-architecture.md:58,191,353` — Verification tiers/Strategy Tier-0 list and Gate item
  (10) updated to cite PROP-402d.

## FIND-204 (critical) — buildChildSpec's 4 unaddressed required fields

**Fix**: REQ-206 extended (not just its identity-anchor clause) to specify a concrete value/derivation
for `parentWallet`, `generation`, `seedUsdc`, `constitutionHash` — reconciled with the real,
re-read `child-spec.js`/`child-spec.test.js`/`run.sh` and this feature's actual architecture:
- `parentWallet` = REQ-106's coordinator-host citizen's own wallet (verified distinct from `childWallet`,
  never triggering `buildChildSpec`'s existing distinct-wallet throw).
- `generation` = fixed `1`, reusing `run.sh`'s own existing `"${ANICCA_GENERATION:-1}"` default
  convention (`run.sh:136`) — no other derivation convention exists in the real code; this feature's
  spawns are non-lineage top-level children.
- `seedUsdc` = REQ-204's gas-seed amount, the SAME value (never conflated with REQ-303/304's distinct
  shelter cost).
- `constitutionHash` = a fixed SHA-256 of `~/anicca/identity/genesis.md` (the real, already-shipped
  canonical genesis file per `install.sh:78-93`), computed once as a spec-level constant.

- `behavioral-spec.md:741-770` — new paragraph inserted into REQ-206's EARS specifying all four
  derivation rules, explicitly citing `child-spec.js:16-34`, `run.sh:136`, and `install.sh:78-93`.
- `behavioral-spec.md:790-799` — three new REQ-206 edge cases added (parentWallet collision reuses the
  existing throw; `generation` != 1 is a spec violation; `seedUsdc`/gas-seed divergence is a spec
  violation).
- `behavioral-spec.md:816-825` — three new REQ-206 Acceptance Criteria added: a full-seven-field
  `buildChildSpec` fixture/integration test, a `generation`-fixed-at-1 structural check, and a
  `seedUsdc`-equals-REQ-204-gas-seed assertion.
- `behavioral-spec.md:1046-1047` (REQ-305) — spawn-flow EARS cross-references REQ-206's now-complete
  seven-field derivation; Acceptance Criteria (`:1053`) adds a criterion that the real `buildChildSpec`
  call supplies all seven fields per REQ-206.
- `behavioral-spec.md:123` (Purity boundary table, "Per-child identity record assembly" row) — updated
  to note the four fields are code-unchanged but now have explicit spec-level derivation rules.
- `verification-architecture.md:22` (Purity Boundary Map, `child-spec.js` row) — updated with the same
  note.
- `verification-architecture.md:145-146` — new proof obligations **PROP-206f** (real full-seven-field
  call succeeds) and **PROP-206g** (`seedUsdc` aliasing + `generation` fixed at 1).
- `verification-architecture.md:72,81,186,204,217,310-311` — Verification tiers/Strategy and Gate item
  (4a) updated to cite PROP-206f/g.

## FIND-206 (low) — vestigial edge case

**Fix**: removed entirely, no replacement.

- `behavioral-spec.md` (REQ-101 Edge Cases, immediately after the missing-telemetry-data bullet,
  originally lines 150-154 pre-edit) — the "claude-p... appears in the same telemetry-file directory
  listing" bullet deleted in full.
- `behavioral-spec.md:47` — new iteration-3 changelog row documents the removal and its rationale
  (unreachable under the registry-only design REQ-105/101 specify).

---

## Scope note

No changes were made to `state.json`, the `reviews/` manifest, or any verdict file, per instructions.
No commits or pushes were made. All 6 findings are addressed as targeted edits; no unrelated spec
sections were rewritten. The 4 iteration-2 findings (FIND-101..104) already reconfirmed resolved in
iteration-3's review were left untouched.
