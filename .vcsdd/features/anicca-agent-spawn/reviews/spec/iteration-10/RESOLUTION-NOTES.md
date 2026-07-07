# Resolution Notes — iteration-10 spec review (FIND-901)

**feature**: anicca-agent-spawn · **mode**: strict · **phase**: 1c (spec-review fix loop)
**input**: `reviews/spec/iteration-10/output/findings/FIND-901.json` (critical)
**files edited**: `specs/behavioral-spec.md`, `specs/verification-architecture.md`
**files NOT touched**: `state.json`, any `reviews/**/manifest*`/`verdict*` file (per instructions)

---

## FIND-901 (critical) — `citizens.json` placed inside the git working tree; versioned-seed vs.
live-append tension never reconciled

### What was wrong
REQ-103/REQ-105 placed the brand-new colony citizen registry, `citizens.json`, at a hardcoded path
INSIDE the `~/anicca` git working tree (`~/anicca/skills/self/spawn/registry/citizens.json`), and
REQ-105/REQ-305 specified that this SAME file is BOTH (a) seeded once with "a single, versioned JSON
registry file" of fixed literal data, AND (b) mutated forever after via live REQ-305 runtime appends
every time a spawn succeeds. Neither spec file ever addressed whether this file is git-tracked, or
reconciled the tension between "versioned seed file" and "live runtime append target" with this
project's own routine, frequently agent-automated `git pull`/`git checkout <branch>`/`git worktree
add|remove` operations on this exact `~/anicca` repo (per `CLAUDE.md`/`worktree.md`). This is exactly
the failure class — spawn-ledger-style live-mutating data stored in a volatile/tracked location instead
of a durable, out-of-tree state directory — that this project's OWN `state-path.js::resolveStateDir`
was built, tested, and is still actively used (`run.sh`) to prevent, one directory over from where
REQ-103 was adding `registry-path.mjs`.

### Investigation performed (real, fresh reads, this session)
- Read `~/anicca/skills/self/spawn/lib/state-path.js` in FULL (19 lines). Its header comment: "Durable
  state-dir resolution for the colony ledger (children.jsonl) + earn ledger. Fail-closed: REFUSE any
  /tmp-rooted path. The 2026-06 self-spawn E2E wrote children.jsonl to /tmp/spawn-live-state, which the
  OS tmp-cleaner deleted — the colony record was lost and the verifier could not reproduce it." Its
  export, `resolveStateDir({env, home})`, computes `env.ANICCA_STATE_DIR || \`${home}/.hermes/state\``
  and throws if the result is `/tmp`- or `/private/tmp`-rooted.
- Read `~/anicca/skills/self/spawn/run.sh` lines 35-50 (the real, current caller). Confirmed EXACTLY how
  it invokes the function and what it produces today:
  ```
  STATE_DIR="$("$NODE" -e '
    const { resolveStateDir } = require(process.argv[1] + "/lib/state-path");
    process.stdout.write(resolveStateDir({ env: process.env, home: process.env.HOME }));
  ' "$SKILL_DIR" 2>&1)" || { ...; exit 1; }
  COLONY="$STATE_DIR/children.jsonl"
  ```
  With `home=process.env.HOME` (this coordinator host's real `$HOME`, `/Users/anicca`) and no
  `ANICCA_STATE_DIR` override, this resolves to `STATE_DIR=/Users/anicca/.hermes/state` and
  `COLONY=/Users/anicca/.hermes/state/children.jsonl` — confirmed the REAL default location, not
  guessed. This is deliberately OUTSIDE the `~/anicca` git working tree.
- Read `~/anicca/.gitignore` (already cited in the finding's own evidence): its current patterns
  (`skills/*/state/`, `skills/*/*/state/`) do NOT match `skills/self/spawn/registry/` — confirming that,
  under the project's own current `.gitignore` rules, the previously-specified
  `skills/self/spawn/registry/citizens.json` path would be git-tracked by default.

### Fix approach
Split the ONE previously-specified `citizens.json` artifact into TWO distinct artifacts, exactly as the
finding's own guidance directs:
1. **A git-tracked SEED TEMPLATE** — `~/anicca/skills/self/spawn/registry/citizens.seed.json` —
   committed to git, read-only, NEVER mutated at runtime; defines the fixed literal 2-entry starting
   content REQ-105 already specified (unchanged content, new home for it).
2. **The actual LIVE, mutable runtime file** — resolved via `CITIZENS_REGISTRY_PATH`, exported from a
   new `~/anicca/skills/self/spawn/lib/registry-path.mjs` (alongside the pre-existing `COORDINATOR_HOME`
   constant), computed as `path.join(resolveStateDir({env, home}), 'citizens.json')` — REUSING, not
   reimplementing, `state-path.js`'s own `resolveStateDir` function, the SAME mechanism `run.sh` already
   uses for `children.jsonl`. Today this resolves to `~/.hermes/state/citizens.json`, alongside
   `~/.hermes/state/children.jsonl` — durable, out-of-git-tree, immune to `git checkout`/`git worktree
   add|remove`/`git pull` on `~/anicca`, and fail-closed against ever being `/tmp`-rooted.

On first access, if `CITIZENS_REGISTRY_PATH`'s file does not yet exist, it is initialized by copying
`citizens.seed.json`'s content VERBATIM — a one-time bootstrap, never an ongoing sync. Every subsequent
REQ-101 read and REQ-305 runtime append happens ONLY at the durable location; the git-tracked seed
template is never read from or written to again after that one-time bootstrap.

### Spec changes made

**`specs/behavioral-spec.md`**:
- Top-of-file revision line (lines 3-11): bumped "iteration 9" → "iteration 10", summarizing the
  two-artifact split and citing `resolveStateDir`/`run.sh`.
- New changelog section "## Changelog (iteration 9 spec review → iteration 10)" inserted immediately
  after the iteration-8→9 changelog and before "## Scope of this increment" — documents the real
  `state-path.js`/`run.sh`/`.gitignore` findings and the FIND-901 resolution, in this document's own
  established per-iteration table format.
- Purity boundary overview table (the "Colony citizen registry (data source for REQ-101)" row): SPLIT
  into two rows — "SEED TEMPLATE (git-tracked, read-only)" and "DURABLE RUNTIME FILE" — each citing its
  own real path/mechanism.
- REQ-103 ("Cross-instance spawn mutual exclusion"): the "Canonical `statePath`" subsection rewritten to
  designate the DURABLE runtime location (never the git-tracked seed template) as the lock's
  `statePath`, citing `resolveStateDir`/`run.sh`'s real, current usage by name; added a new Edge Case
  covering a concurrent git operation during a held lock/append.
- REQ-105 ("Colony citizen registry"): title extended to name the "two-artifact durable design"; new
  "Two-artifact design (resolves FIND-901)" paragraph inserted right after the opening EARS clause,
  describing both artifacts, the bootstrap-copy-once mechanism, and which requirements now cite the
  durable path; the seeding sentence ("THE SYSTEM SHALL seed...") corrected to name `citizens.seed.json`
  explicitly; two new Edge Cases (git-operation immunity; seed template never written) and three new
  Acceptance Criteria bullets (durable-path construction check; live git-operation test; seed-template
  write-grep check) added, citing PROP-105j/PROP-105k.
- REQ-305 ("Deploy/spawn failure handling"): the append-target citation corrected to the durable
  `CITIZENS_REGISTRY_PATH` (never the seed template, never `colony-wallets.json`); one new Edge Case
  (concurrent git operation during an append) and one new Acceptance Criteria bullet (append always
  targets `CITIZENS_REGISTRY_PATH`; a fixture append produces zero git working-tree changes) added.
- REQ-403 ("Wallet mutual non-interference audit"): the registry citation in the EARS clause corrected
  to explicitly name the durable runtime file, never the seed template.
- The "Spawn ledger append" purity-overview row corrected to cite the durable location.
- All remaining `citizens.json` mentions throughout the document were checked (37 occurrences); the ones
  describing schema/content generically were left as-is (now correctly disambiguated by REQ-105's own
  two-artifact section, which every later mention implicitly follows); historical changelog entries
  (iteration 1→2, iteration 2 round 1→2) describing what was true AT THOSE iterations were left
  untouched, per this document's own established convention of never rewriting past changelog entries.

**`specs/verification-architecture.md`**:
- Top-of-file revision line: bumped to "iteration 10", summarizing the fix and the two new proof
  obligations.
- Purity Boundary Map: the single `citizens.json` row SPLIT into two rows (seed template; durable
  runtime file), plus a NEW row for `state-path.js::resolveStateDir` itself (existing, reused
  unmodified, cited here for the first time in this file). The `lock.mjs` row and the
  `registry-path.mjs::CITIZENS_REGISTRY_PATH`/`COORDINATOR_HOME` row both corrected to name the durable
  location and its `resolveStateDir`-based construction explicitly.
- Proof Obligations table: PROP-105a/c/e's descriptions corrected to name `citizens.seed.json`
  specifically where they test seed CONTENT; PROP-105d broadened to cover both artifacts explicitly.
  Two NEW rows added immediately after PROP-105i (before PROP-106a):
  - **PROP-105j** (Tier 0): the git-tracked seed template is never written to by any runtime code path.
  - **PROP-105k** (Tier 0 + Tier 2): `CITIZENS_REGISTRY_PATH` always routes through `resolveStateDir`
    (never a literal in-tree path); a real `git checkout`/`git worktree add`/`git pull` on `~/anicca`
    does not affect the durable `citizens.json`'s content (live test, no mock).
- The ledger-append row (`ledger.js::appendChild`) corrected to cite the durable location for REQ-305's
  registry-append side effect.
- Verification Strategy section: Tier 0 bullet extended to mention PROP-105j/PROP-105k's structural
  halves; Tier 2 bullet extended to mention PROP-105k's live git-operation test.

### What was deliberately left unchanged (and why)
- The registry record SCHEMA itself (`{id, wallet, walletAddress, fuel, humanDependencies, homeDir,
  coLocatedWithCoordinator}`) is UNCHANGED — this finding is about WHERE the file lives and how it is
  bootstrapped, not what it contains. No REQ-101/REQ-403 consumer logic changes.
- `~/anicca/skills/self/spawn/lib/state-path.js` and `run.sh` themselves are UNTOUCHED (existing, reused
  unmodified) — this feature only calls the already-exported `resolveStateDir` function; it does not
  modify it.
- Historical changelog entries from iterations 1-2 that describe the (then-correct, since-superseded)
  single-artifact design were left as literal historical record, per this document's own established
  convention (every prior iteration's changelog does the same for its own since-corrected claims) — the
  new iteration-10 changelog entry explicitly documents what changed and why.

### Verdict for this finding
**Fully resolved by design/spec edit, grounded in a fresh, real read of `state-path.js`/`run.sh` this
session** (not a guess at the default path). Phase 2 will implement `registry-path.mjs` calling the
already-real `resolveStateDir`, and the bootstrap-copy-once logic; Phase 3 (`vcsdd-adversary`) should
independently confirm PROP-105j (grep) and PROP-105k (live git-operation test) against the real
implementation once it exists.

---

## Process notes
- `state.json` and all `reviews/**` manifest/verdict files were left untouched, per instructions.
- No commit/push was performed, per instructions.
- Both spec files' internal changelogs and revision headers were updated to iteration 10, following
  this document's own established per-iteration self-documentation convention.
