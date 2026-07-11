// spawn-funding-swap real client — REQ-018 (sprint-2, HIGHEST-RISK). createRealBaseSigner(): the ONLY
// production implementation of the baseSigner contract (matches createFakeBaseSigner: getAddress(),
// getNextNonce(), signAndBroadcast({amount, nonce, sourceAddress, destinationAkashAddress}) -> {txHash}).
// This is the SOLE real value-moving Base transaction anywhere in this repo -- every other Base-chain
// signer (skills/economy/gig/lib/escrow.mjs) only ever signs a GASLESS EIP-3009 authorization for a
// self-host facilitator to relay; this module submits an ACTUAL on-chain Base transaction that spends
// this instance's own USDC. No copy source exists for this shape anywhere in this repo (documented in
// this feature's sprint-2 task boundary as "the ONLY currently-viable ... highest risk" client).
//
// ==== Skip API integration, VERIFIED LIVE 2026-07-11 (not assumed from training data) ====
// POST https://api.skip.build/v2/fungible/route  -> {..., operations, chain_ids, txs_required, ...}
// POST https://api.skip.build/v2/fungible/msgs   (route's own fields + address_list, one bech32/0x
//   address PER entry of route.chain_ids, in that exact order -- verified: omitting any is rejected
//   with "address_list field is missing required addresses ... [8453 noble-1 osmosis-1 akashnet-2]")
//   -> {txs: [{evm_tx: {chain_id, to, value, data, required_erc20_approvals:[{token_contract,spender,
//   amount}], signer_address}}, {cosmos_tx: {...}}], ...}
// For this feature's live-confirmed route shape (Base USDC -[CCTP,smart_relay]-> noble-1 -[PFM]->
// osmosis-1 -[PFM swap]-> akashnet-2), `smart_relay: true` on the CCTP operation means Skip's OWN relayer
// network automatically executes the noble->osmosis->akashnet-2 leg once our Base evm_tx lands -- we sign
// and broadcast EXACTLY ONE Base transaction (matches driver.mjs's own "leg 0 is the only signed tx, every
// other legIndex is a pure relay-wait" design, lib/driver.mjs:110-116).
//
// ==== Why noble-1/osmosis-1 need REAL, recoverable addresses (not throwaway strings) ====
// These addresses become the IBC-transfer sender / PFM `recover_address` fields embedded in the relay's
// own memo (verified live: a failed swap_and_action would refund to `recover_address` on Osmosis) -- an
// address whose private key this process does not hold would make any relay-failure refund PERMANENTLY
// UNRECOVERABLE. lib/pure/cosmos-address.mjs derives REAL Cosmos-SDK bech32 addresses from the SAME
// secp256k1 private key already resolved for Base signing (the standard "one key, many bech32 prefixes"
// scheme every Cosmos-SDK chain uses), so this instance's own already-controlled key can recover funds
// sent to either intermediate address.
//
// ==== Nonce-tracking / ERC-20 approval design (money-safety-critical, READ BEFORE MODIFYING) ====
// driver.mjs's ensureLeg0Submitted (lib/driver.mjs:67-108) calls `ctx.baseSigner.getNextNonce()` EXACTLY
// ONCE per fresh leg-0 submission, durably writes that nonce to the ledger as `submitting` BEFORE ever
// calling signAndBroadcast, and later (on resume, e.g. after a crash) re-derives THAT SAME nonce's
// on-chain status via `chainReader.getBaseTxStatusByNonce(sourceAddress, nonce)`. This means the nonce
// this module reports via getNextNonce() MUST be EXACTLY the nonce the swap transaction itself will use
// on-chain -- if this module also needed to submit a SEPARATE ERC-20 `approve` transaction, sending it
// with a nonce fetched fresh INSIDE signAndBroadcast would collide with (or shift) the already-reserved
// tracked nonce, breaking crash-recovery's resume check (a classic "which of two txs does this nonce
// actually belong to" money-safety bug). The fix: getNextNonce() itself performs the approval
// check-and-send (using the account's CURRENT pending nonce, since at that point NO tx for this leg has
// been sent yet), and only returns the nonce AFTER any needed approval has landed -- so the nonce it
// returns (and the ledger durably records) is always the swap tx's own, real, exclusive nonce.
import { privateKeyToAccount } from "viem/accounts";
import { createPublicClient, createWalletClient, http as viemHttp, encodeFunctionData } from "viem";
import { base } from "viem/chains";
import { secp256k1 } from "@noble/curves/secp256k1";
import { sha256 } from "@noble/hashes/sha256";
import { ripemd160 } from "@noble/hashes/ripemd160";
import { resolveEvmPrivateKey } from "../../../../earn/lib/resolve-identity.mjs";
import { deriveCosmosAddress } from "../pure/cosmos-address.mjs";

const DEFAULT_BASE_RPC_URL = "https://mainnet.base.org";
const SKIP_ROUTE_ENDPOINT = "https://api.skip.build/v2/fungible/route";
const SKIP_MSGS_ENDPOINT = "https://api.skip.build/v2/fungible/msgs";

// Must equal driver.mjs's own BASE_CHAIN_ID/BASE_USDC_DENOM/AKASH_CHAIN_ID/AKASH_UAKT_DENOM literals
// (lib/driver.mjs:24-27) -- duplicated here (not imported) because the frozen signAndBroadcast interface
// receives only {amount, nonce, sourceAddress, destinationAkashAddress}, never the quoteSnapshot/route
// params driver.mjs already validated, so this module must independently re-derive the same route.
const BASE_CHAIN_ID = 8453;
const BASE_USDC_DENOM = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const AKASH_CHAIN_ID = "akashnet-2";
const AKASH_UAKT_DENOM = "uakt";
const NOBLE_CHAIN_ID = "noble-1";
const OSMOSIS_CHAIN_ID = "osmosis-1";

// Must equal bin/spawn-funding-swap.mjs's own DESTINATION_AKASH_ADDRESS literal (the single colony-wide
// "anicca-akash" keyring address, never overridable) -- duplicated for the same reason as above
// (getNextNonce() has no destinationAkashAddress parameter to work from; signAndBroadcast defensively
// verifies its own destinationAkashAddress argument matches this constant before ever signing).
const DESTINATION_AKASH_ADDRESS = "akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523";

// A small probe amount used ONLY by getNextNonce() to learn which spender contract this route's evm_tx
// would require an ERC-20 approval for -- decoupled from the real swap amount (unknown at getNextNonce()
// time) because CCTP's spender contract is determined by the ROUTE/bridge choice, not the amount.
const APPROVAL_PROBE_AMOUNT_BASE_UNITS = 1_000_000n; // 1 USDC
// Bounded allowance cap -- never MAX_UINT256 (mirrors lib/pure/constants.mjs's SWAP_MAX_USD=20 "small,
// bounded literal" philosophy: a compromised spender contract can drain at most this much, not the whole
// wallet). $100 gives headroom for many swaps at SWAP_MAX_USD=20 before a re-approval is ever needed.
const APPROVAL_CAP_BASE_UNITS = 100_000_000n; // $100

const ERC20_ALLOWANCE_ABI = [{ type: "function", name: "allowance", stateMutability: "view", inputs: [{ name: "owner", type: "address" }, { name: "spender", type: "address" }], outputs: [{ name: "", type: "uint256" }] }];
const ERC20_APPROVE_ABI = [{ type: "function", name: "approve", stateMutability: "nonpayable", inputs: [{ name: "spender", type: "address" }, { name: "amount", type: "uint256" }], outputs: [{ name: "", type: "bool" }] }];

async function rpcCall(fetchImpl, rpcUrl, method, params) {
  const res = await fetchImpl(rpcUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  });
  if (!res.ok) throw new Error(`base-signer: RPC http ${res.status} for ${method}`);
  const json = await res.json();
  if (json.error) throw new Error(`base-signer: RPC error for ${method}: ${JSON.stringify(json.error)}`);
  return json.result;
}

async function postJson(fetchImpl, url, body) {
  const res = await fetchImpl(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const json = await res.json().catch(() => null);
  return { res, json };
}

async function fetchSkipRoute(fetchImpl, amountInBaseUnits) {
  const body = {
    amount_in: amountInBaseUnits.toString(),
    source_asset_denom: BASE_USDC_DENOM,
    source_asset_chain_id: String(BASE_CHAIN_ID),
    dest_asset_denom: AKASH_UAKT_DENOM,
    dest_asset_chain_id: AKASH_CHAIN_ID,
    allow_unsafe: true,
    allow_multi_tx: true,
  };
  const { res, json } = await postJson(fetchImpl, SKIP_ROUTE_ENDPOINT, body);
  if (!res.ok || !json || json.code !== undefined) throw new Error(`base-signer: Skip route request failed: ${JSON.stringify(json)}`);
  if (json.dest_asset_denom !== AKASH_UAKT_DENOM || json.dest_asset_chain_id !== AKASH_CHAIN_ID) {
    throw new Error(`base-signer: Skip route has unexpected destination (${json.dest_asset_denom}/${json.dest_asset_chain_id}) -- refusing to proceed (REQ-004 fail-closed)`);
  }
  return json;
}

function addressForChainHop(chainId, addresses) {
  if (chainId === String(BASE_CHAIN_ID)) return addresses.sourceBaseAddress;
  if (chainId === NOBLE_CHAIN_ID) return addresses.nobleAddress;
  if (chainId === OSMOSIS_CHAIN_ID) return addresses.osmosisAddress;
  if (chainId === AKASH_CHAIN_ID) return addresses.destinationAkashAddress;
  throw new Error(`base-signer: unsupported route chain hop '${chainId}' -- this feature only supports the live-confirmed Base -> noble-1 -> osmosis-1 -> akashnet-2 shape (REQ-004 fail-closed)`);
}

async function fetchSkipMsgs(fetchImpl, route, addresses) {
  const addressList = (route.chain_ids || []).map((cid) => addressForChainHop(cid, addresses));
  const body = {
    source_asset_denom: route.source_asset_denom,
    source_asset_chain_id: route.source_asset_chain_id,
    dest_asset_denom: route.dest_asset_denom,
    dest_asset_chain_id: route.dest_asset_chain_id,
    amount_in: route.amount_in,
    amount_out: route.amount_out,
    operations: route.operations,
    address_list: addressList,
    slippage_tolerance_percent: "1",
  };
  const { res, json } = await postJson(fetchImpl, SKIP_MSGS_ENDPOINT, body);
  if (!res.ok || !json || json.code !== undefined || !Array.isArray(json.txs)) {
    throw new Error(`base-signer: Skip msgs request failed: ${JSON.stringify(json)}`);
  }
  return json;
}

function extractSingleEvmTx(msgsResponse) {
  const evmTxs = (msgsResponse.txs || []).filter((t) => t && t.evm_tx);
  if (evmTxs.length !== 1) {
    throw new Error(`base-signer: expected exactly one evm_tx in Skip msgs response, got ${evmTxs.length} -- refusing to sign an unexpected shape (REQ-004 fail-closed)`);
  }
  return evmTxs[0].evm_tx;
}

/**
 * createRealBaseSigner — REQ-018.
 * @param {{
 *   fetchImpl?: typeof fetch,
 *   baseRpcUrl?: string,
 *   env?: Record<string,string>,
 *   walletClientFactory?: (account: object) => object,
 *   publicClientFactory?: () => object,
 * }} [opts] walletClientFactory/publicClientFactory are test-only seams (default: real viem clients).
 */
export function createRealBaseSigner({
  fetchImpl = globalThis.fetch,
  baseRpcUrl,
  env = process.env,
  walletClientFactory,
  publicClientFactory,
} = {}) {
  const rpcUrl = baseRpcUrl || env.BASE_RPC_URL || DEFAULT_BASE_RPC_URL;

  function resolvePrivateKey() {
    // Mirrors resolve-swap-identity.mjs's own ANICCA_HOME gate exactly -- in production this is already
    // guaranteed true by the CLI's own REQ-009 identity check (which runs BEFORE this module is even
    // imported), but this module stays independently fail-closed/safe if ever constructed standalone.
    if (typeof env.ANICCA_HOME !== "string" || env.ANICCA_HOME.length === 0) {
      throw new Error("base-signer: ANICCA_HOME is not set -- no per-instance signing key to resolve (fail-closed)");
    }
    const pk = resolveEvmPrivateKey({ home: env.ANICCA_HOME, env });
    if (!pk) throw new Error(`base-signer: no Base signing key resolved under ANICCA_HOME=${env.ANICCA_HOME} (fail-closed)`);
    return pk;
  }

  function account() {
    return privateKeyToAccount(resolvePrivateKey());
  }

  function getWalletClient(acct) {
    if (walletClientFactory) return walletClientFactory(acct);
    return createWalletClient({ account: acct, chain: base, transport: viemHttp(rpcUrl) });
  }
  function getPublicClient() {
    if (publicClientFactory) return publicClientFactory();
    return createPublicClient({ chain: base, transport: viemHttp(rpcUrl) });
  }

  function cosmosAddresses() {
    const pk = resolvePrivateKey();
    const privBytes = Uint8Array.from(Buffer.from(pk.slice(2), "hex"));
    const compressedPubkey = secp256k1.getPublicKey(privBytes, true);
    const pubkeyHash = ripemd160(sha256(compressedPubkey));
    return {
      nobleAddress: deriveCosmosAddress(pubkeyHash, "noble"),
      osmosisAddress: deriveCosmosAddress(pubkeyHash, "osmo"),
    };
  }

  async function currentAllowance(ownerAddress, spender) {
    const data = encodeFunctionData({ abi: ERC20_ALLOWANCE_ABI, functionName: "allowance", args: [ownerAddress, spender] });
    const raw = await rpcCall(fetchImpl, rpcUrl, "eth_call", [{ to: BASE_USDC_DENOM, data }, "latest"]);
    return BigInt(raw === "0x" || !raw ? "0x0" : raw);
  }

  // ensureApprovalsSettled — see module header's "Nonce-tracking / ERC-20 approval design". Runs ONLY
  // from getNextNonce(), BEFORE the tracked leg-0 nonce is ever handed to the driver, so any approve tx
  // it sends uses a nonce that is provably free (no swap-leg nonce has been reserved yet).
  async function ensureApprovalsSettled(acct) {
    const { nobleAddress, osmosisAddress } = cosmosAddresses();
    const probeRoute = await fetchSkipRoute(fetchImpl, APPROVAL_PROBE_AMOUNT_BASE_UNITS);
    const msgsResponse = await fetchSkipMsgs(fetchImpl, probeRoute, {
      sourceBaseAddress: acct.address,
      nobleAddress,
      osmosisAddress,
      destinationAkashAddress: DESTINATION_AKASH_ADDRESS,
    });
    const evmTx = extractSingleEvmTx(msgsResponse);
    for (const approval of evmTx.required_erc20_approvals || []) {
      const have = await currentAllowance(acct.address, approval.spender);
      if (have >= APPROVAL_CAP_BASE_UNITS) continue;
      const approveData = encodeFunctionData({ abi: ERC20_APPROVE_ABI, functionName: "approve", args: [approval.spender, APPROVAL_CAP_BASE_UNITS] });
      const nonceHex = await rpcCall(fetchImpl, rpcUrl, "eth_getTransactionCount", [acct.address, "pending"]);
      const approveNonce = Number(BigInt(nonceHex));
      const wc = getWalletClient(acct);
      const hash = await wc.sendTransaction({ to: BASE_USDC_DENOM, data: approveData, value: 0n, nonce: approveNonce });
      const pc = getPublicClient();
      await pc.waitForTransactionReceipt({ hash });
    }
  }

  return {
    async getAddress() {
      return account().address;
    },

    /** getNextNonce — see module header. Performs approval check-and-settle FIRST, THEN returns the
     * account's current pending nonce -- guaranteed to be the swap tx's own, exclusive nonce. */
    async getNextNonce() {
      const acct = account();
      await ensureApprovalsSettled(acct);
      const nonceHex = await rpcCall(fetchImpl, rpcUrl, "eth_getTransactionCount", [acct.address, "pending"]);
      return BigInt(nonceHex);
    },

    /** signAndBroadcast — REQ-004/REQ-005/REQ-009. Signs and submits EXACTLY the pre-reserved `nonce`;
     * never fetches or spends a different nonce (see module header). */
    async signAndBroadcast({ amount, nonce, sourceAddress, destinationAkashAddress }) {
      const acct = account();
      if (typeof sourceAddress === "string" && sourceAddress.toLowerCase() !== acct.address.toLowerCase()) {
        throw new Error(`base-signer: sourceAddress ${sourceAddress} does not match this signer's own address ${acct.address} -- refusing to sign (money-safety)`);
      }
      if (destinationAkashAddress !== DESTINATION_AKASH_ADDRESS) {
        throw new Error(`base-signer: destinationAkashAddress ${destinationAkashAddress} does not match the fixed colony destination -- refusing to sign (money-safety)`);
      }

      const route = await fetchSkipRoute(fetchImpl, BigInt(amount));
      const { nobleAddress, osmosisAddress } = cosmosAddresses();
      const msgsResponse = await fetchSkipMsgs(fetchImpl, route, {
        sourceBaseAddress: acct.address,
        nobleAddress,
        osmosisAddress,
        destinationAkashAddress,
      });
      const evmTx = extractSingleEvmTx(msgsResponse);
      if (evmTx.signer_address.toLowerCase() !== acct.address.toLowerCase()) {
        throw new Error(`base-signer: Skip evm_tx.signer_address ${evmTx.signer_address} does not match this signer's own address -- refusing to sign`);
      }
      for (const approval of evmTx.required_erc20_approvals || []) {
        const have = await currentAllowance(acct.address, approval.spender);
        if (have < BigInt(approval.amount)) {
          throw new Error(`base-signer: insufficient USDC allowance for spender ${approval.spender} at sign time (getNextNonce() should have already settled this) -- refusing to sign without a verified allowance (money-safety)`);
        }
      }

      const wc = getWalletClient(acct);
      const hash = await wc.sendTransaction({
        to: evmTx.to,
        data: evmTx.data,
        value: BigInt(evmTx.value || 0),
        nonce: Number(nonce),
      });
      return { txHash: hash };
    },
  };
}
