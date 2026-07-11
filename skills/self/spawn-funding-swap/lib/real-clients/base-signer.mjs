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
// driver.mjs's ensureLeg0Submitted (lib/driver.mjs:67-108) calls `ctx.baseSigner.getNextNonce(amount)`
// EXACTLY ONCE per fresh leg-0 submission, durably writes that nonce to the ledger as `submitting` BEFORE
// ever calling signAndBroadcast, and later (on resume, e.g. after a crash) re-derives THAT SAME nonce's
// on-chain status via `chainReader.getBaseTxStatusByNonce(sourceAddress, nonce)`. This means the nonce
// this module reports via getNextNonce() MUST be EXACTLY the nonce the swap transaction itself will use
// on-chain -- if this module also needed to submit a SEPARATE ERC-20 `approve` transaction, sending it
// with a nonce fetched fresh INSIDE signAndBroadcast would collide with (or shift) the already-reserved
// tracked nonce, breaking crash-recovery's resume check (a classic "which of two txs does this nonce
// actually belong to" money-safety bug). The fix: getNextNonce() itself performs the approval
// check-and-send (using the account's CURRENT pending nonce, since at that point NO tx for this leg has
// been sent yet), and only returns the nonce AFTER any needed approval has landed -- so the nonce it
// returns (and the ledger durably records) is always the swap tx's own, real, exclusive nonce. `amount`
// is `requiredBaseUnits` -- already computed by driver.mjs's REQ-006/REQ-012 choke point BEFORE
// ensureLeg0Submitted is ever called (lib/driver.mjs:174-175/213) -- so it is available at getNextNonce()
// call time even though it was not previously threaded through this interface.
//
// ==== FIND-001 iter2 fix (CRITICAL, impl review iteration 2): per-swap EXACT-amount approval ====
// PREVIOUSLY (iter1): ensureApprovalsSettled topped the on-chain allowance up to a flat
// APPROVAL_CAP_BASE_UNITS ($100) and NEVER lowered it once reached -- a STANDING allowance that
// outlived any individual swap. verifyEvmTxAgainstIntent's gate 3 only checked Skip's SELF-REPORTED
// `required_erc20_approvals[0].amount` metadata field against the driver's `amount`; it never checked
// what the ACTUAL on-chain allowance was. A fully-malicious/compromised Skip response could therefore
// name the already-$100-approved spender, report a small/honest metadata amount (passing gate 3), and
// embed calldata that pulls the FULL standing $100 allowance on execution -- a 5x loss-amplification
// over SWAP_MAX_USD ($20), because the metadata field has no cryptographic or on-chain link to what the
// spender's own bytecode will actually execute via transferFrom.
//
// THE FIX: this module now approves EXACTLY `amount` (the driver's already-capped, <= SWAP_MAX_USD
// value) for THIS swap's spender, every swap, never a standing higher cap (ensureApprovalsSettled,
// below). The invariant this guarantees: the on-chain allowance available to any spender this module
// ever calls is ALWAYS <= `amount` -- so even a fully-malicious route, naming a spender with an
// arbitrary calldata payload, can never pull more than `amount` (<= $20), because that is structurally
// the most that was ever approved. signAndBroadcast's post-gate allowance check (below) independently
// re-verifies this by querying the CURRENT on-chain allowance at broadcast time and refusing to sign if
// it exceeds the intended amount -- never trusting Skip's metadata alone. Approve-race handling: many
// ERC-20s (historically USDT-style, and defensively assumed here even though Base USDC is a standard
// OpenZeppelin ERC-20 that does not require it) reject setting a non-zero allowance directly over an
// existing non-zero allowance; ensureApprovalsSettled resets to 0 first whenever the current allowance is
// non-zero and does not already exactly equal the desired amount, then sets the desired amount.
// Post-swap reset: a successful swap's transferFrom pull of exactly `amount` naturally leaves the
// allowance at 0 (the honest case). This module does NOT send an additional post-swap reset-to-0
// transaction: doing so would need its own nonce, which the ledger's single-nonce-per-leg-0
// crash-recovery model (this same header comment, above) does not track -- a crash between the swap
// broadcast and a hypothetical reset tx would leave that reset's own state unaccounted for by
// `ensureLeg0Submitted`'s resume logic, and resuming a `submitting` leg re-derives ONLY the swap tx's own
// nonce/status, never a second one. Instead, any residual (non-zero but never-more-than-the-last-swap's-
// `amount`, i.e. <= SWAP_MAX_USD) allowance is self-healed by the NEXT swap's ensureApprovalsSettled call
// (reset-to-0-then-set-to-the-new-amount), so no standing allowance ever exceeds a single swap's own
// `amount` for longer than the gap between two swaps -- and even during that gap, the bound is <= $20,
// never $100.
import { privateKeyToAccount } from "viem/accounts";
import { createPublicClient, createWalletClient, http as viemHttp, encodeFunctionData, decodeFunctionData } from "viem";
import { base } from "viem/chains";
import { secp256k1 } from "@noble/curves/secp256k1";
import { sha256 } from "@noble/hashes/sha256";
import { ripemd160 } from "@noble/hashes/ripemd160";
import { resolveEvmPrivateKey } from "../../../../earn/lib/resolve-identity.mjs";
import { deriveCosmosAddress } from "../pure/cosmos-address.mjs";
import {
  BASE_CHAIN_ID,
  BASE_USDC_DENOM,
  AKASH_CHAIN_ID,
  AKASH_UAKT_DENOM,
  DESTINATION_AKASH_ADDRESS,
  SWAP_MAX_USD,
  USDC_DECIMALS_BASE,
} from "../pure/constants.mjs";

const DEFAULT_BASE_RPC_URL = "https://mainnet.base.org";
const SKIP_ROUTE_ENDPOINT = "https://api.skip.build/v2/fungible/route";
const SKIP_MSGS_ENDPOINT = "https://api.skip.build/v2/fungible/msgs";

// BASE_CHAIN_ID/BASE_USDC_DENOM/AKASH_CHAIN_ID/AKASH_UAKT_DENOM/DESTINATION_AKASH_ADDRESS are now
// imported from lib/pure/constants.mjs (FIND-005 fix, impl review iter1) -- previously each was an
// independent hand-copied literal here, in lib/driver.mjs, and (for DESTINATION_AKASH_ADDRESS) in
// bin/spawn-funding-swap.mjs too. Only pure/constants.mjs defines them now; every one of these files
// imports from there. This module still needs its OWN re-derivation of the route/evm_tx (the frozen
// signAndBroadcast interface receives no quoteSnapshot param), but the LITERAL VALUES it re-derives
// against are single-sourced.
const NOBLE_CHAIN_ID = "noble-1";
const OSMOSIS_CHAIN_ID = "osmosis-1";

// A small probe amount used ONLY by getNextNonce() to learn which spender contract this route's evm_tx
// would require an ERC-20 approval for -- decoupled from the real swap amount for SPENDER DISCOVERY ONLY
// (the actual amount approved to that spender is always the real `amount`, never this probe value -- see
// ensureApprovalsSettled below) because CCTP's spender contract is determined by the ROUTE/bridge choice,
// not the amount.
//
// FIND-003 (impl review iter1, documented assumption, not fixed this iteration -- accepted risk): Skip's
// spender-contract selection for a route COULD in principle vary by amount tier (a different bridge/venue
// chosen for a 1-USDC probe vs. the real, larger swap amount). If that ever happens, the allowance
// getNextNonce() settles targets the wrong spender, and signAndBroadcast's own allowance check (which
// correctly refuses to attempt a second, nonce-colliding approve -- see PROP-047) throws on every real
// invocation: a silent, fail-CLOSED denial-of-service (this feature's funding mechanism stops working),
// NEVER a fund-loss mode (no tx is ever signed/broadcast with a mismatched spender; signAndBroadcast's
// verifyEvmTxAgainstIntent below additionally REQUIRES evm_tx.to to equal the spender the on-chain
// allowance was actually granted to, so even a wrong-spender probe cannot cause a fund-unsafe broadcast --
// it can only ever cause a refusal). This is exercised by PROP-051's test in base-signer.test.mjs
// ("getNextNonce()'s probe-vs-real spender mismatch fails closed via signAndBroadcast's allowance/
// self-consistency checks, never signs against a mismatched spender").
const APPROVAL_PROBE_AMOUNT_BASE_UNITS = 1_000_000n; // 1 USDC

// MAX_SWAP_BASE_UNITS -- FIND-001 fix (CRITICAL, impl review iter1, tightened impl review iter2). The
// ABSOLUTE, independent ceiling signAndBroadcast enforces on the decoded USDC amount a signed tx may
// move, regardless of what `amount` parameter it was called with (defense in depth: a buggy/compromised
// CALLER of this module can never cause it to sign a tx moving more than this). Derived directly from
// `SWAP_MAX_USD`/`USDC_DECIMALS_BASE` (lib/pure/constants.mjs's own single choke point for this feature's
// per-invocation spend cap) rather than a second, independently-tunable literal -- iter1 previously
// reused a separate `APPROVAL_CAP_BASE_UNITS` ($100) here, which was 5x looser than the driver's own
// SWAP_MAX_USD=$20 cap and was exactly FIND-001 (iter2)'s root cause (see this module's header comment).
// Since ensureApprovalsSettled below now approves EXACTLY `amount` per swap (never a standing higher
// cap), this ceiling and the actual on-chain allowance are now the SAME bound, at the SAME ($20, not
// $100) magnitude -- `APPROVAL_CAP_BASE_UNITS` no longer exists as a separate concept.
const MAX_SWAP_BASE_UNITS = BigInt(SWAP_MAX_USD) * 10n ** BigInt(USDC_DECIMALS_BASE);

const ERC20_ALLOWANCE_ABI = [{ type: "function", name: "allowance", stateMutability: "view", inputs: [{ name: "owner", type: "address" }, { name: "spender", type: "address" }], outputs: [{ name: "", type: "uint256" }] }];
const ERC20_APPROVE_ABI = [{ type: "function", name: "approve", stateMutability: "nonpayable", inputs: [{ name: "spender", type: "address" }, { name: "amount", type: "uint256" }], outputs: [{ name: "", type: "bool" }] }];
// FIND-001 fix -- the bare ERC-20 transfer/transferFrom selectors this route's evm_tx.data must NEVER
// encode (Skip's own EVM Transactions doc, docs.skip.build/go/advanced-transfer/evm-transactions,
// verified live 2026-07-11: "data... will be interpreted according to the ABI of the contract... If this
// field is empty, it means the transaction is sending funds to an address" -- this feature's live-
// confirmed CCTP multi-hop route is ALWAYS a contract call into a router/entry-point contract, which
// itself performs any USDC movement via transferFrom against an on-chain-capped allowance; a bare
// transfer()/transferFrom() selector in evm_tx.data is therefore NEVER this route's legitimate shape).
const ERC20_TRANSFER_SELECTOR = "0xa9059cbb"; // transfer(address,uint256)
const ERC20_TRANSFER_FROM_SELECTOR = "0x23b872dd"; // transferFrom(address,address,uint256)
const ERC20_TRANSFER_ABI = [{ type: "function", name: "transfer", stateMutability: "nonpayable", inputs: [{ name: "to", type: "address" }, { name: "amount", type: "uint256" }], outputs: [{ name: "", type: "bool" }] }];
const ERC20_TRANSFER_FROM_ABI = [{ type: "function", name: "transferFrom", stateMutability: "nonpayable", inputs: [{ name: "from", type: "address" }, { name: "to", type: "address" }, { name: "amount", type: "uint256" }], outputs: [{ name: "", type: "bool" }] }];

/**
 * verifyEvmTxAgainstIntent -- FIND-001 (CRITICAL) / FIND-002 fix, PROP-050 (Tier-2, money-safety-
 * critical). Decodes and bound-checks the ACTUAL evm_tx Skip returned against the driver-supplied intent
 * BEFORE signAndBroadcast ever signs anything. Previously (iter1 finding) this module trusted evm_tx.to/
 * data/value completely; every gate below is independent and ALL must pass, fail-closed (throw) on any
 * violation:
 *
 *  1. evm_tx.data must NOT decode as a bare ERC-20 transfer()/transferFrom() call -- this feature's
 *     route shape is always a router/entry-point contract call (see ERC20_TRANSFER_SELECTOR comment
 *     above); a bare transfer selector is the exact "direct wallet-authorized movement, bypasses any
 *     approval cap entirely" attack FIND-001 identified (up to the ENTIRE USDC balance, not bounded by
 *     MAX_SWAP_BASE_UNITS/SWAP_MAX_USD) and is refused unconditionally, regardless of `to`.
 *  2. evm_tx.to must be a single, non-USDC-contract address that EXACTLY equals the sole entry in
 *     evm_tx.required_erc20_approvals[].spender. This allowlist is deliberately NOT a hardcoded Skip
 *     contract-address literal (Skip's own deployed router/entry-point address can differ across route
 *     variants/redeployments, and a wrong hardcoded guess would either falsely refuse legitimate swaps or
 *     -- worse -- be silently stale); instead it is derived FROM the live route response itself, self-
 *     consistently: the only contract this wallet's key is ever asked to call is the exact contract this
 *     same code path also grants an EXACT-`amount`-bounded on-chain ERC-20 allowance to, never a standing
 *     higher cap (enforced by ensureApprovalsSettled AND independently re-verified by the allowance-check
 *     loop below, which queries the CURRENT on-chain allowance -- not Skip's metadata -- at broadcast
 *     time). Since USDC can only leave this wallet via that contract's own transferFrom (never a raw
 *     transfer -- gate 1 above already forbids that), the ACTUAL on-chain allowance is what structurally
 *     bounds this contract's total spend authority to <= `amount`, regardless of what its own internal
 *     calldata/logic does (iter2 fix: no longer relies on Skip's self-reported metadata amount alone).
 *  3. required_erc20_approvals[].amount (Skip's self-reported metadata field) must equal the driver-
 *     supplied `amount` parameter EXACTLY (bigint ===) and must not exceed MAX_SWAP_BASE_UNITS. This is
 *     ONE layer of defense against "Skip quote re-priced/rounded/cached-stale, or was tampered with" --
 *     but (iter2 fix, FIND-001 CRITICAL) it is NEVER trusted alone: gate 4 below independently queries the
 *     REAL on-chain allowance and refuses to sign unless it too is EXACTLY `amount`, so even a fully
 *     malicious Skip response that lies about this metadata field in a way that happens to match `amount`
 *     cannot cause this module to sign against a spender that was actually granted more.
 *  4. (post-gate, in signAndBroadcast below, after ensureApprovalsSettled has run) the ACTUAL current
 *     on-chain allowance for approval.spender must be EXACTLY `amount` -- neither insufficient (the swap
 *     would revert on-chain) NOR in excess (a standing/stale higher allowance from a prior swap or a
 *     compromised probe, the exact iter2 CRITICAL attack: metadata says `amount`, on-chain allowance says
 *     more). This is a REAL RPC query against Base state, never taken on faith from any HTTP response.
 *  5. evm_tx.value (native ETH) must be exactly 0n -- this feature's route is USDC-only; there is no
 *     legitimate reason for a non-zero native-value transfer, so any non-zero value is refused.
 */
function verifyEvmTxAgainstIntent(evmTx, amount) {
  const dataHex = typeof evmTx.data === "string" ? evmTx.data : "";
  const selector = dataHex.slice(0, 10).toLowerCase();
  if (selector === ERC20_TRANSFER_SELECTOR || selector === ERC20_TRANSFER_FROM_SELECTOR) {
    let decodedArgs = null;
    try {
      const abi = selector === ERC20_TRANSFER_SELECTOR ? ERC20_TRANSFER_ABI : ERC20_TRANSFER_FROM_ABI;
      decodedArgs = decodeFunctionData({ abi, data: evmTx.data }).args;
    } catch {
      // Decoding is best-effort (only used to enrich the thrown error message) -- the selector match
      // alone is sufficient grounds to refuse, decodable or not.
    }
    throw new Error(`base-signer: evm_tx.data encodes a bare ERC-20 transfer/transferFrom call (selector ${selector}${decodedArgs ? `, decoded args ${JSON.stringify(decodedArgs, (_k, v) => (typeof v === "bigint" ? v.toString() : v))}` : ""}) -- never a legitimate shape for this feature's CCTP router route, refusing to sign (money-safety, PROP-050/FIND-001)`);
  }

  const approvals = evmTx.required_erc20_approvals || [];
  if (approvals.length !== 1) {
    throw new Error(`base-signer: expected exactly ONE required_erc20_approvals entry in evm_tx (got ${approvals.length}) -- a zero-approval evm_tx can move USDC with no on-chain-enforced bound at all, and a multi-approval evm_tx is an unsupported shape; refusing to sign (money-safety, PROP-050/FIND-001)`);
  }
  const [approval] = approvals;
  if (typeof evmTx.to !== "string" || typeof approval.spender !== "string" || evmTx.to.toLowerCase() !== approval.spender.toLowerCase()) {
    throw new Error(`base-signer: evm_tx.to (${evmTx.to}) does not equal its own required_erc20_approvals[0].spender (${approval.spender}) -- the contract this tx calls MUST be the same contract this feature grants a bounded ERC-20 allowance to (self-consistency allowlist, money-safety, PROP-050/FIND-001)`);
  }
  if (evmTx.to.toLowerCase() === BASE_USDC_DENOM.toLowerCase()) {
    throw new Error(`base-signer: evm_tx.to is the USDC contract itself (${BASE_USDC_DENOM}) -- never a legitimate call target for this feature's router-based route shape; refusing to sign (money-safety, PROP-050/FIND-001)`);
  }
  if (typeof approval.token_contract === "string" && approval.token_contract.toLowerCase() !== BASE_USDC_DENOM.toLowerCase()) {
    throw new Error(`base-signer: required_erc20_approvals[0].token_contract (${approval.token_contract}) is not the expected USDC contract (${BASE_USDC_DENOM}) -- refusing to sign (money-safety, PROP-050/FIND-001)`);
  }
  const approvalAmount = BigInt(approval.amount);
  const intendedAmount = BigInt(amount);
  if (approvalAmount !== intendedAmount) {
    throw new Error(`base-signer: required_erc20_approvals[0].amount (${approvalAmount}) does not exactly equal the driver-supplied swap amount (${intendedAmount}) -- refusing to sign a tx authorizing a different amount than intended (money-safety, PROP-050/FIND-001)`);
  }
  if (approvalAmount > MAX_SWAP_BASE_UNITS) {
    throw new Error(`base-signer: required_erc20_approvals[0].amount (${approvalAmount}) exceeds the absolute per-swap ceiling MAX_SWAP_BASE_UNITS (${MAX_SWAP_BASE_UNITS}) -- refusing to sign (money-safety, PROP-050/FIND-001)`);
  }
  const evmValue = BigInt(evmTx.value || 0);
  if (evmValue !== 0n) {
    throw new Error(`base-signer: evm_tx.value (${evmValue}) is non-zero -- this feature's USDC-only route never legitimately sends native ETH value; refusing to sign (money-safety, PROP-050/FIND-001)`);
  }
}

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

  // sendApprove — one on-chain ERC-20 approve(spender, amountBaseUnits), using the account's CURRENT
  // pending nonce (fetched fresh, immediately before sending), and blocking until it lands. Extracted so
  // ensureApprovalsSettled can call it either once (the common case: allowance is already 0, no reset
  // needed) or twice in sequence (reset-to-0, then set-to-desired), each with its own freshly-fetched,
  // strictly-sequential nonce.
  async function sendApprove(acct, spender, amountBaseUnits) {
    const approveData = encodeFunctionData({ abi: ERC20_APPROVE_ABI, functionName: "approve", args: [spender, amountBaseUnits] });
    const nonceHex = await rpcCall(fetchImpl, rpcUrl, "eth_getTransactionCount", [acct.address, "pending"]);
    const approveNonce = Number(BigInt(nonceHex));
    const wc = getWalletClient(acct);
    const hash = await wc.sendTransaction({ to: BASE_USDC_DENOM, data: approveData, value: 0n, nonce: approveNonce });
    const pc = getPublicClient();
    await pc.waitForTransactionReceipt({ hash });
  }

  // ensureApprovalsSettled — see module header's "Nonce-tracking / ERC-20 approval design" AND its
  // "FIND-001 iter2 fix" section. Runs ONLY from getNextNonce(), BEFORE the tracked leg-0 nonce is ever
  // handed to the driver, so any approve tx it sends uses a nonce that is provably free (no swap-leg
  // nonce has been reserved yet). `amount` is the driver's own already-capped (<= SWAP_MAX_USD) swap
  // amount -- this function grants EXACTLY that much allowance to the spender this route's probe
  // identifies, NEVER a standing higher cap:
  //  - if the current on-chain allowance already EXACTLY equals `amount`, no tx is sent (idempotent
  //    resume-safe: a prior swap for the SAME amount, or this same swap's own already-settled approval,
  //    needs no further action).
  //  - if the current allowance is non-zero and does NOT already equal `amount` (a residual from a prior
  //    swap's different amount, e.g. a route that didn't fully consume its allowance, or a stale grant
  //    from before this fix existed), it is first reset to 0, then set to `amount` -- the standard
  //    ERC-20 approve-race-safe sequence (some tokens revert setting a non-zero allowance directly over
  //    an existing non-zero one; Base USDC is a standard OpenZeppelin ERC-20 that does not require this,
  //    but the reset-first sequence is applied defensively regardless, since it is always safe/idempotent
  //    for a standard-compliant token).
  //  - if the current allowance is exactly 0, it is set directly to `amount` (one tx, the common case).
  async function ensureApprovalsSettled(acct, amount) {
    const { nobleAddress, osmosisAddress } = cosmosAddresses();
    const probeRoute = await fetchSkipRoute(fetchImpl, APPROVAL_PROBE_AMOUNT_BASE_UNITS);
    const msgsResponse = await fetchSkipMsgs(fetchImpl, probeRoute, {
      sourceBaseAddress: acct.address,
      nobleAddress,
      osmosisAddress,
      destinationAkashAddress: DESTINATION_AKASH_ADDRESS,
    });
    const evmTx = extractSingleEvmTx(msgsResponse);
    const desired = BigInt(amount);
    for (const approval of evmTx.required_erc20_approvals || []) {
      const have = await currentAllowance(acct.address, approval.spender);
      if (have === desired) continue;
      if (have !== 0n) {
        await sendApprove(acct, approval.spender, 0n);
      }
      await sendApprove(acct, approval.spender, desired);
    }
  }

  return {
    async getAddress() {
      return account().address;
    },

    /** getNextNonce(amount) — see module header. `amount` is the real, already-capped swap amount
     * (driver.mjs's requiredBaseUnits, computed BEFORE this is called -- REQ-006/REQ-012). Performs
     * approval check-and-settle FIRST (granting EXACTLY `amount`, never a standing higher cap -- FIND-001
     * iter2 fix), THEN returns the account's current pending nonce -- guaranteed to be the swap tx's own,
     * exclusive nonce. */
    async getNextNonce(amount) {
      const acct = account();
      await ensureApprovalsSettled(acct, amount);
      const nonceHex = await rpcCall(fetchImpl, rpcUrl, "eth_getTransactionCount", [acct.address, "pending"]);
      return BigInt(nonceHex);
    },

    /** signAndBroadcast — REQ-004/REQ-005/REQ-009/REQ-018 + PROP-050 (FIND-001 fix). Signs and submits
     * EXACTLY the pre-reserved `nonce`; never fetches or spends a different nonce (see module header).
     * `expectedAmountOutUakt`/`expectedTxsRequired` are OPTIONAL (FIND-004 fix): when the caller (driver.mjs)
     * supplies them, they are the SAME REQ-002-validated quoteSnapshot values driver.mjs already derived
     * from its own earlier Skip route fetch -- this module's own necessary re-fetch below (the frozen
     * interface has no quoteSnapshot param) is reconciled against them and refuses to sign if the two
     * diverge, rather than silently trusting whichever route happened to come back second. */
    async signAndBroadcast({ amount, nonce, sourceAddress, destinationAkashAddress, expectedAmountOutUakt, expectedTxsRequired }) {
      const acct = account();
      if (typeof sourceAddress === "string" && sourceAddress.toLowerCase() !== acct.address.toLowerCase()) {
        throw new Error(`base-signer: sourceAddress ${sourceAddress} does not match this signer's own address ${acct.address} -- refusing to sign (money-safety)`);
      }
      if (destinationAkashAddress !== DESTINATION_AKASH_ADDRESS) {
        throw new Error(`base-signer: destinationAkashAddress ${destinationAkashAddress} does not match the fixed colony destination -- refusing to sign (money-safety)`);
      }

      const route = await fetchSkipRoute(fetchImpl, BigInt(amount));
      // FIND-004 fix: reconcile this module's OWN re-fetched route against the driver's already-validated
      // REQ-002 quote, when supplied. Fail closed (never sign) if Skip's route re-priced/re-topologized
      // between driver.mjs's earlier fetch and this one.
      if (expectedAmountOutUakt !== undefined) {
        const refetchedAmountOut = BigInt(route.amount_out);
        if (refetchedAmountOut !== BigInt(expectedAmountOutUakt)) {
          throw new Error(`base-signer: re-fetched Skip route's amount_out (${refetchedAmountOut}) diverges from the driver's already-validated REQ-002 quote (${expectedAmountOutUakt}) -- refusing to sign against a route that may have re-priced since validation (money-safety, FIND-004)`);
        }
      }
      if (expectedTxsRequired !== undefined && route.txs_required !== expectedTxsRequired) {
        throw new Error(`base-signer: re-fetched Skip route's txs_required (${route.txs_required}) diverges from the driver's already-validated REQ-002 quote (${expectedTxsRequired}) -- refusing to sign against a route whose leg topology changed since validation (money-safety, FIND-004)`);
      }

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

      // PROP-050 / FIND-001 fix (CRITICAL): independently decode+verify the ACTUAL evm_tx contents
      // (destination contract, encoded amount, native value) against the driver-supplied intent BEFORE
      // ever touching a wallet client. See verifyEvmTxAgainstIntent's own doc comment for the full
      // gate rationale. This is the ONLY thing standing between "sign whatever Skip's HTTP response
      // said" and "sign only the exact, capped, intended amount to an allowlisted contract".
      verifyEvmTxAgainstIntent(evmTx, amount);

      // FIND-001 iter2 fix (CRITICAL): query the REAL, CURRENT on-chain allowance for approval.spender --
      // never trust Skip's self-reported required_erc20_approvals[0].amount metadata field alone (gate 3
      // above already checked that field, but a fully-malicious/compromised Skip response could report an
      // honest-looking metadata amount while a STANDING, HIGHER allowance from a prior swap or a
      // compromised probe is what's actually granted on-chain -- exactly the iter2 CRITICAL finding).
      // The invariant enforced here: the on-chain allowance available to evm_tx.to is EXACTLY `amount`,
      // never less (the swap would revert) and never more (a standing excess is itself the attack surface
      // -- worst-case loss under a fully-malicious route is therefore bounded to `amount`, not to
      // whatever a stale/standing allowance happens to be).
      const intendedAmount = BigInt(amount);
      for (const approval of evmTx.required_erc20_approvals || []) {
        const have = await currentAllowance(acct.address, approval.spender);
        if (have < intendedAmount) {
          throw new Error(`base-signer: insufficient USDC allowance for spender ${approval.spender} at sign time (on-chain allowance ${have} < intended amount ${intendedAmount}; getNextNonce() should have already settled this) -- refusing to sign without a verified allowance (money-safety)`);
        }
        if (have > intendedAmount) {
          throw new Error(`base-signer: on-chain USDC allowance for spender ${approval.spender} (${have}) EXCEEDS the intended swap amount (${intendedAmount}) -- a standing/excess allowance is never trusted even if Skip's reported metadata amount matches intent exactly; refusing to sign until the allowance is reset to exactly \`amount\` (money-safety, PROP-050/FIND-001 iter2 CRITICAL fix -- this is precisely the attack a standing higher allowance enables)`);
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
