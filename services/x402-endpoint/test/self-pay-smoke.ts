// Self-pay smoke test: sign (NOT broadcast) a 0.001 USDC transfer from Anicca's wallet
// to herself on Base, derive the would-be tx hash from the signed payload, then exercise
// the verify path against the live endpoint.
//
// Per team-lead instruction (2026-06-03): "do NOT broadcast a real tx until Dais
// approves. Instead, produce a SIGNED tx and feed its hash into the verify path."
//
// Behaviour:
//   1. Read wallet from ~/.automaton/wallet.json
//   2. Build USDC.transfer(receiver, 0.001 USDC) calldata
//   3. Sign offline with the wallet's private key (no broadcast)
//   4. Compute the eventual tx hash via keccak256(signed_serialized_tx)
//   5. Hit ${TARGET}/v0/echo with header x-paid-tx-hash: <hash>
//   6. Log the response code + reason.
//
// HONEST EXPECTATION: because the tx was never broadcast, the on-chain receipt
// will not exist and verify.ts WILL return 402 ("tx receipt not found"). This
// smoke proves the wallet/sign path + the verify wire is intact end-to-end; a
// 200 response would require an actual on-chain broadcast (Dais approval).

import { createWalletClient, http, keccak256, encodeFunctionData, parseUnits, type Hash } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base } from "viem/chains";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const TARGET = process.env.X402_TEST_TARGET ?? "http://localhost:8403";
const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913" as const;
const RECEIVER = "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21" as const; // Anicca's wallet (self-pay)
const PRICE_USDC = "0.001";

interface Wallet {
  privateKey: `0x${string}`;
}

async function main(): Promise<void> {
  const walletPath = join(homedir(), ".automaton", "wallet.json");
  const wallet = JSON.parse(readFileSync(walletPath, "utf8")) as Wallet;
  const account = privateKeyToAccount(wallet.privateKey);

  if (account.address.toLowerCase() !== RECEIVER.toLowerCase()) {
    console.error(
      `[smoke] wallet address ${account.address} != expected receiver ${RECEIVER} — refusing to proceed`
    );
    process.exit(1);
  }
  console.log(`[smoke] wallet  : ${account.address}`);
  console.log(`[smoke] target  : ${TARGET}`);
  console.log(`[smoke] price   : ${PRICE_USDC} USDC`);

  const walletClient = createWalletClient({
    account,
    chain: base,
    transport: http("https://mainnet.base.org"),
  });

  // ERC20 transfer(address,uint256) calldata
  const amount = parseUnits(PRICE_USDC, 6); // USDC = 6 decimals
  const data = encodeFunctionData({
    abi: [
      {
        name: "transfer",
        type: "function",
        inputs: [
          { name: "to", type: "address" },
          { name: "value", type: "uint256" },
        ],
        outputs: [{ type: "bool" }],
        stateMutability: "nonpayable",
      },
    ],
    functionName: "transfer",
    args: [RECEIVER, amount],
  });

  // Use a clearly fake nonce to mark this as a smoke artefact (not for broadcast).
  // The hash we derive cannot match a real on-chain tx unless someone happens to
  // broadcast the exact same payload with the exact same signature.
  const signed = await walletClient.signTransaction({
    to: USDC_BASE,
    value: 0n,
    gas: 100_000n,
    maxFeePerGas: 1_000_000_000n,
    maxPriorityFeePerGas: 100_000_000n,
    nonce: 0,
    chainId: 8453,
    data,
  });
  const wouldBeHash: Hash = keccak256(signed);
  console.log(`[smoke] signed  : ${signed.slice(0, 18)}... (len=${signed.length})`);
  console.log(`[smoke] tx hash : ${wouldBeHash} (NOT broadcast)`);

  // Hit /v0/echo with the would-be hash.
  const url = `${TARGET}/v0/echo?text=self-pay-smoke`;
  const res = await fetch(url, {
    headers: { "x-paid-tx-hash": wouldBeHash },
  });
  const text = await res.text();
  let body: unknown;
  try {
    body = JSON.parse(text);
  } catch {
    body = text;
  }
  console.log(`[smoke] echo    : status=${res.status}`);
  console.log(`[smoke] body    : ${JSON.stringify(body).slice(0, 240)}`);

  // Adjudicate.
  if (res.status === 402) {
    console.log(
      "[smoke] RESULT  : EXPECTED 402 (tx not on-chain — verify wire intact, broadcast withheld per Dais policy)"
    );
    process.exit(0);
  }
  if (res.status === 200) {
    console.log(
      "[smoke] RESULT  : UNEXPECTED 200 — verify path returned content for an unbroadcast tx; investigate!"
    );
    process.exit(2);
  }
  console.log(`[smoke] RESULT  : UNEXPECTED status=${res.status} — investigate`);
  process.exit(3);
}

void main().catch((err) => {
  console.error("[smoke] fatal:", err instanceof Error ? err.message : err);
  process.exit(1);
});
