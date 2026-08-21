# Agent Economy Wallet Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the release-backed agent-economy runtime one isolated EVM identity without moving funds.

**Architecture:** `ensure-wallet.mjs` creates `$ANICCA_HOME/.automaton/wallet.json` with an owner-only mode, validates an existing key/address pair, and uses exclusive creation for races. The agent-economy launch wrapper invokes it only when the release plist explicitly sets `ANICCA_ECONOMY_CREATE_EVM_WALLET=1`.

**Tech Stack:** Node.js ESM, `viem/accounts`, atomic filesystem create, launchd environment flag.

**Spec:** `docs/superpowers/specs/2026-08-21-agent-economy-design.md`

## Global Constraints

- Wallet creation never funds, signs, or broadcasts a transaction.
- Private key is never printed, logged, or returned by the module API.
- Existing malformed wallet files are rejected, never replaced.
- Franklin homes do not receive this automatic EVM bootstrap flag.

---

### Task 1: Bootstrap and expose an isolated wallet identity

**Files:**
- Create: `runtime/compute-proxy/ensure-wallet.mjs`
- Test: `runtime/compute-proxy/__tests__/ensure-wallet.test.mjs`
- Modify: `skills/agent-economy/launch.sh`
- Modify: `loops/agent-economy/loop.toml`
- Modify: `test/agent-economy-control-plane.test.mjs`

**Interfaces:**
- Produces: `{address,path,created}` from `ensureWallet({home})` and a launchd environment with the explicit creation flag.

- [ ] **Step 1: Write creation/idempotency/malformed-wallet tests**

  Use temporary homes to assert first creation, mode `0600`, same address on a second call, and rejection of a mismatched existing file.

- [ ] **Step 2: Run the wallet test and observe the RED result**

  Run: `node --test runtime/compute-proxy/__tests__/ensure-wallet.test.mjs`
  Expected: FAIL because `ensure-wallet.mjs` does not exist.

- [ ] **Step 3: Implement exclusive owner-only creation and wrapper wiring**

  Use `viem/accounts`, `fs.open(...,"wx",0600)`, and an address/private-key consistency check. Invoke it only when `ANICCA_ECONOMY_CREATE_EVM_WALLET=1`; add that flag to the release declaration and plist test.

- [ ] **Step 4: Run focused regression suites**

  Run: `npm run test:agent-economy`, `npm run test:install`, `npm run test:oss`, `node --check runtime/compute-proxy/ensure-wallet.mjs`, and `git diff --check`.
  Expected: 51 focused agent-economy tests, 2 install tests, and 11 OSS tests pass.

- [ ] **Step 5: Cut a new release, reload only agent-economy, and read back the public address without printing the key**

  Run the already-approved sequence: `bin/cut-loop-release.sh HEAD`, `python3 ~/loops/current/bin/plistgen.py ... --only agent-economy`, `bash ~/loops/current/bin/loop-install.sh ai.anicca.agent-economy-loop`, then inspect only `ANICCA_WALLET_ADDRESS`/wallet file mode and loop logs. Do not fund or broadcast.

- [ ] **Step 6: Commit and push**

  Run: `git add runtime/compute-proxy/ensure-wallet.mjs runtime/compute-proxy/__tests__/ensure-wallet.test.mjs skills/agent-economy/launch.sh skills/agent-economy/SKILL.md loops/agent-economy/loop.toml test/agent-economy-control-plane.test.mjs docs/superpowers/plans/2026-08-21-agent-economy-wallet-bootstrap.md package.json && git commit -m "feat: bootstrap isolated agent economy wallet" && git push`
