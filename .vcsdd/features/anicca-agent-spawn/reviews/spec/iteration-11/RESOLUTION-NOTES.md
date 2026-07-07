# Resolution Notes — spec review iteration-11 (FAIL, 2 findings) → iteration-12 candidate

**Findings resolved**: FIND-1001 (critical), FIND-1002 (major)
**Files edited**: `specs/behavioral-spec.md`, `specs/verification-architecture.md`
**Not touched** (per instructions): `state.json`, reviews manifest/verdict files; no commit/push performed.

---

## FIND-1001 (critical) — bootstrap-copy TOCTOU race → atomic exclusive-create

**Root cause confirmed by re-reading `~/anicca/skills/economy/gig/lib/lock.mjs` in full**
(`tryCreateLockFile`, lines 108-117 of that file): the module's own header comment (lines 1-13)
documents a REAL prior double-pay bug — two concurrent `gig_verify_and_pay(true)` calls both observed
status `'delivered'` before either wrote back, and both settled a real on-chain payout, because the
check ("is this already paid?") and the act ("pay it") were two separate, non-atomic steps. The fix
already adopted there is POSIX exclusive-create (`fs.open(file, "wx")` = `O_CREAT|O_EXCL`), which is
atomic even across separate OS processes: `true` = caller now holds the resource, `false` (`EEXIST`) =
someone else already does. REQ-105's bootstrap step had the IDENTICAL shape of bug this pattern exists
to prevent — a plain "IF the file does NOT yet exist, THEN copy" check-then-act sequence — and no
proof obligation (PROP-105j/PROP-105k) ever exercised a concurrent-bootstrap or late-bootstrap-vs-append
race.

### Edits made — `specs/behavioral-spec.md`

1. **Header revision line** (top matter, now lines 4-19): bumped `iteration 10` → `iteration 11` and
   appended a paragraph naming both findings and their resolutions, so the document's own revision
   history stays self-describing.

2. **New changelog section**, `## Changelog (iteration 10 spec review → iteration 11)` — inserted at
   **line 185** (heading), running through **line 191** (the two-row Finding/Severity/Resolution table
   for FIND-1001/FIND-1002), immediately after the existing FIND-901 changelog row (**line 183**) and
   before "## Scope of this increment (read first)". Documents both FIND-1001 and FIND-1002 in the same
   table format every prior iteration uses, grounded in the fresh re-read of
   `lock.mjs::tryCreateLockFile`.

3. **FIND-901's own changelog row** (**line 183**, in the iteration-9→10 changelog table) gained a
   trailing bracketed note: `**[iteration 11 correction, FIND-1001]: this iteration's "on first access,
   IF the file does NOT yet exist, copy" framing was itself a check-then-act (TOCTOU) race — see the
   iteration 11 changelog and REQ-105's corrected, ATOMIC exclusive-create bootstrap below.]**` — so a
   reader following FIND-901's history is pointed forward to the correction rather than reading stale,
   now-superseded framing as if it were still current.

4. **REQ-105's core "One-time bootstrap" paragraph** — the primary fix, now at **lines 714-751**
   (originally lines 689-695 pre-edit; the replacement text is substantially longer). Replaced the
   check-then-act EARS clause:

   > "on first access, IF `CITIZENS_REGISTRY_PATH`'s file does NOT yet exist, THE SYSTEM SHALL initialize
   > it by copying `citizens.seed.json`'s content VERBATIM"

   with an EARS clause specifying a single atomic POSIX exclusive-create operation
   (`fs.open(path, 'wx')` / `O_CREAT|O_EXCL`), explicitly modeled on `tryCreateLockFile`, with three
   sub-cases: (a) exclusive-create succeeds → bootstrap winner, seed content written verbatim; (b)
   exclusive-create fails with `EEXIST` → THE SYSTEM SHALL NOT write anything, and SHALL simply read the
   existing file as-is (covers BOTH "another racer already bootstrapped" AND "a real REQ-305 append
   already happened"); (c) any other failure → fails closed, mirroring `tryCreateLockFile`'s own
   contract. Explicitly states "THE SYSTEM SHALL NEVER perform a separate 'check if the file exists,
   then copy' sequence — existence and creation SHALL be the SAME atomic filesystem call, never two."
   Ends at line 751, citing PROP-105l (new) for the concurrent-race and late-append proof obligations
   this correction adds.

5. **REQ-105 Edge Cases** — two new bullets added at **lines 998-1011**, immediately after the existing
   FIND-901 git-operation edge cases and before "**Acceptance Criteria**:":
   - Lines 998-1006: two simulated "first access" callers race the bootstrap exclusive-create within the
     same millisecond → exactly ONE succeeds, the other fails `EEXIST` and reads-only, never overwrites,
     never double-writes.
   - Lines 1007-1011: a real REQ-305 append has already happened BEFORE a late/slow bootstrap attempt's
     exclusive-create call ever runs → the late caller's exclusive-create fails `EEXIST` and the
     already-appended record survives untouched.
   Both cite PROP-105l.

6. **REQ-105 Acceptance Criteria** — two new bullets added at **lines 1032-1042**, immediately after
   the existing PROP-105j/PROP-105k structural-check bullet (which ends "...(PROP-105j)."):
   - Lines 1032-1035: a structural/Tier-0 bullet — the bootstrap step is a single atomic exclusive-create
     call, with a structural check confirming no separate `fs.existsSync`/`fs.stat`-then-`fs.writeFile`
     check-then-act pair exists for this step (PROP-105l, structural half).
   - Lines 1036-1042: a live/Tier-2 bullet — the two concrete fixtures (concurrent-race;
     late-bootstrap-after-real-append) that must both pass (PROP-105l, live half) — this is the literal
     fixture pair the finding requested.

7. **COORDINATOR_HOME paragraph** in REQ-105 (originally lines 867-884; the sentence citing PROP-105m
   was appended at what is now **line 941**, immediately after "...reads anywhere else in this feature's
   audit-script code path.") gained one added sentence citing PROP-105m and the corrected purity
   classification (see FIND-1002 below) — added while already in this neighborhood of REQ-105 for the
   FIND-1002 fix, not a separate pass.

### Edits made — `specs/verification-architecture.md`

1. **Header revision line** (top matter, lines 1-19): bumped `iteration 10` → `iteration 11`, with a
   prose paragraph describing both fixes (mirrors `behavioral-spec.md`'s header addition), so both spec
   files' own revision headers stay in sync.

2. **Purity Boundary Map row** for the durable `CITIZENS_REGISTRY_PATH` file (the "Effectful Shell
   (BRAND NEW, dedicated, durable, OUT-OF-GIT-TREE...)" row, **line 82**): inserted a
   "**Corrected, resolves FIND-1001 (critical):**" clause describing the atomic exclusive-create
   bootstrap and citing PROP-105l, replacing the prior unqualified "Bootstrapped ONCE from
   `citizens.seed.json`'s content verbatim if the file is absent" phrasing with the corrected,
   race-free mechanism.

3. **Proof Obligations table** — new row **PROP-105l** inserted at **line 250** (immediately after the
   existing PROP-105k row, before PROP-106a), Tier `0/2`, `Required: true`. Tier-0 half: structural read
   confirming the bootstrap implementation performs exactly one `fs.open(..., 'wx')`-equivalent call
   (or its `EEXIST` catch + read-fallthrough), never a separate exists-check-then-write pair. Tier-2
   half: the two concrete fixtures verbatim — (1) concurrent-race (two racers, exactly one succeeds,
   the other reads-only) and (2) late-bootstrap-after-real-append (a real REQ-305 append precedes a
   late bootstrap attempt, which fails `EEXIST` and never overwrites).

4. **Verification Strategy — Tier 0 list**: added a clause at **lines 332-337** (immediately after the
   existing PROP-105k structural-half mention, ending "...the binding live-git-operation test is Tier 2,
   below);"), citing PROP-105l's structural half (lines 332-334) and cross-referencing that the binding
   fixtures are Tier 2, and PROP-105m's structural half (lines 335-337).

5. **Verification Strategy — Tier 2 list**: added a clause at **lines 411-419** (immediately after the
   existing PROP-105k live-half mention), spelling out both PROP-105l fixtures (concurrent-race;
   late-bootstrap-after-real-append, lines 411-415) and PROP-105m's live half (lines 416-419) in the
   Tier-2 integration-test list.

---

## FIND-1002 (major) — `registry-path.mjs` mislabeled "Pure Core"

**Root cause confirmed**: `verification-architecture.md`'s own Purity Boundary Map already classifies
`resolveStateDir` (line 83) as "Effectful Shell (existing, reused unmodified)" two rows away from the
`registry-path.mjs` row (originally line 90, labeled "Pure Core (new, two constants)"). Since
`CITIZENS_REGISTRY_PATH = path.join(resolveStateDir({env, home}), 'citizens.json')` is built directly
from that same Effectful function, and `COORDINATOR_HOME` is built from Node's `os.homedir()` (a real
OS/environment read, confirmed by REQ-105's own text, `behavioral-spec.md` line 933ish: "computed
EXACTLY ONCE, at module-load time, via Node's `os.homedir()`"), the "Pure Core" label directly
contradicted the document's own stated convention.

### Edits made — `specs/verification-architecture.md`

1. **Purity Boundary Map row** for `registry-path.mjs::CITIZENS_REGISTRY_PATH`/`::COORDINATOR_HOME`
   (**line 90**): relabeled from `**Pure Core (new)**` / `PURE (new, two constants)` to
   `**Effectful Shell (new — corrected, resolves FIND-1002, major)**` / `EFFECTFUL (new, two
   constants)`, with a new lead sentence in the Notes column explaining the correction (built from
   `resolveStateDir`, already Effectful two rows above, and `os.homedir()`, a real environment read) and
   citing the new PROP-105m for the missing Tier-2 proof this correction requires.

2. **Proof Obligations table** — new row **PROP-105m** inserted at **line 251** (immediately after the
   new PROP-105l row), Tier `0/2`, `Required: true`. Tier-0 half: structural read confirming
   `COORDINATOR_HOME` is implemented as a direct `os.homedir()` call at module-load time, never a
   hardcoded literal or `process.env.HOME` substitute. Tier-2 half: (1) in the same test process,
   independently call `os.homedir()` and assert equality with the imported constant (no drift/caching
   bug); (2) invoke `registry-path.mjs` in a real child process launched with a DIFFERENT real `HOME`
   value and assert that process's own `COORDINATOR_HOME` reflects ITS OWN `os.homedir()` output — never
   the original coordinator host's cached value — proving genuine environment-coupling.

3. **Verification Strategy — Tier 0 list**: added a clause citing PROP-105m's structural half
   (confirms `os.homedir()` implementation, never a literal/`process.env.HOME` substitute).

4. **Verification Strategy — Tier 2 list**: added a clause citing PROP-105m's live half (the
   different-real-`HOME`-child-process test proving genuine Effectful environment-coupling).

### Edits made — `specs/behavioral-spec.md`

1. **COORDINATOR_HOME definition paragraph** in REQ-105 (the paragraph ending "...See PROP-403f for the
   corresponding structural check..."): appended one new sentence, "**Purity note (resolves FIND-1002,
   major):** because `COORDINATOR_HOME` is a real read of ambient OS/environment state (`os.homedir()`)
   and `CITIZENS_REGISTRY_PATH` (above) is built from `resolveStateDir`, `registry-path.mjs` is
   classified 'Effectful Shell' in `verification-architecture.md`'s Purity Boundary Map, never 'Pure
   Core' — ... see PROP-105m for the Tier-2, real-environment-dependent proof this correction adds."
   This keeps `behavioral-spec.md` internally consistent with the corrected `verification-architecture.md`
   classification, since `behavioral-spec.md` is where `COORDINATOR_HOME` is originally defined
   (REQ-105, per the FIND-802 relocation from a prior iteration).

---

## New proof-obligation IDs introduced (PROP-XXX-lettersuffix convention preserved)

| ID | REQ | Tier | Resolves |
|---|---|---|---|
| PROP-105l | REQ-105 | 0/2 | FIND-1001 (critical) — atomic exclusive-create bootstrap, concurrent-race + late-append fixtures |
| PROP-105m | REQ-105 | 0/2 | FIND-1002 (major) — `COORDINATOR_HOME` real-environment-coupling proof (corrects the Pure-Core mislabeling) |

## Markdown table integrity check performed

After editing, both spec files' markdown tables (`| FIND-... |` changelog rows, `| PROP-... |` proof
obligation rows, `| **...** |` Purity Boundary Map rows) were verified to have a uniform, correct
unescaped-pipe count per row (4 for `FIND-` rows, 7 for `PROP-` rows, 5 for Purity Map `**` rows) — two
literal, unescaped `O_CREAT|O_EXCL` occurrences that had been introduced inside table cells (one in each
spec file) were found and corrected to the escaped `O_CREAT\|O_EXCL` form (matching this document's own
existing convention, e.g. `git worktree add\|remove`), so no table row is broken into a phantom extra
column.

## Not changed

- `state.json`, reviews manifest/verdict files — untouched, per instructions.
- No `git add`/`commit`/`push` performed.
- No other findings, requirements, or proof obligations were touched beyond what FIND-1001/FIND-1002
  required — REQ-101 through REQ-403's other content, and all other Purity Boundary Map rows/Proof
  Obligation rows, are byte-identical to the pre-iteration-11 state.
