import path from 'node:path';
import {
  normalizeHexAddress,
  padTopicAddress,
  parseArgs,
  parseUsdcAmountToBaseUnits,
  readJson,
  repoDir,
  topicToAddress
} from './util.js';

const TRANSFER_TOPIC0 = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';

function hexToBigInt(hex) {
  if (typeof hex !== 'string' || !hex.startsWith('0x')) return null;
  try {
    return BigInt(hex);
  } catch {
    return null;
  }
}

async function rpc(rpcUrl, method, params) {
  const res = await fetch(rpcUrl, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params })
  });
  if (!res.ok) throw new Error(`RPC HTTP ${res.status}`);
  const json = await res.json();
  if (json.error) throw new Error(`RPC error: ${JSON.stringify(json.error)}`);
  return json.result;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const tx = String(args.tx ?? '');
  if (!/^0x[0-9a-fA-F]{64}$/.test(tx)) throw new Error('missing/invalid --tx (0x...)');

  const to = normalizeHexAddress(String(args.to ?? ''));
  const amount = String(args.amount ?? '');
  if (!amount) throw new Error('missing --amount (e.g. 0.10)');

  const cfgPath = path.join(repoDir(), 'config.json');
  const cfg = readJson(cfgPath);

  const chainId = Number(cfg.chainId);
  // crude mainnet guard: most mainnets are not in our expected test chain list anyway
  if (!Number.isFinite(chainId) || chainId <= 0) throw new Error('invalid chainId in config.json');

  const rpcUrl = String(cfg.rpcUrl ?? '');
  if (!rpcUrl) throw new Error('missing rpcUrl in config.json');

  const token = normalizeHexAddress(cfg.usdcTokenAddress);
  const usdcDecimals = Number(cfg.usdcDecimals ?? 6);
  const expectedBaseUnits = parseUsdcAmountToBaseUnits(amount, usdcDecimals);

  const allowlistPath = path.join(repoDir(), 'allowlist.json');
  const allowlist = readJson(allowlistPath);
  const allowed = new Set((allowlist.allowedRecipients || []).map(normalizeHexAddress));
  if (!allowed.has(to)) {
    console.log(JSON.stringify({ ok: false, reason: 'recipient_not_allowlisted', to }, null, 2));
    process.exit(1);
  }

  const receipt = await rpc(rpcUrl, 'eth_getTransactionReceipt', [tx]);
  if (!receipt) {
    console.log(JSON.stringify({ ok: false, reason: 'tx_not_found_or_pending', tx }, null, 2));
    process.exit(1);
  }

  const status = hexToBigInt(receipt.status);
  if (status !== 1n) {
    console.log(JSON.stringify({ ok: false, reason: 'tx_failed', tx, status: receipt.status }, null, 2));
    process.exit(1);
  }

  const blockNumber = hexToBigInt(receipt.blockNumber);
  if (blockNumber == null) throw new Error('invalid receipt.blockNumber');

  const head = hexToBigInt(await rpc(rpcUrl, 'eth_blockNumber', []));
  if (head == null) throw new Error('invalid eth_blockNumber');

  const confirmations = Number(head - blockNumber + 1n);
  const minConfirmations = Number(cfg.minConfirmations ?? 1);
  if (confirmations < minConfirmations) {
    console.log(
      JSON.stringify(
        { ok: false, reason: 'not_enough_confirmations', confirmations, minConfirmations, tx },
        null,
        2
      )
    );
    process.exit(1);
  }

  const logs = Array.isArray(receipt.logs) ? receipt.logs : [];
  const tokenLc = token.toLowerCase();
  const match = logs.find(l => {
    if (!l || typeof l !== 'object') return false;
    if (String(l.address || '').toLowerCase() !== tokenLc) return false;
    const topics = Array.isArray(l.topics) ? l.topics : [];
    return String(topics[0] || '').toLowerCase() === TRANSFER_TOPIC0;
  });

  if (!match) {
    console.log(JSON.stringify({ ok: false, reason: 'no_usdc_transfer_log', tx, token }, null, 2));
    process.exit(1);
  }

  const topics = match.topics || [];
  const fromAddr = topicToAddress(topics[1]);
  const toAddr = topicToAddress(topics[2]);
  const data = String(match.data || '');
  const transferred = data.startsWith('0x') ? BigInt(data) : null;

  if (!toAddr || normalizeHexAddress(toAddr) !== to) {
    console.log(JSON.stringify({ ok: false, reason: 'to_mismatch', tx, expectedTo: to, actualTo: toAddr }, null, 2));
    process.exit(1);
  }

  if (transferred !== expectedBaseUnits) {
    console.log(
      JSON.stringify(
        {
          ok: false,
          reason: 'amount_mismatch',
          tx,
          expectedBaseUnits: expectedBaseUnits.toString(),
          actualBaseUnits: transferred?.toString?.()
        },
        null,
        2
      )
    );
    process.exit(1);
  }

  console.log(
    JSON.stringify(
      {
        ok: true,
        tx,
        chainId,
        token,
        from: fromAddr,
        to,
        amount: { display: amount, decimals: usdcDecimals, baseUnits: expectedBaseUnits.toString() },
        confirmations
      },
      null,
      2
    )
  );
}

main().catch(err => {
  console.error(JSON.stringify({ ok: false, reason: 'exception', message: String(err?.message || err) }, null, 2));
  process.exit(2);
});

