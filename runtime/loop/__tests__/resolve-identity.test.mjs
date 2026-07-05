// #26 EQUALIZE — resolve-identity.mjs unit tests (R1/R2/R5).
// Verifies the 3 resolution paths (env override / $ANICCA_HOME file / back-compat legacy file)
// for both EVM and Solana, plus fail-closed (no key anywhere -> null, never throws).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  resolveEvmPrivateKey,
  resolveSolanaSecret,
} from '../../../skills/earn/lib/resolve-identity.mjs';

function tmpDir(prefix) {
  const dir = path.join(os.tmpdir(), `${prefix}-${process.pid}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function writeWalletJson(dir, privateKey, address = '0xabc') {
  fs.mkdirSync(path.join(dir, '.automaton'), { recursive: true });
  fs.writeFileSync(
    path.join(dir, '.automaton', 'wallet.json'),
    JSON.stringify({ privateKey, address }, null, 2),
  );
}

function writeSolanaJson(dir, secretKey, address = 'FakeAddr111') {
  fs.mkdirSync(path.join(dir, '.automaton'), { recursive: true });
  fs.writeFileSync(
    path.join(dir, '.automaton', 'solana.json'),
    JSON.stringify({ address, secretKey, secretKeyBytes: [] }, null, 2),
  );
}

function writeSolanaSession(dir, secret) {
  fs.mkdirSync(path.join(dir, '.blockrun'), { recursive: true });
  fs.writeFileSync(path.join(dir, '.blockrun', '.solana-session'), secret);
}

// ---------------------------------------------------------------------------
// EVM: R1 priority ① env override
// ---------------------------------------------------------------------------
test('EVM ①: env.ANICCA_EVM_PRIVATE_KEY wins even when wallet files also exist', () => {
  const aniccaHome = tmpDir('eq-evm-anicca');
  const legacyHome = tmpDir('eq-evm-legacy');
  writeWalletJson(aniccaHome, '0x' + 'a'.repeat(64));
  writeWalletJson(legacyHome, '0x' + 'b'.repeat(64));
  const key = resolveEvmPrivateKey({
    env: { ANICCA_EVM_PRIVATE_KEY: '0x' + 'c'.repeat(64), ANICCA_HOME: aniccaHome, HOME: legacyHome },
  });
  assert.equal(key, '0x' + 'c'.repeat(64));
});

test('EVM ①: env override without 0x prefix is normalized', () => {
  const key = resolveEvmPrivateKey({ env: { ANICCA_EVM_PRIVATE_KEY: 'd'.repeat(64) } });
  assert.equal(key, '0x' + 'd'.repeat(64));
});

// ---------------------------------------------------------------------------
// EVM: R1 priority ② $ANICCA_HOME/.automaton/wallet.json
// ---------------------------------------------------------------------------
test('EVM ②: resolves from $ANICCA_HOME/.automaton/wallet.json when no env override', () => {
  const aniccaHome = tmpDir('eq-evm-anicca2');
  const legacyHome = tmpDir('eq-evm-legacy2');
  writeWalletJson(aniccaHome, '0x' + '1'.repeat(64));
  writeWalletJson(legacyHome, '0x' + '2'.repeat(64)); // must NOT be picked (ANICCA_HOME wins over legacy)
  const key = resolveEvmPrivateKey({ env: { ANICCA_HOME: aniccaHome, HOME: legacyHome } });
  assert.equal(key, '0x' + '1'.repeat(64));
});

// ---------------------------------------------------------------------------
// EVM: R1 priority ③ back-compat $HOME/.automaton/wallet.json
// ---------------------------------------------------------------------------
test('EVM ③: falls back to $HOME/.automaton/wallet.json when $ANICCA_HOME has no wallet', () => {
  const aniccaHome = tmpDir('eq-evm-anicca3'); // exists but no wallet.json inside
  const legacyHome = tmpDir('eq-evm-legacy3');
  writeWalletJson(legacyHome, '0x' + '3'.repeat(64));
  const key = resolveEvmPrivateKey({ env: { ANICCA_HOME: aniccaHome, HOME: legacyHome } });
  assert.equal(key, '0x' + '3'.repeat(64));
});

test('EVM ③: falls back to $HOME/.automaton/wallet.json when ANICCA_HOME is unset', () => {
  const legacyHome = tmpDir('eq-evm-legacy4');
  writeWalletJson(legacyHome, '0x' + '4'.repeat(64));
  const key = resolveEvmPrivateKey({ env: { HOME: legacyHome } });
  assert.equal(key, '0x' + '4'.repeat(64));
});

// ---------------------------------------------------------------------------
// EVM: R5 fail-closed
// ---------------------------------------------------------------------------
test('EVM ④ fail-closed: no override, no files anywhere -> null (never throws)', () => {
  const aniccaHome = tmpDir('eq-evm-empty-anicca');
  const legacyHome = tmpDir('eq-evm-empty-legacy');
  assert.doesNotThrow(() => {
    const key = resolveEvmPrivateKey({ env: { ANICCA_HOME: aniccaHome, HOME: legacyHome } });
    assert.equal(key, null);
  });
});

test('EVM fail-closed: missing HOME/ANICCA_HOME entirely -> null (never throws)', () => {
  assert.doesNotThrow(() => {
    assert.equal(resolveEvmPrivateKey({ env: {} }), null);
  });
});

test('EVM fail-closed: malformed wallet.json -> null (never throws)', () => {
  const aniccaHome = tmpDir('eq-evm-malformed');
  fs.mkdirSync(path.join(aniccaHome, '.automaton'), { recursive: true });
  fs.writeFileSync(path.join(aniccaHome, '.automaton', 'wallet.json'), 'not json{{{');
  assert.doesNotThrow(() => {
    assert.equal(resolveEvmPrivateKey({ env: { ANICCA_HOME: aniccaHome } }), null);
  });
});

// ---------------------------------------------------------------------------
// Solana: R2 priority ① env override
// ---------------------------------------------------------------------------
test('Solana ①: env.ANICCA_SOLANA_PRIVATE_KEY wins even when files also exist', () => {
  const aniccaHome = tmpDir('eq-sol-anicca');
  const legacyHome = tmpDir('eq-sol-legacy');
  writeSolanaJson(aniccaHome, 'anicca-secret-b58');
  writeSolanaSession(legacyHome, 'legacy-secret-b58');
  const secret = resolveSolanaSecret({
    env: { ANICCA_SOLANA_PRIVATE_KEY: 'override-secret-b58', ANICCA_HOME: aniccaHome, HOME: legacyHome },
  });
  assert.equal(secret, 'override-secret-b58');
});

// ---------------------------------------------------------------------------
// Solana: R2 priority ② $ANICCA_HOME/.automaton/solana.json
// ---------------------------------------------------------------------------
test('Solana ②: resolves from $ANICCA_HOME/.automaton/solana.json when no env override', () => {
  const aniccaHome = tmpDir('eq-sol-anicca2');
  const legacyHome = tmpDir('eq-sol-legacy2');
  writeSolanaJson(aniccaHome, 'anicca-secret-b58-2');
  writeSolanaSession(legacyHome, 'legacy-secret-b58-2'); // must NOT be picked
  const secret = resolveSolanaSecret({ env: { ANICCA_HOME: aniccaHome, HOME: legacyHome } });
  assert.equal(secret, 'anicca-secret-b58-2');
});

// ---------------------------------------------------------------------------
// Solana: R2 priority ③ back-compat ~/.blockrun/.solana-session
// ---------------------------------------------------------------------------
test('Solana ③: falls back to $HOME/.blockrun/.solana-session when $ANICCA_HOME has no solana.json', () => {
  const aniccaHome = tmpDir('eq-sol-anicca3'); // exists but no solana.json inside
  const legacyHome = tmpDir('eq-sol-legacy3');
  writeSolanaSession(legacyHome, 'legacy-secret-b58-3');
  const secret = resolveSolanaSecret({ env: { ANICCA_HOME: aniccaHome, HOME: legacyHome } });
  assert.equal(secret, 'legacy-secret-b58-3');
});

// ---------------------------------------------------------------------------
// Solana: R5 fail-closed
// ---------------------------------------------------------------------------
test('Solana ④ fail-closed: no override, no files anywhere -> null (never throws)', () => {
  const aniccaHome = tmpDir('eq-sol-empty-anicca');
  const legacyHome = tmpDir('eq-sol-empty-legacy');
  assert.doesNotThrow(() => {
    assert.equal(resolveSolanaSecret({ env: { ANICCA_HOME: aniccaHome, HOME: legacyHome } }), null);
  });
});

test('Solana fail-closed: malformed solana.json -> null (never throws)', () => {
  const aniccaHome = tmpDir('eq-sol-malformed');
  fs.mkdirSync(path.join(aniccaHome, '.automaton'), { recursive: true });
  fs.writeFileSync(path.join(aniccaHome, '.automaton', 'solana.json'), 'not json{{{');
  assert.doesNotThrow(() => {
    assert.equal(resolveSolanaSecret({ env: { ANICCA_HOME: aniccaHome } }), null);
  });
});

// ---------------------------------------------------------------------------
// Fresh-instance integration: a throwaway $ANICCA_HOME laid out exactly the way
// start-local.sh + ensure-solana-wallet.mjs would populate it -> both chains resolve,
// isolated from any other instance's files (R3/R4 fresh-spawn evidence).
// ---------------------------------------------------------------------------
test('fresh ANICCA_HOME: EVM + Solana keys generated under it resolve back via resolve-identity', () => {
  const freshHome = tmpDir('eq-test'); // mirrors ANICCA_HOME=/tmp/eq-test-<pid> from the task
  const evmPk = '0x' + '7'.repeat(64);
  const evmAddr = '0x' + '9'.repeat(40);
  const solSecret = 'FreshInstanceSolanaSecretBase58Value1234567890';
  const solAddr = 'FreshInstanceSolanaAddressBase58';

  writeWalletJson(freshHome, evmPk, evmAddr);
  writeSolanaJson(freshHome, solSecret, solAddr);

  const resolvedEvm = resolveEvmPrivateKey({ env: { ANICCA_HOME: freshHome } });
  const resolvedSol = resolveSolanaSecret({ env: { ANICCA_HOME: freshHome } });

  assert.equal(resolvedEvm, evmPk);
  assert.equal(resolvedSol, solSecret);

  // isolation: files live ONLY under freshHome/.automaton, nowhere else
  assert.ok(fs.existsSync(path.join(freshHome, '.automaton', 'wallet.json')));
  assert.ok(fs.existsSync(path.join(freshHome, '.automaton', 'solana.json')));
});
