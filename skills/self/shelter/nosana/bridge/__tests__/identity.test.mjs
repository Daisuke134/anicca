// node:test — identity.mjs: resolves the Base (source) and Solana (destination) identities from
// real on-disk shapes, using real fs (tmp dirs), matching resolve-identity.mjs's own documented
// lookup paths. No network I/O.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { generatePrivateKey, privateKeyToAccount } from "viem/accounts";
import { Keypair } from "@solana/web3.js";
import bs58 from "bs58";
import { resolveBridgeIdentity } from "../identity.mjs";

function mkTmpHome() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "bridge-identity-test-"));
}

function writeEvmAutomatonWallet(home, privateKey) {
  fs.mkdirSync(path.join(home, ".automaton"), { recursive: true });
  fs.writeFileSync(path.join(home, ".automaton", "wallet.json"), JSON.stringify({ privateKey }));
}

function writeEvmFlatWallet(home, privateKey) {
  // Matches the founder wallet's REAL on-disk shape per this feature's task spec:
  // "$HOME/.anicca-founder (flat wallet.json, `privateKey` field)".
  fs.writeFileSync(path.join(home, "wallet.json"), JSON.stringify({ privateKey }));
}

function writeSolanaAutomatonSecret(home, secretBase58) {
  fs.mkdirSync(path.join(home, ".automaton"), { recursive: true });
  fs.writeFileSync(path.join(home, ".automaton", "solana.json"), JSON.stringify({ secretKey: secretBase58 }));
}

test("resolveBridgeIdentity: resolves a real EVM key (.automaton/wallet.json) and a real Solana secret (.automaton/solana.json) from two distinct homes", () => {
  const evmHome = mkTmpHome();
  const solanaHome = mkTmpHome();
  const pk = generatePrivateKey();
  writeEvmAutomatonWallet(evmHome, pk);
  const kp = Keypair.generate();
  const solanaSecretBase58 = bs58.encode(kp.secretKey);
  writeSolanaAutomatonSecret(solanaHome, solanaSecretBase58);

  const identity = resolveBridgeIdentity({ env: {}, evmHome, solanaHome });
  assert.equal(identity.evmAddress, privateKeyToAccount(pk).address);
  assert.equal(identity.evmPrivateKey, pk);
  assert.equal(identity.solanaAddress, kp.publicKey.toBase58());

  fs.rmSync(evmHome, { recursive: true, force: true });
  fs.rmSync(solanaHome, { recursive: true, force: true });
});

test("resolveBridgeIdentity: resolves the REAL founder-wallet shape — flat wallet.json with a privateKey field, no .automaton subdir", () => {
  const evmHome = mkTmpHome();
  const solanaHome = mkTmpHome();
  const pk = generatePrivateKey();
  writeEvmFlatWallet(evmHome, pk);
  const kp = Keypair.generate();
  writeSolanaAutomatonSecret(solanaHome, bs58.encode(kp.secretKey));

  const identity = resolveBridgeIdentity({ env: {}, evmHome, solanaHome });
  assert.equal(identity.evmAddress, privateKeyToAccount(pk).address);

  fs.rmSync(evmHome, { recursive: true, force: true });
  fs.rmSync(solanaHome, { recursive: true, force: true });
});

test("resolveBridgeIdentity: never exposes Solana secretBytes — only the derived address is returned", () => {
  const evmHome = mkTmpHome();
  const solanaHome = mkTmpHome();
  writeEvmAutomatonWallet(evmHome, generatePrivateKey());
  const kp = Keypair.generate();
  writeSolanaAutomatonSecret(solanaHome, bs58.encode(kp.secretKey));

  const identity = resolveBridgeIdentity({ env: {}, evmHome, solanaHome });
  const keys = Object.keys(identity);
  assert.deepEqual(keys.sort(), ["evmAddress", "evmPrivateKey", "solanaAddress"]);
  // The serialized result must not contain anything base58-secret-key-shaped from the Solana side.
  const serialized = JSON.stringify(identity);
  const solanaSecretBase58 = bs58.encode(kp.secretKey);
  assert.ok(!serialized.includes(solanaSecretBase58));

  fs.rmSync(evmHome, { recursive: true, force: true });
  fs.rmSync(solanaHome, { recursive: true, force: true });
});

test("resolveBridgeIdentity: fails closed when solanaHome is missing (bridging is cross-instance by design, never inferred)", () => {
  const evmHome = mkTmpHome();
  writeEvmAutomatonWallet(evmHome, generatePrivateKey());
  assert.throws(() => resolveBridgeIdentity({ env: {}, evmHome }), /solanaHome is required/);
  fs.rmSync(evmHome, { recursive: true, force: true });
});

test("resolveBridgeIdentity: fails closed when no EVM key resolves for the given home", () => {
  const evmHome = mkTmpHome(); // empty — no wallet.json anywhere
  const solanaHome = mkTmpHome();
  const kp = Keypair.generate();
  writeSolanaAutomatonSecret(solanaHome, bs58.encode(kp.secretKey));
  assert.throws(() => resolveBridgeIdentity({ env: {}, evmHome, solanaHome }), /no EVM private key resolved/);
  fs.rmSync(evmHome, { recursive: true, force: true });
  fs.rmSync(solanaHome, { recursive: true, force: true });
});

test("resolveBridgeIdentity: fails closed when no Solana secret resolves for the given home", () => {
  const evmHome = mkTmpHome();
  const solanaHome = mkTmpHome(); // empty
  writeEvmAutomatonWallet(evmHome, generatePrivateKey());
  assert.throws(() => resolveBridgeIdentity({ env: {}, evmHome, solanaHome }), /no Solana secret resolved/);
  fs.rmSync(evmHome, { recursive: true, force: true });
  fs.rmSync(solanaHome, { recursive: true, force: true });
});
