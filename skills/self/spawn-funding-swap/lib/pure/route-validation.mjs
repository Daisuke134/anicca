// spawn-funding-swap pure core — REQ-002. validateRoute: the pure predicate gating every signing code
// path. Pure, deterministic, no I/O (PROP-017's structural import-boundary guard).

/**
 * validateRoute — REQ-002: rejects a Skip API route response unless it is the live-confirmed shape
 * (Base USDC -> AKT via akashnet-2), with a positive integer amount_out and a positive integer
 * txs_required. Surfaces amountOutUakt (bigint) and txsRequired (number) for downstream consumers
 * (planNextLeg, verifySettlement) on success.
 * @param {unknown} routeResponse
 * @returns {{ok: boolean, amountOutUakt?: bigint, txsRequired?: number}}
 */
export function validateRoute(routeResponse) {
  if (!routeResponse || typeof routeResponse !== "object") return { ok: false };
  const { dest_asset_denom, dest_asset_chain_id, amount_out, txs_required } = routeResponse;

  if (dest_asset_denom !== "uakt") return { ok: false };
  if (dest_asset_chain_id !== "akashnet-2") return { ok: false };
  if (!Number.isInteger(txs_required) || txs_required <= 0) return { ok: false };
  if (typeof amount_out !== "string" || !/^[0-9]+$/.test(amount_out)) return { ok: false };

  const amountOutUakt = BigInt(amount_out);
  if (amountOutUakt <= 0n) return { ok: false };

  return { ok: true, amountOutUakt, txsRequired: txs_required };
}
