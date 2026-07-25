// node:test — tenant/keypair.mjs (Mac-side): generation + idempotent local persistence.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import bs58 from "bs58";

import { generateTenantKeypair, ensureLocalTenantKeypair, TENANT_KEYPAIR_FILE_NAME } from "../keypair.mjs";
import { deriveAddressFromSecret } from "../derive-address.mjs";

test("generateTenantKeypair: produces a real, valid Solana keypair (address derivable from its own secret)", async () => {
  const generated = await generateTenantKeypair({});
  const derived = deriveAddressFromSecret(generated.secretBase58);
  assert.equal(derived.address, generated.address);
});

test("generateTenantKeypair: two calls never produce the same address (real randomness, not a fixture)", async () => {
  const a = await generateTenantKeypair({});
  const b = await generateTenantKeypair({});
  assert.notEqual(a.address, b.address);
});

test("ensureLocalTenantKeypair: first call generates + persists; second call against the same home returns the SAME address", async () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "tenant-keypair-test-"));
  try {
    const first = await ensureLocalTenantKeypair({ home });
    assert.equal(first.created, true);
    assert.ok(fs.existsSync(first.keypairPath));
    assert.equal(path.basename(first.keypairPath), TENANT_KEYPAIR_FILE_NAME);

    const second = await ensureLocalTenantKeypair({ home });
    assert.equal(second.created, false);
    assert.equal(second.address, first.address);
    assert.equal(second.secretBase58, first.secretBase58);
  } finally {
    fs.rmSync(home, { recursive: true, force: true });
  }
});

test("ensureLocalTenantKeypair: persisted file is 0600, parent dir is 0700 (mirrors ../keypair.mjs's discipline)", async () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "tenant-keypair-perm-test-"));
  try {
    const { keypairPath } = await ensureLocalTenantKeypair({ home });
    const fileMode = fs.statSync(keypairPath).mode & 0o777;
    const dirMode = fs.statSync(path.dirname(keypairPath)).mode & 0o777;
    assert.equal(fileMode, 0o600);
    assert.equal(dirMode, 0o700);
  } finally {
    fs.rmSync(home, { recursive: true, force: true });
  }
});

test("ensureLocalTenantKeypair: never writes the secret in plaintext next to an unrelated field name (basic sanity: file round-trips via deriveAddressFromSecret)", async () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "tenant-keypair-roundtrip-"));
  try {
    const { keypairPath, address, secretBase58 } = await ensureLocalTenantKeypair({ home });
    const onDisk = JSON.parse(fs.readFileSync(keypairPath, "utf8"));
    assert.equal(onDisk.address, address);
    assert.equal(onDisk.secretBase58, secretBase58);
    assert.equal(deriveAddressFromSecret(onDisk.secretBase58).address, address);
  } finally {
    fs.rmSync(home, { recursive: true, force: true });
  }
});

test("ensureLocalTenantKeypair: throws when neither home nor ANICCA_HOME is provided", async () => {
  await assert.rejects(() => ensureLocalTenantKeypair({ env: {} }), /ANICCA_HOME/);
});

test("ensureLocalTenantKeypair: throws a clear error on a malformed existing file rather than silently regenerating", async () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "tenant-keypair-malformed-"));
  try {
    const dir = path.join(home, ".automaton");
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, TENANT_KEYPAIR_FILE_NAME), JSON.stringify({ notAddress: true }));
    await assert.rejects(() => ensureLocalTenantKeypair({ home }), /missing address\/secretBase58/);
  } finally {
    fs.rmSync(home, { recursive: true, force: true });
  }
});

test("generateTenantKeypair: bs58-encoded secret is exactly the same format Franklin's treasury secret uses (round-trips through the SAME deriveAddressFromSecret)", async () => {
  const generated = await generateTenantKeypair({});
  // If this format ever drifted from the treasury's own base58 64-byte layout, this would throw.
  assert.doesNotThrow(() => deriveAddressFromSecret(generated.secretBase58));
  assert.equal(bs58.decode(generated.secretBase58).length, 64);
});
