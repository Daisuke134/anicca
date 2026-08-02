"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const test = require("node:test");

const sha = (value) => createHash("sha256").update(value).digest("hex");
const stable = (value) => {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
};

function previewModule() {
  return require("./yc-full-preview.js");
}

const REQUIRED_SOURCES = Object.freeze({
  readme_en: "repo://README.md",
  readme_ja: "repo://README.ja.md",
  agent_registry: "repo://agents/registry.json",
  provider_manifest: "repo://apps/life-manager/config/yc-application-provider.json",
  answer_draft: "workspace://funders/results/FT-YC/yc-answers-lifemanager-2026fall.json",
  application_kit: "application-kit://KIT.md",
  application_submit_receipt: "repo://docs/evidence/funding/2026-08-02-o1c07-yc-fall-2026-submit.json",
  founder_video_source: "application-kit://videos/Anicca_intro_EN.mp4",
  demo_source: "workspace://funders/assets/life-manager-demo.mp4",
});

function source(role, observedAt = "2026-08-02T05:00:10.000Z") {
  const body = role === "application_submit_receipt"
    ? JSON.stringify({ schema_version: 1, task: "O1C-07", result: "submitted_in_review", draft_id: "0b61fe42-e383-490d-b60e-04f1ad7ec5df", batch: "Fall 2026", effect_confirm_clicks: 1, fresh_home_status: "In review" })
    : `fixture-${role}`;
  return {
    role,
    ref: REQUIRED_SOURCES[role],
    observed_at: observedAt,
    sha256: sha(body),
    bytes: Buffer.byteLength(body),
    body,
  };
}

function fixture() {
  return {
    verified_at: "2026-08-02T05:02:00.000Z",
    application: {
      id: "0b61fe42-e383-490d-b60e-04f1ad7ec5df",
      batch: "Fall 2026",
      state: "In review",
      prior_application_submit_count: 1,
      submission_source_role: "application_submit_receipt",
      origin: "https://apply.ycombinator.com",
      path: "/apps/0b61fe42-e383-490d-b60e-04f1ad7ec5df",
      observed_at: "2026-08-02T05:00:30.000Z",
    },
    sources: Object.keys(REQUIRED_SOURCES).map((role) => source(role)),
    scopes: [
      {
        scope: "company_facts",
        status: "current",
        observed_at: "2026-08-02T05:00:40.000Z",
        source_roles: ["readme_en", "readme_ja", "agent_registry", "answer_draft", "application_kit", "provider_manifest"],
        issue_codes: [],
        observation: { field_count: 20, value_set_digest: sha("company-values") },
      },
      {
        scope: "founder_profile",
        status: "current",
        observed_at: "2026-08-02T05:00:50.000Z",
        source_roles: ["application_kit"],
        issue_codes: [],
        observation: { structurally_complete: true, section_count: 6, value_set_digest: sha("founder-values") },
      },
      {
        scope: "founder_video",
        status: "present",
        observed_at: "2026-08-02T05:01:00.000Z",
        source_roles: ["founder_video_source"],
        issue_codes: [],
        observation: {
          remote: { ready_state: 4, duration_seconds: 57.856667, width: 720, height: 1280, storage_origin: "https://yc-app-vids.s3.us-west-2.amazonaws.com", source_path_sha256: sha("remote-founder-video-path") },
          local: { duration_seconds: 57.835, bytes: source("founder_video_source").bytes, sha256: source("founder_video_source").sha256, container: "mp4", video_codec: "h264", audio_codec: "aac", width: 720, height: 1280 },
        },
      },
      {
        scope: "demo",
        status: "present",
        observed_at: "2026-08-02T05:01:10.000Z",
        source_roles: ["demo_source"],
        issue_codes: [],
        observation: {
          dedicated_source_role: "demo_source",
          remote: { ready_state: 4, duration_seconds: 45.5, width: 1280, height: 720, storage_origin: "https://yc-app-vids.s3.us-west-2.amazonaws.com", source_path_sha256: sha("remote-demo-path") },
        },
      },
      {
        scope: "progress",
        status: "current",
        observed_at: "2026-08-02T05:01:20.000Z",
        source_roles: ["readme_en", "answer_draft", "provider_manifest"],
        issue_codes: [],
        observation: { field_count: 5, value_set_digest: sha("progress-values"), update_control_present: true },
      },
    ],
    assessment: {
      decision_owner: "agent",
      preview_complete: true,
      submit_ready: true,
      blocking_issue_codes: [],
    },
    effects: {
      read_only_navigations: 5,
      owned_page_closes: 5,
      form_field_writes: 0,
      option_selections: 0,
      file_attachments: 0,
      save_controls: 0,
      update_submissions: 0,
      application_submissions: 0,
      browser_closes: 0,
    },
  };
}

function build(input = fixture(), now = "2026-08-02T05:03:00.000Z") {
  return previewModule().buildYcFullPreviewReceipt(input, { now: new Date(now) });
}

function resign(receipt) {
  const copy = structuredClone(receipt);
  delete copy.preview_receipt_digest;
  return { ...copy, preview_receipt_digest: sha(stable(copy)) };
}

test("five current scopes become a frozen privacy-minimal submit-ready preview", () => {
  const receipt = build();
  assert.equal(receipt.schema_version, 1);
  assert.deepEqual(receipt.scopes.map(({ scope }) => scope), ["company_facts", "founder_profile", "founder_video", "demo", "progress"]);
  assert.equal(receipt.preview_complete, true);
  assert.equal(receipt.submit_ready, true);
  assert.match(receipt.preview_receipt_digest, /^[0-9a-f]{64}$/);
  assert.equal(Object.isFrozen(receipt), true);
  assert.equal(Object.isFrozen(receipt.scopes[2].observation.remote), true);
  assert.deepEqual(build(), receipt);
  const serialized = JSON.stringify(receipt);
  for (const forbidden of ["fixture-", "raw_answer", "email", "phone", "birth_date", "authenticity_token", "cookie", "signed_url", "/Users/"]) {
    assert.equal(serialized.includes(forbidden), false, forbidden);
  }
});

test("all five scopes can be completely previewed while blockers close submit readiness", () => {
  const input = fixture();
  input.sources = input.sources.filter(({ role }) => role !== "demo_source");
  input.scopes[0].status = "stale";
  input.scopes[0].issue_codes = ["company_facts_stale", "provider_route_drift"];
  input.scopes[1].status = "needs_review";
  input.scopes[1].issue_codes = ["founder_narratives_stale"];
  input.scopes[3] = {
    scope: "demo",
    status: "missing",
    observed_at: "2026-08-02T05:01:10.000Z",
    source_roles: [],
    issue_codes: ["demo_missing"],
    observation: { dedicated_source_role: null, remote: null },
  };
  input.scopes[4].status = "stale";
  input.scopes[4].issue_codes = ["progress_stale", "provider_route_drift"];
  input.assessment.submit_ready = false;
  input.assessment.blocking_issue_codes = ["company_facts_stale", "provider_route_drift", "founder_narratives_stale", "demo_missing", "progress_stale"];
  const receipt = build(input);
  assert.equal(receipt.preview_complete, true);
  assert.equal(receipt.submit_ready, false);
  assert.deepEqual(receipt.blocking_issue_codes, input.assessment.blocking_issue_codes);
});

test("scope and source sets fail closed on omission, duplication, unknown fields, or bad provenance", () => {
  const cases = [
    (x) => { x.scopes.pop(); },
    (x) => { x.scopes[4].scope = "company_facts"; },
    (x) => { x.scopes[0].scope = "other"; },
    (x) => { x.scopes[0].raw_answer = "secret"; },
    (x) => { x.sources = x.sources.filter(({ role }) => role !== "readme_en"); },
    (x) => { x.sources[1].role = "readme_en"; },
    (x) => { x.sources[0].ref = "file:///Users/private/README.md"; },
    (x) => { x.sources[0].sha256 = "not-a-sha256"; },
    (x) => { x.sources[0].sha256 = sha("valid-but-different-content"); },
    (x) => { x.sources[0].bytes = 0; },
    (x) => { x.sources[0].bytes += 1; },
    (x) => { x.scopes[0].source_roles.push("unknown_source"); },
    (x) => { x.application.id = "99b966b0-7e90-4856-ab0d-93651488a4ea"; },
    (x) => { x.application.state = "Draft"; },
    (x) => { x.application.path += "?token=secret"; },
    (x) => { x.application.submission_source_role = "application_kit"; },
    (x) => { x.application.extra = true; },
  ];
  for (const mutate of cases) {
    const input = fixture();
    mutate(input);
    assert.throws(() => build(input));
  }
});

test("each semantic scope requires its exact source-role set", () => {
  const cases = [
    (x) => { x.scopes[0].source_roles = ["founder_video_source"]; },
    (x) => { x.scopes[1].source_roles = ["provider_manifest"]; },
    (x) => { x.scopes[4].source_roles = ["founder_video_source"]; },
    (x) => { x.scopes[0].source_roles.push("founder_video_source"); },
  ];
  for (const mutate of cases) {
    const input = fixture();
    mutate(input);
    assert.throws(() => build(input));
  }
});

test("prior application submit count is bound to the O1C-07 source body", () => {
  const input = fixture();
  const prior = input.sources.find(({ role }) => role === "application_submit_receipt");
  const forged = JSON.parse(prior.body);
  forged.effect_confirm_clicks = 2;
  prior.body = JSON.stringify(forged);
  prior.sha256 = sha(prior.body);
  prior.bytes = Buffer.byteLength(prior.body);
  assert.throws(() => build(input));
});

test("timestamps must be canonical, fresh, and chronologically bound", () => {
  const cases = [
    [(x) => { x.verified_at = "2026-08-02 05:02:00Z"; }, "2026-08-02T05:03:00.000Z"],
    [(x) => { x.scopes[0].observed_at = "2026-08-02T05:02:01.000Z"; }, "2026-08-02T05:03:00.000Z"],
    [(x) => { x.sources[0].observed_at = "2026-08-02T04:30:00.000Z"; }, "2026-08-02T05:03:00.000Z"],
    [(x) => {}, "2026-08-02T05:08:00.001Z"],
  ];
  for (const [mutate, now] of cases) {
    const input = fixture();
    mutate(input);
    assert.throws(() => build(input, now));
  }
});

test("media presence requires bounded playable remote media and valid dedicated local provenance", () => {
  const cases = [
    (x) => { x.scopes[2].observation.remote.ready_state = 3; },
    (x) => { x.scopes[2].observation.remote.duration_seconds = 60.001; },
    (x) => { x.scopes[2].observation.remote.width = 0; },
    (x) => { x.scopes[2].observation.local.video_codec = "vp9"; },
    (x) => { x.scopes[2].observation.local.audio_codec = "opus"; },
    (x) => { x.scopes[2].observation.local.bytes += 1; },
    (x) => { x.scopes[2].observation.local.sha256 = sha("another-founder-video"); },
    (x) => { x.scopes[2].source_roles = []; },
    (x) => { x.scopes[3].observation.remote = null; },
    (x) => { x.scopes[3].observation.dedicated_source_role = "founder_video_source"; },
    (x) => { x.scopes[3].source_roles = ["founder_video_source"]; },
  ];
  for (const mutate of cases) {
    const input = fixture();
    mutate(input);
    assert.throws(() => build(input));
  }
});

test("demo duration is not subjected to the founder video's 60-second rule", () => {
  const input = fixture();
  input.scopes[3].observation.remote.duration_seconds = 120;
  assert.equal(build(input).scopes[3].observation.remote.duration_seconds, 120);
});

test("agent may classify a reviewed issue as non-blocking without validator semantic override", () => {
  const input = fixture();
  input.scopes[1].status = "needs_review";
  input.scopes[1].issue_codes = ["founder_copy_reviewed_nonblocking"];
  const receipt = build(input);
  assert.equal(receipt.submit_ready, true);
  assert.deepEqual(receipt.blocking_issue_codes, []);
  assert.deepEqual(receipt.scopes[1].issue_codes, ["founder_copy_reviewed_nonblocking"]);
});

test("semantic status and issue bookkeeping cannot contradict readiness", () => {
  const cases = [
    (x) => { x.scopes[0].status = "stale"; },
    (x) => { x.scopes[1].status = "needs_review"; },
    (x) => { x.scopes[3].status = "missing"; },
    (x) => { x.scopes[4].issue_codes = ["progress_stale"]; },
    (x) => { x.assessment.submit_ready = false; },
    (x) => { x.assessment.blocking_issue_codes = ["unbound_issue"]; },
    (x) => { x.assessment.preview_complete = false; },
    (x) => { x.assessment.decision_owner = "validator"; },
  ];
  for (const mutate of cases) {
    const input = fixture();
    mutate(input);
    assert.throws(() => build(input));
  }
});

test("every mutation effect and a second application submission fail closed", () => {
  for (const key of ["form_field_writes", "option_selections", "file_attachments", "save_controls", "update_submissions", "application_submissions", "browser_closes"]) {
    const input = fixture();
    input.effects[key] = 1;
    assert.throws(() => build(input), key);
  }
  for (const prior of [0, 2]) {
    const input = fixture();
    input.application.prior_application_submit_count = prior;
    assert.throws(() => build(input), String(prior));
  }
});

test("receipt digest, closed output structure, and input immutability are enforced", () => {
  const input = fixture();
  const before = structuredClone(input);
  const receipt = build(input);
  assert.deepEqual(input, before);
  const forged = structuredClone(receipt);
  forged.submit_ready = false;
  assert.throws(() => previewModule().validateYcFullPreviewReceiptStructure(forged));
  const resigned = resign(forged);
  assert.throws(() => previewModule().validateYcFullPreviewReceiptStructure(resigned));
  const extra = structuredClone(receipt);
  extra.raw_answers = {};
  assert.throws(() => previewModule().validateYcFullPreviewReceiptStructure(resign(extra)));
});
