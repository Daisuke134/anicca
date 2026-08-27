#!/usr/bin/env node
import { verifyBaseUsdcSettlement } from '../src/verifier.mjs';

const args = process.argv.slice(2);
function value(name) {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : null;
}

const selfWallets = [];
for (let index = 0; index < args.length; index += 1) {
  if (args[index] === '--self-wallet' && args[index + 1]) selfWallets.push(args[index + 1]);
}

const txHash = value('--tx');
const expectedPayTo = value('--pay-to');
const expectedAmountAtomic = value('--amount-atomic');
if (!txHash || !expectedPayTo || !expectedAmountAtomic) {
  process.stderr.write('usage: base-usdc-settlement-verify --tx 0x... --pay-to 0x... --amount-atomic 1000000 [--self-wallet 0x...] [--rpc https://...]\n');
  process.exit(2);
}

try {
  const proof = await verifyBaseUsdcSettlement({
    txHash,
    expectedPayTo,
    expectedAmountAtomic,
    selfWallets,
    rpcUrl: value('--rpc') || undefined,
  });
  process.stdout.write(`${JSON.stringify(proof)}\n`);
} catch (error) {
  process.stderr.write(`${String(error?.message || error)}\n`);
  process.exit(1);
}
