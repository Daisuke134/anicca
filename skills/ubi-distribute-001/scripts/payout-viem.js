#!/usr/bin/env node
/**
 * payout-viem.js — self-contained USDC broadcast on Base mainnet.
 *
 * Signs and (optionally) broadcasts an ERC-20 USDC transfer using viem +
 * Anicca's wallet.json privateKey. Replaces the cdp CLI dependency that
 * the upstream anicca-payout-wallet skill assumes; we keep the upstream
 * skill as canonical signing logic, but this fallback unblocks the cron
 * when cdp isn't installed (= current state of the box).
 *
 * USAGE
 *   node payout-viem.js --to 0xADDR --amount 0.01 [--dry-run]
 *
 * EXIT
 *   stdout: one JSON object — {action, to, amount_usdc, tx_hash?, sender,
 *                              base_eth?, base_usdc?, basescan_url?, error?}
 *   action ∈ {dry-run, sent, no-funds, send-failed}
 *
 * NEVER broadcasts when --dry-run is set. The dry-run path uses
 * publicClient.simulateContract (eth_call) to verify the tx WOULD succeed
 * without spending gas — same evidence the cron will rely on in test runs.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const Module = require('module');

// viem isn't bundled with this skill; resolve from a known npm root.
// Default: ~/.openclaw/npm/node_modules (already populated for the wallet
// watcher). Override via VIEM_NODE_MODULES if a different location is preferred.
const VIEM_NM = process.env.VIEM_NODE_MODULES
  || path.join(process.env.HOME || '', '.openclaw/npm');
const localRequire = Module.createRequire(path.join(VIEM_NM, 'package.json'));
let v, base, accounts;
try {
  v = localRequire('viem');
  ({ base } = localRequire('viem/chains'));
  accounts = localRequire('viem/accounts');
} catch (e) {
  process.stdout.write(JSON.stringify({
    action: 'send-failed',
    error: `viem module resolution failed (tried ${VIEM_NM}): ${e.message}`,
  }) + '\n');
  process.exit(67);
}

const WALLET_FILE = process.env.ANICCA_WALLET_FILE
  || path.join(process.env.HOME || '', '.automaton/wallet.json');
const USDC_ADDR = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const ERC20_TRANSFER_ABI = [{
  type: 'function', name: 'transfer', stateMutability: 'nonpayable',
  inputs: [{ name: 'to', type: 'address' }, { name: 'amount', type: 'uint256' }],
  outputs: [{ type: 'bool' }],
}];
const ERC20_BALANCE_ABI = [{
  type: 'function', name: 'balanceOf', stateMutability: 'view',
  inputs: [{ name: '', type: 'address' }],
  outputs: [{ type: 'uint256' }],
}];

function parseArgs(argv) {
  const out = { dryRun: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--to') out.to = argv[++i];
    else if (a === '--amount') out.amount = argv[++i];
    else if (a === '--dry-run' || a === '--dry') out.dryRun = true;
    else if (a.startsWith('--to=')) out.to = a.slice(5);
    else if (a.startsWith('--amount=')) out.amount = a.slice(9);
  }
  return out;
}

function emit(obj, code = 0) {
  process.stdout.write(JSON.stringify(obj) + '\n');
  process.exit(code);
}

(async () => {
  const args = parseArgs(process.argv);
  if (!args.to || !v.isAddress(args.to)) {
    return emit({ action: 'send-failed', error: 'missing or invalid --to' }, 65);
  }
  const amountUsdc = Number(args.amount || '0');
  if (!Number.isFinite(amountUsdc) || amountUsdc <= 0) {
    return emit({ action: 'send-failed', error: 'amount must be > 0' }, 65);
  }

  let walletJson;
  try { walletJson = JSON.parse(fs.readFileSync(WALLET_FILE, 'utf8')); }
  catch (e) {
    return emit({ action: 'send-failed', error: `cannot read wallet.json: ${e.message}` }, 66);
  }
  const pk = walletJson.privateKey;
  if (!pk || !pk.startsWith('0x')) {
    return emit({ action: 'send-failed', error: 'wallet.json privateKey missing or malformed' }, 66);
  }

  const account = accounts.privateKeyToAccount(pk);
  const sender = account.address;
  const to = v.getAddress(args.to);
  // USDC = 6 decimals on Base.
  const amountAtomic = BigInt(Math.round(amountUsdc * 1_000_000));

  const publicClient = v.createPublicClient({
    chain: base,
    transport: v.http('https://mainnet.base.org'),
  });

  // Balance + gas snapshot (informational; also gate for no-funds).
  let baseEth = 0n, baseUsdc = 0n;
  try {
    [baseEth, baseUsdc] = await Promise.all([
      publicClient.getBalance({ address: sender }),
      publicClient.readContract({
        address: USDC_ADDR, abi: ERC20_BALANCE_ABI,
        functionName: 'balanceOf', args: [sender],
      }),
    ]);
  } catch (e) {
    return emit({ action: 'send-failed', error: `rpc snapshot failed: ${e.message}`, sender }, 70);
  }

  const baseEthF = Number(v.formatUnits(baseEth, 18));
  const baseUsdcF = Number(v.formatUnits(baseUsdc, 6));

  if (args.dryRun) {
    // Simulate the transfer (eth_call) — confirms the tx WOULD succeed
    // against current state without spending any gas.
    let simulated = false, simError = null;
    if (baseUsdc >= amountAtomic) {
      try {
        await publicClient.simulateContract({
          address: USDC_ADDR, abi: ERC20_TRANSFER_ABI,
          functionName: 'transfer', args: [to, amountAtomic],
          account: sender,
        });
        simulated = true;
      } catch (e) {
        simError = e.shortMessage || e.message;
      }
    }
    return emit({
      action: 'dry-run',
      to, amount_usdc: amountUsdc,
      sender, base_eth: baseEthF, base_usdc: baseUsdcF,
      simulated_ok: simulated,
      simulation_note: simulated
        ? 'eth_call succeeded — broadcast would land'
        : (baseUsdc < amountAtomic
            ? 'simulation skipped: sender USDC < amount (would revert)'
            : `simulation failed: ${simError}`),
    }, 0);
  }

  // LIVE: balance gate before signing.
  if (baseUsdc < amountAtomic) {
    return emit({
      action: 'no-funds',
      to, amount_usdc: amountUsdc,
      sender, base_eth: baseEthF, base_usdc: baseUsdcF,
      error: `sender USDC ${baseUsdcF} < amount ${amountUsdc}`,
    }, 0);
  }
  if (baseEth === 0n) {
    return emit({
      action: 'no-funds',
      to, amount_usdc: amountUsdc,
      sender, base_eth: baseEthF, base_usdc: baseUsdcF,
      error: 'sender has 0 ETH gas on Base — top up at least ~0.0005 ETH',
    }, 0);
  }

  const walletClient = v.createWalletClient({
    account, chain: base,
    transport: v.http('https://mainnet.base.org'),
  });

  let txHash;
  try {
    const { request } = await publicClient.simulateContract({
      address: USDC_ADDR, abi: ERC20_TRANSFER_ABI,
      functionName: 'transfer', args: [to, amountAtomic],
      account,
    });
    txHash = await walletClient.writeContract(request);
  } catch (e) {
    return emit({
      action: 'send-failed',
      to, amount_usdc: amountUsdc, sender,
      base_eth: baseEthF, base_usdc: baseUsdcF,
      error: e.shortMessage || e.message,
    }, 71);
  }

  // Optionally wait for receipt — don't block forever, give the cron a
  // bounded window to confirm.
  let receipt = null;
  try {
    receipt = await publicClient.waitForTransactionReceipt({
      hash: txHash, timeout: 60_000, pollingInterval: 2_000,
    });
  } catch (e) {
    // Tx may still settle; we already have the hash. Don't fail the cron.
  }

  return emit({
    action: 'sent',
    to, amount_usdc: amountUsdc, sender,
    base_eth: baseEthF, base_usdc: baseUsdcF,
    tx_hash: txHash,
    basescan_url: `https://basescan.org/tx/${txHash}`,
    confirmed: receipt ? (receipt.status === 'success') : null,
    block_number: receipt ? Number(receipt.blockNumber) : null,
  }, 0);
})().catch(e => {
  process.stdout.write(JSON.stringify({
    action: 'send-failed', error: `unhandled: ${e.message}`,
  }) + '\n');
  process.exit(99);
});
