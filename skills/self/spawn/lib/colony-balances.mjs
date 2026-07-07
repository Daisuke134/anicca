// REQ-101: registry-driven balance read — queries EACH citizen's balance directly from public
// chain RPC, keyed on that citizen's own walletAddress (never a coordinator-local file read, so a
// REQ-301-mandated cloud-hosted child's balance is reached exactly as readily as a co-located
// citizen's). fetchEvmBalanceUsd/fetchSolanaBalanceUsd are injected (the real production callers wire
// these to the base-rpc.publicnode.com/api.mainnet-beta.solana.com + spot-price mechanism
// telemetry-collect.sh already proves out — left to the orchestration sprint that wires this module in,
// never guessed here). Each populated chain fails closed INDEPENDENTLY of the other (resolves FIND-503):
// a citizen's total is always 0-or-more, the sum of whichever chains resolved cleanly.
async function safeChainBalance(fetchFn, address) {
  try {
    const value = await fetchFn(address);
    return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : 0;
  } catch {
    return 0;
  }
}

export async function readCitizenBalances({ citizens = [], fetchEvmBalanceUsd, fetchSolanaBalanceUsd } = {}) {
  const results = [];
  for (const citizen of citizens) {
    const walletAddress = (citizen && citizen.walletAddress) || {};
    let balanceUsd = 0;
    if (walletAddress.evm) {
      balanceUsd += await safeChainBalance(fetchEvmBalanceUsd, walletAddress.evm);
    }
    if (walletAddress.solana) {
      balanceUsd += await safeChainBalance(fetchSolanaBalanceUsd, walletAddress.solana);
    }
    results.push({ citizenId: citizen.id, balanceUsd });
  }
  return results;
}
