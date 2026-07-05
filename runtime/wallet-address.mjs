// Prints THIS Anicca's EVM wallet address. The wallet file stores only a privateKey, so the address
// must be DERIVED (viem), exactly as the poster does — never bare-grepped (that matches the first 40
// hex of the 64-char key). The daemon uses this to set ANICCA_WALLET_ADDRESS for the loop's balance
// tier. Run from a dir where viem resolves (runtime/compute-proxy).
import { privateKeyToAccount } from "viem/accounts";
import fs from "fs";
import { loadEvmKey } from "../skills/earn/lib/resolve-identity.mjs";
// #28: derive THIS instance's address from its gated per-instance key (foreign spawn → null → prints
// nothing, so the daemon does not set ANICCA_WALLET_ADDRESS to another instance's address).
const pk = loadEvmKey();
if (pk) process.stdout.write(privateKeyToAccount(pk).address + "\n");
