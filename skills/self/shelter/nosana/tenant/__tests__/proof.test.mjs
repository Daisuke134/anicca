// node:test — proof.mjs: challenge message shape + a REAL tweetnacl sign/verify round trip (not
// just "the function was called") — this is the cryptographic core of the whole S7 evidence claim,
// so it is proven against real ed25519 signing, not a mock.
import { test } from "node:test";
import assert from "node:assert/strict";
import { Keypair } from "@solana/web3.js";

import { buildChallengeMessage, signChallenge, verifyChallengeSignature } from "../proof.mjs";

function baseOpts() {
  return {
    ephemeralAddress: "EPHEMERAL_ADDR",
    blockhash: "BH",
    treasuryAddress: "TREASURY_ADDR",
    treasurySolLamports: 26066471,
    treasuryNosBalance: 2.495705,
    nosPerHour: 0.188945,
    runwayHours: 13.2,
    rateSource: "active-job:JOB1",
    ts: 12345,
  };
}

test("buildChallengeMessage: deterministic — same inputs produce the exact same string", () => {
  const opts = baseOpts();
  assert.equal(buildChallengeMessage(opts), buildChallengeMessage({ ...opts }));
  assert.equal(
    buildChallengeMessage(opts),
    "nosana-tenant-proof-of-life-v2|ephemeralAddress=EPHEMERAL_ADDR|blockhash=BH|treasuryAddress=TREASURY_ADDR|" +
      "treasurySolLamports=26066471|treasuryNosBalance=2.495705|nosPerHour=0.188945|runwayHours=13.2|" +
      "rateSource=active-job:JOB1|ts=12345",
  );
});

test("buildChallengeMessage: differs whenever ANY field differs (binds the whole context, not just the address)", () => {
  const base = baseOpts();
  const variants = [
    { ...base, blockhash: "BH2" },
    { ...base, treasurySolLamports: 101 },
    { ...base, treasuryNosBalance: 0.6 },
    { ...base, nosPerHour: 0.2 },
    { ...base, runwayHours: 14 },
    { ...base, rateSource: "market-fallback:MKT" },
    { ...base, ts: 12346 },
  ];
  const baseMsg = buildChallengeMessage(base);
  for (const v of variants) {
    assert.notEqual(buildChallengeMessage(v), baseMsg);
  }
});

test("buildChallengeMessage: honors null nosPerHour/runwayHours (the honest 'rate unavailable' case)", () => {
  const msg = buildChallengeMessage({ ...baseOpts(), nosPerHour: null, runwayHours: null, rateSource: "unavailable: no active job and no eligible market" });
  assert.match(msg, /nosPerHour=null/);
  assert.match(msg, /runwayHours=null/);
});

test("buildChallengeMessage: fails closed on missing/non-finite required fields", () => {
  const base = baseOpts();
  assert.throws(() => buildChallengeMessage({ ...base, ephemeralAddress: undefined }), /ephemeralAddress/);
  assert.throws(() => buildChallengeMessage({ ...base, treasuryAddress: "" }), /treasuryAddress/);
  assert.throws(() => buildChallengeMessage({ ...base, rateSource: "" }), /rateSource/);
  assert.throws(() => buildChallengeMessage({ ...base, treasurySolLamports: NaN }), /treasurySolLamports/);
  assert.throws(() => buildChallengeMessage({ ...base, nosPerHour: "not-a-number" }), /nosPerHour/);
});

test("REGRESSION: sign then verify with REAL tweetnacl + a REAL generated Solana keypair actually round-trips", async () => {
  const kp = Keypair.generate();
  const message = buildChallengeMessage({
    ...baseOpts(),
    ephemeralAddress: kp.publicKey.toBase58(),
    blockhash: "5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d",
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
