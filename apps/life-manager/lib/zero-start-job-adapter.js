"use strict";
// AE-ZERO-START-1 §4.4 — start a tenant's agent at a balance of zero.
//
// Built on the shape of `lib/report-job-adapter.js` (plan/execute/reconcile/verify/report, secret
// references in `input_refs`, a durable receipt with a provider message id read back). What differs is
// what has to be true before this job is allowed to claim success.
//
// The job is exactly-once per tenant by construction: `job_id` and `effect_key` are both
// `zero-start:<uid>`, and `lm_runtime_jobs` carries UNIQUE (tenant_id, effect_key) plus ON CONFLICT
// (job_id) DO NOTHING. A scheduler sweep may therefore enqueue this on every pass without ever creating a
// second zero-start message for the same tenant; retries happen inside that one row's attempts.
//
// Ordering is deliberate: provision and record the wallets FIRST, then require a chat, then measure, then
// send. Provisioning is idempotent, so putting it first means a tenant who has not linked a chat yet still
// gets real addresses that the inflow watcher can start watching — and the retry that follows is cheap.
//
// Two claims this file refuses to make. It never reports a balance it did not read from a chain (an
// unmeasured `$0.00` is a lie), and it never reports a message it cannot prove was accepted (no
// `message_id` = failure). When delivery is genuinely unknowable — the transport died mid-flight — the
// error is marked `unknownEffect` so the runtime reconciles instead of sending a second message.

const { buildRuntimeJob } = require("./runtime-job-store.js");
const { assertNoSecret, formatUsdAtomic, formatUsdMinor } = require("./earnings-ledger.js");
const { isSolanaAddress } = require("./agent-wallet-solana.js");
const { formatSol, readSolBalance } = require("./solana-balance.js");
const { readUsdcBalance } = require("./base-usdc-balance.js");
const { ensureTenantWallets } = require("./tenant-wallet-store.js");
const { hashChatId, sendMessage } = require("./telegram.js");

const CAPABILITY = "wallet.zero-start";
const LOOP_ID = "agent.zero-start";
const RECEIPT_KIND = "tenant_zero_start";
const SECRET_REF = /^secret:\/\/[a-z0-9][a-z0-9._-]*(?:\/[a-z0-9][a-z0-9._-]*)*$/i;
const EVM_ADDRESS = /^0x[0-9a-fA-F]{40}$/;
const HASH = /^[0-9a-f]{64}$/;
const WHOLE = /^\d+$/;
const USDC_DECIMALS = 6;
const USD_MICROS_PER_CENT = 10_000n;
// A tenant can sit unlinked for a while; 20 is the protocol ceiling (runtime max attempts).
const MAX_ATTEMPTS = 20;

const BASESCAN_ADDRESS = "https://basescan.org/address/";
const SOLSCAN_ACCOUNT = "https://solscan.io/account/";

// §4.4: what the tenant is told has actually started. The shared-seller caveat is named explicitly
// because binding x402 `payTo` to tenant wallets is AE-X402-TENANT-ROUTING-1, not this slice.
const STARTED_RAILS = Object.freeze([
  "x402 SELL (shared seller until AE-X402-TENANT-ROUTING-1)",
  "fee-free WORK",
  "incoming-payment watch",
]);

const WALLET_COLUMNS = Object.freeze([
  "agent_wallet_address",
  "agent_wallet_solana_address",
  "agent_wallet_key_ref",
  "agent_wallet_solana_key_ref",
  "agent_wallet_created_at",
]);

function requiredText(value, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text) throw new Error(`${label} is required`);
  return text;
}

function coded(message, code, extra = {}) {
  return Object.assign(new Error(message), { code }, extra);
}

function zeroStartEffectKey(tenantId) {
  return `zero-start:${requiredText(tenantId, "zero-start tenant")}`;
}

function buildZeroStartJob(input = {}) {
  const tenantId = requiredText(input.tenantId, "zero-start tenant");
  const telegramTokenRef = requiredText(input.telegramTokenRef, "zero-start Telegram secret reference");
  if (!SECRET_REF.test(telegramTokenRef)) {
    throw new Error("zero-start Telegram token must be a secret reference");
  }
  const key = zeroStartEffectKey(tenantId);
  return buildRuntimeJob({
    jobId: key,
    tenantId,
    loopId: LOOP_ID,
    capability: CAPABILITY,
    effectClass: "message",
    effectKey: key,
    inputRefs: { telegram_token_ref: telegramTokenRef },
    maxAttempts: MAX_ATTEMPTS,
  });
}

function credentials(opts = {}) {
  const supaUrl = opts.supaUrl || process.env.SUPABASE_URL;
  const supaKey = opts.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  if (!supaUrl || !supaKey) throw new Error("zero-start needs Supabase credentials");
  if (typeof fetchImpl !== "function") throw new Error("zero-start needs a fetch implementation");
  return { supaUrl, supaKey, fetchImpl };
}

function headers(key, extra) {
  return { apikey: key, Authorization: `Bearer ${key}`, "Content-Type": "application/json", ...(extra || {}) };
}

async function readZeroStartTenant(uid, opts = {}) {
  const tenantUid = requiredText(uid, "zero-start tenant uid");
  const { supaUrl, supaKey, fetchImpl } = credentials(opts);
  const select = ["uid", "telegram_chat_id", ...WALLET_COLUMNS].join(",");
  const url = `${supaUrl}/rest/v1/lm_users?uid=eq.${encodeURIComponent(tenantUid)}`
    + `&select=${select}&limit=1`;
  const response = await fetchImpl(url, { headers: headers(supaKey) });
  if (!response || !response.ok) {
    throw new Error(`zero-start tenant read failed (${response ? response.status : "no response"})`);
  }
  const rows = await response.json();
  if (!Array.isArray(rows) || rows.length !== 1) {
    throw new Error("zero-start tenant lookup did not resolve exactly one row");
  }
  return rows[0];
}

async function writeZeroStartWalletColumns(uid, columns, opts = {}) {
  const tenantUid = requiredText(uid, "zero-start tenant uid");
  if (!columns || typeof columns !== "object" || Array.isArray(columns)) {
    throw new Error("zero-start wallet columns are invalid");
  }
  // An allowlist, not a denylist: a column this slice does not own has no business being written here,
  // and a key smuggled in under any name is refused before the request is built.
  for (const key of Object.keys(columns)) {
    if (!WALLET_COLUMNS.includes(key)) {
      throw new Error(`zero-start may not write the column ${key}`);
    }
  }
  assertNoSecret(columns);
  const { supaUrl, supaKey, fetchImpl } = credentials(opts);
  const response = await fetchImpl(
    `${supaUrl}/rest/v1/lm_users?uid=eq.${encodeURIComponent(tenantUid)}`,
    {
      method: "PATCH",
      headers: headers(supaKey, { Prefer: "return=minimal" }),
      body: JSON.stringify(columns),
    },
  );
  if (!response || !response.ok) {
    throw new Error(`zero-start wallet column write failed (${response ? response.status : "no response"})`);
  }
  return columns;
}

// Exact or full precision, never rounded. A whole number of cents renders as $x.yz; anything finer keeps
// all six USDC decimals, because rounding down shaves the tenant's money and rounding up invents it.
function formatMeasuredUsdc(atomic) {
  const raw = String(atomic == null ? "" : atomic).trim();
  if (!WHOLE.test(raw)) throw new Error("measured USDC balance must be whole atomic units");
  const value = BigInt(raw);
  return value % USD_MICROS_PER_CENT === 0n
    ? formatUsdMinor(value / USD_MICROS_PER_CENT)
    : formatUsdAtomic(raw, USDC_DECIMALS);
}

async function measure(label, read, address) {
  let value;
  try {
    value = await read(address);
  } catch (error) {
    throw new Error(`zero-start could not measure the ${label} balance: ${error && error.message ? error.message : error}`);
  }
  const raw = String(value == null ? "" : value).trim();
  if (!WHOLE.test(raw)) throw new Error(`zero-start could not measure the ${label} balance`);
  return raw;
}

function formatZeroStartMessage(view) {
  return [
    "🪙 <b>Your agent's wallets are live</b>",
    "",
    "<b>Base</b> (EVM)",
    `<code>${view.base.address}</code>`,
    `${BASESCAN_ADDRESS}${view.base.address}`,
    `Measured balance: ${view.base.balance_display} USDC`,
    "",
    "<b>Solana</b>",
    `<code>${view.solana.address}</code>`,
    `${SOLSCAN_ACCOUNT}${view.solana.address}`,
    `Measured balance: ${view.solana.balance_display}`,
    "",
    "<b>Started with no seed:</b>",
    ...STARTED_RAILS.map((rail) => `• ${rail}`),
    "",
    "Both balances above were read from the chains just now — nothing here is estimated.",
    "You do not need to fund anything. Anything you or anyone else sends to these addresses"
    + " is recorded as capital in, never as revenue, and no income is promised.",
  ].join("\n");
}

// A provider answer is either proof of delivery, proof of refusal, or silence. Only the first two can be
// acted on; silence must reconcile, because resending would be a second message the tenant did not ask for.
function assertTelegramAccepted(providerResult) {
  const messageId = providerResult && providerResult.result && providerResult.result.message_id;
  if (providerResult && providerResult.ok === true && Number.isInteger(messageId) && messageId > 0) {
    return messageId;
  }
  if (providerResult && providerResult.ok === true) {
    throw coded(
      "zero-start Telegram provider receipt is incomplete: no message id",
      "ZERO_START_TELEGRAM_RECEIPT_INCOMPLETE",
      { unknownEffect: true },
    );
  }
  // Telegram answered and refused (it always supplies error_code): nothing was delivered, so a retry
  // cannot double-send. No error_code means the transport failed and delivery is unknowable.
  const refused = Number.isInteger(providerResult && providerResult.error_code);
  throw coded(
    "zero-start Telegram send did not succeed",
    refused ? "ZERO_START_TELEGRAM_REFUSED" : "ZERO_START_TELEGRAM_UNKNOWN",
    refused ? {} : { unknownEffect: true },
  );
}

function sentAt(providerResult, fallbackIso) {
  const seconds = Number(providerResult && providerResult.result && providerResult.result.date);
  if (Number.isSafeInteger(seconds) && seconds > 0) return new Date(seconds * 1000).toISOString();
  return fallbackIso;
}

async function executeZeroStartJob(job, deps = {}) {
  if (
    !job
    || job.capability !== CAPABILITY
    || job.effect_class !== "message"
    || job.effect_key !== zeroStartEffectKey(job.tenant_id)
  ) {
    throw new Error("zero-start job contract mismatch");
  }
  const inputRefs = job.input_refs || {};
  if (!SECRET_REF.test(String(inputRefs.telegram_token_ref || ""))) {
    throw new Error("zero-start job is missing its Telegram secret reference");
  }
  if (!deps.secretProvider || typeof deps.secretProvider.get !== "function") {
    throw new Error("zero-start secret provider is required");
  }

  const uid = job.tenant_id;
  const nowIso = typeof deps.now === "function" ? String(deps.now()) : new Date().toISOString();
  const readTenant = deps.readTenant || ((tenantId) => readZeroStartTenant(tenantId, deps));
  const patchTenant = deps.patchTenant || ((tenantId, columns) => writeZeroStartWalletColumns(tenantId, columns, deps));
  const ensureWallets = deps.ensureWallets || ensureTenantWallets;
  const readBaseBalance = deps.readBaseBalance || ((address) => readUsdcBalance(address, deps));
  const readSolanaBalance = deps.readSolanaBalance || ((address) => readSolBalance(address, deps));
  const providerSend = deps.sendTelegram || sendMessage;

  const row = await readTenant(uid);
  if (String(row && row.uid ? row.uid : uid) !== uid) {
    throw new Error("zero-start tenant scope mismatch");
  }

  // 1-2. Provision (idempotent, hard-stops on a file/DB disagreement) and record the public identity.
  const wallets = ensureWallets(uid, { env: deps.env, now: () => nowIso, existing: row });
  const changed = WALLET_COLUMNS.some((column) => (
    String(row[column] == null ? "" : row[column]) !== String(wallets.columns[column])
  ));
  if (changed) await patchTenant(uid, { ...wallets.columns });

  // 3. §11.2 MAJOR-5 — a chat we do not have is a DEFERRED OUTCOME, not a failure.
  //
  // Throwing here used to burn one of the job row's 20 lifetime attempts on every wake, and the schema
  // permits neither replacing the row (UNIQUE (tenant_id, effect_key)) nor resetting `attempt` (the receipt
  // PK collides), so a tenant who linked Telegram after 20 sweeps could NEVER be told. Completing with a
  // real blocked receipt costs one attempt in total; the sweep re-activates the row only once the chat
  // actually appears, so waiting is free and unbounded.
  //
  // The wallets above are already provisioned and published, so AC5 holds and the inflow watch is already
  // running for this tenant — being unreachable by Telegram never delays the money rails.
  const chatId = String(row.telegram_chat_id == null ? "" : row.telegram_chat_id).trim();
  if (!chatId) {
    const receipt = {
      schema_version: 1,
      kind: RECEIPT_KIND,
      status: "blocked_no_chat",
      reason: "no_linked_chat",
      blocked_at: nowIso,
      wallet_status: wallets.status,
      // Public identity only, and deliberately no message_id / chat_id_hash / sent_at: a blocked receipt
      // that carried those would make the tenant look announced to the sweep, forever.
      base: { chain: "base", address: wallets.base.address },
      solana: { chain: "solana", address: wallets.solana.address },
    };
    assertNoSecret(receipt);
    return {
      receipt,
      result: { status: "blocked_no_chat", uid, wallet_status: wallets.status },
    };
  }

  // 4. Measure both chains for real.
  const baseAtomic = await measure("Base USDC", readBaseBalance, wallets.base.address);
  const solanaLamports = await measure("Solana", readSolanaBalance, wallets.solana.address);
  const view = {
    base: {
      chain: "base",
      address: wallets.base.address,
      balance_atomic: baseAtomic,
      balance_decimals: USDC_DECIMALS,
      balance_display: formatMeasuredUsdc(baseAtomic),
    },
    solana: {
      chain: "solana",
      address: wallets.solana.address,
      balance_lamports: solanaLamports,
      balance_display: formatSol(solanaLamports),
    },
  };

  // 5. One message, guarded on the way out.
  const text = formatZeroStartMessage(view);
  // `assertNoSecret` is a FIELD-NAME guard, not a shape scanner: it rejects keys called privateKey,
  // secret, seed and so on, and it cannot recognise key-shaped VALUES. What actually keeps this payload
  // safe is that `view` is built only from public addresses and measured balances — the guard is a cheap
  // backstop against a careless field name being added later.
  assertNoSecret({ ...view, text });
  const telegramToken = await deps.secretProvider.get(uid, inputRefs.telegram_token_ref);
  const providerResult = await providerSend(telegramToken, chatId, text);
  const messageId = assertTelegramAccepted(providerResult);

  const receipt = {
    schema_version: 1,
    kind: RECEIPT_KIND,
    status: "started",
    chat_id_hash: hashChatId(chatId),
    message_id: messageId,
    sent_at: sentAt(providerResult, nowIso),
    measured_at: nowIso,
    wallet_status: wallets.status,
    base: { ...view.base },
    solana: { ...view.solana },
    started_rails: [...STARTED_RAILS],
  };
  assertNoSecret(receipt);
  return { receipt, result: { status: "started", uid, message_id: messageId, wallet_status: wallets.status } };
}

function validIso(value) {
  return typeof value === "string" && Number.isFinite(Date.parse(value));
}

function validRail(rail, addressOk, amountKey) {
  return Boolean(rail)
    && typeof rail === "object"
    && !Array.isArray(rail)
    && addressOk(String(rail.address || ""))
    && WHOLE.test(String(rail[amountKey] == null ? "" : rail[amountKey]))
    && typeof rail.balance_display === "string"
    && rail.balance_display.length > 0;
}

function verifyZeroStartReceipt(receipt) {
  if (
    !receipt
    || typeof receipt !== "object"
    || Array.isArray(receipt)
    || receipt.schema_version !== 1
    || receipt.kind !== RECEIPT_KIND
  ) {
    return false;
  }
  // §11.2: a blocked receipt is real, durable evidence — but it must be unable to look like an
  // announcement, because `status === "started"` is exactly what the sweep trusts.
  if (receipt.status === "blocked_no_chat") {
    return receipt.reason === "no_linked_chat"
      && validIso(receipt.blocked_at)
      && ["created", "existing"].includes(receipt.wallet_status)
      && Boolean(receipt.base) && EVM_ADDRESS.test(String(receipt.base.address || ""))
      && Boolean(receipt.solana) && isSolanaAddress(String(receipt.solana.address || ""))
      && receipt.message_id === undefined
      && receipt.chat_id_hash === undefined
      && receipt.sent_at === undefined;
  }
  if (receipt.status !== "started") return false;
  return Number.isInteger(receipt.message_id)
    && receipt.message_id > 0
    && HASH.test(String(receipt.chat_id_hash || ""))
    && validIso(receipt.sent_at)
    && validIso(receipt.measured_at)
    && ["created", "existing"].includes(receipt.wallet_status)
    && validRail(receipt.base, (value) => EVM_ADDRESS.test(value), "balance_atomic")
    && receipt.base.balance_decimals === USDC_DECIMALS
    && validRail(receipt.solana, isSolanaAddress, "balance_lamports")
    && Array.isArray(receipt.started_rails)
    && receipt.started_rails.length === STARTED_RAILS.length
    && receipt.started_rails.every((rail, index) => rail === STARTED_RAILS[index]);
}

function safeZeroStartSummary(receipt) {
  if (!verifyZeroStartReceipt(receipt)) {
    throw new Error("zero-start receipt verification failed");
  }
  if (receipt.status === "blocked_no_chat") {
    return {
      status: receipt.status,
      reason: receipt.reason,
      blocked_at: receipt.blocked_at,
      wallet_status: receipt.wallet_status,
      base_address: receipt.base.address,
      solana_address: receipt.solana.address,
    };
  }
  return {
    status: receipt.status,
    message_id: receipt.message_id,
    sent_at: receipt.sent_at,
    wallet_status: receipt.wallet_status,
    base_address: receipt.base.address,
    base_balance: receipt.base.balance_display,
    solana_address: receipt.solana.address,
    solana_balance: receipt.solana.balance_display,
    started_rails: [...receipt.started_rails],
  };
}

function createZeroStartLoopAdapter(deps = {}) {
  return Object.freeze({
    async plan(context = {}) {
      return [buildZeroStartJob({
        tenantId: context.tenantId,
        telegramTokenRef: context.telegramTokenRef
          || (deps.env && deps.env.LM_TELEGRAM_TOKEN_REF)
          || "secret://telegram/bot-token",
      })];
    },
    execute(job, services = {}) {
      return executeZeroStartJob(job, { ...deps, ...services });
    },
    async reconcile(effect) {
      if (typeof deps.inspectEffect !== "function") return { state: "unknown" };
      const proof = await deps.inspectEffect(effect);
      if (!proof || !["present", "absent", "unknown"].includes(proof.state)) {
        throw new Error("zero-start reconciliation proof invalid");
      }
      if (proof.state === "unknown") return { state: "unknown" };
      if (!proof.receipt || typeof proof.receipt !== "object" || Array.isArray(proof.receipt)) {
        throw new Error("zero-start reconciliation receipt invalid");
      }
      if (proof.state === "present" && !verifyZeroStartReceipt(proof.receipt)) {
        throw new Error("zero-start reconciliation receipt verification failed");
      }
      return proof;
    },
    verify: verifyZeroStartReceipt,
    report: safeZeroStartSummary,
  });
}

// §10 MINOR-8: there is deliberately NO CLI enqueue entrypoint here. §4.4 rules the scheduler sweep the
// only enqueue point, and a second write surface into the job queue is exactly what that excluded.

module.exports = {
  CAPABILITY,
  LOOP_ID,
  MAX_ATTEMPTS,
  RECEIPT_KIND,
  STARTED_RAILS,
  WALLET_COLUMNS,
  buildZeroStartJob,
  createZeroStartLoopAdapter,
  executeZeroStartJob,
  formatMeasuredUsdc,
  formatZeroStartMessage,
  readZeroStartTenant,
  safeZeroStartSummary,
  verifyZeroStartReceipt,
  writeZeroStartWalletColumns,
  zeroStartEffectKey,
};
