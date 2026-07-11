// spawn-funding-swap real client — REQ-014 (sprint-2). createRealChainReader(): the ONLY production
// implementation of the chainReader contract (lib/driver.mjs's ctx.chainReader / deps.chainReader),
// matching lib/__tests__/fakes/fake-clients.mjs's createFakeChainReader shape exactly:
//   getAkashBalance(address) -> Promise<bigint>            (uakt, REQ-001/REQ-007)
//   getBaseUsdc(address) -> Promise<bigint>                 (raw 6-decimal base units, REQ-003)
//   getBaseGas(address) -> Promise<bigint>                  (wei, REQ-003)
//   getBaseTxStatusByNonce(address, nonce) -> Promise<"confirmed"|"not-found">  (REQ-004/REQ-005 resume)
//
// Akash read — copies skills/self/spawn/lib/spawn-orchestrator.mjs:228-241's own `akash query bank
// balances <addr> -o json` shape verbatim (execFileSync, NOT cosmjs -- this feature never needed a
// signing SDK for a READ-only query, matching that file's own precedent). Unlike that copy source (which
// first resolves a key NAME to an address via `keys show`), this feature's callers always pass an
// ADDRESS directly (deps.destinationAkashAddress), so the `keys show` hop is skipped entirely.
//
// Base reads — copies skills/_shared/lib/usdc.mjs's `eth_call balanceOf(address)` JSON-RPC POST shape
// (fetchImpl-injectable, same BASE_RPC_URL/USDC_ADDRESS env convention), but returns the RAW on-chain
// bigint (never usdc.mjs's own `/1e6` Number-scaled form -- this feature's driver.mjs choke point
// (base-units.mjs) requires the exact base-unit integer, never a float re-derivation).
//
// getBaseTxStatusByNonce — no existing copy source in this repo (new, sprint-2). Uses the standard
// nonce-based confirmation technique: `eth_getTransactionCount(address, "latest")` returns the COUNT of
// mined transactions from `address` (== the next nonce a NEW tx would need); a `nonce` strictly less
// than that count has therefore already landed on-chain ("confirmed"). This needs no tx-hash lookup/
// receipt polling and works even across a process crash that lost the original broadcast's txHash
// (REQ-005's crash-recovery premise -- driver.mjs's ensureLeg0Submitted calls this exactly when resuming
// a `submitting`-status leg that may or may not have actually landed).
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

const DEFAULT_BASE_RPC_URL = "https://mainnet.base.org";
// Native (Circle-issued) USDC on Base mainnet -- the SAME literal as skills/_shared/lib/usdc.mjs and
// skills/economy/gig/lib/escrow.mjs's USDC_BASE_MAINNET, never re-derived.
const DEFAULT_USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const BALANCE_OF_SELECTOR = "0x70a08231"; // balanceOf(address)
const ADDR_RE = /^0x[0-9a-fA-F]{40}$/;

function padAddressForCalldata(address) {
  return address.toLowerCase().replace(/^0x/, "").padStart(64, "0");
}

async function rpcCall(fetchImpl, rpcUrl, method, params) {
  const res = await fetchImpl(rpcUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  });
  if (!res.ok) throw new Error(`chain-reader: RPC http ${res.status} for ${method}`);
  const json = await res.json();
  if (json.error) throw new Error(`chain-reader: RPC error for ${method}: ${JSON.stringify(json.error)}`);
  if (typeof json.result !== "string") throw new Error(`chain-reader: RPC ${method} returned no result`);
  return json.result;
}

function hexToBigInt(hex) {
  return BigInt(hex === "0x" || hex === undefined || hex === null ? "0x0" : hex);
}

/**
 * createRealChainReader — REQ-014. All options are test/production wiring seams; omitting any wires the
 * real transport (fetch for Base JSON-RPC, execFile for the `akash` CLI).
 * @param {{
 *   fetchImpl?: typeof fetch,
 *   execFileImpl?: (cmd: string, args: string[]) => Promise<{stdout: string}>,
 *   baseRpcUrl?: string,
 *   usdcAddress?: string,
 *   env?: Record<string,string>,
 * }} [opts]
 */
export function createRealChainReader({ fetchImpl = globalThis.fetch, execFileImpl, baseRpcUrl, usdcAddress, env = process.env } = {}) {
  const rpcUrl = baseRpcUrl || env.BASE_RPC_URL || DEFAULT_BASE_RPC_URL;
  const usdc = (usdcAddress || env.USDC_ADDRESS || DEFAULT_USDC_ADDRESS).toLowerCase();
  const runAkashCli = execFileImpl || (async (cmd, args) => execFileAsync(cmd, args, { encoding: "utf8" }));

  return {
    /** getAkashBalance — REQ-001/REQ-007. Fails closed by THROWING (driver.mjs wraps every call site of
     * this specific method in try/catch -- REQ-001's `balance_query_failed` / never a silently-wrong 0n). */
    async getAkashBalance(address) {
      const akashCli = env.AKASH_CLI || "akash";
      // REQ-014 edge case: AKASH_NODE/AKASH_CHAIN_ID are akt-treasury.sh's own exported vars (this
      // command's documented sole environment dependency, see bin/spawn-funding-swap.mjs's header
      // comment) -- an unset value fails closed rather than silently querying the CLI's own default
      // node (which could be a DIFFERENT, wrong network).
      const node = env.AKASH_NODE;
      const chainId = env.AKASH_CHAIN_ID;
      if (!node || !chainId) {
        throw new Error("chain-reader: AKASH_NODE/AKASH_CHAIN_ID must be set (akt-treasury.sh's own exported vars) -- refusing to query a default/ambient node");
      }
      const { stdout } = await runAkashCli(akashCli, ["query", "bank", "balances", address, "--node", node, "--chain-id", chainId, "-o", "json"]);
      const parsed = JSON.parse(stdout);
      const balances = Array.isArray(parsed.balances) ? parsed.balances : [];
      const uakt = balances.find((b) => b && b.denom === "uakt");
      if (!uakt || typeof uakt.amount !== "string" || !/^[0-9]+$/.test(uakt.amount)) return 0n;
      return BigInt(uakt.amount);
    },

    /** getBaseUsdc — REQ-003. Raw 6-decimal base units (never Number-scaled). Throws on any transport/
     * parse failure (REQ-003's call site is unwrapped -- a throw here fails the whole invocation closed,
     * consistent with this feature's "never sign on an unverifiable balance" discipline). */
    async getBaseUsdc(address) {
      if (!ADDR_RE.test(address)) throw new Error(`chain-reader: not a Base address: ${address}`);
      const data = BALANCE_OF_SELECTOR + padAddressForCalldata(address);
      const result = await rpcCall(fetchImpl, rpcUrl, "eth_call", [{ to: usdc, data }, "latest"]);
      return hexToBigInt(result);
    },

    /** getBaseGas — REQ-003. Native ETH wei balance via eth_getBalance. */
    async getBaseGas(address) {
      if (!ADDR_RE.test(address)) throw new Error(`chain-reader: not a Base address: ${address}`);
      const result = await rpcCall(fetchImpl, rpcUrl, "eth_getBalance", [address, "latest"]);
      return hexToBigInt(result);
    },

    /** getBaseTxStatusByNonce — REQ-004/REQ-005. Nonce-based confirmation check (see module header). */
    async getBaseTxStatusByNonce(address, nonce) {
      if (!ADDR_RE.test(address)) throw new Error(`chain-reader: not a Base address: ${address}`);
      const result = await rpcCall(fetchImpl, rpcUrl, "eth_getTransactionCount", [address, "latest"]);
      const minedCount = hexToBigInt(result);
      return minedCount > BigInt(nonce) ? "confirmed" : "not-found";
    },
  };
}
