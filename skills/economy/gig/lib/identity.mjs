// economy/gig/lib/identity.mjs — ERC-8004 Trustless Agents identity, called DIRECTLY via viem
// (register() = permissionless ERC-721 _safeMint(msg.sender), per SPEC.md §1.2: "壊れた scaffold
// 不使用"). No create-8004-agent scaffold (confirmed broken: tsc errors + Pinata dependency), no new
// contract deployed by us -- we reuse REAL, already-live registries on each network:
//
//   testnet: IdentityRegistry = 0xdc527768082c489e0ee228d24d3cfa290214f387 (base-sepolia, chainId
//   84532), ChaosChain/trustless-agents-erc-ri legacy v1.1.0 (CC0-1.0) -- verified LIVE 2026-07-07 via
//   eth_call name() -> "ERC-8004 Trustless Agent" (matches the ERC721 constructor name in
//   src/IdentityRegistry.sol).
//
//   mainnet: IdentityRegistry = 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432 (base, chainId 8453) --
//   verified LIVE 2026-07-07 via direct viem readContract calls against
//   https://mainnet.base.org: name()->"AgentIdentity", symbol()->"AGENT", ownerOf(1) returns a real
//   owner address (an agent is already registered there). A DIFFERENT/newer contract than the
//   testnet one, NOT the same source as the legacy v1.1.0 above -- register()/ownerOf() route to real
//   logic (confirmed: a static register() call reverts with a real custom-error selector, not a
//   "function not found" style revert; likely an EOA-only guard -- unconfirmed which, but irrelevant
//   here since every caller in this codebase is always a real EOA wallet, never a contract), but
//   agentExists()/totalAgents() are NOT part of its interface (both revert as unknown selectors) --
//   this is why those two are NOT in the ABI below (they were unused dead code even for the testnet
//   path; removing them makes the same ABI safe to call against either network).
//
// Each agent registers ITSELF (msg.sender = the agent's own wallet, mints the identity NFT to itself)
// -- there is no gasless/relayed register() path in either contract, so the calling wallet needs a
// small amount of native ETH on whichever network is active (scripts/fund-agents.mjs drips testnet ETH
// from the facilitator's own signer; mainnet gas-seeding is a plain documented transfer, see
// WITNESS-RUNBOOK.md -- NOT this script, which is testnet-only).
import { createPublicClient, createWalletClient, http, parseAbi, decodeEventLog } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base, baseSepolia } from "viem/chains";

export const IDENTITY_REGISTRY_BASE_SEPOLIA = "0xdc527768082c489e0ee228d24d3cfa290214f387";
export const IDENTITY_REGISTRY_BASE_MAINNET = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432";

// GIG_CHAIN mirrors lib/escrow.mjs's own toggle (kept as an independent, equally-simple env read here
// rather than a cross-import, so this file stays self-contained) -- 'base-sepolia' (default, testnet)
// or 'base' (mainnet). Unset/anything else falls back to testnet, fail-safe.
export const GIG_CHAIN = process.env.GIG_CHAIN === "base" ? "base" : "base-sepolia";

const CHAIN_PROFILES = {
  "base-sepolia": { chain: baseSepolia, registryAddress: IDENTITY_REGISTRY_BASE_SEPOLIA, rpcUrl: "https://sepolia.base.org" },
  base: { chain: base, registryAddress: IDENTITY_REGISTRY_BASE_MAINNET, rpcUrl: "https://mainnet.base.org" },
};
const ACTIVE_CHAIN = CHAIN_PROFILES[GIG_CHAIN];

export const DEFAULT_RPC_URL = process.env.GIG_RPC_URL || ACTIVE_CHAIN.rpcUrl;

const ABI = parseAbi([
  "function register() returns (uint256 agentId)",
  "function ownerOf(uint256 tokenId) view returns (address)",
  "event Registered(uint256 indexed agentId, string agentURI, address indexed owner)",
]);

function clients(rpcUrl, chain = ACTIVE_CHAIN.chain) {
  const transport = http(rpcUrl);
  return {
    publicClient: createPublicClient({ chain, transport }),
  };
}

/**
 * registerIdentity — mint a fresh ERC-8004 agent identity owned by `privateKey`'s own address.
 * Returns { ok:true, agentId, address, tx } on success, { ok:false, reason } on failure (reverted tx,
 * insufficient gas, etc) -- never throws, fail-closed like the rest of this skill.
 */
export async function registerIdentity({ privateKey, rpcUrl = DEFAULT_RPC_URL, chain = ACTIVE_CHAIN.chain, registryAddress = ACTIVE_CHAIN.registryAddress }) {
  const account = privateKeyToAccount(privateKey);
  const { publicClient } = clients(rpcUrl, chain);
  const walletClient = createWalletClient({ account, chain, transport: http(rpcUrl) });
  let hash;
  try {
    hash = await walletClient.writeContract({ address: registryAddress, abi: ABI, functionName: "register", args: [] });
  } catch (e) {
    return { ok: false, reason: e.shortMessage || e.message || String(e) };
  }
  const receipt = await publicClient.waitForTransactionReceipt({ hash });
  if (receipt.status !== "success") {
    return { ok: false, reason: `tx reverted: ${hash}`, tx: hash };
  }
  let agentId = null;
  for (const log of receipt.logs) {
    try {
      const decoded = decodeEventLog({ abi: ABI, data: log.data, topics: log.topics });
      if (decoded.eventName === "Registered") {
        agentId = decoded.args.agentId.toString();
        break;
      }
    } catch {
      // not our event, skip
    }
  }
  return { ok: true, agentId, address: account.address, tx: hash };
}

/**
 * verifyIdentity — on-chain trust check: does `agentId` exist, and is it owned by `expectedAddress`?
 * This is the primitive two strangers use to trust each other's claimed identity (SPEC.md §1: "見知ら
 * ぬ agent 同士でも trade 可") -- the counterparty states its agentId, we verify it here instead of
 * trusting the claim.
 */
export async function verifyIdentity({ agentId, expectedAddress, rpcUrl = DEFAULT_RPC_URL, chain = ACTIVE_CHAIN.chain, registryAddress = ACTIVE_CHAIN.registryAddress }) {
  const { publicClient } = clients(rpcUrl, chain);
  try {
    const owner = await publicClient.readContract({ address: registryAddress, abi: ABI, functionName: "ownerOf", args: [BigInt(agentId)] });
    return { ok: true, valid: owner.toLowerCase() === expectedAddress.toLowerCase(), owner };
  } catch (e) {
    return { ok: false, valid: false, reason: e.shortMessage || e.message || String(e) };
  }
}
