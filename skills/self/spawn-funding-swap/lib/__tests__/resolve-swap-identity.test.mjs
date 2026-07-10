// node:test — resolve-swap-identity.mjs (REQ-009/FIND-002 fix, contract-review round). Proves the
// ANICCA_HOME-gated, no-shared-env-fallback identity resolution the CLI now depends on for
// expectedBaseSignerAddress/sourceBaseAddress/akashKeyName. Mirrors skills/earn/__tests__/
// run-identity.test.mjs's own hermetic-fixture style (throwaway HOME/ANICCA_HOME dirs, no ambient
// contamination).
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { privateKeyToAccount } from "viem/accounts";
import { resolveOwnBaseIdentity } from "../resolve-swap-identity.mjs";

async function tmpDir(prefix) {
  return fs.mkdtemp(path.join(os.tmpdir(), prefix));
}

async function writeWalletJson(dir, privateKey) {
  await fs.mkdir(path.join(dir, ".automaton"), { recursive: true });
  await fs.writeFile(path.join(dir, ".automaton", "wallet.json"), JSON.stringify({ privateKey }));
}

function addr(pk) {
  return privateKeyToAccount(pk).address;
}

test("(a) ANICCA_HOME unset -> fails closed, ok:false, no address/signing attempt is even possible", async () => {
  const home = await tmpDir("swap-identity-nohome-");
  // A wallet.json genuinely exists at the legacy default location -- proves the failure is the GATE,
  // not merely "no wallet found anywhere".
  await writeWalletJson(path.join(home, ".anicca"), "0x" + "1".repeat(64));
  const result = resolveOwnBaseIdentity({ env: { HOME: home, AKASH_KEY_NAME: "anicca-akash" } });
  assert.equal(result.ok, false);
  assert.match(result.reason, /ANICCA_HOME/);
});

test("(a) ANICCA_HOME set but empty string -> still fails closed (not merely 'unset')", async () => {
  const result = resolveOwnBaseIdentity({ env: { ANICCA_HOME: "", AKASH_KEY_NAME: "anicca-akash" } });
  assert.equal(result.ok, false);
  assert.match(result.reason, /ANICCA_HOME/);
});

test("(a) ANICCA_HOME set but no wallet.json under it -> fails closed (fail-closed, never a default)", async () => {
  const home = await tmpDir("swap-identity-emptyhome-");
  const aniccaHome = path.join(home, "instance-with-no-wallet");
  await fs.mkdir(aniccaHome, { recursive: true });
  const result = resolveOwnBaseIdentity({ env: { HOME: home, ANICCA_HOME: aniccaHome, AKASH_KEY_NAME: "anicca-akash" } });
  assert.equal(result.ok, false);
  assert.match(result.reason, /no Base signing key resolved/);
});

test("happy path: ANICCA_HOME set + its own wallet.json -> resolves the DERIVED address, never a raw literal", async () => {
  const home = await tmpDir("swap-identity-happy-");
  const pk = "0x" + "3".repeat(64);
  const aniccaHome = path.join(home, "this-instance");
  await writeWalletJson(aniccaHome, pk);
  const result = resolveOwnBaseIdentity({ env: { HOME: home, ANICCA_HOME: aniccaHome, AKASH_KEY_NAME: "anicca-akash" } });
  assert.equal(result.ok, true);
  assert.equal(result.baseAddress, addr(pk));
  assert.equal(result.akashKeyName, "anicca-akash");
});

test("(b) a spoofed SPAWN_FUNDING_SWAP_EXPECTED_BASE_SIGNER_ADDRESS / SOURCE_BASE_ADDRESS env value is NEVER read or trusted -- the resolved address always comes from the wallet.json-derived key, proving no path exists for a mismatched/spoofed value to substitute another instance's address", async () => {
  const home = await tmpDir("swap-identity-spoof-");
  const pk = "0x" + "4".repeat(64);
  const aniccaHome = path.join(home, "this-instance");
  await writeWalletJson(aniccaHome, pk);
  const spoofedAddress = "0x000000000000000000000000000000DEADBEEF";
  const result = resolveOwnBaseIdentity({
    env: {
      HOME: home,
      ANICCA_HOME: aniccaHome,
      AKASH_KEY_NAME: "anicca-akash",
      SPAWN_FUNDING_SWAP_EXPECTED_BASE_SIGNER_ADDRESS: spoofedAddress,
      SPAWN_FUNDING_SWAP_SOURCE_BASE_ADDRESS: spoofedAddress,
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.baseAddress, addr(pk));
  assert.notEqual(result.baseAddress, spoofedAddress);
});

test("(c) a shared agent .env-style ANICCA_EVM_PRIVATE_KEY present in the ambient env is NEVER used when ANICCA_HOME is unset -- the ANICCA_HOME gate is checked BEFORE resolveEvmPrivateKey's own override path is ever reached", async () => {
  const sharedLeakedKey = "0x" + "9".repeat(64);
  const result = resolveOwnBaseIdentity({ env: { ANICCA_EVM_PRIVATE_KEY: sharedLeakedKey, AKASH_KEY_NAME: "anicca-akash" } });
  assert.equal(result.ok, false);
  assert.match(result.reason, /ANICCA_HOME/);
});

test("(c) a legacy shared $HOME/.automaton/wallet.json (another instance's default-home wallet) is NEVER resolved when ANICCA_HOME is unset", async () => {
  const home = await tmpDir("swap-identity-legacy-leak-");
  const otherInstancePk = "0x" + "7".repeat(64);
  // Simulates the shared Mac's REAL leak precondition: a wallet.json sits at $HOME/.automaton (the
  // legacy shared default-home path another instance's daemon owns).
  await fs.mkdir(path.join(home, ".automaton"), { recursive: true });
  await fs.writeFile(path.join(home, ".automaton", "wallet.json"), JSON.stringify({ privateKey: otherInstancePk }));
  const result = resolveOwnBaseIdentity({ env: { HOME: home, AKASH_KEY_NAME: "anicca-akash" } });
  assert.equal(result.ok, false);
  assert.notEqual(result.baseAddress, addr(otherInstancePk));
});

test("AKASH_KEY_NAME is undefined (not a spoofable empty string) when absent from env, even with a valid resolved Base identity", async () => {
  const home = await tmpDir("swap-identity-noakash-");
  const pk = "0x" + "2".repeat(64);
  const aniccaHome = path.join(home, "this-instance");
  await writeWalletJson(aniccaHome, pk);
  const result = resolveOwnBaseIdentity({ env: { HOME: home, ANICCA_HOME: aniccaHome } });
  assert.equal(result.ok, true);
  assert.equal(result.akashKeyName, undefined);
});
