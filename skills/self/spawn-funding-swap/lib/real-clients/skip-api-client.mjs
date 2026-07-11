// spawn-funding-swap real client — REQ-016 (sprint-2). createRealSkipApiClient(): the ONLY production
// implementation of the skipApiClient contract (matches createFakeSkipApiClient: getRoute(params) ->
// RouteResponse, REQ-002). No copy source exists in this repo (first Skip API integration); the exact
// request/response shape below was VERIFIED LIVE this session (not assumed from training data):
//   POST https://api.skip.build/v2/fungible/route
//   body: {amount_in, source_asset_denom, source_asset_chain_id, dest_asset_denom, dest_asset_chain_id,
//          allow_unsafe: true, allow_multi_tx: true}
//   (curl 2026-07-11: amount_in="15000000" USDC-on-Base -> amount_out="24513647" uakt, txs_required=2,
//   dest_asset_denom="uakt", dest_asset_chain_id="akashnet-2" -- EXACTLY the fields
//   lib/pure/route-validation.mjs's validateRoute already requires, so this client passes the parsed
//   response body through untouched rather than re-mapping field names.)
//
// chain_id fields MUST be JSON strings, never JSON numbers (verified live: a numeric `8453` literal is
// rejected with `invalid value for string field sourceAssetChainId: 8453`) -- driver.mjs's own
// BASE_CHAIN_ID constant is a JS number (8453) for arithmetic/comparison convenience elsewhere in this
// feature, so String(...) coercion happens HERE, at the one HTTP-boundary choke point, never upstream.
//
// allow_multi_tx:true is REQUIRED for this specific pair (verified live: without it, Skip returns
// code=5 "no single-tx routes found, to enable multi-tx routes set allow_multi_tx to true" -- this
// route's live-confirmed shape genuinely needs multiple chain hops, matching driver.mjs's own
// documented Base -> noble-1 -> osmosis-1 -> akashnet-2 shape).
const DEFAULT_ROUTE_ENDPOINT = "https://api.skip.build/v2/fungible/route";

/**
 * createRealSkipApiClient — REQ-016.
 * @param {{fetchImpl?: typeof fetch, routeEndpoint?: string}} [opts]
 */
export function createRealSkipApiClient({ fetchImpl = globalThis.fetch, routeEndpoint = DEFAULT_ROUTE_ENDPOINT } = {}) {
  return {
    /**
     * getRoute — REQ-002. `params.amount_in` is the exact bigint base-unit amount computed by driver.mjs's
     * REQ-012 choke point; `params.source_asset_chain_id`/`dest_asset_chain_id` may arrive as either a
     * number or a string (driver.mjs passes its own BASE_CHAIN_ID number literal) -- always coerced to a
     * string before it reaches the wire. Throws (never returns a partial/malformed body) on any transport
     * or non-2xx failure; lib/driver.mjs's REQ-002 call site already wraps this in try/catch
     * (`route_request_failed`).
     */
    async getRoute(params) {
      const body = {
        amount_in: String(params.amount_in),
        source_asset_denom: params.source_asset_denom,
        source_asset_chain_id: String(params.source_asset_chain_id),
        dest_asset_denom: params.dest_asset_denom,
        dest_asset_chain_id: String(params.dest_asset_chain_id),
        allow_unsafe: true,
        allow_multi_tx: true,
      };
      const res = await fetchImpl(routeEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const json = await res.json().catch(() => null);
      if (!res.ok || !json || json.code !== undefined) {
        throw new Error(`skip-api-client: route request failed (http ${res.status}): ${JSON.stringify(json)}`);
      }
      // Pass the parsed body through as-is -- its field names already match validateRoute's exact
      // contract (dest_asset_denom/dest_asset_chain_id/amount_out/txs_required); no re-mapping needed,
      // and extra Skip-specific fields (operations, estimated_fees, ...) are harmless surplus that
      // validateRoute simply never reads.
      return json;
    },
  };
}
