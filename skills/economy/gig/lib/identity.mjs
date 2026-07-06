// economy/gig/lib/identity.mjs — ERC-8004 Trustless Agents identity, called DIRECTLY via viem
// (register() = permissionless ERC-721 _safeMint(msg.sender), per SPEC.md §1.2: "壊れた scaffold
// 不使用"). No create-8004-agent scaffold (confirmed broken: tsc errors + Pinata dependency), no new
// contract deployed by us -- we reuse the REAL, already-live reference-implementation deployment
// (ChaosChain/trustless-agents-erc-ri, CC0-1.0) on Base Sepolia, same chain as our x402 facilitator:
//
//   IdentityRegistry = 0xdc527768082c489e0ee228d24d3cfa290214f387 (base-sepolia, chainId 84532)
//   legacy v1.1.0 per deployments.json (github.com/ChaosChain/trustless-agents-erc-ri) -- verified LIVE
//   2026-07-07 via eth_call name() -> "ERC-8004 Trustless Agent" (matches the ERC721 constructor name
//   in src/IdentityRegistry.sol). register()/ownerOf()/agentExists() are unchanged between this legacy
//   v1.1.0 and the current v1.2.0 main-branch source (Jan-2026 update only touched
//   unsetAgentWallet/Reputation/Validation), so the current ABI is accurate for this deployment.
//
// Each agent registers ITSELF (msg.sender = the agent's own wallet, mints the identity NFT to itself)
// -- there is no gasless/relayed register() path in this contract, so the calling wallet needs a small
// amount of Base Sepolia ETH (scripts/fund-agents.mjs drips it from the facilitator's own signer, which
// already holds bridged testnet ETH from P2.1).
import { createPublicClient, createWalletClient, http, parseAbi, decodeEventLog } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { baseSepolia } from "viem/chains";

export const IDENTITY_REGISTRY_BASE_SEPOLIA = "0xdc527768082c489e0ee228d24d3cfa290214f387";
export const DEFAULT_RPC_URL = "https://sepolia.base.org";

const ABI = parseAbi([
  "function register() returns (uint256 agentId)",
  "function ownerOf(uint256 tokenId) view returns (address)",
  "function agentExists(uint256 agentId) view returns (bool)",
  "function totalAgents() view returns (uint256)",
  "event Registered(uint256 indexed agentId, string agentURI, address indexed owner)",
]);

function clients(rpcUrl) {
  const transport = http(rpcUrl);
  return {
    publicClient: createPublicClient({ chain: baseSepolia, transport }),
  };
}

/**
 * registerIdentity — mint a fresh ERC-8004 agent identity owned by `privateKey`'s own address.
 * Returns { ok:true, agentId, address, tx } on success, { ok:false, reason } on failure (reverted tx,
 * insufficient gas, etc) -- never throws, fail-closed like the rest of this skill.
 */
export async function registerIdentity({ privateKey, rpcUrl = DEFAULT_RPC_URL, registryAddress = IDENTITY_REGISTRY_BASE_SEPOLIA }) {
  const account = privateKeyToAccount(privateKey);
  const { publicClient } = clients(rpcUrl);
  const walletClient = createWalletClient({ account, chain: baseSepolia, transport: http(rpcUrl) });
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
export async function verifyIdentity({ agentId, expectedAddress, rpcUrl = DEFAULT_RPC_URL, registryAddress = IDENTITY_REGISTRY_BASE_SEPOLIA }) {
  const { publicClient } = clients(rpcUrl);
  try {
    const owner = await publicClient.readContract({ address: registryAddress, abi: ABI, functionName: "ownerOf", args: [BigInt(agentId)] });
    return { ok: true, valid: owner.toLowerCase() === expectedAddress.toLowerCase(), owner };
  } catch (e) {
    return { ok: false, valid: false, reason: e.shortMessage || e.message || String(e) };
  }
}
