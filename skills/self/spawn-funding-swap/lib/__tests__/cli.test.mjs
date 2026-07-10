// VCSDD spawn-funding-swap Phase 2a (RED). REQ-008 — PROP-014, wiring as TREASURY_SWAP_CMD: the packaged
// CLI entrypoint invoked exactly as akt-treasury.sh:52-54 would (`bash -c "$TREASURY_SWAP_CMD"`), exit
// code 0 only on REQ-007 success, non-zero otherwise. Written against bin/spawn-funding-swap.mjs, which
// does NOT exist yet — every test below MUST fail (spawn ENOENT / non-existent-file error) until Phase 2b.
//
// Mocked-transport-via-env/config seam (Phase 2a-defined, binding on Phase 2b): the CLI entrypoint MUST
// check for SPAWN_FUNDING_SWAP_FAKE_DEPS_MODULE in its environment; when set, it dynamically imports that
// module's `createDeps()` export INSTEAD OF wiring real SkipApiClient/ChainReader/BaseSigner/PriceOracle
// clients, and calls lib/driver.mjs's runSwap(deps) with the result. Production NEVER sets this env var.
// This is how PROP-014 exercises the real subprocess/exit-code contract without ever touching a real
// network/RPC/signing client (Test-Money Safety Rule) — the CLI module itself (not a test file) is
// permitted to import real clients for its non-test code path; PROP-021's static scan only covers files
// under this feature's TEST directories.
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const BIN = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "bin", "spawn-funding-swap.mjs");
const SUCCESS_FIXTURE = path.join(path.dirname(fileURLToPath(import.meta.url)), "fakes", "cli-success-fixture.mjs");
const FAILURE_FIXTURE = path.join(path.dirname(fileURLToPath(import.meta.url)), "fakes", "cli-failure-fixture.mjs");

function runCliViaBashDashC(fixturePath) {
  const cmd = `node ${JSON.stringify(BIN)}`;
  return spawnSync("bash", ["-c", cmd], {
    env: { ...process.env, SPAWN_FUNDING_SWAP_FAKE_DEPS_MODULE: fixturePath, AKASH_KEY_NAME: "anicca-akash", AKASH_KEYRING_BACKEND: "test" },
    encoding: "utf8",
  });
}

test("PROP-014: CLI entrypoint invoked as `bash -c \"$TREASURY_SWAP_CMD\"` exits 0 on a full success fixture", () => {
  const result = runCliViaBashDashC(SUCCESS_FIXTURE);
  assert.equal(result.status, 0, `expected exit 0, got ${result.status}; stderr=${result.stderr}`);
});

test("PROP-014: CLI entrypoint exits non-zero on a failure fixture (insufficient funded source — today's real production blocker)", () => {
  const result = runCliViaBashDashC(FAILURE_FIXTURE);
  assert.notEqual(result.status, 0, `expected non-zero exit, got ${result.status}`);
});

test("REQ-008 edge case: the command must not depend on shell state beyond akt-treasury.sh's own exported vars plus its own self-contained config — invoking with a minimal PATH-only env still exits deterministically (never hangs, matches NFR-4's bounded-latency contract)", () => {
  const cmd = `node ${JSON.stringify(BIN)}`;
  const result = spawnSync("bash", ["-c", cmd], {
    env: { PATH: process.env.PATH, SPAWN_FUNDING_SWAP_FAKE_DEPS_MODULE: SUCCESS_FIXTURE, AKASH_KEY_NAME: "anicca-akash", AKASH_KEYRING_BACKEND: "test" },
    encoding: "utf8",
    timeout: 15_000,
  });
  assert.notEqual(result.signal, "SIGTERM", "must not hang/timeout even with a minimal environment");
  assert.equal(result.status, 0);
});

// REQ-009 / FIND-002 (contract-review, money-path identity isolation): the REAL production wiring path
// (no SPAWN_FUNDING_SWAP_FAKE_DEPS_MODULE) must fail closed on identity resolution BEFORE it ever
// reaches (missing-in-this-repo) lib/real-clients/*.mjs, proving no lock/price/route/sign activity is
// even reachable. A MODULE_NOT_FOUND for a real-clients/*.mjs import here would mean the identity gate
// was bypassed -- this asserts the actual failure is the identity-gate error, not that later error.
test("(a) REQ-009/FIND-002: production wiring (no FAKE_DEPS_MODULE) with ANICCA_HOME unset fails closed on identity resolution, never reaching real-client wiring or any sign call", () => {
  const cmd = `node ${JSON.stringify(BIN)}`;
  const result = spawnSync("bash", ["-c", cmd], {
    env: { PATH: process.env.PATH, AKASH_KEY_NAME: "anicca-akash", AKASH_KEYRING_BACKEND: "test" },
    encoding: "utf8",
    timeout: 15_000,
  });
  assert.notEqual(result.status, 0, "must exit non-zero when identity cannot be resolved");
  assert.match(result.stderr, /identity resolution failed/, `expected the identity-gate error, got stderr=${result.stderr}`);
  assert.match(result.stderr, /ANICCA_HOME/, `expected an ANICCA_HOME-specific reason, got stderr=${result.stderr}`);
  assert.doesNotMatch(result.stderr, /real-clients/, "must fail BEFORE the real-clients import is ever attempted");
});

// (c) proves the CLI's production path never falls back to a shared agent .env key when ANICCA_HOME is
// unset, even though ANICCA_EVM_PRIVATE_KEY is present in the ambient environment (the exact shared-Mac
// leak precondition from feedback_earn_identity_resolve_per_instance_gate_on_anicca_home.md).
test("(c) REQ-009/FIND-002: an ambient ANICCA_EVM_PRIVATE_KEY (simulating a shared agent .env leak) is NEVER used by the CLI's production path when ANICCA_HOME is unset", () => {
  const cmd = `node ${JSON.stringify(BIN)}`;
  const result = spawnSync("bash", ["-c", cmd], {
    env: {
      PATH: process.env.PATH,
      AKASH_KEY_NAME: "anicca-akash",
      AKASH_KEYRING_BACKEND: "test",
      ANICCA_EVM_PRIVATE_KEY: "0x" + "8".repeat(64),
    },
    encoding: "utf8",
    timeout: 15_000,
  });
  assert.notEqual(result.status, 0, "must exit non-zero even with a shared-env key present");
  assert.match(result.stderr, /ANICCA_HOME/, `expected the ANICCA_HOME gate to fire, got stderr=${result.stderr}`);
});
