// node:test — proof.mjs: challenge message shape + a REAL tweetnacl sign/verify round trip (not
// just "the function was called") — this is the cryptographic core of the whole S7 evidence claim,
// so it is proven against real ed25519 signing, not a mock.
import { test } from "node:test";
import assert from "node:assert/strict";
import { Keypair } from "@solana/web3.js";

import { buildChallengeMessage, signChallenge, verifyChallengeSignature, computeRunwayHoursInformational } from "../proof.mjs";

test("buildChallengeMessage: deterministic — same inputs produce the exact same string", () => {
  const opts = { address: "ADDR", blockhash: "BH", solLamports: 100, nosBalance: 0.5, runNumber: 3, ts: 12345 };
  assert.equal(buildChallengeMessage(opts), buildChallengeMessage({ ...opts }));
  assert.equal(
    buildChallengeMessage(opts),
    "nosana-tenant-proof-of-life|address=ADDR|blockhash=BH|solLamports=100|nosBalance=0.5|runNumber=3|ts=12345",
  );
});

test("buildChallengeMessage: differs whenever ANY field differs (binds the whole context, not just the address)", () => {
  const base = { address: "ADDR", blockhash: "BH", solLamports: 100, nosBalance: 0.5, runNumber: 3, ts: 12345 };
  const variants = [
    { ...base, blockhash: "BH2" },
    { ...base, solLamports: 101 },
    { ...base, nosBalance: 0.6 },
    { ...base, runNumber: 4 },
    { ...base, ts: 12346 },
  ];
  const baseMsg = buildChallengeMessage(base);
  for (const v of variants) {
    assert.notEqual(buildChallengeMessage(v), baseMsg);
  }
});

test("buildChallengeMessage: fails closed on missing/non-finite fields", () => {
  assert.throws(() => buildChallengeMessage({ blockhash: "BH", solLamports: 1, nosBalance: 1, runNumber: 1, ts: 1 }), /address/);
  assert.throws(() => buildChallengeMessage({ address: "A", blockhash: "BH", solLamports: NaN, nosBalance: 1, runNumber: 1, ts: 1 }), /solLamports/);
});

test("REGRESSION: sign then verify with REAL tweetnacl + a REAL generated Solana keypair actually round-trips", async () => {
  const kp = Keypair.generate();
  const message = buildChallengeMessage({
    address: kp.publicKey.toBase58(),
    blockhash: "5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d",
    solLamports: 23505190,
    nosBalance: 2.495705,
    runNumber: 1,
    ts: Date.now() / 1000,
  });
  const signatureBytes = await signChallenge({ message, secretKeyBytes: kp.secretKey });
  const verified = await verifyChallengeSignature({
    message,
    signatureBytes,
    publicKeyBytes: kp.publicKey.toBytes(),
  });
  assert.equal(verified, true);
});

test("verifyChallengeSignature: a tampered message fails verification", async () => {
  const kp = Keypair.generate();
  const message = "original message";
  const signatureBytes = await signChallenge({ message, secretKeyBytes: kp.secretKey });
  const verified = await verifyChallengeSignature({
    message: "tampered message",
    signatureBytes,
    publicKeyBytes: kp.publicKey.toBytes(),
  });
  assert.equal(verified, false);
});

test("verifyChallengeSignature: a signature from a DIFFERENT key fails verification against this address", async () => {
  const kpA = Keypair.generate();
  const kpB = Keypair.generate();
  const message = "some message";
  const signatureBytes = await signChallenge({ message, secretKeyBytes: kpA.secretKey });
  const verified = await verifyChallengeSignature({
    message,
    signatureBytes,
    publicKeyBytes: kpB.publicKey.toBytes(),
  });
  assert.equal(verified, false);
});

test("signChallenge: fails closed on a malformed secretKeyBytes", async () => {
  await assert.rejects(() => signChallenge({ message: "m", secretKeyBytes: new Uint8Array(10) }), /64-byte/);
});

test("signChallenge: honors an injected signImpl (for hermetic orchestration tests elsewhere)", async () => {
  let called = null;
  const fakeSig = new Uint8Array([1, 2, 3]);
  const result = await signChallenge({
    message: "m",
    secretKeyBytes: new Uint8Array(64),
    signImpl: (msgBytes, secretBytes) => {
      called = { msgBytes, secretBytes };
      return fakeSig;
    },
  });
  assert.equal(result, fakeSig);
  assert.ok(called);
});

test("computeRunwayHoursInformational: divides balance by burn rate", () => {
  assert.equal(computeRunwayHoursInformational({ nosBalance: 2, nosPerHourBurnRate: 0.5 }), 4);
});

test("computeRunwayHoursInformational: returns null (never throws) on an unknown/non-positive rate", () => {
  assert.equal(computeRunwayHoursInformational({ nosBalance: 2, nosPerHourBurnRate: 0 }), null);
  assert.equal(computeRunwayHoursInformational({ nosBalance: 2, nosPerHourBurnRate: null }), null);
  assert.equal(computeRunwayHoursInformational({ nosBalance: 2, nosPerHourBurnRate: undefined }), null);
});

test("computeRunwayHoursInformational: returns null on an invalid balance rather than throwing", () => {
  assert.equal(computeRunwayHoursInformational({ nosBalance: -1, nosPerHourBurnRate: 1 }), null);
  assert.equal(computeRunwayHoursInformational({ nosBalance: NaN, nosPerHourBurnRate: 1 }), null);
});
