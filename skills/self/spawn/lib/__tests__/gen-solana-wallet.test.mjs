// VCSDD anicca-agent-spawn, sprint-2, Phase 2a (RED). REQ-202/CRIT-207 -- a brand-new
// scripts/gen-solana-wallet.sh (confirmed genuinely absent from the codebase this sprint's own Phase 1a
// research -- no such file, and no @nosana/cli-adjacent auto-keygen wrapper, exists anywhere under
// ~/anicca today, per contracts/sprint-2.md's own CRIT-207). This script does not exist yet -- every
// test below is expected to fail (execFileSync throws ENOENT) until it is implemented in Phase 2b/2c.
// Mirrors gen-wallet.sh's OWN generation discipline exactly (fresh entropy, {address, private_key,
// public_key}-shaped JSON to stdout, 600-perm caller-redirected file, never logged) and REQ-201's own
// cross-check acceptance criterion ("the address independently re-derives... under a second,
// independent implementation"), applied here to REQ-202's new script via the `solana-keygen` CLI (a
// genuinely SEPARATE implementation from whatever this script itself uses to generate the keypair).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
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

test("CRIT-207: the generated Solana address independently re-derives to the same value under solana-keygen (a SECOND, independent derivation path), mirroring REQ-201's ethers-v6 cross-check discipline", () => {
  const { address, private_key: privateKeyBase58 } = JSON.parse(runScript());

  // Independent re-derivation: decode the script's own base58 secret key into the 64-byte raw secret
  // solana-keygen's JSON keypair-file format expects, write it to a temp file, and ask solana-keygen
  // (a completely separate CLI, never this script's own code) to derive the public key from it.
  const bs58 = loadBs58();
  const secretKeyBytes = Array.from(bs58.decode(privateKeyBase58));
  assert.equal(secretKeyBytes.length, 64, "a Solana secret key is the 64-byte {seed(32) + pubkey(32)} keypair, matching @solana/web3.js's own Keypair.secretKey shape");

  const tmpKeypairFile = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "anicca-solana-keygen-crosscheck-")), "keypair.json");
  fs.writeFileSync(tmpKeypairFile, JSON.stringify(secretKeyBytes));
  try {
    const rederivedAddress = execFileSync("solana-keygen", ["pubkey", tmpKeypairFile], { encoding: "utf8" }).trim();
    assert.equal(rederivedAddress, address, "solana-keygen's own independent derivation must match this script's own reported address");
  } finally {
    fs.rmSync(path.dirname(tmpKeypairFile), { recursive: true, force: true });
  }
});

function loadBs58() {
  // bs58 is already a real dependency of this repo (node_modules/bs58) -- reused, never re-implemented.
  return require("bs58");
}
