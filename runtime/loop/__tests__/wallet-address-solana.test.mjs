// REQ-001, REQ-005, REQ-006, PROP-005, PROP-007, PROP-008, PROP-012 —
// Franklin Solana wallet-address resolution (franklin-loop-revival).
//
// RED PHASE: `runtime/wallet-address-solana.mjs` does not exist yet (Phase 2b introduces it,
// mirroring the EXISTING `runtime/wallet-address.mjs` EVM CLI convention: a script that resolves
// THIS instance's own key via resolve-identity.mjs and prints ONLY the derived address to stdout —
// see behavioral-spec.md's Purity Boundary Analysis "new sibling module"). Every test below spawns
// it as a child process and therefore fails with ENOENT/MODULE_NOT_FOUND until Phase 2b creates it.
//
// Contract this test file defines for Phase 2b:
//   node runtime/wallet-address-solana.mjs
//     reads resolve-identity.mjs::resolveSolanaSecret({}) (same per-instance gate as the EVM
//     sibling), derives the base58 public key via @solana/web3.js Keypair + bs58 (both already repo
//     deps — see package.json), prints ONLY the address + "\n" to stdout on success.
//   Any failure (missing secret, malformed secret, wrong-length secret) MUST NOT crash the process:
//     exit code 0, empty stdout, a WARNING on stderr that never contains the raw secret material.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const MODULE_PATH = path.resolve(__dirname, '../../wallet-address-solana.mjs');

// Franklin's real, live production wallet — behavioral-spec.md Context, verified 2026-07 top-up.
const FRANKLIN_REAL_HOME = '/home/life-manager/.blockrun';
const FRANKLIN_REAL_ADDR = '8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9';

function tmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), `${prefix}-`));
}

function writeSolanaSession(legacyHome, content) {
  const dir = path.join(legacyHome, '.blockrun');
  fs.mkdirSync(dir, { recursive: true });
  if (content !== undefined) {
    fs.writeFileSync(path.join(dir, '.solana-session'), content);
  }
}

function runHelper(env) {
  return spawnSync(process.execPath, [MODULE_PATH], {
    env: { ...env },
    encoding: 'utf8',
    timeout: 10_000,
  });
}

// ---------------------------------------------------------------------------
// REQ-001 acceptance criterion #1 + PROP-005: one live invocation against Franklin's REAL home.
// ---------------------------------------------------------------------------
test('PROP-005 (live): ANICCA_HOME=/home/life-manager/.blockrun ANICCA_INSTANCE=franklin prints EXACTLY Franklin\'s real address and nothing else on stdout', () => {
  const result = runHelper({
    PATH: process.env.PATH,
    HOME: '/home/life-manager',
    ANICCA_HOME: FRANKLIN_REAL_HOME,
    ANICCA_INSTANCE: 'franklin',
  });
  assert.equal(result.status, 0, `must exit 0 (stderr: ${result.stderr})`);
  assert.equal(result.stdout, `${FRANKLIN_REAL_ADDR}\n`, 'stdout must be exactly the address + newline, nothing else');
});

// ---------------------------------------------------------------------------
// REQ-001 edge case: missing / empty .solana-session -> warn, no crash, nothing on stdout.
// ---------------------------------------------------------------------------
test('REQ-001 edge case: missing .solana-session -> empty stdout, WARNING on stderr, exit 0 (no crash)', () => {
  const legacyHome = tmpDir('wsol-missing');
  // deliberately do NOT create .blockrun/.solana-session
  const result = runHelper({
    PATH: process.env.PATH,
    HOME: legacyHome,
    ANICCA_HOME: path.join(legacyHome, '.blockrun'),
  });
  assert.equal(result.status, 0);
  assert.equal(result.stdout, '');
  assert.match(result.stderr, /warn/i);
});

test('REQ-001 edge case: empty .solana-session file -> empty stdout, WARNING, exit 0 (no crash)', () => {
  const legacyHome = tmpDir('wsol-empty');
  writeSolanaSession(legacyHome, '');
  const result = runHelper({
    PATH: process.env.PATH,
    HOME: legacyHome,
    ANICCA_HOME: path.join(legacyHome, '.blockrun'),
  });
  assert.equal(result.status, 0);
  assert.equal(result.stdout, '');
  assert.match(result.stderr, /warn/i);
});

// ---------------------------------------------------------------------------
// PROP-012 exhaustive fixture table: {malformed-base58-chars, valid-base58-wrong-length, valid}
// ---------------------------------------------------------------------------
test('PROP-012: malformed base58 (invalid chars) -> catch, empty stdout, WARNING (never the raw secret), exit 0 (no crash)', () => {
  const legacyHome = tmpDir('wsol-badchars');
  const rawSecret = 'this-has-0OIl-and-punctuation!!!-not-base58';
  writeSolanaSession(legacyHome, rawSecret);
  const result = runHelper({
    PATH: process.env.PATH,
    HOME: legacyHome,
    ANICCA_HOME: path.join(legacyHome, '.blockrun'),
  });
  assert.equal(result.status, 0, `must NOT crash the process (stderr: ${result.stderr})`);
  assert.equal(result.stdout, '', 'must print nothing to stdout on derivation failure');
  assert.match(result.stderr, /warn/i, 'must log a WARNING');
  assert.ok(!result.stderr.includes(rawSecret), 'stderr must NEVER contain the raw fixture secret (REQ-006/PROP-008)');
});

test('PROP-012: valid base58 but WRONG BYTE LENGTH -> catch (Keypair derivation throws), empty stdout, WARNING (never the raw secret), exit 0', async () => {
  const bs58 = (await import('bs58')).default;
  const legacyHome = tmpDir('wsol-wronglen');
  // 10-byte buffer encodes to valid base58 but is not a valid 64-byte Solana secret key.
  const shortBuf = Buffer.from(Array.from({ length: 10 }, (_, i) => i + 1));
  const rawSecret = bs58.encode(shortBuf);
  writeSolanaSession(legacyHome, rawSecret);
  const result = runHelper({
    PATH: process.env.PATH,
    HOME: legacyHome,
    ANICCA_HOME: path.join(legacyHome, '.blockrun'),
  });
  assert.equal(result.status, 0, `must NOT crash the process (stderr: ${result.stderr})`);
  assert.equal(result.stdout, '');
  assert.match(result.stderr, /warn/i);
  assert.ok(!result.stderr.includes(rawSecret), 'stderr must NEVER contain the raw fixture secret (REQ-006/PROP-008)');
});

test('PROP-012: valid, well-formed secret (fresh self-consistent fixture, NOT Franklin\'s real key) -> derives the matching address, nothing else on stdout, secret never leaked', async () => {
  const { Keypair } = await import('@solana/web3.js');
  const bs58 = (await import('bs58')).default;
  const legacyHome = tmpDir('wsol-valid');
  const keypair = Keypair.generate();
  const rawSecret = bs58.encode(Buffer.from(keypair.secretKey));
  const expectedAddr = keypair.publicKey.toBase58();
  writeSolanaSession(legacyHome, rawSecret);
  const result = runHelper({
    PATH: process.env.PATH,
    HOME: legacyHome,
    ANICCA_HOME: path.join(legacyHome, '.blockrun'),
  });
  assert.equal(result.status, 0, `must exit 0 (stderr: ${result.stderr})`);
  assert.equal(result.stdout, `${expectedAddr}\n`);
  assert.ok(!result.stdout.includes(rawSecret), 'stdout must contain the derived ADDRESS only, never the raw secret (PROP-008)');
  assert.ok(!result.stderr.includes(rawSecret), 'stderr must never contain the raw secret either');
});

// ---------------------------------------------------------------------------
// REQ-001 edge case #3 / PROP-007: fail-closed identity gate — a foreign ANICCA_HOME must NEVER
// inherit another home's real .solana-session (mirrors resolve-identity.test.mjs's existing
// "foreign spawn does NOT inherit" convention).
// ---------------------------------------------------------------------------
test('PROP-007: foreign ANICCA_HOME (different from $HOME/.blockrun) resolves NOTHING even though a real .solana-session exists at $HOME/.blockrun', () => {
  const legacyHome = tmpDir('wsol-foreign-legacy');
  const foreignHome = tmpDir('wsol-foreign-spawn');
  writeSolanaSession(legacyHome, 'some-real-secret-that-must-never-leak-cross-instance');
  const result = runHelper({
    PATH: process.env.PATH,
    HOME: legacyHome,
    ANICCA_HOME: foreignHome, // NOT $HOME/.blockrun
  });
  assert.equal(result.status, 0);
  assert.equal(result.stdout, '', 'a foreign spawn must never resolve legacyHome\'s .blockrun secret');
});

test('PROP-007: default ANICCA_HOME (unset, falls back to $HOME/.anicca) resolves nothing for Franklin\'s Solana identity', () => {
  const legacyHome = tmpDir('wsol-default-legacy');
  writeSolanaSession(legacyHome, 'another-real-secret-must-not-leak');
  const result = runHelper({
    PATH: process.env.PATH,
    HOME: legacyHome,
    // ANICCA_HOME intentionally unset -> defaults to $HOME/.anicca, not $HOME/.blockrun
  });
  assert.equal(result.status, 0);
  assert.equal(result.stdout, '');
});
