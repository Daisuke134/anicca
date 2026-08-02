"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const {
  buildYcCurrentProgramFactsReceipt,
  projectYcCurrentFactsIntoLegacy,
  validateYcCurrentProgramFactsManifestStructure,
} = require("./yc-current-program-facts.js");

const sha = (value) => createHash("sha256").update(value).digest("hex");
const stable = (value) => {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
};
const resign = (value) => {
  const copy = structuredClone(value);
  delete copy.fact_receipt_digest;
  return { ...copy, fact_receipt_digest: sha(stable(copy)) };
};

function fixture() {
  const applyBody = [
    "Current program: Autumn Lab 2099.",
    "The program runs from September to November at Moon Base.",
    "The on-time deadline was September 9 at 5pm PT, but we are still accepting late applications.",
    "Submit your [application online](https://apply.ycombinator.com/home).",
  ].join("\n");
  const dealBody = [
    "We invest $900,000 in every accepted company.",
    "$200,000 converts into a fixed 8% of the company.",
    "The other $700,000 is invested on an uncapped MFN safe.",
  ].join("\n");
  const applyExcerpt = "Current program: Autumn Lab 2099.\nThe program runs from September to November at Moon Base.";
  const deadlineExcerpt = "The on-time deadline was September 9 at 5pm PT, but we are still accepting late applications.";
  const applicationExcerpt = "Submit your [application online](https://apply.ycombinator.com/home).";
  const investmentExcerpt = dealBody;
  return {
    legacy_config_id: "yc-w26",
    verified_at: "2099-09-10T00:02:00.000Z",
    sources: [
      {
        role: "apply",
        official_url: "https://www.ycombinator.com/apply",
        retrieval_url: "https://r.jina.ai/https://www.ycombinator.com/apply",
        observed_at: "2099-09-10T00:00:00.000Z",
        body: applyBody,
        body_sha256: sha(applyBody),
        body_length: Buffer.byteLength(applyBody),
        links: ["https://www.ycombinator.com/faq", "https://apply.ycombinator.com/home"],
      },
      {
        role: "deal",
        official_url: "https://www.ycombinator.com/deal",
        retrieval_url: "https://r.jina.ai/https://www.ycombinator.com/deal",
        observed_at: "2099-09-10T00:00:30.000Z",
        body: dealBody,
        body_sha256: sha(dealBody),
        body_length: Buffer.byteLength(dealBody),
        links: ["https://www.ycombinator.com/about"],
      },
    ],
    assessment: {
      decision_owner: "agent",
      program_id: "yc-autumn-lab-2099",
      program_name: "Y Combinator Autumn Lab 2099",
      batch: {
        label: "Autumn Lab 2099",
        starts_month: "2099-09",
        ends_month: "2099-11",
        location: "Moon Base",
        source_role: "apply",
        evidence_excerpt: applyExcerpt,
        selected_texts: ["Autumn Lab 2099", "September", "November", "Moon Base"],
      },
      deadline: {
        status: "late_applications_open",
        display: "September 9 at 5pm PT",
        on_time_at: "2099-09-10T00:00:00.000Z",
        timezone: "America/Los_Angeles",
        late_applications_open: true,
        compatibility_deadline_kind: "rolling",
        compatibility_next_deadline: null,
        source_role: "apply",
        evidence_excerpt: deadlineExcerpt,
        selected_texts: ["September 9 at 5pm PT", "still accepting late applications"],
      },
      application: {
        url: "https://apply.ycombinator.com/home",
        source_role: "apply",
        evidence_excerpt: applicationExcerpt,
        selected_texts: ["https://apply.ycombinator.com/home"],
      },
      investment: {
        currency: "USD",
        total_amount: 900000,
        fixed_safe_amount: 200000,
        fixed_equity_percent: 8,
        mfn_safe_amount: 700000,
        mfn_uncapped: true,
        most_favored_nation: true,
        source_role: "deal",
        evidence_excerpt: investmentExcerpt,
        selected_texts: ["$900,000", "$200,000", "8%", "$700,000", "uncapped", "MFN"],
      },
      rationale: "The complete Apply and Deal surfaces identify one current program and one standard investment structure.",
    },
    effects: {
      read_operations: 4,
      write_operations: 0,
      submit_operations: 0,
    },
  };
}

function build(input = fixture(), now = "2099-09-10T00:03:00.000Z") {
  return buildYcCurrentProgramFactsReceipt(input, { now: new Date(now) });
}

test("agent-owned official facts become a closed privacy-minimal current-program receipt", () => {
  const receipt = build();
  assert.equal(receipt.schema_version, 1);
  assert.equal(receipt.legacy_config_id, "yc-w26");
  assert.equal(receipt.program_id, "yc-autumn-lab-2099");
  assert.equal(receipt.program_name, "Y Combinator Autumn Lab 2099");
  assert.deepEqual(receipt.batch, {
    label: "Autumn Lab 2099",
    starts_month: "2099-09",
    ends_month: "2099-11",
    location: "Moon Base",
  });
  assert.deepEqual(receipt.deadline, {
    status: "late_applications_open",
    display: "September 9 at 5pm PT",
    on_time_at: "2099-09-10T00:00:00.000Z",
    timezone: "America/Los_Angeles",
    late_applications_open: true,
    compatibility_deadline_kind: "rolling",
    compatibility_next_deadline: null,
  });
  assert.equal(receipt.application_url, "https://apply.ycombinator.com/home");
  assert.deepEqual(receipt.investment, {
    currency: "USD",
    total_amount: 900000,
    fixed_safe_amount: 200000,
    fixed_equity_percent: 8,
    mfn_safe_amount: 700000,
    mfn_uncapped: true,
    most_favored_nation: true,
  });
  assert.deepEqual(receipt.source_receipts.map(({ role }) => role), ["apply", "deal"]);
  assert.match(receipt.fact_receipt_digest, /^[0-9a-f]{64}$/);
  assert.equal(Object.isFrozen(receipt), true);
  assert.equal(Object.isFrozen(receipt.investment), true);
  const serialized = JSON.stringify(receipt);
  for (const forbidden of [
    "Current program:",
    "The complete Apply",
    "evidence_excerpt",
    "selected_texts",
    "body\"",
    "cookie",
    "header",
    "application_id",
  ]) assert.equal(serialized.includes(forbidden), false, forbidden);
  assert.deepEqual(build(), receipt);
});

test("source provenance, bytes, roles, and observed application link fail closed on substitution", () => {
  const cases = [
    (x) => { x.sources.pop(); },
    (x) => { x.sources[1].role = "apply"; },
    (x) => { x.sources[0].official_url = "https://evil.example/apply"; },
    (x) => { x.sources[0].official_url = "https://www.ycombinator.com/apply?copy=1"; },
    (x) => { x.sources[0].retrieval_url = "https://r.jina.ai/http://www.ycombinator.com/apply"; },
    (x) => { x.sources[0].body += " changed"; },
    (x) => { x.sources[0].body_length += 1; },
    (x) => { x.sources[0].links = ["https://www.ycombinator.com/faq"]; },
    (x) => { x.sources[0].links.push("https://apply.ycombinator.com/home?copy=1"); x.sources[0].links = x.sources[0].links.slice(-1); },
    (x) => { x.sources[0].raw_headers = { authorization: "secret" }; },
  ];
  for (const mutate of cases) {
    const input = fixture();
    mutate(input);
    assert.throws(() => build(input));
  }
});

test("agent selections must be source-bound while semantic normalized values remain agent-owned", () => {
  const cases = [
    (x) => { x.assessment.batch.evidence_excerpt = "not on the official surface"; },
    (x) => { x.assessment.batch.selected_texts[0] = "Spring Lab 2099"; },
    (x) => { x.assessment.batch.source_role = "deal"; },
    (x) => { x.assessment.deadline.selected_texts[1] = "late applications are closed"; },
    (x) => { x.assessment.application.evidence_excerpt = "Apply elsewhere at https://apply.ycombinator.com/home."; },
    (x) => { x.assessment.application.source_role = "deal"; },
    (x) => { x.assessment.investment.selected_texts[0] = "$500,000"; },
    (x) => { x.assessment.investment.source_role = "apply"; },
    (x) => { x.assessment.decision_owner = "regex"; },
  ];
  for (const mutate of cases) {
    const input = fixture();
    mutate(input);
    assert.throws(() => build(input));
  }
  const agentOwned = fixture();
  agentOwned.assessment.program_name = "YC Experimental Autumn Lab";
  agentOwned.assessment.deadline.status = "agent_interpreted_late_window";
  agentOwned.assessment.investment.mfn_uncapped = false;
  agentOwned.assessment.investment.most_favored_nation = false;
  assert.equal(build(agentOwned).program_name, "YC Experimental Autumn Lab");
  assert.equal(build(agentOwned).deadline.status, "agent_interpreted_late_window");
  assert.equal(build(agentOwned).investment.mfn_uncapped, false);
  assert.equal(build(agentOwned).investment.most_favored_nation, false);
});

test("chronology, receipt freshness, offset deadline, amount arithmetic, and zero effects are enforced", () => {
  const cases = [
    (x) => { x.sources[0].observed_at = "2099-09-10T00:03:00.000Z"; },
    (x) => { x.sources[0].observed_at = "2099-09-10T00:00:00"; },
    (x) => { x.verified_at = "2099-09-10T00:02:00"; },
    (x) => { x.sources[1].observed_at = "2099-09-10T00:16:00.001Z"; },
    (x) => { x.sources[0].observed_at = "2099-09-09T23:40:00.000Z"; x.sources[1].observed_at = "2099-09-09T23:40:30.000Z"; },
    (x) => { x.assessment.deadline.on_time_at = "2099-09-10T00:00:00"; },
    (x) => { x.assessment.investment.total_amount = 900000.5; },
    (x) => { x.assessment.investment.total_amount = -900000; },
    (x) => { x.assessment.investment.mfn_safe_amount = 699999; },
    (x) => { x.assessment.investment.fixed_equity_percent = 0; },
    (x) => { x.effects.write_operations = 1; },
    (x) => { x.effects.submit_operations = 1; },
    (x) => { x.effects.browser_operations = 0; },
  ];
  for (const mutate of cases) {
    const input = fixture();
    mutate(input);
    assert.throws(() => build(input));
  }
  assert.throws(() => build(fixture(), "2099-09-10T00:07:00.001Z"), /fresh/i);
});

test("unknown nested fields and malformed normalized fact values are rejected", () => {
  const cases = [
    (x) => { x.extra = true; },
    (x) => { x.assessment.extra = true; },
    (x) => { x.assessment.batch.extra = true; },
    (x) => { x.assessment.deadline.extra = true; },
    (x) => { x.assessment.application.extra = true; },
    (x) => { x.assessment.investment.extra = true; },
    (x) => { x.assessment.program_id = "x"; },
    (x) => { x.assessment.batch.starts_month = "September 2099"; },
    (x) => { x.assessment.batch.ends_month = "2099-9"; },
    (x) => { x.assessment.investment.currency = "US dollars"; },
    (x) => { x.legacy_config_id = "yc-other"; },
    (x) => { x.assessment.deadline.compatibility_next_deadline = "2099-99-99"; },
    (x) => { x.assessment.deadline.compatibility_deadline_kind = "late_open"; },
    (x) => { x.assessment.rationale = " "; },
  ];
  for (const mutate of cases) {
    const input = fixture();
    mutate(input);
    assert.throws(() => build(input));
  }
});

function legacyFixture() {
  return {
    id: "yc-w26",
    name: "Y Combinator W26 Batch",
    url: "https://old.example/apply",
    verified: true,
    deadline_kind: "biannual",
    next_deadline: "2099-12-31",
    funder_type: "accelerator",
    currency: "USD",
    amount_range: { min: 100, max: 200 },
    equity_pct: 8,
    auth: {
      kind: "session_cookie",
      login_url: "https://account.ycombinator.com/",
      profile_dir: "~/.deprecated-profile",
    },
    draft_resolution: {
      strategy: "continue_or_start",
      home_url: "https://apply.ycombinator.com/home",
    },
    pages: [{ name: "main", fields: [{ name: "make", value_source: "config.answer" }] }],
    submit: { button_text: "Submit application" },
    config: { answer: "An old company answer must remain byte-equivalent." },
  };
}

test("current facts project into only the closed legacy paths", () => {
  const legacy = legacyFixture();
  const before = structuredClone(legacy);
  const receipt = build();
  const result = projectYcCurrentFactsIntoLegacy(legacy, receipt);
  assert.deepEqual(legacy, before);
  assert.equal(result.before_non_fact_digest, result.after_non_fact_digest);
  assert.deepEqual(result.changed_paths, [
    "application_url",
    "amount_range",
    "current_batch",
    "deadline",
    "deadline_kind",
    "fact_receipt_digest",
    "fact_sources",
    "facts_verified_at",
    "name",
    "next_deadline",
    "official_url",
    "standard_deal",
    "url",
  ]);
  assert.equal(result.projected.id, "yc-w26");
  assert.equal(result.projected.name, "Y Combinator Autumn Lab 2099");
  assert.equal(result.projected.url, "https://apply.ycombinator.com/home");
  assert.equal(result.projected.deadline_kind, "rolling");
  assert.equal(result.projected.next_deadline, null);
  assert.deepEqual(result.projected.amount_range, { min: 900000, max: 900000 });
  assert.deepEqual(result.projected.current_batch, receipt.batch);
  assert.deepEqual(result.projected.deadline, receipt.deadline);
  assert.deepEqual(result.projected.standard_deal, receipt.investment);
  assert.deepEqual(result.projected.pages, before.pages);
  assert.deepEqual(result.projected.auth, before.auth);
  assert.deepEqual(result.projected.config, before.config);
  assert.deepEqual(result.projected.submit, before.submit);
  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(result.projected.config), true);
  assert.throws(() => { result.projected.config.answer = "drift"; }, /read only|Cannot assign/i);
});

test("legacy projection rejects wrong identity and forged receipt while preserving inputs", () => {
  const validReceipt = build();
  const cases = [
    { legacy: { ...legacyFixture(), id: "yc-other" }, receipt: validReceipt },
    { legacy: { ...legacyFixture(), currency: "JPY" }, receipt: validReceipt },
    { legacy: { ...legacyFixture(), equity_pct: 7 }, receipt: validReceipt },
    { legacy: legacyFixture(), receipt: JSON.parse(JSON.stringify(validReceipt)) },
    { legacy: legacyFixture(), receipt: { ...validReceipt, program_name: "forged" } },
    { legacy: legacyFixture(), receipt: { ...validReceipt, extra: true } },
    { legacy: legacyFixture(), receipt: { ...validReceipt, investment: { ...validReceipt.investment, total_amount: 1 } } },
  ];
  for (const item of cases) {
    const beforeLegacy = structuredClone(item.legacy);
    const beforeReceipt = structuredClone(item.receipt);
    assert.throws(() => projectYcCurrentFactsIntoLegacy(item.legacy, item.receipt));
    assert.deepEqual(item.legacy, beforeLegacy);
    assert.deepEqual(item.receipt, beforeReceipt);
  }
});

test("checked-in yc-w26 manifest validates and carries only current public program facts", () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, "../config/yc-w26.json"), "utf8"));
  assert.equal(validateYcCurrentProgramFactsManifestStructure(manifest), true);
  assert.equal(manifest.program_id, "yc-fall-2026");
  assert.equal(manifest.batch.label, "Fall 2026");
  assert.equal(manifest.deadline.status, "late_applications_open");
  assert.equal(manifest.investment.total_amount, 500000);
  assert.equal(manifest.application_url, "https://apply.ycombinator.com/home");
  for (const forbidden of ["company_name", "founder", "traction", "media_path", "profile_dir", "selector", "submit"]) {
    assert.equal(Object.hasOwn(manifest, forbidden), false, forbidden);
  }
  assert.equal(manifest.effects.submit_operations, 0);
  const malformed = [
    (x) => { x.legacy_config_id = "yc-other"; },
    (x) => { x.source_receipts[0].body_length = 2_000_001; },
    (x) => { x.source_receipts[0].link_count = 301; },
    (x) => { x.assessment_proof.selected_text_sha256.batch = Array(13).fill("a".repeat(64)); },
    (x) => { x.effects.read_operations = 21; },
    (x) => { x.deadline.compatibility_deadline_kind = "late_open"; },
    (x) => { x.verified_at = "2026-08-02T00:08:58"; },
    (x) => { x.source_receipts[0].observed_at = "2026-08-02T00:08:57"; },
  ];
  for (const mutate of malformed) {
    const copy = structuredClone(manifest);
    mutate(copy);
    assert.throws(() => validateYcCurrentProgramFactsManifestStructure(resign(copy)));
  }
});
