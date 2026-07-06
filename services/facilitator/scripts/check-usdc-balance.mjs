import { createPublicClient, http, formatUnits } from "viem";
import { baseSepolia } from "viem/chains";
const USDC = "0x036CbD53842c5426634e7929541eC2318f3dCF7e";
const addr = process.argv[2];
const publicClient = createPublicClient({ chain: baseSepolia, transport: http("https://sepolia.base.org") });
const abi = [{ type: "function", name: "balanceOf", stateMutability: "view", inputs: [{type:"address"}], outputs: [{type:"uint256"}] }];
const bal = await publicClient.readContract({ address: USDC, abi, functionName: "balanceOf", args: [addr] });
console.log(addr, formatUnits(bal, 6), "USDC");
