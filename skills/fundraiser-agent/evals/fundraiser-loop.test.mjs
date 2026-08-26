import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const dailyPrompt = await readFile(new URL("../prompts/daily.md", import.meta.url), "utf8");
const skill = await readFile(new URL("../SKILL.md", import.meta.url), "utf8");
const productionContext = JSON.parse(await readFile(new URL("../../../.agents/startup-context.json", import.meta.url), "utf8"));
const startupContext = Object.freeze({
  product: Object.freeze({
    name: "Life Manager",
    one_liner: "A personal manager that acts within delegated boundaries and reports evidence.",
    mission: "End suffering for humans and all living beings.",
  }),
  traction: Object.freeze({
    founder_attested_revenue: Object.freeze({ display: "approximately $1,000", source: "founder_attested" }),
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
    ["product.mission", context.product.mission],
    ["traction.founder_attested_revenue.display", context.traction.founder_attested_revenue.display],
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
    const inferredJudgment = field.answerClass === "judgment" && action.provenance === "reasonable_inference";
    if (!inferredJudgment && (!facts.has(action.factId) || facts.get(action.factId) !== action.value)) {
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

test("production contract runs every 30 minutes and maximizes real applications", () => {
  const contract = `${skill}\n${dailyPrompt}`;
  assert.match(contract, /every 30 minutes/i);
  assert.match(contract, /as many[^\n]*applications[^\n]*as possible/i);
  assert.match(contract, /continue[^\n]*after[^\n]*(?:first|one)[^\n]*(?:submit|application)/i);
  assert.match(contract, /authenticated[^\n]*X[^\n]*CDP/i);
  assert.match(contract, /Telegram[^\n]*(?:immediately|real.?time)/i);
  assert.match(contract, /reasonable inference/i);
  assert.match(dailyPrompt, /cdp_tab_gc\.py --owner ai\.anicca\.fundraiser/);
  assert.match(dailyPrompt, /cdp_context_lease\.py acquire ai\.anicca\.fundraiser/);
  assert.match(dailyPrompt, /cdp\.py eval "\$TARGET_ID" -/);
  assert.match(dailyPrompt, /gog gmail send[^\n]*--attach fundraising\/application-kit\/deck\.pdf/);
  assert.match(dailyPrompt, /in:sent to:<recipient>/);
  assert.match(dailyPrompt, /prior `failure` candidates whose recorded local or\s+technical cause has been repaired/);
  assert.match(dailyPrompt, /it has no `screenshot` command/);
  assert.match(dailyPrompt, /never release an application lease until every fill/);
  assert.match(dailyPrompt, /there is no `upload` command/);
  assert.doesNotMatch(contract, /at most one/i);
  assert.doesNotMatch(contract, /per user-local day/i);
});

test("production queue enforces founder geography, format, priority, and YC hold", () => {
  const fundraising = productionContext.fundraising;
  assert.deepEqual(fundraising.geographies, [
    "Tokyo, Japan",
    "United States, with San Francisco Bay Area first",
  ]);
  assert.match(fundraising.format_priority, /in-person/i);
  assert.match(fundraising.explicit_format_exceptions.join("\n"), /Base Batches/i);
  assert.deepEqual(fundraising.priority_queue.slice(0, 2).map((item) => item.program), [
    "Base Batches 004",
    "Open Network Lab Seed Accelerator 32nd Batch",
  ]);
  assert.equal(fundraising.priority_queue.find((item) => item.program === "Y Combinator")?.action, "hold_do_not_submit");
  assert.match(dailyPrompt, /Reject Kenya and every other geography/);
  assert.match(dailyPrompt, /Never submit a `hold_do_not_submit` program/);
});

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

test("two eligible candidates are both submitted in one continuous pass", async () => {
  const candidates = [
    candidate({ organization: "Alpha Fund", program: "Alpha Accelerator", applicationUrl: "https://alpha.example/apply" }),
    candidate({ organization: "Beta Fund", program: "Beta Fellowship", applicationUrl: "https://beta.example/apply" }),
  ];
  const receipts = makeReceipts();
  const results = [];
  for (const current of candidates) {
    const browser = makeBrowser({ applicationUrl: current.applicationUrl, fields: [], readback: { official: true, ref: current.organization } });
    results.push(await runDailyPass({
      discover: async () => [current], receipts, browserFor: () => browser, account: "runtime-account",
      decide: async (input) => input.stage === "qualify" ? input.candidates[0] : { kind: "submit" },
    }));
  }
  assert.deepEqual(results.map((result) => result.status), ["submitted", "submitted"]);
  assert.equal(receipts.rows.filter((row) => row.status === "submitted").length, 2);
});

test("an unfamiliar required judgment uses reasonable inference and still submits", async () => {
  const form = {
    applicationUrl: "https://program.example/apply/fall-2026",
    fields: [{ id: "impact", label: "Long-term impact", required: true, answerClass: "judgment" }],
    readback: { official: true },
  };
  const browser = makeBrowser(form);
  const receipts = makeReceipts();
  const result = await runDailyPass({
    discover: async () => [candidate()], receipts, browserFor: () => browser, account: "runtime-account",
    decide: async (input) => {
      if (input.stage === "qualify") return input.candidates[0];
      if (input.stage === "fill") return {
        kind: "fill", fieldId: input.field.id, value: "End suffering by making dependable agency available.", provenance: "reasonable_inference",
      };
      return { kind: "submit" };
    },
  });
  assert.equal(result.status, "submitted");
  assert.equal(browser.state.submitCount, 1);
});

test("an invented legal registration still blocks before any external effect", async () => {
  const form = {
    applicationUrl: "https://program.example/apply/fall-2026",
    fields: [{ id: "registration", label: "Legal registration number", required: true, answerClass: "exact_fact" }],
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
      if (input.stage === "fill") return { kind: "fill", fieldId: input.field.id, factId: "invented.registration", value: "FAKE-123" };
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
