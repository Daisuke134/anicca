"use strict";
// AE-ZERO-START-1 §4.2 — the tenant agent's OWN Solana wallet.
//
// Same two safety rules as the EVM sibling (`agent-wallet.test.js`), for the same reasons. Derivation is
// pinned against PUBLISHED RFC 8032 ed25519 vectors rather than against itself, because a subtly wrong
// address does not fail — it silently sends money nowhere. And the secret must be unable to leave through
// a log line, a receipt, or an error message, so everything printable goes through redactSolanaWallet
// first and no thrown message is allowed to echo the input back.
//
// The two seeds below are the PUBLISHED RFC 8032 §7.1 TEST-1 / TEST-2 vectors. They are famous public
// dummy values that hold nothing and must never be funded; they are here because a self-referential
// derivation test cannot catch a wrong curve.
const assert = require("node:assert/strict");
const test = require("node:test");

const {
  SOLANA_ADDRESS_RE,
  deriveSolanaAddress,
  encodeSolanaSecretKey,
  generateSolanaAgentWallet,
  isValidSolanaSecretKey,
  redactSolanaWallet,
} = require("./agent-wallet-solana.js");

// PUBLISHED RFC 8032 §7.1 test vectors — dummy keys, never funded. [seed hex, expected public key hex]
const VECTORS = [
  [
    "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
    "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
  ],
  [
    "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
    "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
  ],
];

// Built at run time from the hex vectors above so no 88-character secret literal ever sits in the repo.
function vectorSecretKey(index) {
  return encodeSolanaSecretKey(Buffer.from(VECTORS[index][0], "hex"));
}

test("derivation matches the published RFC 8032 ed25519 vectors", () => {
  for (let index = 0; index < VECTORS.length; index++) {
    const [, publicKeyHex] = VECTORS[index];
    const address = deriveSolanaAddress(vectorSecretKey(index));
    assert.equal(
      Buffer.from(require("@scure/base").base58.decode(address)).toString("hex"),
      publicKeyHex,
      "the address must decode to the vector's public key",
    );
  }
});

test("an address is base58 in the Solana shape the ledger already accepts", () => {
  for (let index = 0; index < VECTORS.length; index++) {
    const address = deriveSolanaAddress(vectorSecretKey(index));
    assert.match(address, SOLANA_ADDRESS_RE);
    assert.match(address, /^[1-9A-HJ-NP-Za-km-z]{32,44}$/, "no 0, O, I or l — base58 excludes them");
    // The earnings ledger accepts exactly this shape (lib/earnings-ledger.js SOLANA_ADDRESS_RE), so an
    // address this module mints must never be rejected by the ledger it is meant to be written to.
    const { normaliseEntry } = require("./earnings-ledger.js");
    const row = normaliseEntry({
      entry_key: `test:${index}`,
      kind: "financial_deposit",
      currency: "USD",
      amount_minor: "0",
      occurred_at: "2026-07-30T00:00:00.000Z",
      wallet_address: address,
    });
    assert.equal(row.wallet_address, address);
  }
});

test("a generated wallet is fresh, valid, and self-consistent", () => {
  const wallet = generateSolanaAgentWallet();
  assert.match(wallet.address, SOLANA_ADDRESS_RE);
  assert.equal(isValidSolanaSecretKey(wallet.secretKey), true);
  assert.equal(deriveSolanaAddress(wallet.secretKey), wallet.address);
});

test("two generations never collide", () => {
  const first = generateSolanaAgentWallet();
  const second = generateSolanaAgentWallet();
  assert.notEqual(first.secretKey, second.secretKey);
  assert.notEqual(first.address, second.address);
});

test("a supplied entropy source is used, so generation is auditable", () => {
  const seed = Buffer.from(VECTORS[0][0], "hex");
  const wallet = generateSolanaAgentWallet(() => seed);
  assert.equal(wallet.address, deriveSolanaAddress(vectorSecretKey(0)));
  assert.equal(wallet.secretKey, vectorSecretKey(0));
});

test("entropy that is not 32 usable bytes is refused instead of silently reduced to a weak key", () => {
  assert.throws(() => generateSolanaAgentWallet(() => Buffer.alloc(32, 0)), /entropy/i);
  assert.throws(() => generateSolanaAgentWallet(() => Buffer.alloc(31, 7)), /entropy/i);
  assert.throws(() => generateSolanaAgentWallet(() => Buffer.alloc(64, 7)), /entropy/i);
});

test("a malformed secret key is refused rather than producing a plausible address", () => {
  const bad = [
    "",
    "   ",
    "abc",
    null,
    undefined,
    // base58 deliberately has no 0, O, I or l, so these cannot decode.
    "0OIl".repeat(22),
    // right alphabet, wrong decoded length.
    encodeSolanaSecretKey(Buffer.alloc(32, 3)).slice(0, 40),
  ];
  for (const value of bad) {
    assert.equal(isValidSolanaSecretKey(value), false);
    assert.throws(() => deriveSolanaAddress(value));
  }
});

test("a secret key whose embedded public key does not match its seed is refused", () => {
  // A 64-byte Solana secret key carries seed||publicKey. If the two halves disagree, one of them is a
  // lie, and signing with it would produce receipts nobody can verify against the stated address.
  const { base58 } = require("@scure/base");
  const tampered = Buffer.concat([
    Buffer.from(VECTORS[0][0], "hex"),
    Buffer.from(VECTORS[1][1], "hex"),
  ]);
  const encoded = base58.encode(tampered);
  assert.equal(isValidSolanaSecretKey(encoded), false);
  assert.throws(() => deriveSolanaAddress(encoded), /public key/i);
});

test("no thrown error echoes the secret material back", () => {
  const secret = vectorSecretKey(0);
  const seedHex = VECTORS[0][0];
  const truncated = secret.slice(0, 60);
  for (const value of [truncated, seedHex, `${secret}x`]) {
    let message = "";
    try {
      deriveSolanaAddress(value);
    } catch (error) {
      message = String(error && error.message);
    }
    assert.notEqual(message, "", "a malformed secret must throw");
    for (const fragment of [value, value.slice(0, 12), seedHex.slice(0, 12)]) {
      assert.ok(
        !message.includes(fragment),
        "an error message must never carry secret material into a log",
      );
    }
  }
});

test("redaction removes the secret from anything we might log", () => {
  const wallet = generateSolanaAgentWallet();
  const safe = redactSolanaWallet(wallet);

  assert.equal(safe.address, wallet.address);
  assert.equal("secretKey" in safe, false);
  assert.ok(!JSON.stringify(safe).includes(wallet.secretKey), "the secret must not survive serialisation");
});

test("redaction scrubs every secret spelling, at any depth, inside arrays too", () => {
  const wallet = generateSolanaAgentWallet();
  const safe = redactSolanaWallet({
    context: "zero-start",
    wallets: [{ solana: wallet }],
    nested: { deep: { secretKey: wallet.secretKey, secret_key: wallet.secretKey, privateKey: "x", seed: "y", mnemonic: "z" } },
  });
  const serialised = JSON.stringify(safe);
  assert.ok(!serialised.includes(wallet.secretKey));
  for (const field of ["secretKey", "secret_key", "privateKey", "seed", "mnemonic"]) {
    assert.ok(!serialised.includes(field), `${field} must not survive redaction`);
  }
  assert.equal(safe.context, "zero-start");
  assert.equal(safe.wallets[0].solana.address, wallet.address);
});

test("a wallet object never serialises its secret by default", () => {
  const wallet = generateSolanaAgentWallet();
  // The zero-start adapter puts wallet objects inside receipts and Telegram payloads. A plain
  // JSON.stringify of the wallet must already be safe, so forgetting redactSolanaWallet cannot leak.
  assert.ok(
    !JSON.stringify(wallet).includes(wallet.secretKey),
    "the secret must be non-enumerable, so stringify alone cannot leak it",
  );
  assert.ok(JSON.stringify(wallet).includes(wallet.address));
  // It is still readable by the custody writer that needs it.
  assert.equal(typeof wallet.secretKey, "string");
  assert.equal(deriveSolanaAddress(wallet.secretKey), wallet.address);
});

test("the earnings ledger secret scan passes on a redacted wallet and fails on a raw one", () => {
  const { assertNoSecret } = require("./earnings-ledger.js");
  const wallet = generateSolanaAgentWallet();
  assertNoSecret(redactSolanaWallet({ solana: wallet }));
  assert.throws(() => assertNoSecret({ solana: { secretKey: wallet.secretKey } }), /secret/i);
});
