// PROP-204a (Tier 3) live E2E proof — anicca-agent-spawn Phase 5.
//
// REQ-204's own delivered mechanism (skills/economy/gig/lib/ensure-agent-id.mjs, unmodified from a
// PRIOR already-shipped sprint) already has a REAL register() call on file: automaton's own cached
// {address, agentId} at ~/.anicca/.automaton/gig-agent-id.json (agentId 58381, minted 2026-07-07).
// This sprint's own diff has no orchestrator that would mint a FRESH child identity, so — mirroring
// anicca-agent-lending's own Phase 5 precedent (finding a real historical mainnet tx rather than
// fabricating a new one) — this harness independently re-verifies THAT already-real registration via
// a SEPARATE RPC call, never trusting the cache file's own self-report.
//
// Reads only {address, agentId} (never a private key) from the cache file.
import fs from "node:fs";
import { createPublicClient, http, parseAbi } from "viem";
import { base } from "viem/chains";

const CACHE_FILE = "/Users/anicca/.anicca/.automaton/gig-agent-id.json";
// This instance's real cached registration is on BASE MAINNET (chainId 8453), confirmed live below —
// the base-sepolia testnet registry (0xdc52...f387) reverts "invalid token ID" for this agentId, so
// GIG_CHAIN=base was evidently active when this instance's own ensureAgentId() call actually ran.
const IDENTITY_REGISTRY_BASE_MAINNET = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432";
const ABI = parseAbi(["function ownerOf(uint256 tokenId) view returns (address)"]);

async function main() {
  const cached = JSON.parse(fs.readFileSync(CACHE_FILE, "utf8"));
  const { address, agentId } = cached;
  if (!address || !agentId) throw new Error("cache file missing address/agentId");

  // Two INDEPENDENT public RPC endpoints, mirroring the lending precedent's cross-provider check —
  // neither is the endpoint identity.mjs's own DEFAULT_RPC_URL would use by default in this process.
  const endpoints = ["https://mainnet.base.org", "https://base-rpc.publicnode.com"];
  const results = [];
  for (const rpcUrl of endpoints) {
    const client = createPublicClient({ chain: base, transport: http(rpcUrl) });
    const owner = await client.readContract({
      address: IDENTITY_REGISTRY_BASE_MAINNET,
      abi: ABI,
      functionName: "ownerOf",
      args: [BigInt(agentId)],
    });
    results.push({ rpcUrl, owner });
  }

  const allMatch = results.every((r) => r.owner.toLowerCase() === address.toLowerCase());
  const crossProviderAgree = results[0].owner.toLowerCase() === results[1].owner.toLowerCase();

  const report = {
    prop: "PROP-204a",
    chain: "base (chainId 8453, mainnet)",
    registry: IDENTITY_REGISTRY_BASE_MAINNET,
    agentId,
    expectedAddress: address,
    independentQueries: results,
    ownerMatchesExpectedAddress: allMatch,
    crossProviderAgreement: crossProviderAgree,
    verdict: allMatch && crossProviderAgree ? "PROVED" : "FAILED",
    note:
      "This registration was minted by a PRIOR, already-shipped sprint's real ensureAgentId() call " +
      "(unmodified this sprint) -- this sprint's own diff contains no orchestrator that would mint a " +
      "fresh child identity, so this harness re-verifies the already-real registration live instead of " +
      "fabricating a new on-chain mint purely to produce a proof artifact.",
  };
  console.log(JSON.stringify(report, null, 2));
  if (report.verdict !== "PROVED") process.exitCode = 1;
}

main().catch((e) => {
  console.error(JSON.stringify({ prop: "PROP-204a", verdict: "FAILED", error: e.message || String(e) }));
  process.exitCode = 1;
});
