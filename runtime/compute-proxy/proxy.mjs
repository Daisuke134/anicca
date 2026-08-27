// Instance-bound OpenAI-compatible x402 compute payer with receipt-backed authorization.
import http from "node:http";
import { realpathSync } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadEvmKey } from "../../skills/earn/lib/resolve-identity.mjs";

const BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const API = "https://blockrun.ai/api/v1/chat/completions";
const PROFILES = new Set(["auto", "premium", "eco", "free", "blockrun/auto", "blockrun/premium", "blockrun/eco", "blockrun/free"]);
const CURRENT_FRONTIER_MODEL = "openai/gpt-5.4-nano";
const SAFE_PROVIDER_CODES = new Set(["FREE_MODEL_FAILED"]);

export function resolveFrontierModel(value) {
  const model = typeof value === "string" ? value.trim() : "";
  return model || CURRENT_FRONTIER_MODEL;
}

function validatedHttpStatus(value) {
  const status = Number(value);
  return Number.isInteger(status) && status >= 100 && status <= 599 ? status : null;
}

function validatedProviderCode(value) {
  return SAFE_PROVIDER_CODES.has(value) ? value : null;
}

export function safeComputeDiagnostic(error, { stage = "paid_compute", model } = {}) {
  return {
    event: "compute_execution_failed",
    stage: stage === "paid_compute" ? stage : "paid_compute",
    model: resolveFrontierModel(model),
    httpStatus: validatedHttpStatus(error?.httpStatus),
    providerCode: validatedProviderCode(error?.providerCode),
  };
}

const defaultDiagnosticSink = (diagnostic) => console.error(JSON.stringify(diagnostic));

export function requireInstancePort(value, { receiptBacked = true } = {}) {
  const port = Number(value);
  if (!Number.isInteger(port) || port < 1024 || port > 65535 || (receiptBacked && port === 8402)) {
    throw new Error("COMPUTE_PROXY_PORT must be an instance-specific port other than shared :8402");
  }
  return port;
}

export function selectCappedRequirement(maxCostUsdc, accepts) {
  if (!Number.isFinite(Number(maxCostUsdc)) || Number(maxCostUsdc) <= 0 || !Array.isArray(accepts)) {
    throw new Error("invalid compute payment cap");
  }
  const maxAtomic = BigInt(Math.floor(Number(maxCostUsdc) * 1e6 + 1e-9));
  const eligible = accepts.filter((item) => {
    try {
      return item?.scheme === "exact" && item?.network === "eip155:8453"
        && String(item?.asset || "").toLowerCase() === BASE_USDC.toLowerCase()
        && BigInt(item.amount) > 0n && BigInt(item.amount) <= maxAtomic;
    } catch { return false; }
  }).sort((a, b) => BigInt(a.amount) < BigInt(b.amount) ? -1 : BigInt(a.amount) > BigInt(b.amount) ? 1 : 0);
  if (eligible.length === 0) {
    const error = new Error("BlockRun payment requirement exceeds authorization or uses an unsupported asset");
    error.code = "PAYMENT_REQUIREMENT_REJECTED_BEFORE_SIGNING";
    throw error;
  }
  return eligible[0];
}

async function jsonl(file) {
  const raw = await readFile(file, "utf8");
  const parsed = [];
  for (const line of raw.split("\n").filter(Boolean)) {
    try { parsed.push(JSON.parse(line)); } catch { throw new Error("REVENUE_JOURNAL_CORRUPT"); }
  }
  return parsed;
}

export function publicProxyError(receiptBacked = true) {
  return { error: { code: receiptBacked ? "AGENT_ECONOMY_COMPUTE_FAILED" : "COMPUTE_PROXY_FAILED", message: "compute request failed" } };
}

export function paidTransport(account, fetchImpl = fetch) {
  return async ({ request, maxCostUsdc }) => {
    const [{ wrapFetchWithPaymentFromConfig, decodePaymentResponseHeader }, { ExactEvmScheme }] = await Promise.all([
      import("@x402/fetch"), import("@x402/evm"),
    ]);
    let selected;
    let selectorRejectedBeforeSigning = false;
    let paymentBroadcastStarted = false;
    const trackedFetch = async (input, init) => {
      const outbound = input instanceof Request ? input : new Request(input, init);
      if (outbound.headers.has("PAYMENT-SIGNATURE") || outbound.headers.has("X-PAYMENT")) {
        paymentBroadcastStarted = true;
      }
      return fetchImpl(input, init);
    };
    const paidFetch = wrapFetchWithPaymentFromConfig(trackedFetch, {
      schemes: [{ network: "eip155:8453", client: new ExactEvmScheme(account) }],
      paymentRequirementsSelector: (_version, accepts) => {
        try {
          selected = selectCappedRequirement(maxCostUsdc, accepts);
          return selected;
        } catch (error) {
          if (error?.code === "PAYMENT_REQUIREMENT_REJECTED_BEFORE_SIGNING") selectorRejectedBeforeSigning = true;
          throw error;
        }
      },
    });
    let response;
    try {
      response = await paidFetch(API, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(request),
      });
    } catch (error) {
      if (paymentBroadcastStarted) error.code = "PAYMENT_REQUEST_BROADCAST_AMBIGUOUS";
      else if (selectorRejectedBeforeSigning) error.code = "PAYMENT_REQUIREMENT_REJECTED_BEFORE_SIGNING";
      else if (!paymentBroadcastStarted) error.code = "PAYMENT_REQUEST_NOT_BROADCAST";
      throw error;
    }
    const header = response.headers.get("PAYMENT-RESPONSE") || response.headers.get("X-PAYMENT-RESPONSE");
    if (!response.ok) {
      let providerCode;
      try {
        const body = await response.json();
        providerCode = validatedProviderCode(body?.error?.code ?? body?.code);
      } catch { /* provider body is intentionally discarded */ }
      const error = new Error("BlockRun request failed");
      const httpStatus = validatedHttpStatus(response.status);
      if (httpStatus !== null) error.httpStatus = httpStatus;
      if (providerCode) error.providerCode = providerCode;
      throw error;
    }
    const output = await response.json();
    if (!header) throw new Error("BlockRun response omitted PAYMENT-RESPONSE settlement proof");
    const settlement = decodePaymentResponseHeader(header);
    if (!selected || (settlement.amount !== undefined && BigInt(settlement.amount) !== BigInt(selected.amount))) {
      throw new Error("BlockRun settlement amount does not match the authorized requirement");
    }
    return {
      output,
      settlement: {
        ...settlement,
        requirement: {
          scheme: selected.scheme, network: selected.network, asset: selected.asset,
          pay_to: selected.payTo, amount_atomic: selected.amount,
        },
      },
      costUsdc: Number(selected.amount) / 1e6,
    };
  };
}

async function createLegacyProxy(pk, frontierModel) {
  const { BlockrunClient } = await import("@blockrun/llm");
  const client = new BlockrunClient({ privateKey: pk });
  return http.createServer((req, res) => {
    if (req.method === "POST" && req.url?.includes("/chat/completions")) {
      let raw = "";
      req.on("data", (chunk) => { raw += chunk; });
      req.on("end", async () => {
        try {
          const body = JSON.parse(raw);
          if (PROFILES.has(String(body.model || "").toLowerCase())) body.model = frontierModel;
          const output = await client.post("/v1/chat/completions", body);
          res.writeHead(200, { "content-type": "application/json" });
          res.end(JSON.stringify(output));
        } catch (error) {
          res.writeHead(502, { "content-type": "application/json" });
          res.end(JSON.stringify(publicProxyError(false)));
        }
      });
      return;
    }
    res.writeHead(req.url?.includes("/models") ? 200 : 404, { "content-type": "application/json" });
    res.end(req.url?.includes("/models") ? JSON.stringify({ object: "list", data: [] }) : "");
  });
}

export function createComputeProxy({
  payer,
  revenueJournalPath,
  computeJournalPath,
  fundingReceiptIds,
  maxCostUsdc,
  reserveUsdc,
  sessionCapUsdc,
  getBalance,
  transport,
  frontierModel,
  diagnosticSink = defaultDiagnosticSink,
  executeCompute,
} = {}) {
  if (!payer || !revenueJournalPath || !computeJournalPath || !Array.isArray(fundingReceiptIds)
    || fundingReceiptIds.length === 0 || typeof getBalance !== "function" || typeof transport !== "function"
    || !Number.isFinite(Number(maxCostUsdc)) || Number(maxCostUsdc) <= 0
    || !Number.isFinite(Number(reserveUsdc)) || Number(reserveUsdc) < 0
    || !Number.isFinite(Number(sessionCapUsdc)) || Number(sessionCapUsdc) <= 0
    || typeof diagnosticSink !== "function") {
    throw new Error("compute proxy receipt-backed configuration is incomplete");
  }
  const configuredModel = resolveFrontierModel(frontierModel);
  return http.createServer((req, res) => {
    if (req.method !== "POST" || !req.url?.includes("/chat/completions")) {
      res.writeHead(req.url?.includes("/models") ? 200 : 404, { "content-type": "application/json" });
      res.end(req.url?.includes("/models") ? JSON.stringify({ object: "list", data: [] }) : "");
      return;
    }
    let raw = "";
    req.on("data", (chunk) => { raw += chunk; });
    req.on("end", async () => {
      try {
        const body = JSON.parse(raw);
        const intentId = req.headers["idempotency-key"];
        if (typeof intentId !== "string" || !intentId) throw new Error("Idempotency-Key header is required");
        body.model = configuredModel;
        const revenueReceipts = await jsonl(revenueJournalPath);
        const execute = executeCompute || (await import("./compute-receipt.mjs")).executeComputeRequest;
        const result = await execute({
          journalPath: computeJournalPath, intentId, payer, request: body,
          fundingReceiptIds, revenueReceipts, maxCostUsdc, reserveUsdc,
          sessionSpentUsdc: 0, sessionCapUsdc, getBalance, transport,
        });
        if (result.duplicate) {
          res.writeHead(409, { "content-type": "application/json", "x-agent-economy-receipt": result.receipt.idempotency_key });
          res.end(JSON.stringify({ error: { message: "compute intent already settled" }, receipt: result.receipt }));
          return;
        }
        res.writeHead(200, { "content-type": "application/json", "x-agent-economy-receipt": result.receipt.idempotency_key });
        res.end(JSON.stringify(result.output));
      } catch (error) {
        try {
          Promise.resolve(diagnosticSink(safeComputeDiagnostic(error, { stage: "paid_compute", model: configuredModel }))).catch(() => {});
        } catch { /* diagnostics never alter the public response */ }
        res.writeHead(502, { "content-type": "application/json" });
        res.end(JSON.stringify(publicProxyError(true)));
      }
    });
  });
}

async function main() {
  const home = process.env.ANICCA_HOME;
  if (!home) throw new Error("ANICCA_HOME is required");
  const pk = loadEvmKey({ mode: "agent-economy" });
  if (!pk) {
    const error = new Error("AGENT_ECONOMY_INSTANCE_KEY_MISSING: instance wallet key is unavailable");
    error.code = "AGENT_ECONOMY_INSTANCE_KEY_MISSING";
    throw error;
  }
  const [{ privateKeyToAccount }, { createPublicClient, erc20Abi, http: viemHttp }, { base }] = await Promise.all([
    import("viem/accounts"), import("viem"), import("viem/chains"),
  ]);
  const account = privateKeyToAccount(pk);
  const ids = String(process.env.AGENT_ECONOMY_FUNDING_RECEIPT_IDS || "").split(",").map((v) => v.trim()).filter(Boolean);
  const receiptBacked = process.env.ANICCA_INSTANCE === "agent-economy" || ids.length > 0;
  const port = requireInstancePort(process.env.COMPUTE_PROXY_PORT, { receiptBacked });
  const frontierModel = resolveFrontierModel(process.env.ANICCA_FRONTIER_MODEL);
  if (!receiptBacked) {
    (await createLegacyProxy(pk, frontierModel)).listen(port, "127.0.0.1", () => console.log(`compute proxy on 127.0.0.1:${port}`));
    return;
  }
  if (ids.length === 0) throw new Error("AGENT_ECONOMY_FUNDING_RECEIPT_IDS is required for receipt-backed compute");
  const rpc = process.env.BASE_RPC_URL || "https://mainnet.base.org";
  const publicClient = createPublicClient({ chain: base, transport: viemHttp(rpc) });
  const getBalance = async () => Number(await publicClient.readContract({
    address: BASE_USDC, abi: erc20Abi, functionName: "balanceOf", args: [account.address],
  })) / 1e6;
  const server = createComputeProxy({
    payer: account.address,
    revenueJournalPath: process.env.AGENT_ECONOMY_REVENUE_JOURNAL || path.join(home, "skills/earn/state/revenue-receipts.jsonl"),
    computeJournalPath: process.env.AGENT_ECONOMY_COMPUTE_JOURNAL || path.join(home, ".blockrun/compute-receipts.jsonl"),
    fundingReceiptIds: ids,
    maxCostUsdc: Number(process.env.AGENT_ECONOMY_COMPUTE_MAX_COST_USDC),
    reserveUsdc: Number(process.env.AGENT_ECONOMY_COMPUTE_RESERVE_USDC || 0),
    sessionCapUsdc: Number(process.env.AGENT_ECONOMY_COMPUTE_SESSION_CAP_USDC),
    getBalance,
    transport: paidTransport(account),
    frontierModel,
  });
  server.listen(port, "127.0.0.1", () => console.log(`agent-economy compute proxy on 127.0.0.1:${port}`));
}

function isEntrypoint(argv1) {
  if (!argv1) return false;
  try { return realpathSync.native(fileURLToPath(import.meta.url)) === realpathSync.native(path.resolve(argv1)); }
  catch { return fileURLToPath(import.meta.url) === path.resolve(argv1); }
}

if (isEntrypoint(process.argv[1])) {
  main().catch((error) => { console.error(String(error?.message || error)); process.exitCode = 1; });
}
