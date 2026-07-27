"use strict";

const { createHash } = require("node:crypto");

const { settleBaseUsdc } = require("./base-usdc-payout.js");
const { normaliseEntry, formatUsdMinor } = require("./earnings-ledger.js");
const { recordEarnLoopRevenue } = require("./earnings-runtime.js");
const { validateWalletAddress } = require("./payout-address-intake.js");
const { computePayout, ATOMIC_PER_USD_MINOR } = require("./payout-policy.js");
const { sendMessage } = require("./telegram.js");

const PAGE_SIZE = 1000;
const MAX_LEDGER_ROWS = 10_000;

function credentials(opts = {}) {
  const supaUrl = opts.supaUrl || process.env.SUPABASE_URL;
  const supaKey = opts.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  if (!supaUrl || !supaKey) throw new Error("payout runtime needs Supabase credentials");
  if (typeof fetchImpl !== "function") throw new Error("payout runtime needs fetch");
  return { supaUrl: String(supaUrl).replace(/\/$/, ""), supaKey, fetchImpl };
}

function headers(key, extra = {}) {
  return {
    apikey: key,
    Authorization: `Bearer ${key}`,
    "Content-Type": "application/json",
    ...extra,
  };
}

async function readPayoutTenant(uid, opts = {}) {
  const tenantUid = String(uid == null ? "" : uid).trim();
  if (!tenantUid) throw new Error("payout tenant uid is required");
  const { supaUrl, supaKey, fetchImpl } = credentials(opts);
  const url = `${supaUrl}/rest/v1/lm_users?uid=eq.${encodeURIComponent(tenantUid)}` +
    "&select=uid,telegram_chat_id,payout_destination&limit=1";
  const response = await fetchImpl(url, { headers: headers(supaKey) });
  if (!response || !response.ok) {
    throw new Error(`payout tenant read failed (${response ? response.status : "no response"})`);
  }
  const rows = await response.json();
  if (!Array.isArray(rows) || rows.length !== 1) {
    throw new Error("payout tenant lookup did not resolve exactly one row");
  }
  return rows[0];
}

async function readWalletLedger(walletAddress, opts = {}) {
  const wallet = String(walletAddress == null ? "" : walletAddress).trim();
  if (!wallet) throw new Error("payout wallet address is required");
  const { supaUrl, supaKey, fetchImpl } = credentials(opts);
  const query = "select=*&" +
    `wallet_address=eq.${encodeURIComponent(wallet)}&` +
    "order=occurred_at.asc,entry_key.asc";
  const rows = [];

  for (let start = 0; start <= MAX_LEDGER_ROWS; start += PAGE_SIZE) {
    const end = start === MAX_LEDGER_ROWS ? start : start + PAGE_SIZE - 1;
    const response = await fetchImpl(`${supaUrl}/rest/v1/lm_agent_earnings?${query}`, {
      headers: headers(supaKey, { Range: `${start}-${end}` }),
    });
    if (!response || !response.ok) {
      throw new Error(`payout ledger read failed (${response ? response.status : "no response"})`);
    }
    const page = await response.json();
    if (!Array.isArray(page)) throw new Error("payout ledger returned a non-array body");
    if (start === MAX_LEDGER_ROWS) {
      if (page.length > 0) throw new Error(`payout ledger exceeds the ${MAX_LEDGER_ROWS}-row safety bound`);
      break;
    }
    rows.push(...page);
    if (page.length < PAGE_SIZE) break;
  }
  return rows;
}

function destinationAddress(tenant, uid) {
  if (!tenant || String(tenant.uid || "") !== uid) {
    throw new Error("payout tenant scope does not match the requested uid");
  }
  if (!String(tenant.telegram_chat_id || "")) {
    throw new Error("payout tenant has no Telegram receipt destination");
  }
  const destination = tenant.payout_destination;
  if (!destination || destination.type !== "wallet" || destination.status !== "usable") {
    throw new Error("payout tenant has no usable wallet destination");
  }
  const validated = validateWalletAddress(destination.address);
  if (!validated.ok) throw new Error(`payout wallet destination is invalid (${validated.reason})`);
  return validated.address;
}

function payoutIdFor(input = {}) {
  const rows = (Array.isArray(input.rows) ? input.rows : [])
    .map((candidate) => normaliseEntry(candidate))
    .map((row) => [
      row.entry_key,
      row.wallet_address,
      row.kind,
      String(row.amount_minor),
      row.currency,
      row.occurred_at,
      row.tx_hash || "",
    ].join("|"))
    .sort();
  const material = [
    "life-manager-payout-evidence-v1",
    String(input.uid || ""),
    String(input.walletAddress || "").toLowerCase(),
    String(input.destination || "").toLowerCase(),
    String(input.amountAtomic || ""),
    ...rows,
  ].join("\n");
  return `tenant-${createHash("sha256").update(material, "utf8").digest("hex")}`;
}

function payoutReceiptText(amountAtomic, txHash) {
  const raw = String(amountAtomic == null ? "" : amountAtomic).trim();
  if (!/^\d+$/.test(raw) || BigInt(raw) <= 0n || BigInt(raw) % ATOMIC_PER_USD_MINOR !== 0n) {
    throw new Error("payout receipt amount must be an exact positive cent");
  }
  const tx = String(txHash == null ? "" : txHash).trim().toLowerCase();
  if (!/^0x[0-9a-f]{64}$/.test(tx)) throw new Error("payout receipt needs a transaction hash");
  const minor = BigInt(raw) / ATOMIC_PER_USD_MINOR;
  return `💸 ${formatUsdMinor(minor)}を登録済みのwalletに送金しました。tx: basescan.org/tx/${tx}\n` +
    "着金まで数分かかることがあります。";
}

function assertSettlementReceipt(receipt, expected) {
  const tx = String(receipt && receipt.txHash || "").toLowerCase();
  const block = String(receipt && receipt.blockNumber || "");
  if (!/^0x[0-9a-f]{64}$/.test(tx)
    || String(receipt.amountAtomic) !== expected.amountAtomic
    || String(receipt.from || "").toLowerCase() !== expected.from.toLowerCase()
    || String(receipt.to || "").toLowerCase() !== expected.to.toLowerCase()
    || !/^\d+$/.test(block)) {
    throw new Error("settlement receipt does not match the requested payout");
  }
  return receipt;
}

async function runPayout(request = {}, deps = {}) {
  const uid = String(request.uid == null ? "" : request.uid).trim();
  if (!uid) throw new Error("payout uid is required");
  const walletAddress = String(request.walletAddress == null ? "" : request.walletAddress).trim();
  if (!walletAddress) throw new Error("payout walletAddress is required");

  const readTenant = deps.readTenant || ((tenantUid) => readPayoutTenant(tenantUid, deps));
  const tenant = await readTenant(uid);
  const destination = destinationAddress(tenant, uid);

  const readLedger = deps.readLedger || ((wallet) => readWalletLedger(wallet, deps));
  const rows = await readLedger(walletAddress);
  const readBalance = deps.readBalance;
  if (typeof readBalance !== "function") throw new Error("payout runtime needs an on-chain balance reader");
  if (typeof deps.readOperatingCostMinor !== "function") {
    throw new Error("payout runtime needs an operating cost reader");
  }
  const onchainUsdcAtomic = await readBalance(walletAddress);
  const operatingCostMinor = await deps.readOperatingCostMinor(uid);
  const policy = computePayout({
    rows,
    walletAddress,
    onchainUsdcAtomic,
    operatingCostMinor,
    reserveAtomic: request.reserveAtomic,
    maxPayoutAtomic: request.maxPayoutAtomic,
  });
  if (policy.amountAtomic === "0") {
    return {
      status: "noop",
      reason: policy.reason,
      amountAtomic: "0",
      verifiedSurplusMinor: policy.verifiedSurplusMinor,
      reserveAtomic: policy.reserveAtomic,
    };
  }

  const telegramToken = deps.telegramToken || process.env.LM_TELEGRAM_BOT_TOKEN;
  if (!telegramToken) throw new Error("payout requires a Telegram token before funds may move");
  if (typeof deps.readPrivateWallet !== "function") {
    throw new Error("payout runtime needs a protected wallet reader");
  }
  const protectedWallet = await deps.readPrivateWallet();
  if (!protectedWallet || protectedWallet.address !== walletAddress || !protectedWallet.privateKey) {
    throw new Error("protected payout wallet does not match the public agent wallet");
  }

  const payoutId = payoutIdFor({
    uid,
    walletAddress,
    destination,
    amountAtomic: policy.amountAtomic,
    rows,
  });
  const settle = deps.settle || settleBaseUsdc;
  const receipt = assertSettlementReceipt(await settle({
    privateKey: protectedWallet.privateKey,
    walletAddress,
    destination,
    amountAtomic: policy.amountAtomic,
    payoutId,
    facilitatorUrl: request.facilitatorUrl || "http://127.0.0.1:8405",
    rpcUrl: request.rpcUrl,
    nowMs: request.nowMs,
  }, deps), {
    amountAtomic: policy.amountAtomic,
    from: walletAddress,
    to: destination,
  });
  const amountMinor = BigInt(receipt.amountAtomic) / ATOMIC_PER_USD_MINOR;
  const entry = {
    entry_key: `payout:${receipt.txHash}:transfer`,
    wallet_address: walletAddress,
    kind: "financial_user_transfer",
    amount_minor: Number(amountMinor),
    currency: "USD",
    occurred_at: new Date(request.nowMs == null ? Date.now() : request.nowMs).toISOString(),
    tx_hash: receipt.txHash,
    source: "base_usdc_payout",
    meta: {
      chain_id: 8453,
      block_number: receipt.blockNumber,
      payout_id: payoutId,
    },
  };
  const recordTransfer = deps.recordTransfer || ((row) => recordEarnLoopRevenue(row, deps));
  let recorded;
  try {
    recorded = await recordTransfer(entry);
    if (!recorded || recorded.ok !== true) throw new Error("ledger did not acknowledge the transfer");
  } catch (error) {
    throw new Error(`payout confirmed ${receipt.txHash} but ledger recording failed: ${
      error && error.message ? error.message : error
    }`);
  }

  const text = payoutReceiptText(receipt.amountAtomic, receipt.txHash);
  const sendTelegram = deps.sendTelegram || sendMessage;
  let notificationSent = false;
  try {
    const sent = await sendTelegram(telegramToken, String(tenant.telegram_chat_id), text);
    notificationSent = Boolean(sent && sent.ok);
  } catch {
    notificationSent = false;
  }
  return {
    status: recorded.duplicate ? "duplicate" : "transferred",
    amountAtomic: receipt.amountAtomic,
    txHash: receipt.txHash,
    payoutId,
    notificationSent,
  };
}

module.exports = {
  PAGE_SIZE,
  MAX_LEDGER_ROWS,
  readPayoutTenant,
  readWalletLedger,
  payoutIdFor,
  payoutReceiptText,
  assertSettlementReceipt,
  runPayout,
};
