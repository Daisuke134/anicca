// economy/gig/lib/reputation.mjs — ERC-8004 Reputation Registry write/read, same direct-viem style as
// lib/identity.mjs (23 §11 部品1, 2026-07-12). See
// docs/superpowers/specs/2026-07-12-franklin-reputation-gasless-design.md §1 G2.
//
// Addresses — verified via OWN eth_call this session, not guessed (spec explicit requirement):
//
//   mainnet: 0x8004BAa17C55a88189AE136b182e5fdA19dE9b63 (source: erc-8004/erc-8004-contracts
//   scripts/addresses.ts MAINNET_ADDRESSES.reputationRegistry — matches the address given in this
//   feature's own task brief exactly). Confirmed LIVE 2026-07-12 via direct viem readContract against
//   https://mainnet.base.org: getVersion()->"2.0.0", getIdentityRegistry()->
//   0x8004A169FB4a3325136EB29fA0ceB6D2e539a432 — an EXACT match to identity.mjs's own
//   IDENTITY_REGISTRY_BASE_MAINNET. Our existing mainnet agentIds (registered via identity.mjs today)
//   are therefore valid giveFeedback subjects here with ZERO extra migration.
//
//   base-sepolia: 0x8004B663056A597Dffe9eCcC1965A193B7388713 (source: same erc-8004/erc-8004-contracts
//   repo, scripts/addresses.ts TESTNET_ADDRESSES.reputationRegistry — same CREATE2 vanity-salt/UUPS-proxy
//   family as the verified mainnet address above, deployed identically across every testnet chain id
//   including 84532/base-sepolia). Confirmed LIVE 2026-07-12 via readContract:
//   getVersion()->"2.0.0" — BUT getIdentityRegistry()->0x8004A818BFB912233c491871b3d84c89A494BD9e, which
//   is a DIFFERENT contract than identity.mjs's own IDENTITY_REGISTRY_BASE_SEPOLIA
//   (0xdc527768082c489e0ee228d24d3cfa290214f387, the legacy ChaosChain v1.1.0 reference implementation —
//   see identity.mjs's own header comment).
//
//   ★KNOWN LIMITATION (testnet only, verified not guessed)★: giveFeedback's own on-chain guard calls
//   `IIdentityRegistry(_identityRegistry).isAuthorizedOrOwner(msg.sender, agentId)` against
//   0x8004A818... — an agentId that only exists in identity.mjs's legacy 0xdc5277... testnet registry is
//   NOT a valid subject there (reverts ERC721NonexistentToken, see ReputationRegistryUpgradeable.sol's
//   own comment on that check). Mainnet has NO such mismatch (identityRegistry linkage verified equal
//   above). This is a real, out-of-scope-for-this-spec gap (identity.mjs's testnet registry address is
//   outside this feature's file boundary, §3) — the E2E script
//   (scripts/e2e-reputation-testnet.mjs) works around it by registering a FRESH throwaway agentId
//   directly against 0x8004A818... (identity.mjs's own registerIdentity(), registryAddress overridden)
//   for the specific purpose of exercising giveFeedback/getSummary against a real, valid subject.
import { createPublicClient, createWalletClient, http, parseAbi, keccak256, toBytes } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base, baseSepolia } from "viem/chains";

export const REPUTATION_REGISTRY_BASE_MAINNET = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63";
export const REPUTATION_REGISTRY_BASE_SEPOLIA = "0x8004B663056A597Dffe9eCcC1965A193B7388713";

// Same independent, self-contained GIG_CHAIN read as identity.mjs/escrow.mjs/ensure-gas.mjs (documented
// rationale: identity.mjs L35-37 — stays self-contained rather than cross-importing).
export const GIG_CHAIN = process.env.GIG_CHAIN === "base" ? "base" : "base-sepolia";
const CHAIN_PROFILES = {
  "base-sepolia": { chain: baseSepolia, registryAddress: REPUTATION_REGISTRY_BASE_SEPOLIA, rpcUrl: "https://sepolia.base.org" },
  base: { chain: base, registryAddress: REPUTATION_REGISTRY_BASE_MAINNET, rpcUrl: "https://mainnet.base.org" },
};
const ACTIVE_CHAIN = CHAIN_PROFILES[GIG_CHAIN];
export const DEFAULT_RPC_URL = process.env.GIG_RPC_URL || ACTIVE_CHAIN.rpcUrl;

// ABI verified against erc-8004/erc-8004-contracts/contracts/ReputationRegistryUpgradeable.sol (read
// directly this session) — exact signature match to this feature's task brief.
const ABI = parseAbi([
  "function giveFeedback(uint256 agentId,int128 value,uint8 valueDecimals,string tag1,string tag2,string endpoint,string feedbackURI,bytes32 feedbackHash)",
  "function getSummary(uint256 agentId,address[] clientAddresses,string tag1,string tag2) view returns (uint64 count,int128 summaryValue,uint8 summaryValueDecimals)",
]);

export const GIG_COMPLETE_TAG1 = "gig-complete"; // spec §1 G2 wording, matches 23 §11's own tag convention
export const GIG_COMPLETE_TAG2 = "";
export const FEEDBACK_VALUE_DECIMALS = 0; // whole-number reputation points, spec's own +100/-100
export const POSITIVE_FEEDBACK_VALUE = 100n;
export const NEGATIVE_FEEDBACK_VALUE = -100n;

/**
 * buildFeedbackArgs — pure: builds giveFeedback's 8 positional args from a gig outcome. gigId is hashed
 * into feedbackHash deterministically (keccak256 of its own string form) so the SAME gigId always
 * produces the SAME on-chain feedbackHash — bookkeeping, not judgment (coding-style.md: pure fns for
 * deterministic transforms are fine). Throws synchronously (loudly, at build time, never silently) if
 * agentId is missing — never gives feedback with an undefined subject.
 */
export function buildFeedbackArgs({ agentId, positive, gigId, tag1 = GIG_COMPLETE_TAG1, tag2 = GIG_COMPLETE_TAG2, endpoint = "", feedbackURI }) {
  if (!agentId) throw new Error("reputation.mjs::buildFeedbackArgs -- agentId required");
  const value = positive ? POSITIVE_FEEDBACK_VALUE : NEGATIVE_FEEDBACK_VALUE;
  const feedbackHash = keccak256(toBytes(String(gigId ?? "")));
  const uri = feedbackURI ?? String(gigId ?? "");
  return [BigInt(agentId), value, FEEDBACK_VALUE_DECIMALS, tag1, tag2, endpoint, uri, feedbackHash];
}

/**
 * giveFeedback — writes one feedback entry for `agentId`, signed by `signerPrivateKey` (the CLIENT
 * giving feedback -- e.g. the gig's poster, never the agent being rated itself: the contract's own
 * "Self-feedback not allowed" guard reverts if msg.sender isAuthorizedOrOwner for agentId). Fail-open
 * contract (spec §4 MUST): NEVER throws -- every failure returns {ok:false, reason}, matching
 * identity.mjs's own registerIdentity() convention. `walletClientFactory`/`publicClientFactory` are
 * dependency-injected (tests pass fakes; production default constructs real viem clients).
 */
export async function giveFeedback({
  signerPrivateKey,
  agentId,
  positive,
  gigId,
  endpoint = "",
  feedbackURI,
  tag1 = GIG_COMPLETE_TAG1,
  tag2 = GIG_COMPLETE_TAG2,
  rpcUrl = DEFAULT_RPC_URL,
  chain = ACTIVE_CHAIN.chain,
  registryAddress = ACTIVE_CHAIN.registryAddress,
  walletClientFactory = (account) => createWalletClient({ account, chain, transport: http(rpcUrl) }),
  publicClientFactory = () => createPublicClient({ chain, transport: http(rpcUrl) }),
} = {}) {
  try {
    const account = privateKeyToAccount(signerPrivateKey);
    const args = buildFeedbackArgs({ agentId, positive, gigId, tag1, tag2, endpoint, feedbackURI });
    const walletClient = walletClientFactory(account);
    const hash = await walletClient.writeContract({ address: registryAddress, abi: ABI, functionName: "giveFeedback", args });
    const publicClient = publicClientFactory();
    const receipt = await publicClient.waitForTransactionReceipt({ hash });
    if (receipt.status !== "success") return { ok: false, reason: `giveFeedback tx reverted: ${hash}`, tx: hash };
    return { ok: true, tx: hash, agentId: String(agentId), positive: !!positive };
  } catch (e) {
    return { ok: false, reason: e.shortMessage || e.message || String(e) };
  }
}

/**
 * getReputationSummary — reads getSummary(agentId, clientAddresses, tag1, tag2). `clientAddresses` is
 * REQUIRED and must be non-empty: the contract itself `revert("clientAddresses required")`s on an empty
 * array (verified by reading ReputationRegistryUpgradeable.sol directly, NOT assumed from the spec's own
 * ABI wording) — we fail fast on that case WITHOUT constructing a client or making a network call at
 * all. Fail-open contract: never throws, returns {ok:false, reason} on any failure.
 */
export async function getReputationSummary({
  agentId,
  clientAddresses,
  tag1 = "",
  tag2 = "",
  rpcUrl = DEFAULT_RPC_URL,
  chain = ACTIVE_CHAIN.chain,
  registryAddress = ACTIVE_CHAIN.registryAddress,
  publicClientFactory = () => createPublicClient({ chain, transport: http(rpcUrl) }),
} = {}) {
  if (!Array.isArray(clientAddresses) || clientAddresses.length === 0) {
    return { ok: false, reason: "clientAddresses required and must be non-empty (contract reverts on empty array)" };
  }
  try {
    const publicClient = publicClientFactory();
    const [count, summaryValue, decimals] = await publicClient.readContract({
      address: registryAddress,
      abi: ABI,
      functionName: "getSummary",
      args: [BigInt(agentId), clientAddresses, tag1, tag2],
    });
    return { ok: true, count: Number(count), summaryValue: Number(summaryValue), decimals: Number(decimals) };
  } catch (e) {
    return { ok: false, reason: e.shortMessage || e.message || String(e) };
  }
}
