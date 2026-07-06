import { createPublicClient, http } from "viem";
import { baseSepolia } from "viem/chains";

const USDC = "0x036CbD53842c5426634e7929541eC2318f3dCF7e";
const publicClient = createPublicClient({ chain: baseSepolia, transport: http("https://sepolia.base.org") });

const abi = [
  { type: "function", name: "name", stateMutability: "view", inputs: [], outputs: [{ type: "string" }] },
  { type: "function", name: "version", stateMutability: "view", inputs: [], outputs: [{ type: "string" }] },
  { type: "function", name: "symbol", stateMutability: "view", inputs: [], outputs: [{ type: "string" }] },
  { type: "function", name: "decimals", stateMutability: "view", inputs: [], outputs: [{ type: "uint8" }] },
];

const [name, version, symbol, decimals] = await Promise.all([
  publicClient.readContract({ address: USDC, abi, functionName: "name" }),
  publicClient.readContract({ address: USDC, abi, functionName: "version" }),
  publicClient.readContract({ address: USDC, abi, functionName: "symbol" }),
  publicClient.readContract({ address: USDC, abi, functionName: "decimals" }),
]);
console.log({ name, version, symbol, decimals });
