// economy/gig/lib/wallet.mjs — thin CLI so run.sh (bash) can read THIS instance's own wallet address
// and USDC balance on the gig board's own chain (Base Sepolia today, see MAINNET.md) without ever
// echoing a private key to stdout or argv (argv is ps-visible; the key travels via the SIGNKEY env var
// only, exactly like skills/earn/run.sh's PKVAR indirection). Deterministic I/O only — derive + one
// on-chain eth_call, no judgment.
import path from "node:path";
import { fileURLToPath } from "node:url";
import { privateKeyToAccount } from "viem/accounts";
import { usdcBalance } from "../../../_shared/lib/usdc.mjs";
import { USDC_BASE_SEPOLIA } from "./escrow.mjs";

// escrow.mjs's own DEFAULT_RPC_URL isn't exported (it's a local const there) — mirrored here so this
// balance check always reads the SAME chain the gig board itself settles on. Override via GIG_RPC_URL
// if the board ever migrates (MAINNET.md documents that move; this becomes a one-line env change).
const RPC_URL = process.env.GIG_RPC_URL || "https://sepolia.base.org";

export function addressFromKey(privateKey) {
  return privateKeyToAccount(privateKey).address;
}

export async function balanceOf(address) {
  return usdcBalance(address, { rpc: RPC_URL, token: USDC_BASE_SEPOLIA });
}

// CLI: `SIGNKEY=0x... node wallet.mjs address` | `ADDR=0x... node wallet.mjs balance`
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const cmd = process.argv[2];
  if (cmd === "address") {
    const pk = process.env.SIGNKEY;
    if (!pk) process.exit(1);
    console.log(addressFromKey(pk));
  } else if (cmd === "balance") {
    const addr = process.env.ADDR;
    if (!addr) {
      console.log(0);
    } else {
      balanceOf(addr)
        .then((b) => console.log(b))
        .catch(() => console.log(0));
    }
  } else {
    process.stderr.write("usage: SIGNKEY=0x.. node wallet.mjs address | ADDR=0x.. node wallet.mjs balance\n");
    process.exitCode = 2;
  }
}
