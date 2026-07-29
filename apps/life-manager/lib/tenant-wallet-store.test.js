"use strict";
// AE-ZERO-START-1 §4.3 / §5.1 / §5.4 — per-tenant key custody on the local rail.
//
// This is the only place in the slice where private key material touches a disk, so the tests are about
// the four ways that goes wrong: the file is readable by someone else (mode), the file and the database
// disagree about which wallet a tenant owns (collision — money at the old address would be abandoned),
// a second provisioning run mints a second wallet (double-spend of identity), and one tenant's key
// leaking into another tenant's path.
//
// Every test writes under a per-test LM_DATA_ROOT in a temp directory. Nothing here may touch the real
// ${HOME}/.anicca default — the default is only ever asserted as a string.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const {
  MAX_WALLET_BYTES,
  createTenantWalletKeychain,
  ensureTenantWallets,
  readTenantWallet,
  tenantWalletKeyRef,
  tenantWalletPaths,
  walletRootDir,
} = require("./tenant-wallet-store.js");
const { deriveAddress } = require("./agent-wallet.js");
const { deriveSolanaAddress } = require("./agent-wallet-solana.js");

function sandbox() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-tenant-wallets-"));
  return { LM_DATA_ROOT: root };
}

function provision(uid, env, extra = {}) {
  return ensureTenantWallets(uid, { env, now: () => "2026-07-30T00:00:00.000Z", ...extra });
}

function fileFingerprint(filePath) {
  const stat = fs.statSync(filePath);
  return { content: fs.readFileSync(filePath, "utf8"), mode: stat.mode & 0o777 };
}

test("the wallet root defaults to ~/.anicca/wallets and is overridable", () => {
  assert.equal(walletRootDir({}), path.join(os.homedir(), ".anicca", "wallets"));
  assert.equal(walletRootDir({ LM_DATA_ROOT: "/srv/lm" }), path.join("/srv/lm", "wallets"));
  // A relative root would put key files wherever the process happens to be running.
  assert.throws(() => walletRootDir({ LM_DATA_ROOT: "relative/path" }), /absolute/i);
});

test("each tenant gets its own directory and the two canonical filenames", () => {
  const env = sandbox();
  const a = tenantWalletPaths("tenant-a", env);
  const b = tenantWalletPaths("tenant-b", env);

  assert.equal(a.dir, path.join(env.LM_DATA_ROOT, "wallets", "tenant-a"));
  assert.equal(a.base, path.join(a.dir, "base.json"));
  assert.equal(a.solana, path.join(a.dir, "solana.json"));
  assert.notEqual(a.dir, b.dir);
  for (const key of ["dir", "base", "solana"]) {
    assert.notEqual(a[key], b[key], `${key} must be per-tenant`);
  }
});

test("a uid that could escape its own directory is refused", () => {
  const env = sandbox();
  for (const uid of ["", "   ", "..", "../evil", "a/b", "/abs", "tenant a", ".hidden", "x".repeat(200), null]) {
    assert.throws(() => tenantWalletPaths(uid, env), /tenant/i, `${uid} must be refused`);
  }
});

test("a key reference names the tenant and the rail, and nothing else", () => {
  assert.equal(tenantWalletKeyRef("tenant-a", "base"), "secret://lm-agent-wallet/tenant-a/base");
  assert.equal(tenantWalletKeyRef("tenant-a", "solana"), "secret://lm-agent-wallet/tenant-a/solana");
  assert.notEqual(tenantWalletKeyRef("tenant-a", "base"), tenantWalletKeyRef("tenant-b", "base"));
  assert.throws(() => tenantWalletKeyRef("tenant-a", "bitcoin"), /rail/i);
});

test("a key reference is a value the database will actually accept", () => {
  // The migration's CHECK is the real gate (§5.3). A ref this module mints that the schema refuses would
  // fail provisioning in production and pass every test here, so the two are compared directly.
  const SQL = fs.readFileSync(
    path.join(__dirname, "../migrations/2026-07-30-lm-tenant-agent-wallets.sql"),
    "utf8",
  );
  const grammar = /agent_wallet_key_ref ~ '([^']+)'/.exec(SQL);
  assert.ok(grammar, "the migration must carry a key-ref grammar");
  const pattern = new RegExp(grammar[1]);
  for (const uid of ["tenant-a", "550e8400-e29b-41d4-a716-446655440000", "u.1_ok"]) {
    for (const rail of ["base", "solana"]) {
      const ref = tenantWalletKeyRef(uid, rail);
      assert.match(ref, pattern, `${ref} must satisfy the database CHECK`);
      assert.ok(ref.length >= 12 && ref.length <= 200);
      assert.doesNotMatch(ref, /[0-9a-fA-F]{64}/);
    }
  }
});

test("first provisioning writes both key files 0600 in a 0700 directory", () => {
  const env = sandbox();
  const result = provision("tenant-a", env);

  assert.equal(result.status, "created");
  assert.equal(result.base.status, "created");
  assert.equal(result.solana.status, "created");

  const paths = tenantWalletPaths("tenant-a", env);
  assert.equal(fs.statSync(paths.dir).mode & 0o777, 0o700, "the directory must not be group/world readable");
  for (const filePath of [paths.base, paths.solana]) {
    assert.equal(fs.statSync(filePath).mode & 0o777, 0o600, "a key file must be 0600");
  }

  // The files hold real, self-consistent key material.
  const base = JSON.parse(fs.readFileSync(paths.base, "utf8"));
  assert.equal(deriveAddress(base.privateKey), base.address);
  assert.equal(base.address, result.base.address);
  const solana = JSON.parse(fs.readFileSync(paths.solana, "utf8"));
  assert.equal(deriveSolanaAddress(solana.secretKey), solana.address);
  assert.equal(solana.address, result.solana.address);

  // And nothing temporary is left behind.
  assert.deepEqual(fs.readdirSync(paths.dir).sort(), ["base.json", "solana.json"]);
});

test("the returned result carries public identity only — never key material", () => {
  const env = sandbox();
  const result = provision("tenant-a", env);
  const paths = tenantWalletPaths("tenant-a", env);
  const secrets = [
    JSON.parse(fs.readFileSync(paths.base, "utf8")).privateKey,
    JSON.parse(fs.readFileSync(paths.solana, "utf8")).secretKey,
  ];

  const serialised = JSON.stringify(result);
  for (const secret of secrets) {
    assert.ok(secret && secret.length > 32);
    assert.ok(!serialised.includes(secret), "a secret must never reach the adapter's return value");
  }
  const { assertNoSecret } = require("./earnings-ledger.js");
  assertNoSecret(result);
});

test("the result is exactly the set of database columns the migration added", () => {
  const env = sandbox();
  const result = provision("tenant-a", env);
  assert.deepEqual(Object.keys(result.columns).sort(), [
    "agent_wallet_address",
    "agent_wallet_created_at",
    "agent_wallet_key_ref",
    "agent_wallet_solana_address",
    "agent_wallet_solana_key_ref",
  ]);
  assert.equal(result.columns.agent_wallet_address, result.base.address);
  assert.equal(result.columns.agent_wallet_solana_address, result.solana.address);
  assert.equal(result.columns.agent_wallet_key_ref, tenantWalletKeyRef("tenant-a", "base"));
  assert.equal(result.columns.agent_wallet_solana_key_ref, tenantWalletKeyRef("tenant-a", "solana"));
  assert.equal(result.columns.agent_wallet_created_at, "2026-07-30T00:00:00.000Z");
});

test("a second run with an agreeing database row is a no-op, not a second wallet", () => {
  const env = sandbox();
  const first = provision("tenant-a", env);
  const paths = tenantWalletPaths("tenant-a", env);
  const before = [fileFingerprint(paths.base), fileFingerprint(paths.solana)];

  let generated = 0;
  const second = provision("tenant-a", env, {
    existing: first.columns,
    generateBase: () => { generated += 1; throw new Error("must not mint a second EVM wallet"); },
    generateSolana: () => { generated += 1; throw new Error("must not mint a second Solana wallet"); },
  });

  assert.equal(generated, 0, "an already-provisioned tenant must not draw new entropy");
  assert.equal(second.status, "existing");
  assert.equal(second.base.address, first.base.address);
  assert.equal(second.solana.address, first.solana.address);
  assert.deepEqual([fileFingerprint(paths.base), fileFingerprint(paths.solana)], before);
});

test("a run with no database row at all adopts the existing key files rather than replacing them", () => {
  // The row can legitimately be missing: the file write succeeded and the DB update did not. Minting a
  // new wallet here would abandon anything already sent to the address on disk.
  const env = sandbox();
  const first = provision("tenant-a", env);
  const second = provision("tenant-a", env, {
    existing: null,
    generateBase: () => { throw new Error("must not mint"); },
    generateSolana: () => { throw new Error("must not mint"); },
  });
  assert.equal(second.status, "existing");
  assert.equal(second.base.address, first.base.address);
  assert.equal(second.solana.address, first.solana.address);
});

test("a key file that disagrees with the database hard-stops and is never overwritten", () => {
  const env = sandbox();
  const first = provision("tenant-a", env);
  const paths = tenantWalletPaths("tenant-a", env);
  const before = fileFingerprint(paths.base);

  assert.throws(
    () => provision("tenant-a", env, {
      existing: {
        ...first.columns,
        agent_wallet_address: "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
      },
    }),
    (error) => {
      assert.equal(error.code, "WALLET_KEY_ADDRESS_MISMATCH");
      assert.equal(error.rail, "base");
      return true;
    },
  );
  assert.deepEqual(fileFingerprint(paths.base), before, "a mismatch must never rewrite the key file");
});

test("a database address with no key file hard-stops instead of minting a replacement", () => {
  const env = sandbox();
  assert.throws(
    () => provision("tenant-a", env, {
      existing: { agent_wallet_solana_address: "FVen3X669xLzsi6N2V91DoiyzHzg1uAgqiT8jZ9nS96Z" },
    }),
    (error) => {
      assert.equal(error.code, "WALLET_KEY_FILE_MISSING");
      assert.equal(error.rail, "solana");
      return true;
    },
  );
  // Nothing was written on the way to the refusal.
  const paths = tenantWalletPaths("tenant-a", env);
  assert.equal(fs.existsSync(paths.solana), false);
});

test("a key file anyone else can read is refused on read", () => {
  const env = sandbox();
  provision("tenant-a", env);
  const paths = tenantWalletPaths("tenant-a", env);
  for (const mode of [0o644, 0o660, 0o604, 0o700]) {
    fs.chmodSync(paths.base, mode);
    assert.throws(() => readTenantWallet("tenant-a", "base", { env }), /0600/);
  }
  fs.chmodSync(paths.base, 0o600);
  assert.equal(readTenantWallet("tenant-a", "base", { env }).address.startsWith("0x"), true);
});

test("a symlinked key file is refused — the target's mode says nothing about the link", () => {
  const env = sandbox();
  const result = provision("tenant-a", env);
  const paths = tenantWalletPaths("tenant-a", env);
  const moved = `${paths.base}.real`;
  fs.renameSync(paths.base, moved);
  fs.symlinkSync(moved, paths.base);
  assert.throws(() => readTenantWallet("tenant-a", "base", { env }), /symlink|regular file/i);
  assert.equal(result.base.address.startsWith("0x"), true);
});

test("an empty, oversized, malformed, or tampered key file is refused", () => {
  const env = sandbox();
  provision("tenant-a", env);
  const paths = tenantWalletPaths("tenant-a", env);
  const original = fs.readFileSync(paths.base, "utf8");

  const write = (content) => {
    fs.writeFileSync(paths.base, content, { mode: 0o600 });
    fs.chmodSync(paths.base, 0o600);
  };

  write("");
  assert.throws(() => readTenantWallet("tenant-a", "base", { env }), /size/i);

  write("x".repeat(MAX_WALLET_BYTES + 1));
  assert.throws(() => readTenantWallet("tenant-a", "base", { env }), /size/i);

  write("{not json");
  assert.throws(() => readTenantWallet("tenant-a", "base", { env }), /JSON/i);

  // The address swapped for another tenant's: the key no longer derives it, so signing would produce
  // receipts nobody can verify against the stated address.
  const tampered = { ...JSON.parse(original), address: "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf" };
  write(JSON.stringify(tampered));
  assert.throws(() => readTenantWallet("tenant-a", "base", { env }), /derive/i);

  write(original);
  assert.equal(readTenantWallet("tenant-a", "base", { env }).address, JSON.parse(original).address);
});

test("no thrown error carries key material into a log", () => {
  const env = sandbox();
  provision("tenant-a", env);
  const paths = tenantWalletPaths("tenant-a", env);
  const secret = JSON.parse(fs.readFileSync(paths.base, "utf8")).privateKey;

  fs.writeFileSync(paths.base, JSON.stringify({ address: "0xnope", privateKey: secret }), { mode: 0o600 });
  fs.chmodSync(paths.base, 0o600);
  let message = "";
  try {
    readTenantWallet("tenant-a", "base", { env });
  } catch (error) {
    message = `${error.message}\n${error.stack}`;
  }
  assert.notEqual(message, "");
  assert.ok(!message.includes(secret), "an error must never echo the key");
  assert.ok(!message.includes(secret.slice(0, 16)));
});

test("two tenants provisioned in the same root share nothing", () => {
  const env = sandbox();
  const a = provision("tenant-a", env);
  const b = provision("tenant-b", env);

  assert.notEqual(a.base.address, b.base.address);
  assert.notEqual(a.solana.address, b.solana.address);
  assert.notEqual(a.columns.agent_wallet_key_ref, b.columns.agent_wallet_key_ref);
  assert.notEqual(a.columns.agent_wallet_solana_key_ref, b.columns.agent_wallet_solana_key_ref);

  const pathsA = tenantWalletPaths("tenant-a", env);
  const pathsB = tenantWalletPaths("tenant-b", env);
  const secretA = JSON.parse(fs.readFileSync(pathsA.base, "utf8")).privateKey;
  const secretB = JSON.parse(fs.readFileSync(pathsB.base, "utf8")).privateKey;
  assert.notEqual(secretA, secretB);
  assert.ok(!fs.readFileSync(pathsB.base, "utf8").includes(secretA), "tenant A's key must not be in B's file");
  assert.ok(!fs.readFileSync(pathsA.base, "utf8").includes(secretB));

  // Re-running A leaves B's files byte-identical.
  const beforeB = [fileFingerprint(pathsB.base), fileFingerprint(pathsB.solana)];
  provision("tenant-a", env, { existing: a.columns });
  assert.deepEqual([fileFingerprint(pathsB.base), fileFingerprint(pathsB.solana)], beforeB);
});

test("the secret provider seam resolves only the asking tenant's own key", async () => {
  const env = sandbox();
  const a = provision("tenant-a", env);
  provision("tenant-b", env);
  const { createSecretProvider } = require("./secret-provider.js");
  const provider = createSecretProvider({ mode: "local", keychain: createTenantWalletKeychain({ env }) });

  assert.equal(await provider.health().then((h) => h.ok), true);

  const baseSecret = await provider.get("tenant-a", tenantWalletKeyRef("tenant-a", "base"));
  assert.equal(deriveAddress(baseSecret), a.base.address);
  const solanaSecret = await provider.get("tenant-a", tenantWalletKeyRef("tenant-a", "solana"));
  assert.equal(deriveSolanaAddress(solanaSecret), a.solana.address);

  // Cross-tenant reads are the whole risk in this slice.
  await assert.rejects(
    () => provider.get("tenant-a", tenantWalletKeyRef("tenant-b", "base")),
    /scope/i,
  );
  await assert.rejects(() => provider.get("tenant-a", "secret://telegram/bot-token"), /reference/i);
  await assert.rejects(() => provider.get("tenant-c", tenantWalletKeyRef("tenant-c", "base")), /wallet/i);
});
