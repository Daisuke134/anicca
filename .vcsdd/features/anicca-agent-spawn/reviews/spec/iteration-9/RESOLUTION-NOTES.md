# Resolution Notes — iteration-9 spec review (FIND-801, FIND-802)

**feature**: anicca-agent-spawn · **mode**: strict · **phase**: 1c (spec-review fix loop)
**input**: `reviews/spec/iteration-9/output/findings/FIND-801.json` (critical), `FIND-802.json` (major)
**files edited**: `specs/behavioral-spec.md`, `specs/verification-architecture.md`
**files NOT touched**: `state.json`, any `reviews/**/manifest*`/`verdict*` file (per instructions)

---

## FIND-801 (critical) — PROP-105g's re-derivation tool was EVM-only, no Solana method

### What was wrong
PROP-105g's only named re-derivation tool, `viem`'s `privateKeyToAccount`, is a secp256k1/EVM-only
function. Franklin's seeded registry record is Solana-only (`walletAddress: {solana:
"8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9"}`, no `evm` field), and REQ-202 makes a Solana wallet
the norm — not the exception — for every future Nosana-path child. The proof obligation was therefore
structurally inapplicable to half the colony's real citizens and to the feature's own common future
case.

### Investigation performed (real, cited)
- Read `~/anicca/skills/earn/lib/resolve-identity.mjs::resolveSolanaSecret` (lines 115-138) and its
  `readRawSecretFile` helper (lines 39-46) in full: `resolveSolanaSecret` returns exactly what
  `readRawSecretFile` returns — `fs.readFileSync(filePath, 'utf8').trim()` — a bare base58-encoded
  STRING, no JSON wrapper, no byte array. This is the real, current, on-disk format of
  `~/.blockrun/.solana-session`.
- Read `~/anicca/runtime/dashboard/telemetry-post-franklin.mjs` (lines 1-23): this file ALREADY reads
  this SAME file and converts it to Solana Keypair-compatible bytes via `bs58.decode(secretB58)`,
  producing a 64-byte value — its own comment confirms: `"64 bytes: tweetnacl secretKey format ==
  Solana Keypair.secretKey"`. This is the exact, already-proven, already-working conversion pattern in
  this codebase — not invented for this fix.
- Read `~/anicca/package.json`: confirmed `"@solana/web3.js": "^1.98.4"` is ALREADY a real dependency
  (no new dependency added to satisfy this finding).
- Read `~/anicca/runtime/package.json`: confirmed `"bs58": "^5.0.0"` is ALREADY a real dependency,
  already imported by `telemetry-post-franklin.mjs` (also no new dependency).
- Confirmed via `find`/`ls` that `bs58` is physically present at
  `~/anicca/runtime/node_modules/bs58` (already installed), and that `@solana/web3.js` is NOT currently
  installed anywhere in this repo's own `node_modules` (declared in `package.json` but not yet
  `npm install`-ed at the repo root) — so the LIVE check below used a disposable scratch install
  outside the repo, never touching/modifying the repo's own `package.json`/`package-lock.json`/
  `node_modules`.

### Live re-derivation actually performed (not hypothetical)
Installed `@solana/web3.js@^1.98.4` + `bs58@^6.0.0` to a scratch directory
(`/private/tmp/claude-501/.../scratchpad/solana-verify/`, outside this repo) and ran:

```js
import fs from 'node:fs';
import bs58 from 'bs58';
import { Keypair } from '@solana/web3.js';
const raw = fs.readFileSync(process.env.HOME + '/.blockrun/.solana-session', 'utf8').trim();
const secretKeyBytes = bs58.decode(raw);
const keypair = Keypair.fromSecretKey(secretKeyBytes);
console.log('derived-address:', keypair.publicKey.toBase58());
```

Output: `derived-address: 8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9` (secretKeyBytes.length: 64) —
an EXACT match against Franklin's seeded `walletAddress.solana` in `citizens.json`'s seed array. The
raw secret bytes were never printed/logged, only the derived public address (matching this spec's own
established secrets-handling discipline). This was run live, 2026-07-07, in this session — not
fabricated.

### Spec changes made
**`specs/behavioral-spec.md`**:
- Lines 703-739 (new paragraph inserted after the existing automaton-only FIND-601 worked example,
  before the JSON seed block): added the full FIND-801 correction — explains why `viem` is EVM-only,
  names `@solana/web3.js::Keypair.fromSecretKey` + `.publicKey.toBase58()` as the Solana-equivalent
  tool, cites the exact real byte-format derivation (`bs58.decode()` of the raw base58 string,
  confirmed via `readRawSecretFile`), cites both dependencies as already-real (no new dependency), and
  states the live-performed result (`8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`, exact match).
- Lines 741-745: PROP-105g's binding rule restated as explicitly two-branch (EVM via
  `viem::privateKeyToAccount` against `walletAddress.evm`; Solana via
  `@solana/web3.js::Keypair.fromSecretKey` against `walletAddress.solana`; both independently if both
  populated).
- Lines 854-868 (REQ-105 Acceptance Criteria, the bullet resolving FIND-601): rewritten to state the
  two-branch method explicitly and to demote "a live on-chain balance query" from an acceptable
  alternative to, at most, an ADDITIONAL corroboration — never a substitute, since it does not prove
  derivation-correctness (this directly addresses FIND-801's secondary critique that the prior
  balance-query escape hatch was never elaborated).
- New changelog section "## Changelog (iteration 8 spec review → iteration 9)" inserted at line 133
  (before "## Scope of this increment"), documenting both findings' resolutions in the doc's own
  established per-iteration table format.
- Top-of-file revision line (lines 3-10) updated from "iteration 8" to "iteration 9", listing
  FIND-801/802 as resolved.

**`specs/verification-architecture.md`**:
- PROP-105g table row (originally single-branch EVM-only) rewritten to a two-branch description
  (Description + Tool/Method columns), citing the same real dependencies/derivation and the live
  Franklin result.
- New table row **PROP-105i** added immediately after PROP-105h: covers the conjunctive requirement
  that a citizen with BOTH `walletAddress.evm` and `walletAddress.solana` populated (REQ-202's expected
  Nosana-path shape) must pass BOTH branches independently — a mismatch on either chain fails the whole
  check; includes Tier 0 (never short-circuits) and Tier 2 (three-fixture: both-match/EVM-mismatch/
  Solana-mismatch) proof requirements.
- Tier 0 / Tier 1-2 "Verification tiers" convention section and the separate "Verification Strategy"
  section (both pre-existing parallel listings in this file) updated to mention the two-branch method
  and PROP-105i in each of their Tier-0/Tier-2 bullet lists.
- Gate section (item 1a) updated to require the adversary confirm re-derivation for EVERY populated
  chain (conjunctively, per PROP-105i), name the correct chain-specific tool, and reject a live balance
  query as a standalone substitute.
- Top-of-file revision line updated to "iteration 9", with a summary of the FIND-801 fix and an
  explicit note that this file's own FIND-802 exposure was nil (see below).

### Verdict for this finding
**LIVE-CONFIRMED, not merely specified.** The Solana re-derivation was actually run in this session
against Franklin's real `~/.blockrun/.solana-session` file and produced an exact match. Phase 2 will
implement the actual re-derivation script/test using the real, already-available dependencies
identified here; Phase 3 (`vcsdd-adversary`) should independently re-run this same check against the
real script once it exists.

---

## FIND-802 (major) — literal hardcoded HOME value appeared before its own constant definition

### What was wrong
`COORDINATOR_HOME` was formally defined only in REQ-403 (behavioral-spec.md, iteration 8), but the
literal value it represents (`/Users/anicca`) was used, unexplained, in REQ-105's own worked example
(which appears EARLIER in the document) and in REQ-403's own "Seed-data correction" subsection — both
BEFORE the constant's definition in reading order. Additionally, one Acceptance Criteria bullet in
REQ-403 (originally ~line 1944) already correctly used `COORDINATOR_HOME`, while a LATER bullet in the
SAME Acceptance Criteria list (originally ~line 1945-1951) still hardcoded the literal — an internal
inconsistency within one requirement.

### Fix approach
Per the finding's own guidance: moved `COORDINATOR_HOME`'s formal definition UP into REQ-105 — the
first point in the document's reading order that needs to express "the coordinator host's own real
`$HOME`" as a worked-example value (behavioral-spec.md, new paragraph at lines 779-796, inserted
immediately after REQ-105's `homeDir`-is-already-resolved sentence and immediately before the
FIND-501 worked-example paragraph that first needs the symbol). The literal's current real value
(`/Users/anicca`) is now stated exactly ONCE, parenthetically, at this one definition point (line 791)
— every other use in the document is now the symbol `COORDINATOR_HOME`.

REQ-403's own former "Canonical coordinator-HOME constant" paragraph (previously a full, second
re-definition) was replaced with a short pointer paragraph that references REQ-105's earlier
definition instead of re-stating it (behavioral-spec.md, ~line 1939-1946 post-edit).

### Every literal `/Users/anicca` occurrence in a "coordinator's own HOME, passed as `env.HOME`" sense
was converted to `COORDINATOR_HOME`, specifically:
- `specs/behavioral-spec.md` REQ-105's own FIND-501 worked example (originally lines ~731-736,
  now ~810-813): `env: {HOME: '/Users/anicca', ...}` → `env: {HOME: COORDINATOR_HOME, ...}` (both the
  `resolveEvmPrivateKey` and `resolveSolanaSecret` invocations).
- `specs/behavioral-spec.md` REQ-403's "Seed-data correction" subsection (originally lines ~1828-1841,
  now ~1914-1930): the same `env.HOME` literal fixed in both the abstract (`citizen.homeDir`-shaped)
  and concrete (today's real values) invocation examples.
- `specs/behavioral-spec.md` REQ-403's Acceptance Criteria — the internally-inconsistent bullet
  (originally ~lines 1944-1951, now ~lines 2021-2032): fixed to use `COORDINATOR_HOME`, matching the
  earlier bullet in the same list (originally ~line 1934, now ~line 2011) that already used it
  correctly — the inconsistency is explicitly called out and resolved in the bullet's own text.
- The "Explicit-env correction" paragraph's own cross-reference phrase ("canonical,
  `os.homedir()`-derived constant defined immediately above") was corrected to "REQ-105 above defines"
  since the definition itself moved.

### What was deliberately left unchanged (and why)
- The real seed-data JSON block (`citizens.json`'s literal `homeDir` values, e.g.
  `"/Users/anicca/.anicca"`, `"/Users/anicca/.blockrun"`) was left as literal, real, already-resolved
  path strings — REQ-105 elsewhere explicitly requires `homeDir` to be an ALREADY-RESOLVED absolute
  path, never an unresolved template (resolves FIND-202); writing it as a template string
  (`${COORDINATOR_HOME}/.anicca`) would contradict that existing, correct requirement. This is legitimate
  real seed data, not the "coordinator's bare HOME, independently hardcoded at a call site" hazard
  FIND-802/FIND-701 target.
- Prose describing the OLD, WRONG, historical seed data (e.g. "an earlier revision... stored the SAME
  bare `$HOME` value (`/Users/anicca`) for BOTH citizens") was left as literal — this is historical,
  dated changelog narration of a specific past defect (the same convention every other iteration's
  changelog in this document already uses to cite exact historical literal values for auditability),
  not a current worked-example invocation a Phase-2 implementer would copy.
- Real evidence file-path citations (e.g. `/Users/anicca/.automaton/wallet.json`,
  `/Users/anicca/.blockrun/.solana-session`) were left as literal — these cite real, concrete evidence
  paths on disk, not the coordinator's bare `$HOME` value.

### `specs/verification-architecture.md` exposure
A full grep confirmed this file's own `PROP-403b` row and all other `env.HOME` mentions ALREADY used
`COORDINATOR_HOME` consistently (no literal-before-definition ordering problem in this file) — its
Purity Boundary Map row for `registry-path.mjs::COORDINATOR_HOME` (near the top of the file, before
`PROP-403b`'s use) already served as this file's own definition point, in correct reading order. No
FIND-802-class fix was needed in this file; the top-of-file revision header was updated only to note
this and to record the iteration bump.

### Verdict for this finding
**Fully resolved by inspection/edit** — no live execution needed for a prose reading-order fix. A
fresh grep of both spec files for the literal `/Users/anicca` (reproduced below) confirms every
remaining occurrence is one of: (a) the one definition-point statement, (b) real, already-resolved seed
data, (c) historical changelog narration of a past defect, or (d) a real evidence file-path citation —
never an un-pinned, independently-hardcoded "coordinator's own HOME" value used ahead of its own
definition.

---

## Process notes
- `state.json` and all `reviews/**` manifest/verdict files were left untouched, per instructions.
- No commit/push was performed, per instructions.
- Both spec files' internal changelogs and revision headers were updated to iteration 9, following this
  document's own established per-iteration self-documentation convention (every prior iteration did the
  same for its own findings) — this keeps the spec's own history internally consistent rather than
  leaving an orphaned patch.
