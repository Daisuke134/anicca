# Resolution notes — iteration-2 spec review round 1 → round 2

feature: `anicca-agent-spawn` · mode: strict
Fixes 4 findings from `reviews/spec/iteration-2/output/findings/FIND-101..104.json` (all 6
iteration-1 findings were reconfirmed genuinely resolved and are untouched by this pass).

Files edited:
- `specs/behavioral-spec.md`
- `specs/verification-architecture.md`

No other files touched. `state.json`, the reviews manifest, and verdict files were left untouched
per instructions.

---

## FIND-101 (critical) — stop repurposing `colony-wallets.json`

**Design decision implemented**: introduced a brand-new, dedicated registry file at
`~/anicca/skills/self/spawn/registry/citizens.json`, seeded with a fixed literal 2-entry JSON array
(automaton + Franklin — the colony's two currently-verified self-funded citizens, per
`~/anicca/skills/self/colony-status.sh` and this project's own `CLAUDE.md` colony table). claude-p
(`0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74`, human-funded per `docs/WALLETS.md` lines 49-62) is
never seeded. `~/anicca/skills/economy/ubi/colony-wallets.json` is now explicitly documented as
untouched and out of scope, sharing zero state with the new file.

**`specs/behavioral-spec.md`**:
- Lines 1-6, 16: header revision line + FIND-002 changelog row updated to reference the new
  registry path instead of `colony-wallets.json`.
- Lines 22-32 (new): added a second changelog table, "iteration 2 spec review, round 1 → round 2",
  documenting FIND-101/102/103/104 and their resolutions.
- Lines 104-105 (Purity boundary analysis overview table): rewrote the "Colony citizen registry"
  row to describe the brand-new `citizens.json` file (not a migration); added a new row directly
  below it explicitly stating `colony-wallets.json` is untouched/out of scope and citing its 2nd
  entry as claude-p's human-funded wallet.
- Line ~120 (Purity boundary overview, "Spawn ledger append" row): updated to cite
  `citizens.json` instead of `colony-wallets.json`, and to note the new `isSelfFunded()`
  pre-append gate.
- Lines 329-426 (REQ-105, fully rewritten): EARS clause now specifies the brand-new dedicated file,
  explicitly forbids reading/writing/migrating `colony-wallets.json`, defines the two-field
  `wallet`/`walletAddress` split (also resolves FIND-104), embeds the literal 2-entry seed JSON
  array (lines 367-386), and states claude-p/any human-funded wallet must never be seeded. Added a
  4th edge case and 2 new acceptance criteria requiring `citizens.json` to never contain an entry
  whose `isSelfFunded()` verdict is `false`, at seed time or at any later append (cross-referencing
  REQ-305's new pre-append gate below).
- Lines 843-899 (REQ-305, edited): registry-append path now targets `citizens.json` (not
  `colony-wallets.json`); new paragraph (lines 867-874) requires calling `isSelfFunded()` on the new
  record's `{wallet, fuel, humanDependencies}` sub-object BEFORE appending and REFUSING the append
  (logged, distinct failure mode) if it returns `false`; added a 4th edge case (lines 891-898)
  distinguishing this permanent-refusal case from a transient filesystem-error retry, and a new
  acceptance criterion requiring a fixture proving zero append when `isSelfFunded()` would fail.

**`specs/verification-architecture.md`**:
- Lines 1-10: revision line updated to reference the FIND-101..104 follow-up fixes.
- Lines 16-18 (Purity Boundary Map): rewrote the `is-self-funded.mjs` row to note the
  `wallet`/`walletAddress` split; rewrote the registry row to describe the brand-new `citizens.json`
  file; added a new row explicitly marking `colony-wallets.json` as existing/untouched/out of scope.
- Line 35 (ledger-append row): updated to cite `citizens.json` and the new `isSelfFunded()`
  pre-append gate.
- Lines 46-52, 53-65 (Verification tiers): added `citizens.json` seed-purity structural/unit checks
  to Tier 0/Tier 1; removed the stale "registry-migration round-trip test" from Tier 2 (there is no
  migration); added REQ-305's append-refusal check to Tier 1 (unit half) and Tier 2 (integration
  half).
- Lines 105-108 (Proof Obligations): rewrote PROP-105a (citizens.json shape, wallet/walletAddress
  split); rewrote PROP-105c (direct seed-data-passes-`isSelfFunded()` assertion, replacing the
  "compare against today's known-good identities" method the finding flagged as incoherent); added
  new PROP-105d (seed purity — citizens.json never contains a false-isSelfFunded entry, at seed or
  append time).
- Line 143 (new PROP-305e): append-on-spawn calls `isSelfFunded()` before appending and refuses
  (zero write) if `false`.
- Lines 172-199 (Verification Strategy Tier 0/1/2 lists): added PROP-105d/PROP-305e references;
  removed the stale Tier-2 "registry-round-trip migration test" bullet.
- Lines 221-230 (Gate item 1a): rewritten to describe `citizens.json` (not `colony-wallets.json`),
  cite PROP-105a/c/d, and require the adversary confirm the seed set excludes claude-p/any
  human-funded wallet.
- Lines 288-295 (Gate item 8): added the append-time `isSelfFunded()` refusal check (PROP-305e) to
  REQ-305's gate item.

---

## FIND-102 (major) — REQ-206 EARS/edge-case self-contradiction

**Design decision implemented**: rewrote the EARS clause itself to state "at least one of these two
anchors, it is not an error for both to be present, it is an error for neither" — removing the
XOR-reading "never both, and never neither" phrasing that contradicted the requirement's own edge
case. Added a 5th acceptance-criteria fixture and a new PROP for the both-present path.

**`specs/behavioral-spec.md`**:
- Lines 655-668 (REQ-206 EARS clause, rewritten): replaced "requiring at least ONE of these two
  anchors, never both, and never neither" with an explicit non-XOR statement: at least one required;
  both present is not an error; neither present is an error. Cross-references FIND-102 by name.
- Lines 704-707 (new acceptance criterion): added a 5th fixture — both `childInbox` AND the
  ERC-8004 pair present simultaneously succeeds and the returned row carries all three fields.

**`specs/verification-architecture.md`**:
- Line 129 (new PROP-206e): both-anchors-present-accepted path, Tier 1 unit test.
- Lines 60-62 (Tier 1 list): added PROP-206e reference.
- Lines 264-272 (Gate item 4a): added the both-present-accepted confirmation, citing PROP-206e.

---

## FIND-103 (major) — name the canonical `statePath` for the colony-spawn lock

**Design decision implemented**: designated REQ-105's `citizens.json` path as the colony-spawn
lock's one canonical `statePath` (a natural fit since the critical section IS "read citizens.json +
decide + possibly append to citizens.json"), exported as a single named constant
`CITIZENS_REGISTRY_PATH` from a new shared module `~/anicca/skills/self/spawn/lib/registry-path.mjs`
that every call site must import.

**`specs/behavioral-spec.md`**:
- Lines 246-260 (REQ-103, new "Canonical `statePath`" paragraph inserted after the existing
  reuse paragraph): explains `withGigLock`'s real `(statePath, lockKey, fn, opts)` signature, the
  `lockPaths()` derivation from both `statePath` and `lockKey`, the mismatched-`statePath` hazard,
  and designates `citizens.json`'s path as the canonical `statePath`, exported as
  `CITIZENS_REGISTRY_PATH`.
- Lines 273-276 (new 4th edge case): a future call site hardcoding its own literal path instead of
  importing the constant is a spec violation caught at Phase 3 review.
- Lines 278-291 (Acceptance Criteria, edited/added): 1st bullet now requires `statePath` be set to
  the exported `CITIZENS_REGISTRY_PATH` constant; new 3rd bullet requires a structural/Tier-0
  source-grep/import-identity check that every call site imports the same constant, explicitly
  noting this is required in addition to (not instead of) the existing concurrent-race integration
  test.

**`specs/verification-architecture.md`**:
- Line 22 (lock.mjs Purity Boundary row, edited): added the `statePath`/`CITIZENS_REGISTRY_PATH`
  explanation.
- Line 23 (new row): added `registry-path.mjs::CITIZENS_REGISTRY_PATH` as its own Purity Boundary
  Map entry.
- Line 100 (PROP-103a, edited): now also asserts both callers acquire the lock via the same
  `CITIZENS_REGISTRY_PATH` constant, and notes PROP-103d is required in addition.
- Line 103 (new PROP-103d): structural/Tier-0 check that every call site imports and uses the same
  exported constant, never an independently hardcoded string.
- Lines 46-52, 162-163 (Tier 0 list): added PROP-103d.
- Lines 232-240 (Gate item 2, edited): added the canonical-`statePath`-constant confirmation citing
  PROP-103d.

---

## FIND-104 (medium) — reconcile wallet field type mismatch

**Design decision implemented**: split the citizen-registry record's wallet field into two separate
fields — `wallet: {evm?: boolean, solana?: boolean}` (matching `is-self-funded.mjs::hasOwnWallet()`'s
real, documented boolean contract exactly) and `walletAddress: {evm?: string, solana?: string}` (the
actual address string(s), for REQ-305's append use and any future consumer needing the real
address, never passed to `isSelfFunded()`).

**`specs/behavioral-spec.md`**:
- Lines 341-358 (REQ-105 EARS clause): defines the two-field split explicitly, citing
  `hasOwnWallet()`'s `Boolean(wallet.evm) || Boolean(wallet.solana)` implementation as the reason for
  the split, and states `walletAddress` is never passed to `isSelfFunded()`.
- Lines 367-386 (literal seed JSON): each seed entry carries both `wallet` (boolean) and
  `walletAddress` (string) fields correctly split.
- Lines 409-412 (Acceptance Criteria, edited): clarifies `isSelfFunded()` is called on
  `{wallet, fuel, humanDependencies}` only, never `walletAddress`.
- Lines 856-862 (REQ-305, edited): the appended record now splits `wallet: {evm: true, solana:
  true-if-generated}` (booleans) from `walletAddress: {evm: childWallet, solana:
  childSolanaAddress-if-generated}` (strings), explicitly citing `hasOwnWallet()`'s documented
  contract.
- Line 886 (Acceptance Criteria, edited): the registry-append integration test criterion now
  explicitly requires asserting the wallet/walletAddress split is correct.

**`specs/verification-architecture.md`**:
- Line 16 (is-self-funded.mjs Purity Boundary row, edited): clarifies `wallet.evm`/`wallet.solana`
  are consumed strictly in boolean shape, `walletAddress` is a separate field never passed to the
  function.
- Line 17 (citizens.json Purity Boundary row): shows the two-field record shape.
- Line 105 (PROP-105a, edited): now specifies the full two-field shape and that `isSelfFunded()`
  never receives `walletAddress`.
- Line 142 (PROP-305d, edited): now requires asserting the wallet-boolean/walletAddress-string
  split is correct in the appended record.
- Lines 221-224 (Gate item 1a): cites the two-field split explicitly as part of the confirmed shape.

---

## Verification performed on this revision

- Confirmed both spec files are well-formed Markdown (balanced code fences: `behavioral-spec.md` has
  2 backtick fences forming one balanced JSON code block for REQ-105's seed data;
  `verification-architecture.md` has none, as expected).
- Re-grepped both files for `colony-wallets.json` after all edits: every remaining occurrence is a
  deliberate clarifying reference stating the file is untouched/out of scope/not migrated — no
  stray unedited references to the old repurposing design remain.
- Cross-checked the literal seed data against live, on-disk evidence: `automaton`'s current wallet
  (`0xB9dd3B67921B354c656523d6851537988F31DD56`, per `~/anicca/skills/economy/ubi/run.sh`,
  `~/anicca/skills/self/colony-status.sh`, and `~/anicca/specs/09-EARN-X402-LIVE.md`'s 2026-07-07
  rotation note) and Franklin's wallet (`8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`, per the same
  scripts and this project's `CLAUDE.md` colony table) are the colony's only two currently-verified
  self-funded citizens; claude-p's wallet is confirmed excluded.
- Did not touch `state.json`, the reviews manifest, or verdict files, and did not commit/push, per
  instructions — those transitions are the architect's to perform after this report.
