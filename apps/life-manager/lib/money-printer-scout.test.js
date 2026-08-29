"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const test = require("node:test");

const {
  CAPABILITY,
  LOOP_ID,
  enqueueMoneyPrinterScoutCycle,
  createMoneyPrinterScout,
  createMoneyPrinterScoutLoopAdapter,
} = require("./money-printer-scout.js");

const TENANT = "tenant-a";
const NOW_MS = Date.parse("2026-08-29T08:23:00.000Z");
const WINDOW_MS = 8 * 60 * 60 * 1000;

function jobFor(nowMs = NOW_MS) {
  const windowStart = Math.floor(nowMs / WINDOW_MS) * WINDOW_MS;
  const cycleRef = `money-printer-scout://${TENANT}/${windowStart}`;
  const jobId = `money-printer-scout:${createHash("sha256").update(`${TENANT}\n${windowStart}`, "utf8").digest("hex")}`;
  return {
    tenant_id: TENANT,
    job_id: jobId,
    loop_id: LOOP_ID,
    capability: CAPABILITY,
    effect_class: "none",
    effect_key: null,
    input_refs: { cycle_ref: cycleRef },
    max_attempts: 2,
  };
}

function candidate(sourceUrl, title = "Public paid opportunity") {
  return {
    source_url: sourceUrl,
    title,
    goal_statement: "Build the requested software deliverable.",
    value_minor: "0",
    currency: "USD",
  };
}

function geminiResponse(value) {
  return { ok: true, text: async () => JSON.stringify(value) };
}

function researchResponse(urls, text = "Grounded public listings.") {
  return geminiResponse({
    candidates: [{
      content: { parts: [{ text }] },
      groundingMetadata: { groundingChunks: urls.map((uri) => ({ web: { uri } })) },
    }],
  });
}

test("scout scheduler inserts or reads exactly one deterministic no-effect job per tenant window", async () => {
  const calls = [];
  const query = async (sql, values) => {
    calls.push({ sql, values });
    const window = Number(String(JSON.parse(values[6]).cycle_ref).split("/").at(-1));
    return { rows: [jobFor(window)] };
  };
  const first = await enqueueMoneyPrinterScoutCycle({ query, tenantId: TENANT, nowMs: NOW_MS });
  const replay = await enqueueMoneyPrinterScoutCycle({ query, tenantId: TENANT, nowMs: NOW_MS + 1 });
  const next = await enqueueMoneyPrinterScoutCycle({ query, tenantId: TENANT, nowMs: NOW_MS + WINDOW_MS });

  assert.deepEqual(first, jobFor());
  assert.deepEqual(replay, jobFor());
  assert.notEqual(next.job_id, first.job_id);
  assert.equal(calls.length, 3);
  assert.match(calls[0].sql, /WITH inserted AS[\s\S]+INSERT INTO public\.lm_runtime_jobs/i);
  assert.match(calls[0].sql, /ON CONFLICT \(job_id\) DO NOTHING/i);
  assert.match(calls[0].sql, /SELECT \* FROM public\.lm_runtime_jobs/i);
  assert.deepEqual(calls[0].values, [
    first.tenant_id, first.job_id, first.loop_id, first.capability,
    first.effect_class, first.effect_key, JSON.stringify(first.input_refs), first.max_attempts,
  ]);
  assert.equal(calls[2].values[1], jobFor(NOW_MS + WINDOW_MS).job_id);
});

test("scout scheduler rejects unsafe interval or mismatched durable readback", async () => {
  for (const intervalMs of [299999, 86400001, 1.5, "28800000"]) {
    await assert.rejects(
      enqueueMoneyPrinterScoutCycle({ query: async () => ({ rows: [jobFor()] }), tenantId: TENANT, nowMs: NOW_MS, intervalMs }),
      /interval/i,
    );
  }
  await assert.rejects(
    enqueueMoneyPrinterScoutCycle({
      query: async () => ({ rows: [{ ...jobFor(), capability: "other" }] }), tenantId: TENANT, nowMs: NOW_MS,
    }),
    /readback/i,
  );
});

test("scout uses two Gemini stages, canonical URL dedupe, and safe durable receipt refs", async () => {
  const created = [];
  const reads = [];
  const requests = [];
  const runScout = createMoneyPrinterScout({
    apiKey: "test-gemini-key",
    fetchImpl: async (_url, options) => {
      requests.push(JSON.parse(options.body));
      if (requests.length === 1) return researchResponse([
        "https://example.com/work", "https://fresh.example/paid-work",
      ], "Grounded public listings with metadata.");
      return geminiResponse({
        candidates: [{ content: { parts: [{ text: JSON.stringify({ candidates: [
          candidate("https://Example.com:443/work#tracking"),
          candidate("https://example.com/work", "Duplicate URL"),
          candidate("https://fresh.example/paid-work", "Fresh public work"),
        ] }) }] } }],
      });
    },
    now: () => "2026-08-29T08:23:00.000Z",
    readOpportunityBySource: async (input) => {
      reads.push(input);
      return input.source_url === "https://example.com/work"
        ? { uid: TENANT, source_url: input.source_url } : null;
    },
    createOpportunity: async (row) => {
      created.push(row);
      return { ...row, uid: TENANT };
    },
  });
  const receipt = await runScout(jobFor());

  assert.equal(requests.length, 2);
  assert.deepEqual(requests[0].tools, [{ google_search: {} }]);
  assert.equal(requests[1].generationConfig.responseMimeType, "application/json");
  assert.deepEqual(requests[1].generationConfig.thinkingConfig, { thinkingBudget: 0 });
  assert.match(requests[1].contents[0].parts[0].text, /https:\/\/example\.com\/work/);
  assert.equal(reads.length, 2);
  assert.equal(created.length, 1);
  assert.equal(created[0].source_url, "https://fresh.example/paid-work");
  assert.deepEqual(Object.keys(receipt).sort(), [
    "created_count", "cycle_ref", "deduped_count", "discovered_count", "job_id", "kind", "opportunity_refs", "status", "tenant_id",
  ]);
  assert.deepEqual(receipt, {
    kind: "money_printer_scout", status: "completed", tenant_id: TENANT,
    job_id: jobFor().job_id, cycle_ref: jobFor().input_refs.cycle_ref,
    discovered_count: 2, created_count: 1, deduped_count: 1,
    opportunity_refs: [`opportunity://${TENANT}/${created[0].opportunity_id}`],
  });
  assert.doesNotMatch(JSON.stringify(receipt), /Grounded public listings|groundingMetadata|test-gemini-key/i);
});

test("scout rejects model-shaped data before durable writes and adapter verifies exact scope", async () => {
  let writes = 0;
  const runScout = createMoneyPrinterScout({
    apiKey: "test-gemini-key",
    fetchImpl: async (_url, options) => {
      const body = JSON.parse(options.body);
      return body.tools ? researchResponse(["https://bad.example/work"], "Research")
        : geminiResponse({ candidates: [{ content: { parts: [{ text: JSON.stringify({ candidates: [{
          ...candidate("https://bad.example/work"), extra: "no",
        }] }) }] } }] });
    },
    readOpportunityBySource: async () => null,
    createOpportunity: async () => { writes += 1; },
  });
  await assert.rejects(runScout(jobFor()), /response|candidate|invalid/i);
  assert.equal(writes, 0);

  const adapter = createMoneyPrinterScoutLoopAdapter({ runScout: async () => ({
    kind: "money_printer_scout", status: "completed", tenant_id: TENANT,
    job_id: jobFor().job_id, cycle_ref: jobFor().input_refs.cycle_ref,
    discovered_count: 1, created_count: 1, deduped_count: 0,
    opportunity_refs: [`opportunity://${TENANT}/${"a".repeat(64)}`],
  }) });
  const execution = await adapter.execute(jobFor());
  assert.equal(adapter.verify(execution.receipt, jobFor()), true);
  assert.deepEqual(await adapter.reconcile(), { state: "unknown" });
  assert.deepEqual(adapter.report(execution.receipt), { discovered_count: 1, created_count: 1, deduped_count: 0 });
  assert.equal(adapter.verify({ ...execution.receipt, tenant_id: "tenant-b" }, jobFor()), false);
});

test("configured scout tenant rejects a foreign expected job before cloud or runtime access", async () => {
  let calls = 0;
  const runScout = createMoneyPrinterScout({
    tenantId: TENANT,
    apiKey: "test-gemini-key",
    fetchImpl: async () => { calls += 1; return geminiResponse({}); },
    readOpportunityBySource: async () => { calls += 1; return null; },
    createOpportunity: async () => { calls += 1; },
  });
  await assert.rejects(runScout({ ...jobFor(), tenant_id: "tenant-b" }), /tenant/i);
  assert.equal(calls, 0);
});

test("scout bounds both Gemini requests with its configured shared deadline", async () => {
  const budgets = [];
  const clockValues = [0, 0, 400];
  const runScout = createMoneyPrinterScout({
    apiKey: "test-gemini-key", timeoutMs: 1_000,
    clock: () => clockValues.shift() ?? 400,
    abortSignalTimeout: (milliseconds) => {
      budgets.push(milliseconds);
      return AbortSignal.timeout(milliseconds);
    },
    fetchImpl: async (_url, options) => {
      return budgets.length === 1
        ? researchResponse(["https://allowed.example/work"], "Research")
        : geminiResponse({ candidates: [{ content: { parts: [{ text: '{"candidates":[]}' }] } }] });
    },
    readOpportunityBySource: async () => null,
    createOpportunity: async () => { throw new Error("unexpected write"); },
  });
  await runScout(jobFor());
  assert.deepEqual(budgets, [1_000, 600]);
  for (const timeoutMs of [999, 180001, 1.5, "1000"]) {
    assert.throws(() => createMoneyPrinterScout({
      apiKey: "test-gemini-key", timeoutMs,
      fetchImpl: async () => {}, readOpportunityBySource: async () => null, createOpportunity: async () => {},
    }), /timeout/i);
  }
});

test("scout resolves Gemini grounding redirects and permits only the resolved public source", async () => {
  const calls = [];
  const created = [];
  const groundingRedirect = "https://vertexaisearch.cloud.google.com/grounding-api-redirect/opaque";
  const runScout = createMoneyPrinterScout({
    apiKey: "test-gemini-key",
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      if (options.redirect === "manual") {
        return { status: 302, headers: new Headers({ location: "https://openai.com/careers/search/" }) };
      }
      return calls.filter((call) => !call.options.redirect).length === 1
        ? researchResponse([groundingRedirect], "Redirect-backed listing")
        : geminiResponse({ candidates: [{ content: { parts: [{ text: JSON.stringify({ candidates: [
          candidate("https://openai.com/careers/search/"),
        ] }) }] } }] });
    },
    readOpportunityBySource: async () => null,
    createOpportunity: async (row) => { created.push(row); return { ...row, uid: TENANT }; },
  });
  const receipt = await runScout(jobFor());
  const redirect = calls.find((call) => call.options.redirect === "manual");
  assert.equal(redirect.url, groundingRedirect);
  assert.equal(created[0].source_url, "https://openai.com/careers/search/");
  assert.equal(receipt.created_count, 1);
  assert.doesNotMatch(JSON.stringify(receipt), /vertexaisearch|opaque/i);
  const extraction = calls.at(-1);
  assert.match(JSON.parse(extraction.options.body).contents[0].parts[0].text, /https:\/\/openai\.com\/careers\/search\//);
});

test("scout rejects missing or ungrounded sources before runtime writes", async () => {
  let writes = 0;
  const runScout = createMoneyPrinterScout({
    apiKey: "test-gemini-key",
    fetchImpl: async (_url, options) => JSON.parse(options.body).tools
      ? researchResponse(["https://allowed.example/work"], "Grounded")
      : geminiResponse({ candidates: [{ content: { parts: [{ text: JSON.stringify({ candidates: [
        candidate("https://ungrounded.example/work"),
      ] }) }] } }] }),
    readOpportunityBySource: async () => { writes += 1; return null; },
    createOpportunity: async () => { writes += 1; },
  });
  await assert.rejects(runScout(jobFor()), /source|candidate|invalid/i);
  assert.equal(writes, 0);
  const noGrounding = createMoneyPrinterScout({
    apiKey: "test-gemini-key",
    fetchImpl: async () => geminiResponse({ candidates: [{ content: { parts: [{ text: "No chunks" }] } }] }),
    readOpportunityBySource: async () => { writes += 1; return null; },
    createOpportunity: async () => { writes += 1; },
  });
  await assert.rejects(noGrounding(jobFor()), /ground|research|invalid/i);
  assert.equal(writes, 0);
});
