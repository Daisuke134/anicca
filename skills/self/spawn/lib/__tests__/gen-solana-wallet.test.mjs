// VCSDD anicca-agent-spawn, sprint-2, Phase 2a (RED). REQ-202/CRIT-207 -- a brand-new
// scripts/gen-solana-wallet.sh (confirmed genuinely absent from the codebase this sprint's own Phase 1a
// research -- no such file, and no @nosana/cli-adjacent auto-keygen wrapper, exists anywhere under
// the canonical checkout today, per contracts/sprint-2.md's own CRIT-207). This script does not exist yet -- every
// test below is expected to fail (execFileSync throws ENOENT) until it is implemented in Phase 2b/2c.
// Mirrors gen-wallet.sh's OWN generation discipline exactly (fresh entropy, {address, private_key,
// public_key}-shaped JSON to stdout, 600-perm caller-redirected file, never logged) and REQ-201's own
// cross-check acceptance criterion ("the address independently re-derives... under a second,
// independent implementation"), applied here to REQ-202's new script via @solana/web3.js's own
// Keypair.fromSecretKey (a genuinely SEPARATE library from the `solana-keygen` CLI this script itself
// shells out to for generation -- corrected, FIND-004: an earlier version of this cross-check called
// `solana-keygen` a SECOND time, which is not independent).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCRIPT_PATH = path.resolve(__dirname, "../../scripts/gen-solana-wallet.sh");

function runScript() {
  return execFileSync("bash", [SCRIPT_PATH], { encoding: "utf8" });
}

test("CRIT-207 structural: gen-solana-wallet.sh exists and documents the same 600-perm/never-logged discipline gen-wallet.sh's own header already establishes", () => {
  const src = fs.readFileSync(SCRIPT_PATH, "utf8");
  assert.match(src, /600-perm/i, "must document the caller-must-redirect-to-a-600-perm-file discipline, matching gen-wallet.sh");
  assert.match(src, /NEVER.*log|never.*stdout.*reach.*log/i, "must document that stdout must never reach a shared log");
});

test("CRIT-207: a live invocation emits {address, private_key, public_key}-shaped JSON to stdout, matching gen-wallet.sh's own output contract", () => {
  const out = runScript();
  const parsed = JSON.parse(out);
  assert.equal(typeof parsed.address, "string");
  assert.equal(typeof parsed.private_key, "string");
  assert.equal(typeof parsed.public_key, "string");
  assert.ok(parsed.address.length > 0);
  assert.ok(parsed.private_key.length > 0);
});

test("CRIT-207: two live invocations produce two DISTINCT keypairs (fresh entropy each run, never a fixed/cached keypair)", () => {
  const first = JSON.parse(runScript());
  const second = JSON.parse(runScript());
  assert.notEqual(first.address, second.address);
  assert.notEqual(first.private_key, second.private_key);
});

test("CRIT-207 (FIND-004 fix): the generated Solana address independently re-derives to the same value under @solana/web3.js's Keypair.fromSecretKey (a SECOND, GENUINELY independent derivation path -- a real, separate library, never the SAME solana-keygen CLI this script's own generation shells out to), mirroring REQ-201's viem privateKeyToAccount cross-check discipline", () => {
  const { address, private_key: privateKeyBase58 } = JSON.parse(runScript());

  // Independent re-derivation via @solana/web3.js -- already a real dependency of this repo
  // (package.json, node_modules/@solana/web3.js), and the SAME library runtime/wallet-address-solana.mjs
  // already uses for this identical Keypair.fromSecretKey(...).publicKey.toBase58() derivation. Prior to
  // this fix, this test instead shelled out to `solana-keygen pubkey` a SECOND time -- the exact same
  // tool gen-solana-wallet.sh itself uses to generate the address, so it could never catch a systematic
  // bug in solana-keygen's own derivation logic (FIND-004).
  const bs58 = loadBs58();
  const secretKeyBytes = bs58.decode(privateKeyBase58);
  assert.equal(secretKeyBytes.length, 64, "a Solana secret key is the 64-byte {seed(32) + pubkey(32)} keypair, matching @solana/web3.js's own Keypair.secretKey shape");

  const { Keypair } = loadSolanaWeb3();
  const rederivedAddress = Keypair.fromSecretKey(secretKeyBytes).publicKey.toBase58();
  assert.equal(rederivedAddress, address, "@solana/web3.js's own independent derivation must match this script's own reported address");
});

function loadBs58() {
  // bs58 is already a real dependency of this repo (node_modules/bs58) -- reused, never re-implemented.
  return require("bs58");
}

function loadSolanaWeb3() {
  // @solana/web3.js is already a real dependency of this repo (package.json, node_modules/@solana/web3.js)
  // -- reused, never re-implemented.
  return require("@solana/web3.js");
}
