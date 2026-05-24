import path from 'node:path';
import { normalizeHexAddress, parseArgs, parseUsdcAmountToBaseUnits, readJson, repoDir } from './util.js';

function main() {
  const args = parseArgs(process.argv.slice(2));
  const to = normalizeHexAddress(args.to);
  const amount = String(args.amount ?? '');
  if (!amount) throw new Error('missing --amount (e.g. 0.10)');

  const cfgPath = path.join(repoDir(), 'config.json');
  const cfg = readJson(cfgPath);

  const usdcDecimals = Number(cfg.usdcDecimals ?? 6);
  const baseUnits = parseUsdcAmountToBaseUnits(amount, usdcDecimals);

  const token = normalizeHexAddress(cfg.usdcTokenAddress);
  const chainId = Number(cfg.chainId);

  // EIP-681-ish (wallets vary). This is a convenience string, not a guarantee.
  // ethereum:<token>@<chainId>/transfer?address=<to>&uint256=<amountBaseUnits>
  const eip681 = `ethereum:${token}@${chainId}/transfer?address=${to}&uint256=${baseUnits.toString()}`;

  const intent = {
    kind: 'usdc_testnet_transfer_intent',
    chainId,
    token,
    to,
    amount: {
      display: amount,
      decimals: usdcDecimals,
      baseUnits: baseUnits.toString()
    },
    safety: {
      mainnetForbidden: true,
      privateKeysForbidden: true,
      recipientAllowlistEnforced: true
    }
  };

  console.log(
    JSON.stringify(
      {
        ok: true,
        intent,
        eip681
      },
      null,
      2
    )
  );
}

main();

