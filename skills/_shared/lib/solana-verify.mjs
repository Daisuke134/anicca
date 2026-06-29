// solana-verify — confirm a Solana signature + compute the inbound SPL-USDC delta to OUR ATA.
// The Solana sibling of verify-tx.mjs / usdc.mjs (which are EVM/Base only). Promote.fun pays USDC
// on Solana, so the earn gate needs a Solana-native proof: a confirmed signature + a positive
// USDC delta credited to our wallet. Pure transport — `fetchImpl` is injectable so tests never
// touch the network. RPC = SOLANA_RPC_URL (default public mainnet).
//
// Verified against real mainnet RPC shapes 2026-06-29:
//   getSignatureStatuses → result.value[0] = {confirmationStatus, err, ...} | null
//   getTransaction(jsonParsed) → result.meta.{pre,post}TokenBalances[] =
//     {accountIndex, mint, owner, uiTokenAmount:{amount, decimals, uiAmount, uiAmountString}}
//   getTokenAccountsByOwner(jsonParsed) → result.value[].account.data.parsed.info.tokenAmount
const SOL_RPC = process.env.SOLANA_RPC_URL || "https://api.mainnet-beta.solana.com";
// Native USDC SPL mint on Solana mainnet (verified accepted by getTokenAccountsByOwner 2026-06-29).
const USDC_MINT = process.env.USDC_MINT || "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
// base58 alphabet (no 0 O I l); Solana signatures are ~87-88 chars, addresses 32-44.
const B58_RE = /^[1-9A-HJ-NP-Za-km-z]{32,90}$/;
const round = (n) => Math.round(Number(n) * 1e6) / 1e6;

async function rpc(method, params, opts = {}) {
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  const url = opts.rpc || SOL_RPC;
  const res = await fetchImpl(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  });
  if (!res.ok) throw new Error(`solana-verify: rpc ${res.status}`);
  const j = await res.json();
  if (j && j.error) throw new Error(`solana-verify: rpc error ${j.error.message || JSON.stringify(j.error)}`);
  return j && j.result;
}

// uiTokenAmount → a JS number. Prefer uiAmount; fall back to amount/10**decimals when null.
function amountOf(uiTokenAmount) {
  if (!uiTokenAmount) return 0;
  if (uiTokenAmount.uiAmount !== null && uiTokenAmount.uiAmount !== undefined) {
    return Number(uiTokenAmount.uiAmount);
  }
  return Number(uiTokenAmount.amount) / 10 ** Number(uiTokenAmount.decimals);
}

function assertSig(signature) {
  if (typeof signature !== "string" || !B58_RE.test(signature)) {
    throw new Error(`solana-verify: not a base58 signature: ${signature}`);
  }
}

// Confirm a signature: {confirmed, err}. confirmed iff status ∈ {confirmed,finalized} AND err === null.
export async function sigStatus(signature, opts = {}) {
  assertSig(signature);
  const result = await rpc("getSignatureStatuses", [[signature], { searchTransactionHistory: true }], opts);
  const v = result && result.value ? result.value[0] : null;
  if (!v) return { confirmed: false, err: null };
  const ok = (v.confirmationStatus === "confirmed" || v.confirmationStatus === "finalized") && v.err == null;
  return { confirmed: Boolean(ok), err: v.err ?? null };
}

// Net inbound USDC to OUR ATA in this signature. Sums (post-pre) ONLY over token-balance entries whose
// owner === wallet AND mint === USDC, matching pre↔post by accountIndex (absent pre ⇒ 0, the
// first-inbound/ATA-creation case). Ignores every other transfer in a batch tx.
export async function usdcDeltaForSig(signature, wallet, opts = {}) {
  assertSig(signature);
  const mint = opts.mint || USDC_MINT;
  const result = await rpc(
    "getTransaction",
    [signature, { encoding: "jsonParsed", maxSupportedTransactionVersion: 0 }],
    opts,
  );
  const meta = result && result.meta;
  if (!meta) return 0;
  const pre = meta.preTokenBalances || [];
  const post = meta.postTokenBalances || [];
  const preByIdx = new Map(pre.map((p) => [p.accountIndex, p]));
  let delta = 0;
  for (const p of post) {
    if (p.owner !== wallet || p.mint !== mint) continue;
    const before = preByIdx.has(p.accountIndex) ? amountOf(preByIdx.get(p.accountIndex).uiTokenAmount) : 0;
    delta += amountOf(p.uiTokenAmount) - before;
  }
  return round(delta);
}

// Wallet's USDC balance via getTokenAccountsByOwner. Returns 0 (no throw) when the ATA does not exist.
export async function usdcBalance(wallet, opts = {}) {
  if (typeof wallet !== "string" || !B58_RE.test(wallet)) {
    throw new Error(`solana-verify: not a base58 wallet: ${wallet}`);
  }
  const mint = opts.mint || USDC_MINT;
  const result = await rpc(
    "getTokenAccountsByOwner",
    [wallet, { mint }, { encoding: "jsonParsed" }],
    opts,
  );
  const accts = (result && result.value) || [];
  if (accts.length === 0) return 0;
  let total = 0;
  for (const a of accts) {
    const ta = a?.account?.data?.parsed?.info?.tokenAmount;
    total += amountOf(ta);
  }
  return round(total);
}
