// spawn-funding-swap real client — REQ-015 (sprint-2). createRealPriceOracle(): the ONLY production
// implementation of the priceOracle contract (matches createFakePriceOracle: getAktUsdPrice() -> number,
// REQ-011). No copy source exists in this repo for a spot-price feed (documented "honest limitation" in
// skills/self/spawn/lib/spawn-orchestrator.mjs:215-219 -- "no live NOS/AKT spot-price feed ... exists
// anywhere in this codebase yet"); this is the first one, using CoinGecko's free, no-API-key `simple/price`
// endpoint (verified live 2026-07-11: `GET .../simple/price?ids=akash-network&vs_currencies=usd` ->
// `{"akash-network":{"usd":0.606867}}`).
//
// driver.mjs's REQ-011 call site wraps getAktUsdPrice() in try/catch AND separately validates the
// returned value is a finite positive number (`typeof !== "number" || !Number.isFinite || <= 0` ->
// `invalid_price`) -- so this module's contract is: THROW on any transport/parse failure, and only ever
// RESOLVE with a value that already passed that same finite-positive check itself (belt-and-suspenders --
// never hand driver.mjs a value it would have to reject).
const DEFAULT_ENDPOINT = "https://api.coingecko.com/api/v3/simple/price?ids=akash-network&vs_currencies=usd";

/**
 * createRealPriceOracle — REQ-015.
 * @param {{fetchImpl?: typeof fetch, endpoint?: string}} [opts]
 */
export function createRealPriceOracle({ fetchImpl = globalThis.fetch, endpoint = DEFAULT_ENDPOINT } = {}) {
  return {
    async getAktUsdPrice() {
      const res = await fetchImpl(endpoint);
      if (!res.ok) throw new Error(`price-oracle: http ${res.status}`);
      const json = await res.json();
      const price = json && json["akash-network"] ? json["akash-network"].usd : undefined;
      if (typeof price !== "number" || !Number.isFinite(price) || price <= 0) {
        throw new Error(`price-oracle: invalid akash-network.usd in response: ${JSON.stringify(json)}`);
      }
      return price;
    },
  };
}
