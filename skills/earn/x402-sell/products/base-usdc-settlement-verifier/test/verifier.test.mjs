import test from 'node:test';
import assert from 'node:assert/strict';

import { verifyBaseUsdcSettlement } from '../src/verifier.mjs';

const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const TRANSFER = [
  '0xddf252ad1be2c89b69c2b068fc378daa',
  '952ba7f163c4a11628f55a4df523b3ef',
].join('');
const TX = `0x${'ab'.repeat(32)}`;
const BLOCK_HASH = `0x${'cd'.repeat(32)}`;
const PAYER = '0x1111111111111111111111111111111111111111';
const PAY_TO = '0x2222222222222222222222222222222222222222';

function addressTopic(address) {
  return `0x${'0'.repeat(24)}${address.slice(2).toLowerCase()}`;
}

function validReceipt(overrides = {}) {
  return {
    transactionHash: TX,
    status: '0x1',
    blockNumber: '0x60',
    blockHash: BLOCK_HASH,
    logs: [{
      address: USDC,
      topics: [TRANSFER, addressTopic(PAYER), addressTopic(PAY_TO)],
      data: '0x0f4240',
    }],
    ...overrides,
  };
}

function rpcFetch(overrides = {}) {
  const receipt = overrides.receipt || validReceipt();
  const transaction = overrides.transaction || { hash: TX, from: PAYER };
  return async (_url, init) => {
    const request = JSON.parse(init.body);
    const results = {
      eth_chainId: overrides.chainId || '0x2105',
      eth_getTransactionReceipt: receipt,
      eth_getTransactionByHash: transaction,
    };
    const result = request.method === 'eth_getBlockByNumber'
      ? (request.params[0] === 'finalized'
        ? (overrides.finalized || { number: '0x64' })
        : (overrides.canonicalBlock || { number: '0x60', hash: BLOCK_HASH }))
      : results[request.method];
    return Response.json({ jsonrpc: '2.0', id: request.id, result });
  };
}

test('verifies an exact finalized external Base USDC transfer and returns a safe proof', async () => {
  const proof = await verifyBaseUsdcSettlement({
    txHash: TX,
    expectedPayTo: PAY_TO,
    expectedAmountAtomic: '1000000',
    selfWallets: ['0x3333333333333333333333333333333333333333'],
    fetchImpl: rpcFetch(),
  });

  assert.deepEqual(proof, {
    verified: true,
    chainId: 8453,
    txHash: TX,
    blockNumber: 96,
    finalizedBlock: 100,
    usdc: USDC.toLowerCase(),
    payer: PAYER,
    payTo: PAY_TO,
    amountAtomic: '1000000',
  });
});

test('rejects a receipt whose block hash is not canonical below the finalized head', async () => {
  await assert.rejects(() => verifyBaseUsdcSettlement({
    txHash: TX,
    expectedPayTo: PAY_TO,
    expectedAmountAtomic: '1000000',
    fetchImpl: rpcFetch({
      canonicalBlock: { number: '0x60', hash: `0x${'ef'.repeat(32)}` },
    }),
  }), /canonical block mismatch/);
});

test('fails closed on wrong chain, failed or unfinalized receipt, wrong transfer, self-pay, and ambiguity', async () => {
  const exactLog = validReceipt().logs[0];
  const cases = [
    { name: 'wrong chain', rpc: { chainId: '0x1' }, error: /wrong chain/ },
    { name: 'failed receipt', rpc: { receipt: validReceipt({ status: '0x0' }) }, error: /failed receipt/ },
    { name: 'unfinalized receipt', rpc: { receipt: validReceipt({ blockNumber: '0x65' }) }, error: /not finalized/ },
    {
      name: 'wrong amount',
      rpc: { receipt: validReceipt({ logs: [{ ...exactLog, data: '0x0f4241' }] }) },
      error: /exact USDC transfer not found/,
    },
    { name: 'self transfer', rpc: {}, selfWallets: [PAYER], error: /self transaction sender/ },
    { name: 'ambiguous transfer', rpc: { receipt: validReceipt({ logs: [exactLog, exactLog] }) }, error: /ambiguous/ },
  ];
  for (const scenario of cases) {
    await assert.rejects(() => verifyBaseUsdcSettlement({
      txHash: TX,
      expectedPayTo: PAY_TO,
      expectedAmountAtomic: '1000000',
      selfWallets: scenario.selfWallets || [],
      fetchImpl: rpcFetch(scenario.rpc),
    }), scenario.error, scenario.name);
  }
});
