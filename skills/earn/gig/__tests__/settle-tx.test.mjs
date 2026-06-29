// node:test — settle-tx real-chain extraction path (FIND-001 round-5 coverage gap).
// Uses the FOUNDER_TEST-gated GIG_RAW_LOGS_JSON seam to inject raw eth_getLogs and exercise
// the REAL parse + founder/SHARED exclude filter + explicit-window logic (no network).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { representativeExternalTx } from '../lib/settle-tx.mjs';

const WALLET = '0x810f6d61f7606deee2657d3083e150a222bc29c5';
const SHARED = ['0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21', '0x9b1ee988b1a2931abce467f0a8eaff6c70c93e83'];
const TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const toTopic = '0x000000000000000000000000' + WALLET.slice(2).toLowerCase();
const fromTopic = (addr) => '0x000000000000000000000000' + addr.slice(2).toLowerCase();
const log = (fromAddr, tx) => ({ address: USDC, topics: [TRANSFER, fromTopic(fromAddr), toTopic], data: '0x' + (1000000).toString(16), transactionHash: tx });

function withSeam(rawLogs, fn) {
  process.env.FOUNDER_TEST = '1';
  process.env.GIG_RAW_LOGS_JSON = JSON.stringify(rawLogs);
  return fn().finally(() => { delete process.env.FOUNDER_TEST; delete process.env.GIG_RAW_LOGS_JSON; });
}

test('a genuine EXTERNAL Transfer log → returns its transactionHash', async () => {
  const ext = '0x1111111111111111111111111111111111111111';
  const r = await withSeam([log(ext, '0xfeedface')], () =>
    representativeExternalTx(WALLET, { myWallets: SHARED, fromBlock: 100, toBlock: 200 }));
  assert.ok(r && r.tx === '0xfeedface', 'did not return the external tx: ' + JSON.stringify(r));
  assert.equal(r.from, ext.toLowerCase());
});

test('logs ONLY from founder + SHARED wallets → null (self/internal transfers excluded)', async () => {
  const r = await withSeam([log(WALLET, '0xself'), log(SHARED[0], '0xsharedA'), log(SHARED[1], '0xsharedB')], () =>
    representativeExternalTx(WALLET, { myWallets: SHARED, fromBlock: 100, toBlock: 200 }));
  assert.equal(r, null, 'a self/SHARED transfer was wrongly returned as external: ' + JSON.stringify(r));
});

test('picks the MOST RECENT external, skipping a trailing self-transfer', async () => {
  const ext = '0x2222222222222222222222222222222222222222';
  const r = await withSeam([log(ext, '0xexternalOlder'), log(SHARED[0], '0xsharedLater')], () =>
    representativeExternalTx(WALLET, { myWallets: SHARED, fromBlock: 1, toBlock: 9 }));
  assert.ok(r && r.tx === '0xexternalOlder', 'did not skip the trailing SHARED transfer: ' + JSON.stringify(r));
});

test('a log to a DIFFERENT recipient is ignored (recipient re-verified, not trusted)', async () => {
  const ext = '0x3333333333333333333333333333333333333333';
  const wrongTo = { address: USDC, topics: [TRANSFER, fromTopic(ext), fromTopic('0x9999999999999999999999999999999999999999')], data: '0x'+ (1).toString(16), transactionHash: '0xwrong' };
  const r = await withSeam([wrongTo], () => representativeExternalTx(WALLET, { myWallets: SHARED, fromBlock: 1, toBlock: 9 }));
  assert.equal(r, null);
});
