// PROP-105g (Tier 0/2) live re-derivation audit — anicca-agent-spawn Phase 5/6.
//
// REQ-105's own requirement: every seeded citizens.seed.json entry's walletAddress value must be
// verified, at write time, against that citizen's ACTUAL signing key material via an ACTUAL,
// MECHANICALLY-PERFORMED cryptographic re-derivation (EVM: viem::privateKeyToAccount; Solana:
// @solana/web3.js::Keypair.fromSecretKey + bs58.decode) -- never a hand-authored fixture asserting
// the two happen to match.
//
// Uses the REAL, unmodified skills/earn/lib/resolve-identity.mjs resolvers (same as PROP-403b/e's own
// harness) to obtain each citizen's real private key material, re-derives the corresponding public
// address, and compares it against the REAL citizens.seed.json entry's walletAddress -- never printing
// raw key material, only the boolean match result.
import { resolveEvmPrivateKey, resolveSolanaSecret } from "file:///Users/anicca/anicca/skills/earn/lib/resolve-identity.mjs";
import { COORDINATOR_HOME } from "file:///Users/anicca/anicca/skills/self/spawn/lib/registry-path.mjs";
import { privateKeyToAccount } from "viem/accounts";
import { Keypair } from "@solana/web3.js";
import bs58 from "bs58";
import fs from "node:fs";

const seed = JSON.parse(
  fs.readFileSync("/Users/anicca/anicca/skills/self/spawn/registry/citizens.seed.json", "utf8")
);

function main() {
  const automaton = seed.find((c) => c.id === "automaton");
  const franklin = seed.find((c) => c.id === "Franklin");

  const evmKey = resolveEvmPrivateKey({
    home: `${COORDINATOR_HOME}/.anicca`,
    env: { HOME: COORDINATOR_HOME, ANICCA_HOME: `${COORDINATOR_HOME}/.anicca` },
  });
  const evmAccount = privateKeyToAccount(evmKey);
  const evmMatch = evmAccount.address.toLowerCase() === automaton.walletAddress.evm.toLowerCase();

  const solSecret = resolveSolanaSecret({
    home: `${COORDINATOR_HOME}/.blockrun`,
    env: { HOME: COORDINATOR_HOME, ANICCA_HOME: `${COORDINATOR_HOME}/.blockrun` },
  });
  const secretBytes = typeof solSecret === "string" ? bs58.decode(solSecret) : Uint8Array.from(solSecret);
  const kp = Keypair.fromSecretKey(secretBytes);
  const solMatch = kp.publicKey.toBase58() === franklin.walletAddress.solana;

  const verdict = {
    automatonEvmReDerivationMatch: evmMatch,
    franklinSolanaReDerivationMatch: solMatch,
    overall: evmMatch && solMatch ? "PASS" : "FAIL",
  };
  console.log(JSON.stringify(verdict, null, 2));
}

main();
