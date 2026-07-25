"use strict";
// FIN-a: the agent generates its OWN wallet — reusing an existing one is forbidden by spec 10.1 U7.
// A wrong address here loses money silently, so derivation is pinned against published Ethereum
// vectors rather than against itself, and the private key must never be able to leave through a log.
const assert = require("node:assert/strict");
const test = require("node:test");

const { deriveAddress, generateAgentWallet, redactWallet, isValidPrivateKey } = require("./agent-wallet.js");

// Published vectors: private key 1 and private key 2 on secp256k1.
const VECTORS = [
  ["0000000000000000000000000000000000000000000000000000000000000001", "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"],
  ["0000000000000000000000000000000000000000000000000000000000000002", "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF"],
];

test("derivation matches published Ethereum vectors, including EIP-55 casing", () => {
  for (const [key, expected] of VECTORS) {
    assert.equal(deriveAddress(key), expected);
    assert.equal(deriveAddress(`0x${key}`), expected, "a 0x prefix must be accepted");
  }
});

test("a key outside the curve order is refused rather than producing a plausible address", () => {
  const order = "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141";
  for (const bad of ["00".repeat(32), order, "ff".repeat(32)]) {
    assert.equal(isValidPrivateKey(bad), false, `${bad.slice(0, 8)}… must be refused`);
    assert.throws(() => deriveAddress(bad));
  }
});

test("a malformed key is refused", () => {
  for (const bad of ["", "abc", "zz".repeat(32), "01".repeat(31)]) {
    assert.equal(isValidPrivateKey(bad), false);
    assert.throws(() => deriveAddress(bad));
  }
});

test("a generated wallet is fresh, valid, and self-consistent", () => {
  const wallet = generateAgentWallet();
  assert.equal(isValidPrivateKey(wallet.privateKey), true);
  assert.match(wallet.address, /^0x[0-9a-fA-F]{40}$/);
  assert.equal(deriveAddress(wallet.privateKey), wallet.address);
});

test("two generations never collide", () => {
  const first = generateAgentWallet();
  const second = generateAgentWallet();
  assert.notEqual(first.privateKey, second.privateKey);
  assert.notEqual(first.address, second.address);
});

test("a supplied entropy source is used, so generation is auditable", () => {
  const fixed = Buffer.from(VECTORS[0][0], "hex");
  const wallet = generateAgentWallet(() => fixed);
  assert.equal(wallet.address, VECTORS[0][1]);
});

test("entropy that yields an unusable key is rejected instead of silently retried into a weak key", () => {
  assert.throws(() => generateAgentWallet(() => Buffer.alloc(32, 0)), /entropy/i);
});

test("redaction removes the private key from anything we might log", () => {
  const wallet = generateAgentWallet();
  const safe = redactWallet(wallet);

  assert.equal(safe.address, wallet.address);
  assert.equal("privateKey" in safe, false);
  assert.ok(!JSON.stringify(safe).includes(wallet.privateKey), "the key must not survive serialisation");
});

test("redaction also scrubs a nested key, so a wrapper object cannot leak it", () => {
  const wallet = generateAgentWallet();
  const safe = redactWallet({ context: "startup", wallet });
  assert.ok(!JSON.stringify(safe).includes(wallet.privateKey));
});
