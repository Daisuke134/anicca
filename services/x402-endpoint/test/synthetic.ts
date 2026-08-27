// Synthetic E2E test for anicca-x402-endpoint.
// Per spec 09 § 4 G5 + team-lead deliverable #7.
//
// Sanity checks (no on-chain interaction, no real USDC spend):
//   1. GET /health → 200, ok:true, receiver matches Anicca wallet
//   2. GET /v0/echo?text=hello (no payment header) → 402 + challenge JSON
//   3. GET /v0/echo with bogus x-paid-tx-hash → 402 (verify fails for invalid hash)
//   4. POST /v0/learn (no payment header) → 402 + challenge JSON
//
// Exits 0 on full pass, 1 on any failure. Intended for CI + cron heartbeats.

const BASE = process.env.X402_TEST_BASE ?? "http://localhost:8403";
const EXPECTED_RECEIVER = "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21";

interface CaseResult {
  name: string;
  ok: boolean;
  detail: string;
}

const results: CaseResult[] = [];

function record(name: string, ok: boolean, detail: string): void {
  results.push({ name, ok, detail });
  // eslint-disable-next-line no-console
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}  — ${detail}`);
}

async function jsonOr<T>(res: Response): Promise<T | null> {
  try {
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

async function caseHealth(): Promise<void> {
  const res = await fetch(`${BASE}/health`);
  const body = await jsonOr<{ ok?: boolean; receiver?: string; port?: number }>(res);
  const ok =
    res.status === 200 &&
    body?.ok === true &&
    typeof body.receiver === "string" &&
    body.receiver.toLowerCase() === EXPECTED_RECEIVER.toLowerCase();
  record(
    "health/200",
    ok,
    `status=${res.status} receiver=${body?.receiver} port=${body?.port}`
  );
}

async function caseEchoNoPayment(): Promise<void> {
  const res = await fetch(`${BASE}/v0/echo?text=hello`);
  const body = await jsonOr<{ status?: number; challenge?: { price_usdc?: number; nonce?: string; nonce_sig?: string } }>(
    res
  );
  const ok =
    res.status === 402 &&
    body?.status === 402 &&
    typeof body.challenge?.nonce === "string" &&
    typeof body.challenge?.nonce_sig === "string" &&
    body.challenge?.price_usdc === 0.001;
  record(
    "echo/no-payment-402",
    ok,
    `status=${res.status} price=${body?.challenge?.price_usdc} nonce_present=${Boolean(body?.challenge?.nonce)}`
  );
}

async function caseEchoBogusHash(): Promise<void> {
  // 64 hex chars → passes format guard but won't resolve to a real receipt.
  const bogus = "0x" + "de".repeat(32);
  const res = await fetch(`${BASE}/v0/echo?text=hi`, {
    headers: { "x-paid-tx-hash": bogus },
  });
  const body = await jsonOr<{ status?: number; detail?: string }>(res);
  const ok = res.status === 402 && body?.status === 402 && /verification failed/i.test(body?.detail ?? "");
  record(
    "echo/bogus-hash-402",
    ok,
    `status=${res.status} detail=${(body?.detail ?? "").slice(0, 80)}`
  );
}

async function caseLearnNoPayment(): Promise<void> {
  const res = await fetch(`${BASE}/v0/learn`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ topic: "compounding" }),
  });
  const body = await jsonOr<{ status?: number; challenge?: { price_usdc?: number; route_id?: string } }>(res);
  const ok =
    res.status === 402 &&
    body?.status === 402 &&
    body.challenge?.price_usdc === 0.01 &&
    body.challenge?.route_id === "learn";
  record(
    "learn/no-payment-402",
    ok,
    `status=${res.status} price=${body?.challenge?.price_usdc} route_id=${body?.challenge?.route_id}`
  );
}

async function main(): Promise<void> {
  // eslint-disable-next-line no-console
  console.log(`[synthetic] target=${BASE}`);
  try {
    await caseHealth();
    await caseEchoNoPayment();
    await caseEchoBogusHash();
    await caseLearnNoPayment();
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    record("fatal", false, `unexpected error: ${msg}`);
  }

  const passed = results.filter((r) => r.ok).length;
  // eslint-disable-next-line no-console
  console.log(`\n[synthetic] ${passed}/${results.length} passed`);
  if (passed !== results.length) {
    process.exit(1);
  }
  process.exit(0);
}

void main();
