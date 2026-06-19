// Prints THIS Anicca's EVM wallet address. The wallet file stores only a privateKey, so the address
// must be DERIVED (viem), exactly as the poster does — never bare-grepped (that matches the first 40
// hex of the 64-char key). The daemon uses this to set ANICCA_WALLET_ADDRESS for the loop's balance
// tier. Run from a dir where viem resolves (runtime/compute-proxy).
import { privateKeyToAccount } from "viem/accounts";
import fs from "fs";
const w = JSON.parse(fs.readFileSync(process.env.HOME + "/.automaton/wallet.json", "utf8"));
const pk = w.privateKey.startsWith("0x") ? w.privateKey : "0x" + w.privateKey;
process.stdout.write((w.address || privateKeyToAccount(pk).address) + "\n");
