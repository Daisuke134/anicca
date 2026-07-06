# P0 Adversarial Review — anicca-agent-economy

**Reviewer**: fresh VCSDD adversary, zero builder context, disk-only (+ 1 fresh `origin` fetch to check
live public-repo state for the secret-leak dimension). All commands re-run myself; no prior claim trusted
without independent reproduction.

**Reviewed against**: `.vcsdd/features/anicca-agent-economy/specs/SPEC.md` §1.2 + §3 P0.

**Artifacts inspected**:
- Worktree: `/Users/anicca/anicca/.worktrees/agent-economy` @ `361c736` (branch `feature/agent-economy`, clean, unpushed)
- Fresh clone: `Daisuke134/profitable-claude` (private) → `/private/tmp/.../scratchpad/p0-adv-clone/profitable-claude` @ `bb0ec62`
- Source repo live state: `/Users/anicca/anicca` `main` = `origin/main` = `898395f` (fetched fresh)

---

## Verdict summary

| Dimension | Verdict |
|---|---|
| isolation-complete | **PASS** |
| earn-intact | **PASS** |
| no-secret-leak | **FAIL** (critical, on the SOURCE repo's live public history — see below) |
| gate-correctness | **FAIL** (fail-open bug found, contradicts documented invariant) |
| test-integrity | **PASS** |
| no-dropped-coverage | **PASS** |

**P0 overall: NOT clean. 2 of 6 dimensions FAIL.** Neither is cosmetic — one is a live public credential
leak, the other is a correctness defect in the security-critical join gate itself.

---

## 1. isolation-complete — PASS

```
$ git -C /Users/anicca/anicca/.worktrees/agent-economy ls-files skills/human-funded
(empty)
$ ls skills/human-funded
ls: skills/human-funded: No such file or directory
```

Swept the whole worktree for lingering functional references, both literal (`skills/human-funded`) and
bare-segment (`human-funded`) forms. ~160 grep hits total; every one is either:
- an accurate comment describing the removal itself (`test_healthcheck_stale_fallback.sh:13`,
  `test_gig_run_shim_no_human_touch.py:6`: "skills/human-funded is now isolated to the private
  profitable-claude repo"),
- unrelated legitimate use of "human-funded" as the pre-existing funding-tier label (claude-p vs
  self-funded — `colony-status.sh`, `telemetry-collect.sh`, `THESIS.md`, `README.md`, dozens of
  `docs/superpowers/specs/*.md`) that has nothing to do with the removed skill directory, or
- stale, gitignored `__pycache__/*.pyc` (not tracked: `git ls-files skills/_shared/__tests__/__pycache__/`
  is empty; harmless, auto-regenerated, one `.pyc` is a leftover for a `.py` that no longer exists on disk
  but this predates/is orthogonal to P0).

`skills/registry.json` has **zero** `"dir"` fields pointing at the removed path (checked via JSON walk).
The 3 shared-infra files that DID reference the old path (`test_g2_static.py`, `step3_recipe.py`,
`test_gig_run_shim_no_human_touch.py`, `test_healthcheck_stale_fallback.sh`) were correctly and
surgically updated — see §6 below, no dangling reference remains in any of them.

## 2. earn-intact — PASS

```
$ ls skills/earn/
board-poller clip clip-producer clip-promote finchip-publish hl-trade
polymarket-trade sol-trade token-launch video x402-sell
(+ shared infra: README.md SKILL.md __tests__ _probe lib run.sh etc.)
```
All 11 required sub-skills present, untouched by the P0 diff (confirmed via `git diff main...HEAD --stat`
— zero touches under `skills/earn/`).

## 3. no-secret-leak — FAIL (critical, scope-adjacent but directly relevant)

**The destination clone itself is clean.** Independently scanned the fresh `profitable-claude` clone:
- `github-ai-creds.json`: 0 hits anywhere on disk or in full history (`git rev-list --objects --all`
  enumerated all 58 blobs ever committed to this repo; dumped every one with `git cat-file -p` and grepped
  for `password[:=]`, PEM/PGP headers, `ghp_`/`github_pat_` tokens, `mnemonic`, and 64-hex strings — zero
  matches, in working tree AND full history).
- `git log --all --diff-filter=A --name-only` for filenames matching `cred|secret|password|\.env|token`:
  zero results ever added.

**But the SOURCE repo (`Daisuke134/anicca`, PUBLIC, this worktree's own base) still leaks a live plaintext
credential in its pushed history, right now:**

```
$ cd /Users/anicca/anicca && git fetch origin main
$ git rev-parse origin/main          # 898395f (current, just fetched)
$ git branch -r --contains c561a4e
  origin/main
$ git show c561a4e:skills/human-funded/bounty/state/github-ai-creds.json
{
  "service": "github.com", "username": "anicca-earn",
  "email": "keiodaisuke+aiclaude@gmail.com",
  "password": "vZKgA9P1lx0fnX6Z9QjHVcAa9!",
  ...
}
```

Commit `898395f` ("security: untrack leaked github-ai-creds.json (password rotated...)") only **removes
the file going forward** — it is a plain deletion commit, not a history rewrite. `c561a4e` (the commit that
carries the file) is a confirmed ancestor of `origin/main` **right now** (freshly fetched, not stale local
state). Anyone who clones the public `Daisuke134/anicca` repo today can run
`git show c561a4e:skills/human-funded/bounty/state/github-ai-creds.json` and get this cleartext password.
Password rotation is claimed in the commit message but is unverifiable from disk; even if rotated, a public
secret-scanner / anyone browsing history still finds a live-looking credential.

**This directly contradicts the task tracker.** Mid-review, task #13 ("SEC: rotate leaked anicca-earn
GitHub password + purge from public history") flipped from `in_progress` to `completed` in the ambient
task list — but "purge from public history" is demonstrably NOT done: the blob is still reachable from
`origin/main` at this exact moment (re-verified via a fresh `git fetch`, not cached local refs). Marking
this task completed is premature. Purge requires `git filter-repo`/BFG + force-push + re-clone-everywhere,
none of which happened.

Note: `profitable-claude`'s own history does NOT contain this secret — its 3 commits ("import... scrubbed
of state/ + credentials") are fresh imports, not a `git filter-repo`-preserved migration of the original
anicca history as SPEC.md's stated method describes ("別 repo ... へ git filter-repo で履歴保持のまま移設").
That's actually the SAFER outcome here (it's why the credential didn't propagate into the new repo), but it
means the P0 "検証" line's claim of history-preserving migration doesn't literally hold for this destination
repo — a secondary, non-blocking spec-conformance note, dwarfed by the open leak on the source side.

## 4. gate-correctness — FAIL (fail-open bug, independently discovered)

Read `skills/_shared/lib/is-self-funded.mjs` in full and re-ran the checked-in suite
(`node --test .../is-self-funded.test.js`): **14/14 pass**. The (a) own-wallet, (b) own-funded-fuel, (c)
human-zero logic is correct and fails closed for every case the builder's own suite covers (null/undefined
agent, missing wallet, malformed wallet, missing fuel, unknown fuel provider, populated
`humanDependencies` array).

**Independent adversarial probing beyond the checked-in tests found a real fail-open defect:**

```js
$ node --input-type=module -e "
import { isSelfFunded } from './skills/_shared/lib/is-self-funded.mjs';
console.log(isSelfFunded({
  wallet: { evm: true },
  fuel: { provider: 'x402' },
  humanDependencies: 'oauth',   // malformed: string, not array
}));
"
true   // <-- WRONG. Should be false (fail-closed).
```

Root cause, `is-self-funded.mjs:46-52`:
```js
function humanDependencies(agent) {
  const deps = agent && agent.humanDependencies;
  return Array.isArray(deps) ? deps : [];   // <- malformed non-array silently becomes []
}
function hasNoHumanDependency(agent) {
  return humanDependencies(agent).length === 0;   // <- [] .length === 0 -> "no dependency" -> PASSES
}
```

When `humanDependencies` is present but malformed as anything other than an array (a string, an object,
a number), the helper silently coerces it to `[]` instead of denying. This means an agent that declares a
human dependency in a malformed shape is treated as if it declared none — the gate can return `true` for
an agent with a real, if mis-encoded, human dependency. This is the exact opposite of the module's own
documented contract (top-of-file comment: *"Fail-closed ... any missing/malformed/unrecognized field
DENIES the gate"*) and of what the money-safety invariant in SPEC.md §4 requires ("human-zero gate: ...
の全経路で human account/credential ... を要求しない").

Compare with the sibling checks in the same file: `hasOwnWallet()` and `fuelIsOwnFunded()` both correctly
treat a malformed shape as absent-and-therefore-denying (a malformed `wallet` or `fuel.provider` correctly
fails the gate — I verified `wallet: 'evm'` (string, not object) → `false`, `fuel.provider: {}` (object,
not string) → `false`). Only the `humanDependencies` leg has this asymmetric fail-open behavior, and no
test in the 14-case suite exercises a malformed (non-array, present) `humanDependencies` value — every
test either omits the field, or sets a well-formed array (empty or populated). This is a real coverage gap
that let a real bug through, not a hypothetical.

**Severity**: MAJOR for a security-critical join gate whose entire purpose is "does this agent depend on a
human." It requires a specific malformed-input shape to trigger (not the normal well-formed
empty/populated array paths that make up all real callers observed so far), so it is not an immediate
five-alarm fire, but it is exactly the kind of gap a fresh adversary is supposed to catch before a P0
security primitive is called "done."

**Fix required before PASS**: `humanDependencies()` should deny (return a non-empty sentinel, or the outer
`isSelfFunded` should explicitly check `Array.isArray(agent.humanDependencies ?? [])` and fail on non-array)
when the field is present but not an array — matching the same fail-closed pattern already used for
`wallet` and `fuel.provider`. Add a test case for it.

## 5. test-integrity — PASS

Re-ran everything myself (not trusting the builder's numbers):

- `node --test skills/_shared/lib/__tests__/*.test.js` → **59/59 pass**, 0 fail (7 files:
  identity-guard, is-self-funded, ledger, solana-verify, transfer, usdc, verify-tx).
- `bash skills/_shared/__tests__/test_healthcheck_stale_fallback.sh` → **15/15 pass** (clip,
  clip-promote, video × 5 scenarios each).
- `python3 -m pytest skills/_shared/__tests__/` → **507 passed, 7 failed**. All 7 failures are in
  `test_install_integration_darwin.py`, all with the same root cause:
  `stderr = b'anicca repo root mismatch: expected /Users/anicca/anicca, got
  /Users/anicca/anicca/.worktrees/agent-economy\n'`.

  Verified the builder's "pre-existing, unrelated" claim rather than accepting it: `git diff main --
  skills/_shared/__tests__/test_install_integration_darwin.py skills/_shared/install-proactive-plist.sh`
  is **byte-for-byte empty** (both files identical to `main`), AND re-ran the identical test file from the
  actual repo root (`/Users/anicca/anicca`, not the worktree) — **8/8 pass** there. This confirms the
  failure is a pure worktree-path artifact (the script/test pair hard-checks the repo root against a
  literal `/Users/anicca/anicca` path, which trips specifically when invoked from `.worktrees/*`), present
  identically on both branches, not a P0 regression. Claim CONFIRMED true, not just asserted.

## 6. no-dropped-coverage — PASS

Full diff-stat outside `skills/human-funded/` touches exactly 7 non-human-funded files. Checked each:

- `skills/_shared/lib/is-self-funded.mjs` + `.../__tests__/is-self-funded.test.js` — new, reviewed above.
- `skills/_shared/__tests__/test_gig_run_shim_darwin.py` — **deleted whole** (105 lines). Confirmed its
  target was hardcoded exclusively to the removed path (`RUN_SH = REPO_ROOT / "skills" / "human-funded" /
  "gig" / "run.sh"`, read from `main`'s copy) — this is not shared-infra, deletion is correct. Confirmed it
  (and its sibling `no-human-loop.test.mjs`) were carried into `profitable-claude` at
  `skills/human-funded/gig/__tests__/{test_gig_run_shim_darwin.py, test_gig_run_shim_no_human_touch.py,
  no-human-loop.test.mjs}` (per that repo's `bb0ec62`/`84b6c0e` "bring gig's ... test along" commits) — the
  coverage moved with the code it tests, it was not lost.
- `test_gig_run_shim_no_human_touch.py` — edited, not deleted: removed only the `RUN_SH`-specific
  parametrize entry + the `test_no_tmux_kill_in_run_sh` case (both gig-specific), kept the shared
  `OBSERVE_PY` (`proactive_observe.py`, used across all earn slots) check intact. Comment explicitly
  documents the split. Correct.
- `test_healthcheck_stale_fallback.sh` — edited: removed only the 3 human-funded `TARGETS[]` entries
  (bounty/affiliate/gig), kept the clip/clip-promote/video entries and the underlying marker-reseed
  regression test unchanged. 15/15 still pass (§5).
- `test_g2_static.py` + `step3_recipe.py` — both just replace the hardcoded reference to the removed skill
  path with a generic placeholder / empty-dict + explanatory comment; no assertions removed, the actual
  shared logic under test (`skill_writes_own_manifest`, `execute_recipe`) is unchanged and still exercised.

No shared-infra assertion was silently gutted; every reduction in test count is accounted for by code that
moved to `profitable-claude` along with an equivalent test.

---

## Bottom line

isolation / earn-intact / test-integrity / no-dropped-coverage are solid. The two FAILs are not
nitpicks: (1) a plaintext GitHub password for the "anicca-earn" account is still live and retrievable from
`Daisuke134/anicca`'s public, pushed `main` history right now — the task tracker's "completed" mark for
purging it is factually wrong as of this fetch — and (2) the P0 join gate itself, the literal
security-critical deliverable of this phase, has a fail-open bug on malformed `humanDependencies` input
that its own doc comment promises can't happen. Both are fixable without re-architecture, but P0 should not
be called done until both are closed and re-verified.
