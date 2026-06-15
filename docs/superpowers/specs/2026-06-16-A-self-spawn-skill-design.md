# A-self-spawn skill — design spec

2026-06-16. Track A builder "self-spawn". Implements spec26 A4 / spec27 §2 WF-A **A-self-spawn**:
`skills/self/spawn` births a child Anicca on DO/Akash with its own wallet + own AgentMail inbox; the
child runs its own earn wake without parent instruction.

Canonical product spec: `anicca-project/docs/superpowers/specs/anicca/{26,27}`. This is the OSS-repo
(`~/anicca`) implementation spec for the reserved registry slot `self/spawn` (entrypoint `run.sh`).

## §1 Goal (verifiable)
`bash skills/self/spawn/run.sh` on a profitable parent → a REAL child instance is provisioned with a
DISTINCT wallet + DISTINCT AgentMail inbox, recorded in `state/children.jsonl`. Per spec27 the live
verifier checks: child droplet active + parent≠child wallet addr + new instance appears on /dashboard
(the child POSTs telemetry from its own report skill, which already exists and is LIVE).

## §2 Structure (decision core is pure + TDD'd; side effects are thin shell)
Three failure modes (spec27 §1) are structurally prevented:
- **laziness** → the gate is deterministic and self-contained; one `run.sh` does the whole birth.
- **self-preference** → `run.sh` NEVER reports success it didn't verify: a real spawn must produce a
  provider id + a distinct child wallet addr or it exits non-zero. `--dry-run` does ZERO side effects
  and says so (no fake/mock success — HARD 0.24).
- **drift** → all spawn POLICY (threshold, rate-limit, id derivation, seed amount) lives in pure
  JS modules tested by `node:test`; the shell only orchestrates.

## §3 Files
| file | responsibility |
|---|---|
| `skills/self/spawn/SKILL.md` | what/when/gate/flow/verify (no-human-in-loop rules) |
| `skills/self/spawn/lib/spawn-decision.js` | PURE: `decideSpawn({ balanceUsdc, children, nowMs, minBalanceUsdc, rateLimitDays, maxChildren })` → `{ eligible, reason }`. No I/O. |
| `skills/self/spawn/lib/child-spec.js` | PURE: `nextChildId(children, prefix)`, `buildChildSpec({ parentWallet, childWallet, childInbox, generation, seedUsdc, constitutionHash })` → spec object. No I/O. |
| `skills/self/spawn/lib/ledger.js` | `appendChild(file, row)` + `readChildren(file)` (jsonl; injectable fs for tests). The only DB-ish file. |
| `skills/self/spawn/lib/__tests__/*.test.js` | `node:test` for every pure module + ledger round-trip. |
| `skills/self/spawn/run.sh` | entrypoint: load env → read wallet balance + children → call decision (via `node -e`) → if eligible: gen child wallet + provision AgentMail inbox + DO/Akash droplet + seed tx → append ledger → print verifiable facts. `--dry-run` = gate-only, no spend. |
| `skills/self/spawn/scripts/gen-wallet.sh` | fresh secp256k1 keypair → `{address,private_key,public_key}` JSON to a 600-perm file (reused proven script). |

## §4 Gate (deterministic, decideSpawn)
```
eligible = balanceUsdc >= minBalanceUsdc        (default 20: ~1mo host $5 + $1 seed + buffer)
        && children since (now - rateLimitDays) == 0   (default rateLimitDays = 14)
        && children.length < maxChildren                (default maxChildren = 1, parent caps concurrency)
otherwise { eligible:false, reason: <"low_balance"|"rate_limited"|"max_children"> }   → dormant, silent, exit 0
```
Money rule: not profitable → contribute nothing, spawn nothing (own survival first).

## §5 Child identity (child-spec)
- `nextChildId([...], "anicca-c")` → `anicca-c001`, `anicca-c002`, … (zero-padded, monotonic, gap-safe = max existing + 1).
- child gets: own wallet (gen-wallet.sh), own AgentMail inbox (`client.inboxes.create`), `seedUsdc` from parent ($1), `generation = parentGeneration + 1`, inherited constitution hash, inherited default skills.
- child is pure Anicca lineage (no Dais keys) — "Daughter of Anicca <hash>".

## §6 run.sh contract (no fake run)
- `--dry-run`: validate env + read balance + children + call decision; print the decision JSON; touch NOTHING. Exit 0.
- real run: only when decision.eligible. Provision child wallet → AgentMail inbox → droplet → seed tx → ledger append. Print `CHILD_ID=…`, `CHILD_WALLET=0x…` (≠ parent), `CHILD_INBOX=…@agentmail.to`, `PROVIDER_ID=…`. If any step fails, mark the provisional ledger row `failed` and exit 1 (honest ledger).
- never asks the user "spawn OK?" / "where to host?" — gate decides, provider auto-bids (HARD: no-human-in-loop).

## §7 Verify (E2E, runtime — NOT a web page)
This subsystem has **no aniccaai.com / Netlify surface** (it is a runtime skill in the OSS body), so the
products-repo Netlify-green wait does not apply. Verification per spec27 A-self-spawn:
- `node --test skills/self/spawn/lib/__tests__/*.test.js` → all pass (this PR's self-test).
- `bash run.sh --dry-run` on a parent below threshold → prints `eligible:false` + reason, zero side effects.
- (post-fund, runtime) real run → child droplet active + `CHILD_WALLET ≠ parent` on basescan + child row in dashboard.

## §8 Collision
Touches ONLY `skills/self/spawn/**` (its reserved slot dir) + this spec/plan doc. Does NOT edit
`skills/registry.json`, `install.sh`, or any landing file. The slot's `status` flip to `"live"` is a
separate one-line registry change made by Foundation once runtime E2E lands (per the brief's HARD
collision rule, the builder does not edit the shared registry).
