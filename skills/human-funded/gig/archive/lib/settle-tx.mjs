/**
 * settle-tx.mjs — find a REPRESENTATIVE on-chain tx hash for a verified external USDC inflow.
 *
 * record-earn (the AMOUNT oracle) sums external USDC over a block-cursor span and drops the
 * tx hashes. The loop's profitability gate (isProfitable) requires `tx && status==="0x1"`.
 * So, ONLY when record-earn has already VERIFIED a real external inflow, this finds the most
 * recent external USDC Transfer LOG to the wallet and returns its transactionHash. A Transfer
 * log only exists for a MINED, SUCCESSFUL tx (reverted txs emit no logs) → status "0x1" is sound.
 *
 * This NEVER fabricates: if no external Transfer log exists, it returns null and the slot
 * records no profitable line. It only attaches a real tx to an already-chain-verified earn.
 */
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'; // Base USDC
const TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';
const RPC = process.env.BASE_RPC_URL || 'https://mainnet.base.org';

async function rpc(method, params) {
  const r = await fetch(RPC, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }), signal: AbortSignal.timeout(20000),
  });
  const j = await r.json();
  if (j.error) throw new Error(j.error.message || 'rpc error');
  return j.result;
}

/** @returns {Promise<{tx:string, from:string}|null>} most recent EXTERNAL USDC Transfer to `wallet`.
 *  Prefer the EXACT block range record-earn just processed ({fromBlock,toBlock}); else fall back to
 *  the FINALIZED head minus spanBlocks (finalized matches record-earn's reorg-safe scan, FIND-003). */
export async function representativeExternalTx(wallet, { spanBlocks = 9000, myWallets = [], fromBlock, toBlock } = {}) {
  if (!wallet || !/^0x[0-9a-fA-F]{40}$/.test(wallet)) return null;
  const exclude = new Set([wallet.toLowerCase(), ...myWallets.map(w => String(w).toLowerCase())]);
  let from, now;
  if (Number.isInteger(fromBlock) && Number.isInteger(toBlock)) {
    from = fromBlock; now = toBlock;   // exact window record-earn verified (already finalized)
  } else {
    try { const b = await rpc('eth_getBlockByNumber', ['finalized', false]); now = Number(BigInt(b.number)); }
    catch { return null; }
    from = Math.max(0, now - spanBlocks);
  }
  const toTopic = '0x000000000000000000000000' + wallet.slice(2).toLowerCase();
  let logs;
  // TEST-ONLY seam (gated by FOUNDER_TEST, like record-earn's FOUNDER_RAW_LOGS_JSON): inject raw
  // eth_getLogs to exercise the real parse + founder/SHARED exclude + window logic without a node.
  if (process.env.FOUNDER_TEST === '1' && process.env.GIG_RAW_LOGS_JSON !== undefined) {
    try { logs = JSON.parse(process.env.GIG_RAW_LOGS_JSON); } catch { return null; }
  } else {
    try {
      logs = await rpc('eth_getLogs', [{ address: USDC, topics: [TRANSFER, null, toTopic],
        fromBlock: '0x' + from.toString(16), toBlock: '0x' + now.toString(16) }]);
    } catch { return null; }
  }
  if (!Array.isArray(logs)) return null;
  // most recent external Transfer (re-verify topic0 + recipient; never trust server filter)
  for (let i = logs.length - 1; i >= 0; i--) {
    const l = logs[i];
    if (String(l.address || '').toLowerCase() !== USDC.toLowerCase()) continue;
    if (!Array.isArray(l.topics) || l.topics.length < 3) continue;
    if (String(l.topics[0]).toLowerCase() !== TRANSFER) continue;
    if (String(l.topics[2]).toLowerCase() !== toTopic) continue;
    const payer = '0x' + String(l.topics[1]).slice(26).toLowerCase();
    if (exclude.has(payer)) continue;          // self-transfer → not external
    if (l.transactionHash) return { tx: l.transactionHash, from: payer };
  }
  return null;
}
