# A-self-spawn skill — implementation plan (DONE)

Spec: `docs/superpowers/specs/2026-06-16-A-self-spawn-skill-design.md`. TDD with `node:test`. All
tasks complete; this file records what was built + how it was verified.

## Tech stack
- Pure decision/derivation: CommonJS `.js` (repo root has no `package.json` -> CJS default, no marker needed).
- Tests: `node:test` (zero new dep).
- Entrypoint: bash `run.sh` orchestrating the pure libs via `node -e`, `jq`, `curl`, `openssl`.

## Tasks
- [x] **T1 — decision core (RED->GREEN)**: `lib/spawn-decision.js` `decideSpawn(...)`. Tests:
  `lib/__tests__/spawn-decision.test.js` (11 cases: threshold boundary, rate-limit window, max-children
  cap, order of checks, malformed rows, non-numeric balance).
- [x] **T2 — child-spec (RED->GREEN)**: `lib/child-spec.js` `nextChildId` (gap-safe, zero-padded) +
  `buildChildSpec` (refuses parent==child wallet, requires every field). Tests: `child-spec.test.js` (7 cases).
- [x] **T3 — ledger (RED->GREEN)**: `lib/ledger.js` `appendChild`/`readChildren` (jsonl, mkdir -p,
  ENOENT->[], blank-line tolerant). Tests: `ledger.test.js` (5 cases).
- [x] **T4 — entrypoint**: `run.sh` (load env -> read balance+ledger -> decideSpawn -> on eligible:
  gen child wallet + AgentMail inbox + provisional ledger + DO/Akash provision + print verifiable facts).
  `--dry-run` = gate-only, zero side effects. `bash -n` clean.
- [x] **T5 — reuse**: `scripts/gen-wallet.sh` copied from the proven archived spawn-child colony script
  (secp256k1 keypair -> 600-perm JSON). `SKILL.md` documenting gate/flow/verify/no-human-in-loop.

## Self-test (run in this session)
```
node --test skills/self/spawn/lib/__tests__/*.test.js   # 22 pass / 0 fail
bash -n skills/self/spawn/run.sh                          # syntax OK
bash run.sh --dry-run (no wallet)        -> eligible:false low_balance, no side effects
bash run.sh --dry-run (funded, 0 kids)   -> eligible:true ok, no children.jsonl written
bash run.sh --dry-run (1 recent child)   -> eligible:false rate_limited
```

## Out of scope (separate work)
- Flipping the `self/spawn` registry slot to `"live"` (Foundation, after runtime E2E — collision rule).
- Real DO/Akash spend E2E (needs a funded parent wallet; gated correctly, dry-run proves the gate).
- The `self/issue-dev` slot (separate skill; this PR delivers `self/spawn`).
