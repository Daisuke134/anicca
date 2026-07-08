// PROP-002 — balance.mjs Solana-dispatch unit tests (franklin-loop-revival, REQ-002).
//
// RED PHASE: `fetchUsdcBalance` currently (pre-Phase-2b) validates ONLY `/^0x[0-9a-fA-F]{40}$/`
// and throws `invalid wallet address: ...` for ANY base58 Solana address — including Franklin's
// own real wallet. Every "new capability" test below therefore FAILS today (it throws instead of
// resolving/rejecting the way REQ-002 requires) until Phase 2b adds the Solana branch.
//
// Contract this test file defines for Phase 2b (verification-architecture.md):
//   fetchUsdcBalance(address, config) — when classifyAddress(address) === 'solana' — MUST
//   delegate to skills/_shared/lib/solana-verify.mjs::usdcBalance(address, opts), NOT reimplement
//   RPC parsing. To keep this a pure unit test (no real network), the Solana branch MUST accept an
//   injectable transport the same way solana-verify.mjs's own tests do (see
//   skills/_shared/lib/__tests__/solana-verify.test.js's fakeFetch convention): this test assumes
//   the dispatch code reads `config.SOLANA_FETCH_IMPL` (a function) and forwards it as
//   `usdcBalance(address, { fetchImpl: config.SOLANA_FETCH_IMPL })` — mirroring the EXISTING
//   `ANICCA_BALANCE_OVERRIDE` test-hook convention already used for the EVM path in this same file.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { fetchUsdcBalance } from '../balance.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BALANCE_SRC_PATH = path.resolve(__dirname, '../balance.mjs');

// Franklin's real, live Solana wallet address (behavioral-spec.md Context).
const SOLANA_ADDR = '8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9';

// Build a fake fetch that returns a canned JSON-RPC result for the requested method — same shape
// as skills/_shared/lib/__tests__/solana-verify.test.js's fakeFetch (NOT a new mock convention).
function fakeSolanaFetch(byMethod) {
  return async (_url, init) => {
    const body = JSON.parse(init.body);
    const result = byMethod[body.method];
    if (result === undefined) throw new Error(`unexpected method ${body.method}`);
    return { ok: true, json: async () => ({ jsonrpc: '2.0', id: body.id, result }) };
  };
}

function config(extra = {}) {
  return { BALANCE_CACHE_TTL_S: 0, ...extra };
}

test('PROP-002/REQ-002 AC1: fetchUsdcBalance(Franklin real Solana address) resolves a real numeric balance instead of throwing "invalid wallet address"', async () => {
  const value = [{
    account: { data: { parsed: { info: { tokenAmount: { amount: '11630000', decimals: 6, uiAmount: 11.63, uiAmountString: '11.63' } } } } },
  }];
  const fetchImpl = fakeSolanaFetch({ getTokenAccountsByOwner: { value } });
  const balance = await fetchUsdcBalance(SOLANA_ADDR, config({ SOLANA_FETCH_IMPL: fetchImpl }));
  assert.equal(typeof balance, 'number');
  assert.ok(Number.isFinite(balance), 'balance must be finite, not throw invalid wallet address');
  assert.equal(balance, 11.63);
});

test('PROP-002: zero-ATA Solana wallet -> fetchUsdcBalance resolves 0 (does NOT throw), matching usdcBalance\'s own "no ATA" behavior', async () => {
  const fetchImpl = fakeSolanaFetch({ getTokenAccountsByOwner: { value: [] } });
  const balance = await fetchUsdcBalance(SOLANA_ADDR, config({ SOLANA_FETCH_IMPL: fetchImpl }));
  assert.equal(balance, 0);
});

test('PROP-002: Solana RPC failure propagates as a throw (caller keeps prior tier) — NOT the generic "invalid wallet address" message', async () => {
  const fetchImpl = async () => ({ ok: false, status: 503, json: async () => ({}) });
  await assert.rejects(
    () => fetchUsdcBalance(SOLANA_ADDR, config({ SOLANA_FETCH_IMPL: fetchImpl })),
    (err) => {
      // Today this call throws "invalid wallet address: 8Fpqd..." — the exact wrong-diagnosis
      // this requirement retires. After the fix it must surface the REAL RPC failure instead.
      assert.ok(!/invalid wallet address/i.test(err.message), `must not still be the address-shape error: ${err.message}`);
      return true;
    },
  );
});

test('PROP-002: dispatch does NOT reimplement Solana RPC parsing — balance.mjs must import usdcBalance from solana-verify.mjs, not define its own getTokenAccountsByOwner call', () => {
  const source = fs.readFileSync(BALANCE_SRC_PATH, 'utf8');
  assert.ok(
    /from\s+['"].*solana-verify\.mjs['"]/.test(source),
    'balance.mjs must import from skills/_shared/lib/solana-verify.mjs (REQ-002: reuse, do not port)',
  );
  assert.ok(
    !/getTokenAccountsByOwner/.test(source),
    'balance.mjs must NOT define its own getTokenAccountsByOwner RPC call — that logic belongs to solana-verify.mjs only',
  );
});
