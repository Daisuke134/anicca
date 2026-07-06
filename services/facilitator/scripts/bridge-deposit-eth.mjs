// One-shot: bridge ETH from Ethereum Sepolia (L1) -> Base Sepolia (L2) via the
// official OP-stack L1StandardBridge, so the facilitator signer has gas on
// Base Sepolia without touching any Coinbase/CDP faucet or account.
// Usage: FACILITATOR_PRIVATE_KEY=0x... AMOUNT_ETH=0.05 node bridge-deposit-eth.mjs
import { createWalletClient, createPublicClient, http, parseEther } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { sepolia } from "viem/chains";

const L1_STANDARD_BRIDGE = "0xfd0Bf71F60660E2f608ed56e1659C450eB113120"; // Base Sepolia's L1StandardBridge on Ethereum Sepolia (docs.base.org/base-chain/network-information/base-contracts)

const privateKey = process.env.FACILITATOR_PRIVATE_KEY;
const amountEth = process.env.AMOUNT_ETH || "0.05";
if (!privateKey) throw new Error("set FACILITATOR_PRIVATE_KEY");

const account = privateKeyToAccount(privateKey);
const transport = http("https://ethereum-sepolia-rpc.publicnode.com");
const publicClient = createPublicClient({ chain: sepolia, transport });
const walletClient = createWalletClient({ account, chain: sepolia, transport });

const depositEthAbi = [
  {
    type: "function",
    name: "depositETH",
    stateMutability: "payable",
    inputs: [
      { name: "_minGasLimit", type: "uint32" },
      { name: "_extraData", type: "bytes" },
    ],
    outputs: [],
  },
];

console.log(`bridging ${amountEth} ETH from Sepolia -> Base Sepolia for ${account.address}`);
const hash = await walletClient.writeContract({
  address: L1_STANDARD_BRIDGE,
  abi: depositEthAbi,
  functionName: "depositETH",
  args: [200000, "0x"],
  value: parseEther(amountEth),
  gas: 900000n, // prior attempt (auto-estimated ~475k) reverted at ~94% gas used -> force headroom
});
console.log("L1 tx hash:", hash);
const receipt = await publicClient.waitForTransactionReceipt({ hash });
console.log("L1 tx status:", receipt.status);
