// eth-price.mjs — real ETH/USD price, keyless, no signup: CoinGecko's public simple-price
// endpoint, in the same "no key needed for a low-frequency read" spirit as
// ../funding/acquire-nos.mjs's Jupiter /price/v3 usage (Jupiter only prices Solana-ecosystem
// mints, hence a different provider here). fetchImpl is injectable so nothing here hits the
// network in tests. Fails closed (throws) rather than treating a missing/invalid price as free.

export const COINGECKO_SIMPLE_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd";

export async function fetchEthUsdPrice({ fetchImpl = fetch, url = COINGECKO_SIMPLE_PRICE_URL } = {}) {
  const res = await fetchImpl(url);
  if (!res || !res.ok) {
    throw new Error(`fetchEthUsdPrice: HTTP ${res && res.status} fetching ETH/USD price (fail-closed)`);
  }
  const data = await res.json();
  const usd = data && data.ethereum && data.ethereum.usd;
  if (typeof usd !== "number" || !Number.isFinite(usd) || usd <= 0) {
    throw new Error("fetchEthUsdPrice: no valid USD price returned — refusing to treat as free/zero (fail-closed)");
  }
  return usd;
}
