// PROP-001 — address-classify.mjs unit tests (franklin-loop-revival, REQ-002).
//
// RED PHASE: `../address-classify.mjs` does not exist yet (Phase 2b introduces it). Every test
// below therefore fails at import time until the module + its three exports
// (isEvmAddress/isSolanaAddress/classifyAddress) are implemented. This is the expected RED
// evidence for REQ-002 / PROP-001.
//
// Contract this test file defines for Phase 2b (verification-architecture.md "New pure predicate"):
//   isEvmAddress(address)    -> boolean   (true iff /^0x[0-9a-fA-F]{40}$/)
//   isSolanaAddress(address) -> boolean   (true iff base58, 32-90 chars, matching the SAME
//                                          alphabet already used by skills/_shared/lib/solana-verify.mjs's
//                                          B58_RE — no new alphabet invented)
//   classifyAddress(address) -> 'evm' | 'solana' | 'invalid'
// Pure, synchronous, no I/O, no network — string-shape classification only (verification-architecture.md
// Purity Boundary Map).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { isEvmAddress, isSolanaAddress, classifyAddress } from '../address-classify.mjs';

const EVM_ADDR = '0x' + 'a'.repeat(40);
const EVM_ADDR_MIXED_CASE = '0x' + 'A1b2C3d4E5f60718293a4b5c6d7e8f9012345678';
// Franklin's real, live Solana wallet address (behavioral-spec.md Context) — 44 chars, base58.
const SOLANA_ADDR = '8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9';

test('PROP-001: classifyAddress(evm 0x+40hex) === "evm"', () => {
  assert.equal(classifyAddress(EVM_ADDR), 'evm');
});

test('PROP-001: classifyAddress accepts mixed-case hex (checksummed) as evm', () => {
  assert.equal(classifyAddress(EVM_ADDR_MIXED_CASE), 'evm');
});

test('PROP-001: classifyAddress(Franklin real Solana address) === "solana"', () => {
  assert.equal(classifyAddress(SOLANA_ADDR), 'solana');
});

test('PROP-001: a valid 0x+40hex string is NEVER classified "solana"', () => {
  assert.notEqual(classifyAddress(EVM_ADDR), 'solana');
  assert.equal(isSolanaAddress(EVM_ADDR), false);
});

test('PROP-001: a valid base58 32-byte-decodable string is NEVER classified "evm"', () => {
  assert.notEqual(classifyAddress(SOLANA_ADDR), 'evm');
  assert.equal(isEvmAddress(SOLANA_ADDR), false);
});

test('PROP-001: empty string -> invalid', () => {
  assert.equal(classifyAddress(''), 'invalid');
});

test('PROP-001: "unknown" (index.mjs\'s own placeholder) -> invalid', () => {
  assert.equal(classifyAddress('unknown'), 'invalid');
});

test('PROP-001: too-short 0x string -> invalid (not evm, not solana)', () => {
  assert.equal(classifyAddress('0x123'), 'invalid');
});

test('PROP-001: too-long 0x string (41 hex chars) -> invalid', () => {
  assert.equal(classifyAddress('0x' + 'a'.repeat(41)), 'invalid');
});

test('PROP-001: 0x string with non-hex chars -> invalid', () => {
  assert.equal(classifyAddress('0x' + 'g'.repeat(40)), 'invalid');
});

test('PROP-001: non-string inputs (null/undefined/number) -> invalid, never throw', () => {
  assert.doesNotThrow(() => {
    assert.equal(classifyAddress(null), 'invalid');
    assert.equal(classifyAddress(undefined), 'invalid');
    assert.equal(classifyAddress(123), 'invalid');
  });
});

test('PROP-001: classifyAddress returns EXACTLY one of evm/solana/invalid for any input (never both true)', () => {
  const table = [EVM_ADDR, SOLANA_ADDR, '', 'unknown', '0x123', 'not-base58-!!!', null, undefined, 123];
  for (const input of table) {
    const result = classifyAddress(input);
    assert.ok(['evm', 'solana', 'invalid'].includes(result), `unexpected classification: ${result}`);
    // isEvmAddress/isSolanaAddress must agree with classifyAddress and never both be true
    const evm = isEvmAddress(input);
    const sol = isSolanaAddress(input);
    assert.ok(!(evm && sol), `both evm and solana true for ${JSON.stringify(input)}`);
    assert.equal(result === 'evm', evm);
    assert.equal(result === 'solana', sol);
  }
});
