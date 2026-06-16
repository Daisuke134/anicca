# Plan — self/spawn runtime completion (2026-06-16)

Make `~/anicca/skills/self/spawn` a SELF-CONTAINED, working self-replication skill that births a
child Anicca with (a) its OWN Base wallet, (b) its OWN AgentMail inbox, (c) a real DO droplet running
the automaton (proven cloud-init/systemd), (d) a live-dashboard registration (signed telemetry POST).

## Why this plan (root cause of the prior REJECT)
spec27b moved the *proven* pipeline into `anicca-products` (`apps/landing/...`) and proved a LIVE birth
there. But the `~/anicca` runtime skill (`skills/self/spawn/run.sh`) — the one the automaton actually
invokes — was left with three gaps that make its child a non-running, invisible body:
1. DO droplet created with a bare `docker-20-04` image, NO cloud-init → no clawrouter/automaton service
   → `systemctl is-active automaton` would be inactive → not a running Anicca.
2. No telemetry POST → the child never signs/POSTs → never appears on aniccaai.com dashboard.
3. `scripts/deploy-akash.sh` referenced at `run.sh:144` is MISSING → akash host path is a dangling ref.

`~/anicca` is dependency-light (no `ethers`). Verified self-contained primitives ARE available:
- `scripts/gen-wallet.sh` (openssl secp256k1 + python keccak) produces a VALID, ethers-cross-checked
  keypair (address derives identically under ethers v6 — confirmed 2026-06-16).
- `python3 -c eth_account` IS installed → EIP-191 personal_sign that recovers to the signer, byte-compatible
  with the live `telemetry-verify.js` (`verifyMessage`, freshness `now-ts<=60`).

## Steps
1. `scripts/cloud-init.sh CHILD_ID OWNER_EMAIL` — emit the proven systemd `#cloud-config` user_data
   (port of `apps/landing/netlify/functions/_lib/cloud-init.js`, verbatim units: clawrouter.service +
   automaton.service with `AUTOMATON_GOAL=earn`, `StateDirectory=anicca`, `enable --now`). No secret values.
2. `scripts/sign-telemetry.py` — read child private key (env CHILD_PRIVKEY) + host/geo, emit
   `{"message":...,"signature":...}` JSON (eth_account, canonicalMessage field order). Fail-closed.
3. `scripts/deploy-akash.sh CHILD_ID` — real akash CLI lease path, fail-closed if `akash` missing
   (exit 1, no fake). Closes the dangling ref.
4. `run.sh` — (a) pass `user_data` (base64 of cloud-init.sh) to the DO create call so the child boots the
   automaton; (b) after the droplet is up, sign + POST the child's first telemetry to
   `${TELEMETRY_URL:-https://aniccaai.com/.netlify/functions/telemetry}`, require 202, record
   `telemetry_status` + `dashboard_id` in the final ledger row. Any failed step exits non-zero with an
   honest `provisioning`/`failed` row (HARD 0.24 — no fake success).
5. Tests stay green (`node --test lib/__tests__/*.test.js`, 26/26).
6. REAL test child on a SEPARATE durable state dir (`~/.hermes/state-spawn-test`) so the production
   colony ledger stays at exactly 1 (anicca-c001, no double-count). Verify: distinct wallet, own inbox,
   droplet, dashboard row. THEN DESTROY the test droplet + delete the test inbox + test state dir.

## Earn-gating honesty (HARD 0.24/0.31)
The child boots `automaton.service` with `AUTOMATON_GOAL=earn`, so its OWN wake runs the earn loop — but
ACTUAL earning is the same demand-gated GATE-0 as the parent (no demand ⇒ $0). The child is BORN + WIRED
to earn; we do NOT claim a child earned.

## Collision
Edits ONLY `skills/self/spawn/**` + this plan. Does NOT touch `skills/registry.json`, `install.sh`, nav.
