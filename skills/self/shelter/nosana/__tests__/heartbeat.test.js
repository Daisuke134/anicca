// node:test — heartbeat: the pure signing/verification core of the S9 steward loop. A heartbeat
// is third-party-verifiable evidence the tenant process was alive: the message embeds a fresh
// Solana blockhash + slot (cannot be built before that slot existed) and is ed25519-signed by
// Franklin's own key (cannot be forged by anyone else). These tests use a THROWAWAY nacl keypair
// generated in-test — never Franklin's real secret.
import { test } from "node:test";
import assert from "node:assert/strict";
import nacl from "tweetnacl";
import bs58 from "bs58";
import {
  buildHeartbeatMessage,
  signHeartbeat,
  makeHeartbeatEntry,
  verifyHeartbeatEntry,
} from "../heartbeat.mjs";

function throwawayKeypair() {
  const kp = nacl.sign.keyPair();
  return { address: bs58.encode(kp.publicKey), secretBytes: kp.secretKey };
}

const FIELDS = {
  jobAddress: "CUcMnkzWL8RdNDtGw7pdbqE8xVawuPf2dUigQ3wS5qDs",
  payer: "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T",
  blockhash: "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
  slot: 312345678,
  ts: 1785000000.123,
  cycle: 7,
};

test("buildHeartbeatMessage: canonical JSON with sorted keys, deterministic", () => {
  const a = buildHeartbeatMessage(FIELDS);
  // Same fields given in a different property order must produce the identical string.
  const b = buildHeartbeatMessage({
    ts: FIELDS.ts,
    cycle: FIELDS.cycle,
    slot: FIELDS.slot,
    blockhash: FIELDS.blockhash,
    payer: FIELDS.payer,
    jobAddress: FIELDS.jobAddress,
  });
  assert.equal(a, b);
  const parsed = JSON.parse(a);
  assert.deepEqual(Object.keys(parsed), ["blockhash", "cycle", "jobAddress", "payer", "slot", "ts"]);
});

test("buildHeartbeatMessage: throws on missing/invalid fields", () => {
  for (const key of Object.keys(FIELDS)) {
    const broken = { ...FIELDS };
    delete broken[key];
    assert.throws(() => buildHeartbeatMessage(broken), new RegExp(key));
  }
  assert.throws(() => buildHeartbeatMessage({ ...FIELDS, slot: "not-a-number" }), /slot/);
  assert.throws(() => buildHeartbeatMessage({ ...FIELDS, cycle: -1 }), /cycle/);
});

test("sign + verify round-trip with a throwaway keypair", () => {
  const kp = throwawayKeypair();
  const entry = makeHeartbeatEntry({ ...FIELDS, payer: kp.address, secretBytes: kp.secretBytes });
  assert.equal(entry.v, 1);
  assert.equal(entry.kind, "shelter-heartbeat");
  assert.equal(entry.payer, kp.address);
  assert.equal(typeof entry.sig, "string");
  const verdict = verifyHeartbeatEntry(entry);
  assert.equal(verdict.valid, true, verdict.reason);
});

test("verify rejects a tampered field", () => {
  const kp = throwawayKeypair();
  const entry = makeHeartbeatEntry({ ...FIELDS, payer: kp.address, secretBytes: kp.secretBytes });
  const tampered = { ...entry, slot: entry.slot + 1 };
  const verdict = verifyHeartbeatEntry(tampered);
  assert.equal(verdict.valid, false);
});

test("verify rejects a signature from a different key claiming Franklin's address", () => {
  const kp = throwawayKeypair();
  const impostor = throwawayKeypair();
  const entry = makeHeartbeatEntry({ ...FIELDS, payer: kp.address, secretBytes: impostor.secretBytes });
  const verdict = verifyHeartbeatEntry(entry);
  assert.equal(verdict.valid, false);
});

test("verifyHeartbeatEntry never throws on garbage", () => {
  for (const garbage of [null, {}, { kind: "shelter-heartbeat" }, { ...FIELDS, sig: "%%%not-base58%%%", v: 1, kind: "shelter-heartbeat" }]) {
    const verdict = verifyHeartbeatEntry(garbage);
    assert.equal(verdict.valid, false);
    assert.equal(typeof verdict.reason, "string");
  }
});
