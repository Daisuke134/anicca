// scripts/fund-agents.mjs — one-off: drip a small amount of Base Sepolia ETH from the facilitator's
// own signer (which already holds bridged testnet ETH from P2.1, see services/facilitator/README.md)
// to a target wallet so it can pay gas for ERC-8004 register() (register() is a direct on-chain tx,
// not gasless -- there is no relayed/meta-tx path in the reference-implementation contract). This is
// plain ETH gas provisioning between OUR OWN controlled testnet wallets, not a marketplace "payment".
//
// Usage: FACILITATOR_PRIVATE_KEY=... node scripts/fund-agents.mjs <toAddress> [amountEth=0.0005]
import { createWalletClient, createPublicClient, http, parseEther } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { baseSepolia } from "viem/chains";

const to = process.argv[2];
const amountEth = process.argv[3] || "0.0005";
if (!to) {
  console.error("usage: node fund-agents.mjs <toAddress> [amountEth]");
  process.exit(1);
}
const privateKey = process.env.FACILITATOR_PRIVATE_KEY;
if (!privateKey) {
  console.error("set FACILITATOR_PRIVATE_KEY (source ~/.anicca-signing/x402-facilitator/.env)");
  process.exit(1);
}

const account = privateKeyToAccount(privateKey);
const transport = http("https://sepolia.base.org");
const walletClient = createWalletClient({ account, chain: baseSepolia, transport });
const publicClient = createPublicClient({ chain: baseSepolia, transport });

const hash = await walletClient.sendTransaction({ to, value: parseEther(amountEth) });
const receipt = await publicClient.waitForTransactionReceipt({ hash });
console.log(JSON.stringify({ from: account.address, to, amountEth, tx: hash, status: receipt.status }));
