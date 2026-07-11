// spawn-funding-swap effectful shell — the driver orchestrator. runSwap(deps) wires the pure core
// (lib/pure/**) to the injected effectful clients (chainReader, priceOracle, skipApiClient, baseSigner,
// relayPoller, ledgerStore) per behavioral-spec.md's REQ-001..REQ-012. THE SOLE dollar->base-unit choke
// point is `toBaseUnits(capUsd(usdEquivalentOf(need, aktUsdPrice)), USDC_DECIMALS_BASE)` (REQ-012); its
// exact bigint output — never a re-derived value, never the pre-conversion float — is what reaches BOTH
// the Skip route request's `amount_in` and BaseSigner.signAndBroadcast()'s tx amount. SWAP_MAX_USD,
// MIN_GAS_WEI, and TOLERANCE_BPS are fixed literals applied AFTER any need/price derivation (REQ-006,
// REQ-003, REQ-007) — never read from process.env/CLI/genome/config.
import {
  computeSwapNeed as defaultComputeSwapNeed,
  usdEquivalentOf as defaultUsdEquivalentOf,
  capUsd as defaultCapUsd,
} from "./pure/swap-need.mjs";
import { toBaseUnits as defaultToBaseUnits, fromBaseUnits as defaultFromBaseUnits } from "./pure/base-units.mjs";
import { validateRoute as defaultValidateRoute } from "./pure/route-validation.mjs";
import { checkSourceFunded as defaultCheckSourceFunded } from "./pure/funding-check.mjs";
import { verifySettlement as defaultVerifySettlement } from "./pure/settlement.mjs";
import { planNextLeg as defaultPlanNextLeg, reconcileLedgerOnResume as defaultReconcileLedgerOnResume } from "./pure/ledger-plan.mjs";
import {
  USDC_DECIMALS_BASE,
  AKT_DECIMALS,
  MIN_GAS_WEI,
  TOLERANCE_BPS,
  BASE_CHAIN_ID,
  BASE_USDC_DENOM,
  AKASH_CHAIN_ID,
  AKASH_UAKT_DENOM,
} from "./pure/constants.mjs";

// Skip API route parameters confirmed live this session (behavioral-spec.md) — the ONLY currently-
// viable source chain/asset for this pair; the route response itself (validateRoute) remains the source
// of truth every invocation, never assumed (REQ-002). FIND-005 fix (impl review iter1): these four are
// now imported from pure/constants.mjs (single choke point), never re-literal'd here.
const REQUIRED_AKASH_KEY_NAME = "anicca-akash";

function defaultPureFns() {
  return {
    computeSwapNeed: defaultComputeSwapNeed,
    usdEquivalentOf: defaultUsdEquivalentOf,
    capUsd: defaultCapUsd,
    toBaseUnits: defaultToBaseUnits,
    fromBaseUnits: defaultFromBaseUnits,
    validateRoute: defaultValidateRoute,
    checkSourceFunded: defaultCheckSourceFunded,
    verifySettlement: defaultVerifySettlement,
    planNextLeg: defaultPlanNextLeg,
    reconcileLedgerOnResume: defaultReconcileLedgerOnResume,
  };
}

function findLeg(ledgerState, legIndex) {
  return (ledgerState.legs || []).find((l) => l.legIndex === legIndex);
}

function upsertLeg(ledgerState, legEntry) {
  const legs = (ledgerState.legs || []).filter((l) => l.legIndex !== legEntry.legIndex);
  legs.push(legEntry);
  legs.sort((a, b) => a.legIndex - b.legIndex);
  return { ...ledgerState, legs };
}

function withQuoteSnapshot(ledgerState, quoteSnapshot) {
  return { ...ledgerState, quoteSnapshot };
}

/**
 * ensureLeg0Submitted — REQ-004/REQ-005/REQ-005-PROP-020: submits (or resumes) the single Base-chain
 * signed leg (leg index 0). A leg found `submitting` from a prior attempt is NEVER blind-resubmitted —
 * the driver first re-derives its deterministic on-chain query key (source address + nonce) and queries
 * chain state before deciding. The pre-broadcast `submitting` record is written SYNCHRONOUSLY and BEFORE
 * the broadcast RPC call (PROP-020's call-order requirement).
 */
async function ensureLeg0Submitted(ctx, ledgerState, requiredBaseUnits, quoteSnapshot) {
  const existing = findLeg(ledgerState, 0);
  if (existing && existing.status === "confirmed") {
    return { ledgerState, timedOut: false };
  }

  let nonce = existing && existing.status === "submitting" ? existing.nonce : undefined;
  if (existing && existing.status === "submitting") {
    const onChainStatus = await ctx.chainReader.getBaseTxStatusByNonce(ctx.sourceBaseAddress, nonce);
    if (onChainStatus === "confirmed") {
      const confirmedState = withQuoteSnapshot(upsertLeg(ledgerState, { legIndex: 0, status: "confirmed", nonce, txHash: existing.txHash ?? null }), quoteSnapshot);
      await ctx.ledgerStore.writeState(ctx.destinationAkashAddress, confirmedState);
      return { ledgerState: confirmedState, timedOut: false };
    }
    // "not-found" -- the earlier broadcast RPC call never actually landed on chain; fall through and
    // (re)submit using this SAME re-derived nonce, never a blindly-fresh one.
  } else {
    nonce = await ctx.baseSigner.getNextNonce();
  }

  // Pre-broadcast durable write -- SYNCHRONOUS and BEFORE the broadcast RPC call (REQ-005/PROP-020).
  const submittingState = withQuoteSnapshot(upsertLeg(ledgerState, { legIndex: 0, status: "submitting", nonce }), quoteSnapshot);
  await ctx.ledgerStore.writeState(ctx.destinationAkashAddress, submittingState);

  // FIND-004 fix (impl review iter1): pass the driver's ALREADY-VALIDATED REQ-002 quote through, so
  // base-signer's own necessary re-fetch (its frozen interface has no quoteSnapshot param, only
  // {amount, nonce, sourceAddress, destinationAkashAddress}) can be reconciled against it rather than
  // silently drifting if Skip's route re-priced/re-topologized between the two fetches.
  const { txHash } = await ctx.baseSigner.signAndBroadcast({
    amount: requiredBaseUnits,
    nonce,
    sourceAddress: ctx.sourceBaseAddress,
    destinationAkashAddress: ctx.destinationAkashAddress,
    expectedAmountOutUakt: quoteSnapshot.amountOutUakt,
    expectedTxsRequired: quoteSnapshot.txsRequired,
  });

  const relayStatus = await ctx.relayPoller.waitForConfirmation(BASE_CHAIN_ID, txHash, ctx.legTimeoutMs);
  if (relayStatus !== "confirmed") {
    const pendingState = withQuoteSnapshot(upsertLeg(submittingState, { legIndex: 0, status: "pending", nonce, txHash }), quoteSnapshot);
    await ctx.ledgerStore.writeState(ctx.destinationAkashAddress, pendingState);
    return { ledgerState: pendingState, timedOut: true };
  }

  const confirmedState = withQuoteSnapshot(upsertLeg(submittingState, { legIndex: 0, status: "confirmed", nonce, txHash }), quoteSnapshot);
  await ctx.ledgerStore.writeState(ctx.destinationAkashAddress, confirmedState);
  return { ledgerState: confirmedState, timedOut: false };
}

/**
 * ensureRelayOnlyLegSubmitted — REQ-004: a non-zero leg index is a pure cross-chain relay-wait (no new
 * signed transaction) — this route's live-confirmed shape (Base -> noble-1 -> osmosis-1 -> akashnet-2)
 * has exactly one signed Base-chain leg (index 0); every subsequent leg index is the relay landing at
 * the destination chain. Never re-submitted once `confirmed`; a stall records `pending`, never
 * `failed`/absent (REQ-004 edge case).
 */
async function ensureRelayOnlyLegSubmitted(ctx, ledgerState, legIndex, quoteSnapshot) {
  const existing = findLeg(ledgerState, legIndex);
  if (existing && existing.status === "confirmed") {
    return { ledgerState, timedOut: false };
  }

  const relayStatus = await ctx.relayPoller.waitForConfirmation(AKASH_CHAIN_ID, existing?.txHash ?? null, ctx.legTimeoutMs);
  if (relayStatus !== "confirmed") {
    const pendingState = withQuoteSnapshot(upsertLeg(ledgerState, { legIndex, status: "pending" }), quoteSnapshot);
    await ctx.ledgerStore.writeState(ctx.destinationAkashAddress, pendingState);
    return { ledgerState: pendingState, timedOut: true };
  }

  const confirmedState = withQuoteSnapshot(upsertLeg(ledgerState, { legIndex, status: "confirmed" }), quoteSnapshot);
  await ctx.ledgerStore.writeState(ctx.destinationAkashAddress, confirmedState);
  return { ledgerState: confirmedState, timedOut: false };
}

/**
 * runInsideLock — everything REQ-010 requires to happen AFTER the canonical lock is held: REQ-011's
 * price lookup, the REQ-006/REQ-011/REQ-012 cap+conversion choke point, REQ-003's funding precondition,
 * REQ-002's route request/validation, REQ-004/REQ-005's leg-execution loop, and REQ-007's settlement
 * verification.
 */
async function runInsideLock(ctx, pureFns, need, preBalanceUakt) {
  const rawLedger = await ctx.ledgerStore.readState(ctx.destinationAkashAddress);
  const reconciled = pureFns.reconcileLedgerOnResume(rawLedger);
  if (reconciled === "CORRUPT") {
    return { ok: false, status: "ledger_corrupt" };
  }
  let ledgerState = reconciled;

  // REQ-011: price lookup -- fail closed on rejection or an invalid (<=0/NaN/Infinity) price, BEFORE any
  // Skip request or signing.
  let aktUsdPrice;
  try {
    aktUsdPrice = await ctx.priceOracle.getAktUsdPrice();
  } catch {
    return { ok: false, status: "price_lookup_failed" };
  }
  if (typeof aktUsdPrice !== "number" || !Number.isFinite(aktUsdPrice) || aktUsdPrice <= 0) {
    return { ok: false, status: "invalid_price" };
  }

  // REQ-006/REQ-011/REQ-012 choke point: the ONLY dollar->base-unit conversion for this run's amount.
  const cappedUsd = pureFns.capUsd(pureFns.usdEquivalentOf(need, aktUsdPrice));
  const requiredBaseUnits = pureFns.toBaseUnits(cappedUsd, USDC_DECIMALS_BASE);

  // REQ-003: source-funding precondition -- exact bigint comparisons, MIN_GAS_WEI always the literal.
  const [baseUsdcBalance, baseGasBalance] = await Promise.all([ctx.chainReader.getBaseUsdc(ctx.sourceBaseAddress), ctx.chainReader.getBaseGas(ctx.sourceBaseAddress)]);
  const funded = pureFns.checkSourceFunded(baseUsdcBalance, baseGasBalance, requiredBaseUnits, MIN_GAS_WEI);
  if (!funded) {
    return { ok: false, status: "insufficient_funded_source", have: { baseUsdcBalance, baseGasBalance }, need: { requiredBaseUnits, minGasWei: MIN_GAS_WEI } };
  }

  // REQ-002: route request in amount_in mode, using the exact requiredBaseUnits integer.
  let routeResponse;
  try {
    routeResponse = await ctx.skipApiClient.getRoute({
      amount_in: requiredBaseUnits,
      source_asset_chain_id: BASE_CHAIN_ID,
      source_asset_denom: BASE_USDC_DENOM,
      dest_asset_chain_id: AKASH_CHAIN_ID,
      dest_asset_denom: AKASH_UAKT_DENOM,
    });
  } catch {
    return { ok: false, status: "route_request_failed" };
  }
  const validated = pureFns.validateRoute(routeResponse);
  if (!validated.ok) {
    return { ok: false, status: "no_valid_route" };
  }
  const quoteSnapshot = { txsRequired: validated.txsRequired, amountOutUakt: validated.amountOutUakt };

  // REQ-004/REQ-005: execute (or resume) each leg in order, never re-submitting a confirmed leg.
  for (;;) {
    const action = pureFns.planNextLeg({ txsRequired: quoteSnapshot.txsRequired }, ledgerState);
    if (action.action === "ALREADY_COMPLETE") {
      return { ok: true, status: "already_complete" };
    }
    if (action.action === "DONE") break;

    const legResult =
      action.legIndex === 0
        ? await ensureLeg0Submitted(ctx, ledgerState, requiredBaseUnits, quoteSnapshot)
        : await ensureRelayOnlyLegSubmitted(ctx, ledgerState, action.legIndex, quoteSnapshot);
    ledgerState = legResult.ledgerState;
    if (legResult.timedOut) {
      return { ok: false, status: "leg_pending_timeout" };
    }
  }

  // REQ-007: final on-chain settlement verification -- a fresh, genuine re-query, NEVER inferred from
  // legs' own zero-exit-code status or from the route's quoted amount_out alone (that would make
  // REQ-007 vacuous -- exactly the "false success" failure mode this REQ exists to prevent, per
  // behavioral-spec.md: "THE SYSTEM SHALL NOT declare success merely because all leg transactions
  // returned a zero exit code"). `createFakeChainReader.getAkashBalance` (fake-clients.mjs) is stateful
  // and opt-in (`akashBalanceCreditUakt`): fixtures that intend a genuine ok:true success pass the
  // route's quoted amount_out as the post-swap credit so this re-query observes a real delta; fixtures
  // that intend the "legs confirmed but AKT not observed at destination" fail-closed path (PROP-013,
  // PROP-008) leave the credit at its 0n default so the balance stays unchanged. Either way this check
  // performs a real re-query against whatever the injected chainReader reports -- never trusting the
  // quote/relay confirmation alone -- which is what makes both outcomes correctly observable.
  const postBalanceUakt = await ctx.chainReader.getAkashBalance(ctx.destinationAkashAddress);
  const settled = pureFns.verifySettlement(preBalanceUakt, postBalanceUakt, quoteSnapshot.amountOutUakt, TOLERANCE_BPS);
  if (!settled) {
    return { ok: false, status: "settlement_unverified" };
  }

  const finalState = withQuoteSnapshot({ ...ledgerState, completedAtMs: (ctx.now || Date.now)() }, quoteSnapshot);
  await ctx.ledgerStore.writeState(ctx.destinationAkashAddress, finalState);
  return { ok: true, status: "settled" };
}

/**
 * runSwap — the driver's public entrypoint. See lib/__tests__/driver-preconditions.test.mjs for the
 * full `deps` contract (Phase 2a-defined, binding). Returns `{ok, status, ...detail}`.
 */
export async function runSwap(deps) {
  const pureFns = { ...defaultPureFns(), ...(deps.pure || {}) };

  // REQ-009: identity/key safety -- fail closed before any lock/price/route/sign activity.
  if (deps.akashKeyName !== REQUIRED_AKASH_KEY_NAME) {
    return { ok: false, status: "invalid_akash_key_name" };
  }
  const actualBaseSignerAddress = await deps.baseSigner.getAddress();
  if (actualBaseSignerAddress !== deps.expectedBaseSignerAddress) {
    return { ok: false, status: "unexpected_base_signer_address" };
  }

  // REQ-001 edge case: an unset/non-numeric threshold fails closed rather than defaulting to a swap.
  if (typeof deps.thresholdAkt !== "number" || !Number.isFinite(deps.thresholdAkt)) {
    return { ok: false, status: "invalid_threshold" };
  }

  // REQ-001: balance-gated idempotent trigger. current MUST be fromBaseUnits(balanceUakt, AKT_DECIMALS)
  // -- never the raw bigint, never an un-scaled Number() cast (PROP-023).
  let balanceUakt;
  try {
    balanceUakt = await deps.chainReader.getAkashBalance(deps.destinationAkashAddress);
  } catch {
    return { ok: false, status: "balance_query_failed" };
  }
  const current = pureFns.fromBaseUnits(balanceUakt, AKT_DECIMALS);
  const need = pureFns.computeSwapNeed(current, deps.thresholdAkt);
  if (need === 0) {
    return { ok: true, status: "no_swap_needed" };
  }

  // REQ-010: canonical destination-address-keyed lock, acquired BEFORE any price lookup or route
  // request. A caller that observes the lock already held resumes/no-ops -- never a second lock, never
  // a price/route call.
  const ctx = {
    chainReader: deps.chainReader,
    priceOracle: deps.priceOracle,
    skipApiClient: deps.skipApiClient,
    baseSigner: deps.baseSigner,
    relayPoller: deps.relayPoller,
    ledgerStore: deps.ledgerStore,
    sourceBaseAddress: deps.sourceBaseAddress,
    destinationAkashAddress: deps.destinationAkashAddress,
    legTimeoutMs: deps.legTimeoutMs,
    now: deps.now,
  };
  const lockResult = await deps.ledgerStore.withLock(deps.destinationAkashAddress, () => runInsideLock(ctx, pureFns, need, balanceUakt));
  if (!lockResult.ok) {
    return { ok: false, status: "lock_held", reason: lockResult.reason };
  }
  return lockResult.result;
}
