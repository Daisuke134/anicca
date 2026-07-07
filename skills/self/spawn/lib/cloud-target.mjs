// REQ-306: deterministic price/availability-based cloud-target selection — bookkeeping, never a
// model judgment. selectCloudTarget is synchronous, zero I/O, over already-fetched primitives only.
export function selectCloudTarget({ nosanaAvailable = false, nosanaPriceUsd, akashAvailable = false, akashPriceUsd } = {}) {
  if (!nosanaAvailable && !akashAvailable) return "none";
  if (!nosanaAvailable) return "akash";
  if (!akashAvailable) return "nosana";
  // Equal normalized prices -> deterministic tie-breaker, always "nosana", never randomized.
  return nosanaPriceUsd <= akashPriceUsd ? "nosana" : "akash";
}

// Fail-closed spot-price fetch: any thrown error or non-finite parsed value collapses to 0, never
// throws. fetchImpl is injected — real production wiring (which public price endpoint to call) is
// left to the orchestration sprint that wires this module in, never guessed here.
async function fetchSpotPriceUsd({ fetchImpl }) {
  try {
    const response = await fetchImpl();
    const data = await response.json();
    const price = data && data.price;
    return typeof price === "number" && Number.isFinite(price) ? price : 0;
  } catch {
    return 0;
  }
}

export async function fetchAktUsdPrice({ fetchImpl } = {}) {
  return fetchSpotPriceUsd({ fetchImpl });
}

export async function fetchNosUsdPrice({ fetchImpl } = {}) {
  return fetchSpotPriceUsd({ fetchImpl });
}
