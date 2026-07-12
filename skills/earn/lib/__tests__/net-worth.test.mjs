/**
 * net-worth.test.mjs — unit tests for the multi-chain / multi-token net-worth reader.
 * No network: every RPC and the spot-price endpoint go through an injected fake fetch.
 */
import assert from 'node:assert/strict';
import {
  fetchNetWorth, hexToUnits, balanceOfCalldata, EVM_TOKENS, SOLANA_USDC_MINT, resolveInstanceWallets,
} from '../net-worth.mjs';

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); console.log(`  ok  ${name}`); pass++; }
  catch (e) { console.error(`  FAIL ${name}\n       ${e.message}`); fail++; }
}
async function ta(name, fn) {
  try { await fn(); console.log(`  ok  ${name}`); pass++; }
  catch (e) { console.error(`  FAIL ${name}\n       ${e.message}`); fail++; }
}

const ok = (obj) => ({ json: async () => obj });

/** Build a fake fetch from a per-(url,method) responder. Records every call for assertions. */
function fakeFetch(handler) {
  const calls = [];
  const f = async (url, init) => {
    const body = init?.body ? JSON.parse(init.body) : null;
    calls.push({ url, method: body?.method, params: body?.params });
    return handler(url, body, calls);
  };
  f.calls = calls;
  return f;
}

console.log('net-worth.mjs');

// ---- pure helpers ---------------------------------------------------------------------------
t('hexToUnits: 6-decimal token', () => {
  assert.equal(hexToUnits('0x' + (14148061).toString(16), 6), 14.148061);
});
t('hexToUnits: empty / 0x / null → 0 (unfunded ERC-20 read, not a crash)', () => {
  assert.equal(hexToUnits('0x', 6), 0);
  assert.equal(hexToUnits(null, 6), 0);
  assert.equal(hexToUnits(undefined, 6), 0);
});
t('hexToUnits: 18-decimal native', () => {
  assert.equal(hexToUnits('0x' + (2n * 10n ** 18n).toString(16), 18), 2);
});
t('balanceOfCalldata: selector + 32-byte left-padded address, lowercased', () => {
  const d = balanceOfCalldata('0x810F6D61F7606dEEE2657d3083E150a222Bc29C5');
  assert.equal(d, '0x70a08231' + '0'.repeat(24) + '810f6d61f7606deee2657d3083e150a222bc29c5');
  assert.equal(d.length, 10 + 64);
});
t('balanceOfCalldata: rejects a non-EVM address instead of silently querying garbage', () => {
  assert.throws(() => balanceOfCalldata('8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9'), /not an EVM address/);
});

// ---- the bug this module exists to fix -------------------------------------------------------
await ta('counts the Polymarket deposit wallet pUSD the old Base-only reader could not see', async () => {
  const f = fakeFetch(async (url, body) => {
    if (url.includes('polygon')) {
      const to = body.params[0].to.toLowerCase();
      // pUSD holds $14.15; the other Polygon stables are empty
      if (to === EVM_TOKENS.polygon.find((x) => x.symbol === 'pUSD').address.toLowerCase()) {
        return ok({ result: '0x' + (14148061).toString(16) });
      }
      return ok({ result: '0x0' });
    }
    return ok({ result: '0x0' });
  });
  const r = await fetchNetWorth(
    [{ chain: 'polygon', address: '0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74', label: 'pm-deposit' }],
    { fetchImpl: f, includeNative: false },
  );
  assert.equal(r.total_usd, 14.148061);
  assert.equal(r.holdings.length, 1);
  assert.equal(r.holdings[0].symbol, 'pUSD');
  assert.deepEqual(r.errors, []);
});

await ta('counts Solana SOL as well as USDC (the SOL the loop was blind to)', async () => {
  const f = fakeFetch(async (url, body) => {
    if (body?.method === 'getTokenAccountsByOwner') {
      assert.equal(body.params[1].mint, SOLANA_USDC_MINT);
      return ok({ result: { value: [{ account: { data: { parsed: { info: { tokenAmount: { uiAmount: 26.34 } } } } } }] } });
    }
    if (body?.method === 'getBalance') return ok({ result: { value: 205_000_000 } }); // 0.205 SOL
    if (String(url).includes('SOL-USD')) return ok({ data: { amount: '76.9' } });
    return ok({ result: null });
  });
  const r = await fetchNetWorth([{ chain: 'solana', address: '8Fpqd', label: 'franklin' }], { fetchImpl: f });
  const sol = r.holdings.find((h) => h.symbol === 'SOL');
  const usdc = r.holdings.find((h) => h.symbol === 'USDC');
  assert.equal(usdc.usd, 26.34);
  assert.ok(sol.priced);
  assert.equal(Math.round(sol.usd * 100) / 100, 15.76); // 0.205 * 76.9
  assert.equal(Math.round(r.total_usd * 100) / 100, 42.1);
});

await ta('aggregates across chains AND wallets into one number', async () => {
  const f = fakeFetch(async (url, body) => {
    if (body?.method === 'getTokenAccountsByOwner') {
      return ok({ result: { value: [{ account: { data: { parsed: { info: { tokenAmount: { uiAmount: 10 } } } } } }] } });
    }
    if (body?.method === 'eth_call') return ok({ result: '0x' + (5_000_000).toString(16) }); // $5 in every EVM token
    return ok({ result: null });
  });
  const r = await fetchNetWorth([
    { chain: 'base', address: '0x810f6d61f7606deee2657d3083e150a222bc29c5', label: 'evm' },
    { chain: 'polygon', address: '0x810f6d61f7606deee2657d3083e150a222bc29c5', label: 'evm' },
    { chain: 'solana', address: '8Fpqd', label: 'sol' },
  ], { fetchImpl: f, includeNative: false });
  // base: 1 token * $5 ; polygon: 3 tokens * $5 ; solana: $10  => $30
  assert.equal(r.total_usd, 30);
  assert.equal(r.holdings.length, 5);
});

// ---- fail-safe behaviour --------------------------------------------------------------------
await ta('a failing RPC degrades ONE leg to an error and still returns the legs that read', async () => {
  const f = fakeFetch(async (url, body) => {
    if (url.includes('polygon')) return ok({ error: { message: 'rpc exploded' } });
    if (body?.method === 'eth_call') return ok({ result: '0x' + (7_000_000).toString(16) });
    return ok({ result: null });
  });
  const r = await fetchNetWorth([
    { chain: 'base', address: '0x810f6d61f7606deee2657d3083e150a222bc29c5' },
    { chain: 'polygon', address: '0x810f6d61f7606deee2657d3083e150a222bc29c5' },
  ], { fetchImpl: f, includeNative: false });
  assert.equal(r.total_usd, 7);              // the Base leg survived
  assert.equal(r.errors.length, 3);          // all 3 Polygon tokens errored
  assert.ok(r.errors.every((e) => /rpc exploded/.test(e.error)));
});

await ta('an unpriceable native asset counts as $0 and is flagged — never guessed', async () => {
  const f = fakeFetch(async (url, body) => {
    if (body?.method === 'getBalance') return ok({ result: { value: 1_000_000_000 } }); // 1 SOL
    if (body?.method === 'getTokenAccountsByOwner') return ok({ result: { value: [] } });
    if (String(url).includes('SOL-USD')) throw new Error('price feed down');
    return ok({ result: null });
  });
  const r = await fetchNetWorth([{ chain: 'solana', address: '8Fpqd' }], { fetchImpl: f });
  const sol = r.holdings.find((h) => h.symbol === 'SOL');
  assert.equal(sol.amount, 1);
  assert.equal(sol.usd, 0, 'unpriceable asset must contribute 0, not a guess');
  assert.equal(sol.priced, false);
  assert.equal(r.total_usd, 0);
  assert.ok(r.errors.some((e) => /no spot price/.test(e.error)));
});

await ta('zero balances are omitted from holdings (no noise rows)', async () => {
  const f = fakeFetch(async () => ok({ result: '0x0' }));
  const r = await fetchNetWorth(
    [{ chain: 'base', address: '0x810f6d61f7606deee2657d3083e150a222bc29c5' }],
    { fetchImpl: f, includeNative: false },
  );
  assert.equal(r.total_usd, 0);
  assert.deepEqual(r.holdings, []);
  assert.deepEqual(r.errors, []);
});

await ta('counts a Hyperliquid margin account — money no chain reader can see', async () => {
  const f = fakeFetch(async (url, body) => {
    if (body?.type === 'clearinghouseState') {
      return ok({ marginSummary: { accountValue: '7.720186' }, assetPositions: [{}] });
    }
    return ok({ result: '0x0' });
  });
  const r = await fetchNetWorth(
    [{ chain: 'hyperliquid', address: '0x810f6d61f7606deee2657d3083e150a222bc29c5', label: 'HL' }],
    { fetchImpl: f },
  );
  assert.equal(r.total_usd, 7.720186);
  assert.equal(r.holdings[0].chain, 'hyperliquid');
  assert.deepEqual(r.errors, []);
});

await ta('a Hyperliquid account that never deposited contributes 0, not NaN', async () => {
  const f = fakeFetch(async (url, body) => {
    if (body?.type === 'clearinghouseState') return ok({ marginSummary: { accountValue: '0.0' } });
    return ok({ result: '0x0' });
  });
  const r = await fetchNetWorth([{ chain: 'hyperliquid', address: '0xdead' }], { fetchImpl: f });
  assert.equal(r.total_usd, 0);
  assert.deepEqual(r.holdings, []);
  assert.deepEqual(r.errors, []);
});

await ta('an unknown chain is reported, not silently dropped', async () => {
  const f = fakeFetch(async () => ok({ result: '0x0' }));
  const r = await fetchNetWorth([{ chain: 'dogecoin', address: 'D123' }], { fetchImpl: f });
  assert.equal(r.total_usd, 0);
  assert.equal(r.errors.length, 1);
  assert.match(r.errors[0].error, /unknown chain/);
});

await ta('spot price is fetched once per asset, not once per wallet', async () => {
  const f = fakeFetch(async (url, body) => {
    if (body?.method === 'getBalance') return ok({ result: { value: 1_000_000_000 } });
    if (body?.method === 'getTokenAccountsByOwner') return ok({ result: { value: [] } });
    if (String(url).includes('SOL-USD')) return ok({ data: { amount: '76.9' } });
    return ok({ result: null });
  });
  await fetchNetWorth(
    [{ chain: 'solana', address: 'A' }, { chain: 'solana', address: 'B' }, { chain: 'solana', address: 'C' }],
    { fetchImpl: f },
  );
  const priceCalls = f.calls.filter((c) => String(c.url).includes('SOL-USD'));
  assert.equal(priceCalls.length, 1, 'price must be cached across wallets');
});

// ---- wallet resolution ----------------------------------------------------------------------
t('resolveInstanceWallets: an EVM address expands to Base + Polygon + Hyperliquid', () => {
  const w = resolveInstanceWallets({ ANICCA_WALLET_ADDRESS: '0x810f6d61f7606deee2657d3083e150a222bc29c5' });
  assert.deepEqual(w.map((x) => x.chain).sort(), ['base', 'hyperliquid', 'polygon']);
});
t('resolveInstanceWallets: a Solana address resolves to the Solana leg only', () => {
  const w = resolveInstanceWallets({ ANICCA_WALLET_ADDRESS: '8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9' });
  assert.deepEqual(w.map((x) => x.chain), ['solana']);
});
t('resolveInstanceWallets: ANICCA_EXTRA_WALLETS adds venue wallets (e.g. the PM deposit proxy)', () => {
  const w = resolveInstanceWallets({
    ANICCA_WALLET_ADDRESS: '0x810f6d61f7606deee2657d3083e150a222bc29c5',
    ANICCA_EXTRA_WALLETS: JSON.stringify([
      { chain: 'polygon', address: '0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74', label: 'PM deposit' },
    ]),
  });
  assert.equal(w.length, 4);
  assert.ok(w.some((x) => x.label === 'PM deposit'));
});
t('resolveInstanceWallets: malformed ANICCA_EXTRA_WALLETS is ignored, never crashes the wake', () => {
  const w = resolveInstanceWallets({
    ANICCA_WALLET_ADDRESS: '0x810f6d61f7606deee2657d3083e150a222bc29c5',
    ANICCA_EXTRA_WALLETS: '{not json',
  });
  assert.equal(w.length, 3);
});
t('resolveInstanceWallets: no address → empty list (caller keeps prior behaviour, no throw)', () => {
  const saved = process.env.ANICCA_WALLET_ADDRESS;
  delete process.env.ANICCA_WALLET_ADDRESS;
  assert.deepEqual(resolveInstanceWallets({}), []);
  if (saved !== undefined) process.env.ANICCA_WALLET_ADDRESS = saved;
});

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
