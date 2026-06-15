const { test } = require("node:test");
const assert = require("node:assert");
const { newChildWallet, assertDistinct } = require("../child-wallet");

test("newChildWallet returns a valid 0x address + private key", () => {
  const w = newChildWallet();
  assert.match(w.address, /^0x[a-fA-F0-9]{40}$/);
  assert.match(w.privateKey, /^0x[a-fA-F0-9]{64}$/);
});

test("two child wallets are distinct", () => {
  const a = newChildWallet(), b = newChildWallet();
  assert.notEqual(a.address.toLowerCase(), b.address.toLowerCase());
});

test("assertDistinct passes for different addresses", () => {
  assert.doesNotThrow(() =>
    assertDistinct("0x1111111111111111111111111111111111111111", "0x2222222222222222222222222222222222222222"));
});

test("assertDistinct throws when child collides with parent (case-insensitive)", () => {
  assert.throws(() => assertDistinct("0xABCabcABCabcABCabcABCabcABCabcABCabcABCa", "0xabcabcabcabcabcabcabcabcabcabcabcabcabca"));
});

test("the private key recovers the address (sign/recover sanity)", async () => {
  const { Wallet, verifyMessage } = require("ethers");
  const w = newChildWallet();
  const wallet = new Wallet(w.privateKey);
  const sig = await wallet.signMessage("hello");
  assert.equal(verifyMessage("hello", sig).toLowerCase(), w.address.toLowerCase());
});
