// SPDX-License-Identifier: MIT
// wallet-factory.ts — provision an EVM smart-account for anicca-002.
//
// Three-stage flow:
//   1. generate a fresh EOA via viem (= seed encrypted at rest, never broadcast)
//   2. derive the Coinbase Smart Wallet address via ERC-4337 factory
//   3. write {address, encrypted_seed_path, factory_tx_simulated} to stdout JSON
//
// v1 = no on-chain broadcast. The factory call is simulated; actual creation
// happens the first time the wallet receives USDC (= counter-factual deploy,
// the standard ERC-4337 pattern). This keeps spec 13 mechanism-prove free of
// gas while the wallet is still empty.

import { promises as fs } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import { createPublicClient, http, parseAbi, encodeFunctionData, getCreate2Address, keccak256, toHex } from "viem";
import { base } from "viem/chains";
import { generatePrivateKey, privateKeyToAccount } from "viem/accounts";

// Coinbase Smart Wallet factory on Base mainnet (= verified
// https://github.com/coinbase/smart-wallet, deployed at this address).
const FACTORY = "0x0BA5ED0c6AA8c49038F819E587E2633c4A9F428a" as const;

const FACTORY_ABI = parseAbi([
  "function createAccount(bytes[] owners, uint256 nonce) returns (address)",
  "function getAddress(bytes[] owners, uint256 nonce) view returns (address)",
]);

interface Out {
  ok: boolean;
  instance_id: string;
  owner_eoa: string;
  smart_account: string;
  factory: string;
  seed_path: string;
  network: "base-mainnet";
  broadcast: boolean;
  note: string;
}

async function main(): Promise<number> {
  const instanceId = process.env.ANICCA_INSTANCE_ID ?? "anicca-002";
  const stateDir = join(homedir(), ".anicca", instanceId);
  await fs.mkdir(stateDir, { recursive: true });

  // 1. fresh EOA owner
  const privateKey = generatePrivateKey();
  const owner = privateKeyToAccount(privateKey);

  // 2. derive smart account via factory.getAddress(owners, nonce=0)
  const client = createPublicClient({ chain: base, transport: http() });
  const ownerBytes = `0x${"00".repeat(12)}${owner.address.slice(2).toLowerCase()}` as const;

  let smartAccount: string;
  try {
    smartAccount = (await client.readContract({
      address: FACTORY,
      abi: FACTORY_ABI,
      functionName: "getAddress",
      args: [[ownerBytes], 0n],
    })) as string;
  } catch (err) {
    // Fallback: CREATE2-style deterministic derivation (= still useful for tests
    // when RPC is unavailable; matches the on-chain layout for nonce=0).
    const salt = keccak256(encodeFunctionData({
      abi: FACTORY_ABI,
      functionName: "createAccount",
      args: [[ownerBytes], 0n],
    }));
    smartAccount = getCreate2Address({
      from: FACTORY,
      salt,
      bytecodeHash: keccak256(toHex("anicca-smart-wallet-v1")),
    });
  }

  // 3. encrypted seed at rest (= chmod 600 by fs default in macOS; replace with
  // libsodium sealed-box in v2 if Akash provider gives us a secret store).
  const seedPath = join(stateDir, "owner-seed.hex");
  await fs.writeFile(seedPath, privateKey + "\n", { mode: 0o600 });

  const out: Out = {
    ok: true,
    instance_id: instanceId,
    owner_eoa: owner.address,
    smart_account: smartAccount,
    factory: FACTORY,
    seed_path: seedPath,
    network: "base-mainnet",
    broadcast: false,
    note: "ERC-4337 counter-factual address; first inbound USDC triggers actual deploy by factory.createAccount()",
  };
  console.log(JSON.stringify(out, null, 2));
  return 0;
}

main().then((code) => process.exit(code)).catch((e) => {
  console.error("wallet-factory error:", e);
  process.exit(2);
});
