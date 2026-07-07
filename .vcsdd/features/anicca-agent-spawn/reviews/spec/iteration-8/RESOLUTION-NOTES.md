# Resolution Notes — Spec Review Iteration 8 (FIND-701, FIND-702, FIND-703)

**Date**: 2026-07-07
**Feature**: anicca-agent-spawn (strict mode)
**Files revised**: `specs/behavioral-spec.md` (iteration 7 → 8), `specs/verification-architecture.md`
(iteration 7 → 8)
**Pre-work verification performed before editing** (per the task's Process step 1): read
`~/anicca/skills/self/spawn/lib/registry-path.mjs` directly — confirmed it does **not yet exist on
disk** (Phase 2 has not been reached; the module is a planned Phase-2-created file, and its only
planned export prior to this revision was `CITIZENS_REGISTRY_PATH`, per REQ-103). Also confirmed the
real current sibling files in `~/anicca/skills/self/spawn/lib/` (`child-spec.js`, `ledger.js`,
`spawn-decision.js`, `state-path.js` — NOT `registry-path.mjs`), and re-read
`~/anicca/skills/earn/lib/resolve-identity.mjs`'s exact resolution logic (`resolveEvmPrivateKey`/
`resolveSolanaSecret`, the `legacyHome = e.HOME` gate, the 20-case reused test suite) to ground every
edit below in the module's real, current behavior.

---

## FIND-701 (critical) — canonical `COORDINATOR_HOME` constant

**Problem**: REQ-403's explicit-env fix required "the coordinator host's own real `$HOME`, sourced
from a registry/coordinator constant" — a placeholder phrase with no constant actually defined anywhere,
unlike REQ-103's disciplined single-named-constant (`CITIZENS_REGISTRY_PATH`) treatment of the
structurally analogous hazard.

**Fix — behavioral-spec.md**:
- `behavioral-spec.md:1851-1868` — new subsection **"Canonical coordinator-HOME constant,
  `COORDINATOR_HOME` (resolves FIND-701 — critical)"** inserted into REQ-403, immediately before the
  existing "Explicit-env correction" subsection. Defines: THE SYSTEM SHALL export a SECOND named
  constant, `COORDINATOR_HOME`, from the SAME shared module REQ-103 already introduces
  (`~/anicca/skills/self/spawn/lib/registry-path.mjs`), computed EXACTLY ONCE at module-load time via
  Node's `os.homedir()` — never `process.env.HOME` read ad hoc, never a hardcoded literal. Spells out
  both defeat modes the vague phrase permitted (independent hardcoding; independent
  `os.homedir()`/`process.env.HOME` reads at the call site) and why each silently reintroduces the
  ambient-environment coupling the fix exists to eliminate. States the constant currently resolves to
  `/Users/anicca` on this coordinator host (confirmed live via `os.homedir()`, 2026-07-07).
- `behavioral-spec.md:1878-1902` — "Explicit-env correction" subsection's worked example rewritten:
  `resolveEvmPrivateKey({home: citizen.homeDir, env: {HOME: COORDINATOR_HOME, ANICCA_HOME:
  citizen.homeDir}})` replaces the old `<the coordinator host's own real $HOME, sourced from a
  registry/coordinator constant>` placeholder. Cross-references PROP-403e (explicit-env obligation) and
  the new PROP-403f (import-identity structural obligation).
- `behavioral-spec.md:1924-1936` (Acceptance Criteria) — rewritten to require the audit script's `env`
  object use `COORDINATOR_HOME` (imported from `registry-path.mjs`) rather than the vague phrase, and to
  cite PROP-403f alongside PROP-403e.
- `behavioral-spec.md:118-133` — new changelog table entry (`## Changelog (iteration 7 spec review →
  iteration 8)`) summarizing FIND-701's resolution.
- `behavioral-spec.md:4` — revision line bumped to "iteration 8," FIND-701..703 added to the resolved
  list.

**Fix — verification-architecture.md**:
- `verification-architecture.md:55` — Purity Boundary Map row for `registry-path.mjs` extended:
  `::CITIZENS_REGISTRY_PATH`, `::COORDINATOR_HOME` (two constants). New sentence: "this SAME module ALSO
  exports `COORDINATOR_HOME`... computed EXACTLY ONCE at module-load time via Node's `os.homedir()`...
  REQ-403's live-audit script imports and uses this SAME constant... (PROP-403f)."
- `verification-architecture.md:73` — the REQ-403 audit-script Purity Boundary Map row's description
  updated to show the invocation passing `env: {HOME: COORDINATOR_HOME, ANICCA_HOME: citizen.homeDir}`.
- `verification-architecture.md:265` — **new row, PROP-403f**: "EVERY call site in the implementation's
  REQ-403 live-audit script that supplies an `env.HOME` value to `resolveEvmPrivateKey`/
  `resolveSolanaSecret` imports and passes the SAME exported `COORDINATOR_HOME` constant from
  `registry-path.mjs`... mirrors PROP-403d's structural discipline exactly." Tier `0`, Tool/Method =
  "structural/Tier-0 check: source-grep or import-identity check across the diff confirming a single
  import site for `COORDINATOR_HOME`... and ZERO occurrences of `os.homedir()`/`process.env.HOME`
  anywhere else in that same code path."
- `verification-architecture.md:261` (PROP-403b) and `:264` (PROP-403e) — literal `<the coordinator
  host's own real $HOME>` placeholders replaced with `COORDINATOR_HOME`.
- `verification-architecture.md:100-104` (Tier 0 prose list) — PROP-403f added, mirroring PROP-103d.
- Gate section `(11)`, `verification-architecture.md:573-597` — new bolded clause requiring the
  adversary to confirm every `env.HOME`-supplying call site imports the SAME `COORDINATOR_HOME`
  constant, with zero independent `os.homedir()`/`process.env.HOME` reads (PROP-403f).
- `verification-architecture.md:5-17` — revision header updated (iteration 8, FIND-701..703 summary).

---

## FIND-702 (major) — PROP-105g rewritten from citation-check to actual re-derivation

**Problem**: PROP-105g's Tool/Method column only required the adversary to confirm a commit/PR *cites*
a verification method — never that the cited computation was actually performed. This reproduced,
one layer removed, the exact "unverified citation" failure class FIND-601 (this same iteration's own
prior fix) had just closed.

**Fix — verification-architecture.md:201** — PROP-105g's Description and Tool/Method columns rewritten
in full:
- Description now states the value must be verified via "an ACTUAL, MECHANICALLY-PERFORMED cryptographic
  re-derivation... diffed against `citizens.json`'s stored `walletAddress`" and explicitly rejects a
  citation-presence check as "a materially weaker, non-equivalent substitute... explicitly rejected."
- Tier changed from `0` to `0/2` (structural existence-of-script check remains Tier 0; the actual
  re-derivation execution is now Tier 2, matching PROP-403b's analogous live-local-filesystem-check
  tier).
- Tool/Method column now requires: Tier 0 confirms a real re-derivation script/test exists in the diff
  and is wired to Phase 3; Tier 2 is the binding check — "a real script/test reads the real private-key
  file's content IN-MEMORY..., computes the resulting address via `privateKeyToAccount`..., and DIFFS
  the result against `citizens.json`'s stored `walletAddress`... FAILING HARD... on any mismatch."
- **New carve-out** (the secrets-handling reconciliation the finding required): "reading the private-key
  file's content IN-MEMORY, for THIS ONE specific re-derivation purpose, is explicitly PERMITTED and
  REQUIRED — narrower than, and not in conflict with, REQ-105's general 'file EXISTENCE only — content
  never read/printed' discipline used elsewhere in this spec for checks that do not need to read secret
  content (e.g. REQ-403's live filesystem-existence check)... the ONLY discipline retained here is that
  the raw private key itself is NEVER logged, printed, or persisted anywhere — only the DERIVED PUBLIC
  ADDRESS may ever be logged/compared/asserted on."

**Consistency updates**:
- `verification-architecture.md:82-90` (Tier 0 prose list) — PROP-105g's mention split to "STRUCTURAL
  half ONLY... the actual re-derivation EXECUTION itself is Tier 2, see below — never merely a citation
  check."
- `verification-architecture.md:136-143` (Tier 2 prose list) — new clause: "REQ-105's
  walletAddress-verification-method check, BINDING RE-DERIVATION half (PROP-105g, integration half,
  resolves FIND-702 — the actual real script/test that reads the real private-key file in memory,
  computes the address via `privateKeyToAccount`, and diffs it against `citizens.json`'s stored
  `walletAddress`, failing hard on mismatch)."
- Gate section `(1a)`, `verification-architecture.md:391-419` — rewritten: "every seeded entry's
  `walletAddress` is INDEPENDENTLY RE-DERIVED — never merely CITED... the adversary must confirm an
  ACTUAL re-derivation script/test was run... a commit/PR message merely claiming the right kind of
  verification method, without the computation ever having been run, does NOT satisfy this obligation."
- No change was needed to `behavioral-spec.md`'s own REQ-105 body (lines ~653-656, 737-742): on review,
  that prose already said "verified... against... ACTUAL signing key material... OR a live on-chain
  balance query" and never used citation language — the citation-check framing existed only in
  verification-architecture.md's PROP-105g row, which is now corrected.

---

## FIND-703 (critical) — `coLocatedWithCoordinator` registry field

**Problem**: `citizens.json`'s schema had no field distinguishing a co-located citizen from a
cloud-hosted one, yet REQ-301 mandates every spawned child is cloud-hosted and REQ-305 mandates every
spawned child is appended into this same registry — making REQ-403's "co-located" enumeration and
PROP-403d's exclusion claim both structurally unenforceable, and REQ-403's own EARS clause ("before any
newly-spawned CO-LOCATED child...") vacuous, since a co-located spawned child can never exist per
REQ-301.

**Fix — behavioral-spec.md**:
- `behavioral-spec.md:611-634` — REQ-105's schema section: "plus ONE additional field" → "plus TWO
  additional fields"; new bullet added for `coLocatedWithCoordinator: boolean` explaining its purpose,
  seed rule (`true` for today's two citizens), and REQ-305's append rule (`false`, always).
- `behavioral-spec.md:698-716` — literal seed JSON array: both entries gain
  `"coLocatedWithCoordinator": true`; new paragraph immediately after the JSON block explains this is a
  structural fact about physical placement, not an inference.
- `behavioral-spec.md:787-792` (Acceptance Criteria) — new bullet requiring the structural check that
  REQ-403's enumeration filters on `citizens.filter(c => c.coLocatedWithCoordinator === true)`.
- `behavioral-spec.md:1508-1521` — REQ-305's append-record template extended with
  `coLocatedWithCoordinator: false`, plus a new explanatory sentence: "THE SYSTEM SHALL ALWAYS set
  `coLocatedWithCoordinator` to exactly `false` for every REQ-305 append... a fixed structural constant
  for this increment, not a judgment call."
- `behavioral-spec.md:1586-1590` (REQ-305 Acceptance Criteria) — new bullet requiring the structural
  check that no code path ever appends `true`, citing PROP-305f.
- `behavioral-spec.md:1771` — REQ-403's own header extended: "...(live-comparison half scoped to
  co-located instances this increment — resolves FIND-303; enumeration keyed on
  `coLocatedWithCoordinator`, resolves FIND-703)."
- `behavioral-spec.md:1772-1799` — REQ-403's EARS clause rewritten: the live-comparison half now reads
  "invoked once per instance in REQ-105's registry whose `coLocatedWithCoordinator` field is exactly
  `true`" instead of an undefined "co-located" notion, and a new **"Corrected, resolves FIND-703"**
  paragraph explicitly removes the vacuous promise ("before any newly-spawned CO-LOCATED child is
  permitted...") — replacing it with: every spawned child is `coLocatedWithCoordinator: false` by
  REQ-305/REQ-301 construction, so the live-comparison half never runs against and never gates a
  spawned child's REQ-401 participation; every spawned child is covered only by the static grep-sweep
  half.
- `behavioral-spec.md:1801-1818` — "Scoping correction" paragraph updated to key the scope statement on
  the real field (`coLocatedWithCoordinator === true`) rather than an implicit notion.
- `behavioral-spec.md:1924-1936` (Acceptance Criteria, shared with the FIND-701 edit above) — rewritten
  to enumerate via `citizens.filter(c => c.coLocatedWithCoordinator === true)`.

**Fix — verification-architecture.md**:
- `verification-architecture.md:48` — Purity Boundary Map `citizens.json` row: schema extended with
  `coLocatedWithCoordinator: boolean`; new bolded sentence describing the seed/append rule and REQ-403's
  filter.
- `verification-architecture.md:61` — `resolve-identity.mjs` Purity Boundary Map row: "invokes it ONLY
  once per CO-LOCATED running instance" → "invokes it ONLY once per instance whose registry record has
  `coLocatedWithCoordinator === true`."
- `verification-architecture.md:73` — REQ-403 audit-script row: enumeration description rewritten to
  `citizens.filter(c => c.coLocatedWithCoordinator === true)`.
- `verification-architecture.md:195` (PROP-105a) — schema extended; Tool/Method column adds the
  boolean-type structural check.
- `verification-architecture.md:202` — **new row, PROP-105h**: seed entries' `coLocatedWithCoordinator`
  is present, boolean, and `true` for both. Tier `0/1`.
- `verification-architecture.md:248` — **new row, PROP-305f**: every REQ-305 append sets
  `coLocatedWithCoordinator` to exactly `false`. Tier `0/2`.
- `verification-architecture.md:261` (PROP-403b) — enumeration rewritten to
  `citizens.filter(c.coLocatedWithCoordinator === true)`; worked examples retained but the invocation
  shape now cites `COORDINATOR_HOME` (shared fix with FIND-701).
- `verification-architecture.md:263` (PROP-403d) — Description and Tool/Method rewritten: "no code path...
  invokes `resolveEvmPrivateKey`/`resolveSolanaSecret` against a record with `coLocatedWithCoordinator
  === false`"; Tool/Method now requires confirming the enumeration is "genuinely constructed via
  `citizens.filter(c => c.coLocatedWithCoordinator === true)` — never any other predicate."
- `verification-architecture.md:82-101` (Tier 0 prose list), `:118-125` (Tier 1), `:136-155` (Tier 2),
  `:163` and `:370` (Tier 3 REQ-403 mentions) — all updated to reference the real
  `coLocatedWithCoordinator` field instead of an implicit "co-located" notion.
- Gate section `(1a)` (`:391-419`), `(8)` (`:533-541`), `(11)` (`:573-597`) — updated to require the
  adversary confirm the new field's seed values (PROP-105h), the append rule (PROP-305f), and the
  enumeration's real structural filter (PROP-403d), respectively.

---

## Cross-cutting verification performed

- Confirmed via `python3 json.loads()` that the revised seed JSON block in `behavioral-spec.md` still
  parses correctly and both entries carry `"coLocatedWithCoordinator": true`.
- Confirmed no markdown table row in either file was corrupted by the edits (line-by-line pipe-count
  sanity check across both files, 1955 + 606 total lines, zero suspicious rows).
- Confirmed the vague phrase `"sourced from a registry/coordinator constant"` / `<...own real $HOME>`
  now appears ONLY inside this iteration's own changelog/historical-description text (2 occurrences in
  `behavioral-spec.md`, both describing what the OLD text used to say) — zero live/binding occurrences
  remain in either spec.
- Confirmed `COORDINATOR_HOME` (10 + 12 occurrences), `coLocatedWithCoordinator` (23 + 34 occurrences),
  `PROP-403f` (4 + 7), `PROP-105h` (2 + 6), and `PROP-305f` (2 + 7) are each referenced in both the
  requirement body/schema AND the corresponding Tier list / Gate section of
  `verification-architecture.md` — no orphaned PROP ID.
- Did NOT touch `state.json`, any reviews manifest/verdict file, and did not commit/push, per the task's
  explicit instructions.
