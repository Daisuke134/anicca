import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const dailyPrompt = await readFile(new URL("../prompts/daily.md", import.meta.url), "utf8");
const startupContext = Object.freeze({
  product: Object.freeze({
    name: "Life Manager",
    one_liner: "A personal manager that acts within delegated boundaries and reports evidence.",
  }),
  links: Object.freeze({
    product: Object.freeze({ url: "https://aniccaai.com/lm", status: "verified" }),
    repository: Object.freeze({ url: "https://github.com/Daisuke134/life-manager", status: "verified" }),
  }),
  claims: Object.freeze([
    Object.freeze({ id: "public-repository", statement: "Life Manager is developed in a public repository." }),
  ]),
});

function factIndex(context) {
  return new Map([
    ["product.name", context.product.name],
    ["product.one_liner", context.product.one_liner],
    ["links.product.url", context.links.product.url],
    ["links.repository.url", context.links.repository.url],
    ...context.claims.map((claim) => [`claim:${claim.id}`, claim.statement]),
  ]);
}

function applicationIdentity(candidate, account) {
  return [candidate.organization, candidate.program, candidate.cohort_window, account]
    .map((part) => String(part).trim().toLocaleLowerCase())
    .join("\u001f");
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function makeBrowser(form, submitResult = { kind: "confirmed", receiptRef: "ui-confirmation-1" }) {
  const state = { fields: new Map(), actions: [], submitCount: 0, submitResult };
  const browser = {
    state,
    async observe() {
      return clone({
        url: form.applicationUrl,
        fields: form.fields.map((field) => ({ ...field, value: state.fields.get(field.id) ?? null })),
        submit: { visible: true, enabled: true },
      });
    },
    async fill(field, value) {
      const current = form.fields.find((item) => item.id === field.id);
      if (!current) throw new Error("stale_field");
      state.fields.set(current.id, value);
      state.actions.push({ kind: "fill", fieldId: current.id, label: current.label, value });
      return this.observe();
    },
    async submit() {
      state.submitCount += 1;
      state.actions.push({ kind: "submit" });
      return clone(state.submitResult);
    },
    async readback() {
      return clone(form.readback || null);
    },
  };
  return browser;
}

function makeReceipts(rows = []) {
  const receipts = rows.map((row) => ({ ...row }));
  return {
    rows: receipts,
    has(identity) {
      return receipts.find((row) => row.identity === identity) || null;
    },
    claim(identity) {
      if (this.has(identity)) return false;
      receipts.push({ identity, status: "submit_claimed" });
      return true;
    },
    finalize(identity, status, readback) {
      const row = this.has(identity);
      if (!row) throw new Error("receipt_claim_missing");
      row.status = status;
      row.readback = readback;
    },
  };
}

/**
 * A provider-neutral behavioral harness. The model chooses candidates and field actions;
 * this harness supplies only generic freshness, context, receipt, and one-shot boundaries.
 */
async function runDailyPass({ discover, receipts, browserFor, context = startupContext, account, decide }) {
  const candidates = await discover();
  const candidate = await decide({ stage: "qualify", candidates: clone(candidates), receipts: clone(receipts.rows) });
  const candidateIndex = candidates.findIndex((item) => (
    item?.applicationUrl === candidate?.applicationUrl
    && item?.organization === candidate?.organization
    && item?.program === candidate?.program
    && item?.cohort_window === candidate?.cohort_window
  ));
  if (candidateIndex < 0) return { status: "not_submitted", reason: "candidate_not_from_live_discovery" };
  const selectedCandidate = candidates[candidateIndex];
  if (selectedCandidate.official?.verified !== true || selectedCandidate.official?.eligible !== true) {
    return { status: "not_submitted", reason: "official_eligibility_unverified" };
  }
  const identity = applicationIdentity(selectedCandidate, account);
  const prior = receipts.has(identity);
  if (prior) return { status: "skipped", reason: prior.status === "submit_unknown" ? "submit_unknown_terminal" : "already_applied", identity };

  const browser = browserFor(selectedCandidate);
  let observation = await browser.observe();
  const facts = factIndex(context);
  for (const field of observation.fields) {
    const action = await decide({ stage: "fill", candidate: clone(selectedCandidate), field: clone(field), observation: clone(observation), context: clone(context) });
    if (action?.kind === "stop") return { status: "human_required", reason: action.reason, identity };
    if (action?.kind !== "fill" || action.fieldId !== field.id) {
      if (field.required) return { status: "not_submitted", reason: "required_field_unresolved", field: field.label, identity };
      continue;
    }
    if (field.guard === "human_required") return { status: "human_required", reason: "human_only_field", identity };
    if (!facts.has(action.factId) || facts.get(action.factId) !== action.value) {
      return { status: "not_submitted", reason: "unsupported_claim", field: field.label, identity };
    }
    observation = await browser.fill(field, action.value);
  }
  const final = await decide({ stage: "submit", candidate: clone(selectedCandidate), observation: clone(observation) });
  if (final?.kind !== "submit" || observation.fields.some((field) => field.required && !field.value)) {
    return { status: "not_submitted", reason: "review_not_ready", identity };
  }
  assert.equal(receipts.claim(identity), true, "the submit effect is claimed immediately before the click");
  const outcome = await browser.submit();
  if (outcome.kind === "ambiguous") {
    receipts.finalize(identity, "submit_unknown", await browser.readback());
    return { status: "submit_unknown", identity, submitCount: browser.state.submitCount };
  }
  if (outcome.kind !== "confirmed") {
    receipts.finalize(identity, "not_submitted", await browser.readback());
    return { status: "not_submitted", reason: "submit_failed", identity };
  }
  const readback = await browser.readback();
  if (readback?.official !== true) {
    receipts.finalize(identity, "submit_unknown", readback);
    return { status: "submit_unknown", identity, submitCount: browser.state.submitCount };
  }
  receipts.finalize(identity, "submitted", readback);
  return { status: "submitted", identity, readback, submitCount: browser.state.submitCount };
}

function candidate(overrides = {}) {
  return {
    organization: "Open Program Collective",
    program: "Builder Fellowship",
    cohort_window: "Fall 2026",
    cohort: "Fall 2026",
    applicationUrl: "https://program.example/apply/fall-2026",
    official: { verified: true, eligible: true, deadline: "2026-09-30" },
    ...overrides,
  };
}

function contextPlanner() {
  return async (input) => {
    if (input.stage === "qualify") return input.candidates.find((item) => item.official?.eligible === true);
    if (input.stage === "fill") {
      const byLabel = {
        "Product name": ["product.name", startupContext.product.name],
        "Product summary": ["product.one_liner", startupContext.product.one_liner],
        "Public product URL": ["links.product.url", startupContext.links.product.url],
      };
      const pair = byLabel[input.field.label];
      return pair ? { kind: "fill", fieldId: input.field.id, factId: pair[0], value: pair[1] } : { kind: "skip" };
    }
    return { kind: "submit" };
  };
}

test("unseen rendered fields are filled from startup context and read back after one submit", async () => {
  assert.ok(dailyPrompt.trim().length > 200);
  const form = {
    applicationUrl: "https://program.example/apply/fall-2026",
    fields: [
      { id: "question-a", label: "Product summary", required: true },
      { id: "question-b", label: "Product name", required: true },
      { id: "question-c", label: "Public product URL", required: true },
    ],
    readback: { official: true, confirmation: "Application received", ref: "confirmation-42" },
  };
  const browser = makeBrowser(form);
  const receipts = makeReceipts();
  const result = await runDailyPass({
    discover: async () => [candidate()],
    receipts,
    browserFor: () => browser,
    account: "runtime-account",
    decide: contextPlanner(),
  });
  assert.equal(result.status, "submitted");
  assert.equal(result.readback.ref, "confirmation-42");
  assert.equal(browser.state.submitCount, 1);
  assert.deepEqual(browser.state.actions.filter((action) => action.kind === "fill").map((action) => action.label), [
    "Product summary", "Product name", "Public product URL",
  ]);
});

test("an already-applied cohort is skipped before opening its form", async () => {
  const old = candidate({ cohort_window: "Spring 2026", cohort: "Spring 2026", applicationUrl: "https://program.example/apply/spring-2026" });
  const receipts = makeReceipts([{ identity: applicationIdentity(old, "runtime-account"), status: "submitted" }]);
  let opened = false;
  const result = await runDailyPass({
    discover: async () => [old],
    receipts,
    browserFor: () => { opened = true; return makeBrowser({ applicationUrl: old.applicationUrl, fields: [] }); },
    account: "runtime-account",
    decide: async (input) => input.stage === "qualify" ? input.candidates[0] : { kind: "submit" },
  });
  assert.equal(result.reason, "already_applied");
  assert.equal(opened, false);
});

test("a genuinely new cohort remains eligible after an earlier cohort receipt", async () => {
  const old = candidate({ cohort_window: "Spring 2026", cohort: "Spring 2026", applicationUrl: "https://program.example/apply/spring-2026" });
  const fresh = candidate();
  const receipts = makeReceipts([{ identity: applicationIdentity(old, "runtime-account"), status: "submitted" }]);
  const browser = makeBrowser({ applicationUrl: fresh.applicationUrl, fields: [], readback: { official: true } });
  const result = await runDailyPass({
    discover: async () => [old, fresh],
    receipts,
    browserFor: () => browser,
    account: "runtime-account",
    decide: async (input) => input.stage === "qualify" ? input.candidates[1] : { kind: "submit" },
  });
  assert.equal(result.status, "submitted");
  assert.equal(receipts.rows.filter((row) => row.status === "submitted").length, 2);
});

test("a required unsupported claim blocks before any external effect", async () => {
  const form = {
    applicationUrl: "https://program.example/apply/fall-2026",
    fields: [{ id: "revenue", label: "Current annual revenue", required: true }],
    readback: { official: true },
  };
  const browser = makeBrowser(form);
  const receipts = makeReceipts();
  const result = await runDailyPass({
    discover: async () => [candidate()],
    receipts,
    browserFor: () => browser,
    account: "runtime-account",
    decide: async (input) => {
      if (input.stage === "qualify") return input.candidates[0];
      if (input.stage === "fill") return { kind: "fill", fieldId: input.field.id, factId: "invented.revenue", value: "$1M" };
      return { kind: "submit" };
    },
  });
  assert.equal(result.reason, "unsupported_claim");
  assert.equal(browser.state.submitCount, 0);
  assert.equal(receipts.rows.length, 0);
});

test("a human-only field stops the loop before Submit", async () => {
  const form = {
    applicationUrl: "https://program.example/apply/fall-2026",
    fields: [{ id: "video", label: "Founder video", required: true, guard: "human_required" }],
    readback: { official: true },
  };
  const browser = makeBrowser(form);
  const receipts = makeReceipts();
  const result = await runDailyPass({
    discover: async () => [candidate()],
    receipts,
    browserFor: () => browser,
    account: "runtime-account",
    decide: async (input) => {
      if (input.stage === "qualify") return input.candidates[0];
      if (input.stage === "fill") return { kind: "stop", reason: "human_only_field" };
      return { kind: "submit" };
    },
  });
  assert.equal(result.status, "human_required");
  assert.equal(browser.state.submitCount, 0);
  assert.equal(receipts.rows.length, 0);
});

test("ambiguous Submit becomes terminal submit_unknown and is never retried", async () => {
  const form = {
    applicationUrl: "https://program.example/apply/fall-2026",
    fields: [],
    readback: null,
  };
  const browser = makeBrowser(form, { kind: "ambiguous" });
  const receipts = makeReceipts();
  const input = {
    discover: async () => [candidate()],
    receipts,
    browserFor: () => browser,
    account: "runtime-account",
    decide: async (value) => value.stage === "qualify" ? value.candidates[0] : { kind: "submit" },
  };
  const first = await runDailyPass(input);
  const second = await runDailyPass(input);
  assert.equal(first.status, "submit_unknown");
  assert.equal(second.reason, "submit_unknown_terminal");
  assert.equal(browser.state.submitCount, 1);
  assert.equal(receipts.rows[0].status, "submit_unknown");
});
