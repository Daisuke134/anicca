// node:test — derive-address.mjs: the self-contained address derivation + in-job env resolution.
import { test } from "node:test";
import assert from "node:assert/strict";
import bs58 from "bs58";
import { Keypair } from "@solana/web3.js";

import { deriveAddressFromSecret, resolveTenantSecretForJob } from "../derive-address.mjs";

test("deriveAddressFromSecret: real generated keypair round-trips to its own public address", () => {
  const kp = Keypair.generate();
  const secretBase58 = bs58.encode(kp.secretKey);
  const { address, secretBytes } = deriveAddressFromSecret(secretBase58);
  assert.equal(address, kp.publicKey.toBase58());
  assert.deepEqual(Array.from(secretBytes), Array.from(kp.secretKey));
});

test("deriveAddressFromSecret: rejects a non-base58 string without echoing it back", () => {
  assert.throws(() => deriveAddressFromSecret("not-valid-base58-!!!"), (err) => {
    assert.match(err.message, /not valid base58/);
    assert.doesNotMatch(err.message, /not-valid-base58/);
    return true;
  });
});

test("deriveAddressFromSecret: rejects wrong-length decoded secrets", () => {
  const tooShort = bs58.encode(Buffer.from("short"));
  assert.throws(() => deriveAddressFromSecret(tooShort), /64-byte secret key/);
});

test("deriveAddressFromSecret: rejects empty/non-string input", () => {
  assert.throws(() => deriveAddressFromSecret(""), /non-empty string/);
  assert.throws(() => deriveAddressFromSecret(undefined), /non-empty string/);
});

test("resolveTenantSecretForJob: resolves ONLY from NOSANA_TENANT_SECRET_KEY", () => {
  const kp = Keypair.generate();
  const secretBase58 = bs58.encode(kp.secretKey);
  const { address } = resolveTenantSecretForJob({ env: { NOSANA_TENANT_SECRET_KEY: secretBase58 } });
  assert.equal(address, kp.publicKey.toBase58());
});

test("resolveTenantSecretForJob: fails closed (throws) when the env var is missing", () => {
  assert.throws(() => resolveTenantSecretForJob({ env: {} }), /NOSANA_TENANT_SECRET_KEY is not set/);
});

test("resolveTenantSecretForJob: never falls back to any treasury-style env var (e.g. ANICCA_SOLANA_PRIVATE_KEY)", () => {
  const kp = Keypair.generate();
  assert.throws(
    () => resolveTenantSecretForJob({ env: { ANICCA_SOLANA_PRIVATE_KEY: bs58.encode(kp.secretKey) } }),
    /NOSANA_TENANT_SECRET_KEY is not set/,
  );
});
