import { createPublicClient, http, formatUnits } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base } from "viem/chains";
import fs from "node:fs";
const w = JSON.parse(fs.readFileSync(process.env.HOME + "/.automaton/wallet.json", "utf8"));
const account = privateKeyToAccount(w.privateKey);
const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const ABI = [{ name:"balanceOf", type:"function", inputs:[{name:"",type:"address"}], outputs:[{type:"uint256"}], stateMutability:"view" }];
const c = createPublicClient({ chain: base, transport: http("https://mainnet.base.org") });
const usdc = await c.readContract({ address: USDC, abi: ABI, functionName: "balanceOf", args: [account.address] });
const eth = await c.getBalance({ address: account.address });
const nonce = await c.getTransactionCount({ address: account.address });
console.log(JSON.stringify({
  wallet: account.address,
  usdc_base_balance: formatUnits(usdc, 6),
  usdc_base_units: usdc.toString(),
  eth_balance: formatUnits(eth, 18),
  eth_wei: eth.toString(),
  next_nonce: nonce,
  can_self_loop_0_001: usdc >= 1000n && eth >= 50_000_000_000_000n, // 0.001 USDC + ~0.00005 ETH
}, null, 2));
