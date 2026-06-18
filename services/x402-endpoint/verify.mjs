// x402 payment verifier — confirms a buyer actually paid USDC on Base for a route.
// Pure, dependency-free (Base JSON-RPC). The heart of anicca earning real USDC.
//
// verifyUsdcPayment({ txHash, expectedReceiver, minAmountBase }) -> {ok, amountBase, from}
// Checks the tx is confirmed (status 0x1) and contains an ERC20 USDC Transfer log
// to expectedReceiver of >= minAmountBase (6-decimal micros). No trust in headers.

const USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913';
const TRANSFER_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';
const RPC = process.env.BASE_RPC || 'https://mainnet.base.org';

async function rpc(method, params) {
  const res = await fetch(RPC, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }),
  });
  const j = await res.json();
  if (j.error) throw new Error(`${method}: ${j.error.message}`);
  return j.result;
}

export async function verifyUsdcPayment({ txHash, expectedReceiver, minAmountBase }) {
  if (!/^0x[0-9a-fA-F]{64}$/.test(txHash || '')) return { ok: false, reason: 'bad txHash' };
  const recv = (expectedReceiver || '').toLowerCase().replace(/^0x/, '');
  if (!/^[0-9a-f]{40}$/.test(recv)) return { ok: false, reason: 'bad receiver' };

  const rcpt = await rpc('eth_getTransactionReceipt', [txHash]);
  if (!rcpt) return { ok: false, reason: 'tx not found' };
  if (rcpt.status !== '0x1') return { ok: false, reason: 'tx not successful' };

  for (const log of rcpt.logs || []) {
    if ((log.address || '').toLowerCase() !== USDC) continue;
    if ((log.topics?.[0] || '').toLowerCase() !== TRANSFER_TOPIC) continue;
    const to = '0x' + (log.topics[2] || '').slice(-40);
    if (to.toLowerCase().replace(/^0x/, '') !== recv) continue;
    const amountBase = parseInt(log.data, 16);
    if (amountBase >= Number(minAmountBase)) {
      const from = '0x' + (log.topics[1] || '').slice(-40);
      return { ok: true, amountBase, from, txHash };
    }
  }
  return { ok: false, reason: 'no matching USDC transfer >= min' };
}
