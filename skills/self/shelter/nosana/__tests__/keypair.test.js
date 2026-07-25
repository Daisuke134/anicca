// node:test — keypair: address derivation + keypair-file materialization. Not one of the four
// pure modules the spec explicitly requires tests for, but this is the single most money-critical
// piece of code in this skill (it touches Franklin's real private key), so it gets tests anyway.
//
// The fixture secret below is a FRESH, randomly generated, never-funded, throwaway test keypair
// (generated once via `Keypair.generate()` purely to have a known secret/address pair) — it is
// NOT Franklin's real wallet and holds no funds.
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fsp } from "node:fs";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { deriveAddressFromSecret, materializeKeypairFile, ensureNosanaKeypair } from "../keypair.mjs";

const FIXTURE_SECRET_BASE58 = "XGWTVYQosP9baocV7vLADYZ9Jtz28Jqg9VSTxZzChmzi8GhD1rgFrZVgrPXbmFeNnVd8xUoKX1an1Ss2CECXq3C";
const FIXTURE_ADDRESS = "84JLtrs64tNPQbXiwwsGG9WhPDHZw7dB7VuWsDaRbkRL";

test("deriveAddressFromSecret recovers the known address for a fixture secret", () => {
  const { address, secretBytes } = deriveAddressFromSecret(FIXTURE_SECRET_BASE58);
  assert.equal(address, FIXTURE_ADDRESS);
  assert.equal(secretBytes.length, 64);
});

test("deriveAddressFromSecret rejects invalid base58 without echoing the input", () => {
  assert.throws(
    () => deriveAddressFromSecret("not-valid-base58-!!!"),
    (err) => err instanceof Error && !err.message.includes("not-valid-base58"),
  );
});

test("deriveAddressFromSecret rejects a secret of the wrong byte length", () => {
  // A valid base58 string, but far too short to be a 64-byte secret key.
  assert.throws(() => deriveAddressFromSecret("2NEpo7TZRRrLZSi2U"), /64-byte secret key/);
});

test("deriveAddressFromSecret rejects empty/non-string input", () => {
  assert.throws(() => deriveAddressFromSecret(""), /non-empty string/);
  assert.throws(() => deriveAddressFromSecret(undefined), /non-empty string/);
});

test("materializeKeypairFile writes a 0600 JSON-array file into a 0700 parent dir", async () => {
  const dir = await fsp.mkdtemp(path.join(os.tmpdir(), "nosana-keypair-test-"));
  const keypairPath = path.join(dir, "sub", "nosana_key.json");
  const { secretBytes } = deriveAddressFromSecret(FIXTURE_SECRET_BASE58);

  materializeKeypairFile({ secretBytes, keypairPath });

  const fileStat = fs.statSync(keypairPath);
  const dirStat = fs.statSync(path.dirname(keypairPath));
  assert.equal(fileStat.mode & 0o777, 0o600);
  assert.equal(dirStat.mode & 0o777, 0o700);

  const written = JSON.parse(fs.readFileSync(keypairPath, "utf8"));
  assert.deepEqual(written, Array.from(secretBytes));
  assert.equal(written.length, 64);
});

test("materializeKeypairFile is idempotent — a second call overwrites in place", async () => {
  const dir = await fsp.mkdtemp(path.join(os.tmpdir(), "nosana-keypair-test-"));
  const keypairPath = path.join(dir, "nosana_key.json");
  const { secretBytes } = deriveAddressFromSecret(FIXTURE_SECRET_BASE58);
  materializeKeypairFile({ secretBytes, keypairPath });
  materializeKeypairFile({ secretBytes, keypairPath });
  const entries = fs.readdirSync(dir);
  assert.deepEqual(entries, ["nosana_key.json"]);
});

test("ensureNosanaKeypair resolves via ANICCA_SOLANA_PRIVATE_KEY override and writes under home/.automaton", async () => {
  const dir = await fsp.mkdtemp(path.join(os.tmpdir(), "nosana-keypair-home-"));
  const result = ensureNosanaKeypair({
    home: dir,
    env: { ANICCA_SOLANA_PRIVATE_KEY: FIXTURE_SECRET_BASE58 },
  });
  assert.equal(result.address, FIXTURE_ADDRESS);
  assert.equal(result.keypairPath, path.join(dir, ".automaton", "nosana_key.json"));
  const written = JSON.parse(fs.readFileSync(result.keypairPath, "utf8"));
  assert.equal(written.length, 64);
});

test("ensureNosanaKeypair fails closed with a secret-free message when no secret resolves", () => {
  assert.throws(
    () => ensureNosanaKeypair({ home: "/no/such/home", env: {} }),
    /no Solana secret resolved/,
  );
});
