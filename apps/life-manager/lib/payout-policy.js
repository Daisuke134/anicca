"use strict";

const { normaliseEntry } = require("./earnings-ledger.js");
const { toChecksumAddress } = require("./agent-wallet.js");

const DEFAULT_RESERVE_ATOMIC = 35_000_000n;
const ATOMIC_PER_USD_MINOR = 10_000n;

function integerAtomic(value, label) {
  const raw = typeof value === "bigint"
    ? value.toString()
    : String(value == null ? "" : value).trim();
  if (!/^\d+$/.test(raw)) throw new Error(`${label} must be an exact non-negative integer`);
  return BigInt(raw);
}

function checksummedAddress(value) {
  const raw = String(value == null ? "" : value).trim();
  if (!/^0x[0-9a-fA-F]{40}$/.test(raw)) throw new Error("walletAddress must be an Ethereum address");
  const checksummed = toChecksumAddress(raw.slice(2).toLowerCase());
  if (raw !== checksummed) throw new Error("walletAddress fails its EIP-55 checksum");
  return checksummed;
}

function computePayout(input = {}) {
  const walletAddress = checksummedAddress(input.walletAddress);
  const rows = Array.isArray(input.rows) ? input.rows : [];
  const onchain = integerAtomic(input.onchainUsdcAtomic, "onchainUsdcAtomic");
  const reserve = input.reserveAtomic == null
    ? DEFAULT_RESERVE_ATOMIC
    : integerAtomic(input.reserveAtomic, "reserveAtomic");
  if (reserve < DEFAULT_RESERVE_ATOMIC) {
    throw new Error("reserveAtomic may not be lower than the $35 survival reserve");
  }
  const cap = input.maxPayoutAtomic == null
    ? null
    : integerAtomic(input.maxPayoutAtomic, "maxPayoutAtomic");

  let gross = 0n;
  let costs = 0n;
  for (const candidate of rows) {
    const row = normaliseEntry(candidate);
    if (row.wallet_address !== walletAddress) {
      throw new Error("an earnings row belongs to another wallet");
    }
    if (row.currency !== "USD") {
      throw new Error("Base USDC payouts require USD ledger rows");
    }
    const amount = BigInt(row.amount_minor);
    if (row.kind === "financial_external_income") gross += amount;
    if (row.kind === "financial_realized_loss"
      || row.kind === "financial_fee"
      || row.kind === "financial_user_transfer") {
      costs += amount;
    }
  }

  const verifiedSurplus = gross > costs ? gross - costs : 0n;
  const surplusAtomic = verifiedSurplus * ATOMIC_PER_USD_MINOR;
  const balanceAvailable = onchain > reserve ? onchain - reserve : 0n;
  let amount = surplusAtomic < balanceAvailable ? surplusAtomic : balanceAvailable;
  if (cap != null && cap < amount) amount = cap;

  let reason = "ready";
  if (verifiedSurplus === 0n) reason = "no_verified_surplus";
  else if (balanceAvailable === 0n) reason = "reserve_floor";
  else if (cap === 0n) reason = "transaction_cap";

  return {
    amountAtomic: amount.toString(),
    verifiedSurplusMinor: Number(verifiedSurplus),
    reason,
    reserveAtomic: reserve.toString(),
  };
}

module.exports = {
  DEFAULT_RESERVE_ATOMIC,
  ATOMIC_PER_USD_MINOR,
  computePayout,
};
