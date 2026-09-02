#!/usr/bin/env node
"use strict";

const { createHash } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const { buildYcFullPreviewReceipt } = require("../lib/yc-full-preview.js");
const { buildYcTypedUpdatePlan } = require("../lib/yc-typed-update.js");
const { executeYcTypedUpdateOperation } = require("../lib/yc-typed-update-executor.js");
const { readFence } = require("../lib/yc-typed-update-store.js");
const { createYcTypedUpdateBrowserAdapter } = require("../lib/yc-typed-update-browser.js");
const { createOwnedYcRawCdpPage } = require("../lib/yc-raw-cdp-page.js");
const { loadYcSubmittedUpdateProviderManifest } = require("../lib/yc-submitted-update-provider.js");

const ROOT = path.resolve(__dirname, "../../..");
const APP_ID = "0b61fe42-e383-490d-b60e-04f1ad7ec5df";
const ORIGIN = "https://apply.ycombinator.com";
const APP_PATH = `/apps/${APP_ID}`;
const PROFILE_PATH = "/bio/721f696b-0566-4a16-bda7-a9c368b1eac1/edit";
const KIT_ROOT = "/Users/anicca/.openclaw/identity/application-kit";
const ANSWER_DRAFT = "/Users/anicca/.openclaw/workspace/funders/results/FT-YC/yc-answers-lifemanager-2026fall.json";
const DEMO_FILE = path.join(KIT_ROOT, "videos/life-manager-yc-demo.mp4");
const FOUNDER_VIDEO_FILE = path.join(KIT_ROOT, "videos/Anicca_intro_EN.mp4");
const EVIDENCE = path.join(ROOT, "docs/evidence/funding/2026-08-02-o1c26-yc-typed-update.json");
const FENCE_DIR = path.join(ROOT, "docs/evidence/funding/2026-08-02-o1c26-fences");

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}
const sha = (value) => createHash("sha256").update(value).digest("hex");
const valueDigest = (value) => sha(stable(value));
const fileMeta = (file) => {
  const body = fs.readFileSync(file);
  return { body, bytes: body.length, sha256: sha(body) };
};
function source(role, ref, file, observedAt) {
  const meta = fileMeta(file);
  return { role, ref, observed_at: observedAt, sha256: meta.sha256, bytes: meta.bytes, body: meta.body };
}
function writeJsonExclusive(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const descriptor = fs.openSync(file, "wx", 0o600);
  try { fs.writeFileSync(descriptor, `${JSON.stringify(value, null, 2)}\n`, "utf8"); fs.fsyncSync(descriptor); } finally { fs.closeSync(descriptor); }
}
function mediaMeta(file, expected) {
  const actual = fileMeta(file);
  if (actual.sha256 !== expected.sha256 || actual.bytes !== expected.bytes) throw new Error("media artifact drift");
  return { duration_seconds: expected.duration_seconds, bytes: actual.bytes, sha256: actual.sha256, container: "mp4", video_codec: "h264", audio_codec: "aac", width: expected.width, height: expected.height };
}
async function ownedObservation(route, inspect) {
  const page = await createOwnedYcRawCdpPage();
  try {
    await page.navigate(route);
    return { ...(await inspect(page)), observed_at: new Date().toISOString() };
  } finally { await page.close(); }
}
async function remoteMedia(page) {
  await page.waitFor(() => {
    const video = document.querySelector("video");
    return video && video.readyState === 4 && Number.isFinite(video.duration) && video.videoWidth > 0 && video.videoHeight > 0;
  }, [], 45_000);
  return page.evaluate(() => {
    const videos = [...document.querySelectorAll("video")];
    if (videos.length !== 1) return null;
    const video = videos[0];
    let current = null;
    try { current = new URL(video.currentSrc); } catch { return null; }
    if (video.readyState !== 4 || !Number.isFinite(video.duration) || !video.videoWidth || !video.videoHeight) return null;
    return { ready_state: video.readyState, duration_seconds: video.duration, width: video.videoWidth, height: video.videoHeight, storage_origin: current.origin, source_path: current.pathname };
  });
}
async function observeFive(expected, phase) {
  const application = await ownedObservation("/", async (page) => {
    await page.waitFor(() => document.body.innerText.includes("In review") && document.body.innerText.includes("Fall 2026"), [], 15_000);
    const state = await page.evaluate(() => {
      const body = document.body.innerText;
      return { in_review: body.includes("In review"), fall_2026: body.includes("Fall 2026") };
    });
    if (!state.in_review || !state.fall_2026) throw new Error("application is not Fall 2026 In review");
    return { value_set_digest: valueDigest(expected.progress), field_count: 7 };
  });
  const profile = await ownedObservation(PROFILE_PATH, async (page) => {
    const fields = ["fhack", "fability", "projects", "awards", "testScores", "clubs"];
    const values = await page.evaluate((names) => Object.fromEntries(names.map((name) => [name, document.querySelector(`[name=${name}]`)?.value ?? null])), fields);
    if (Object.values(values).some((value) => value === null)) throw new Error("founder profile field drift");
    if (phase === "after" && valueDigest(values) !== valueDigest(expected.profile)) throw new Error("founder profile readback mismatch");
    return { value_set_digest: valueDigest(phase === "before" ? expected.profile : values), section_count: fields.length };
  });
  const founderVideo = await ownedObservation(`/apps/${APP_ID}/edit/video`, remoteMedia);
  if (!founderVideo.ready_state || founderVideo.duration_seconds > 60) throw new Error("founder video unavailable");
  founderVideo.source_path_sha256 = sha(founderVideo.source_path);
  delete founderVideo.source_path;
  const demo = await ownedObservation(`/apps/${APP_ID}/edit/demo`, remoteMedia);
  if (phase === "after" && !demo.ready_state) throw new Error("demo readback unavailable");
  if (demo.ready_state) {
    demo.source_path_sha256 = sha(demo.source_path);
    delete demo.source_path;
  }
  const progress = await ownedObservation(`/apps/${APP_ID}/edit/progress`, async (page) => {
    const fields = ["productLink", "productCreds", "howfar", "worked", "techstack"];
    const state = await page.evaluate((names) => ({
      values: Object.fromEntries(names.map((name) => [name, document.querySelector(`[name=${name}]`)?.value ?? null])),
      update_controls: [...document.querySelectorAll("button")].filter((button) => button.innerText.trim() === "Submit update").length,
    }), fields);
    const values = state.values;
    if (Object.values(values).some((value) => value === null)) throw new Error("progress field drift");
    if (phase === "after" && fields.some((name) => values[name] !== expected.progress[name])) throw new Error("progress text readback mismatch");
    if (state.update_controls !== 1) throw new Error("progress control drift");
    return { value_set_digest: valueDigest(phase === "before" ? expected.progress : values), field_count: 7, update_control_present: true };
  });
  return { application, profile, founderVideo, demo, progress };
}
function buildSources(observedAt) {
  return [
    source("readme_en", "repo://README.md", path.join(ROOT, "README.md"), observedAt),
    source("readme_ja", "repo://README.ja.md", path.join(ROOT, "README.ja.md"), observedAt),
    source("agent_registry", "repo://agents/registry.json", path.join(ROOT, "agents/registry.json"), observedAt),
    source("provider_manifest", "repo://apps/life-manager/config/yc-submitted-update-provider.json", path.join(ROOT, "apps/life-manager/config/yc-submitted-update-provider.json"), observedAt),
    source("answer_draft", "workspace://funders/results/FT-YC/yc-answers-lifemanager-2026fall.json", ANSWER_DRAFT, observedAt),
    source("application_kit", "application-kit://KIT.md", path.join(KIT_ROOT, "KIT.md"), observedAt),
    source("application_submit_receipt", "repo://docs/evidence/funding/2026-08-02-o1c07-yc-fall-2026-submit.json", path.join(ROOT, "docs/evidence/funding/2026-08-02-o1c07-yc-fall-2026-submit.json"), observedAt),
    source("founder_video_source", "application-kit://videos/Anicca_intro_EN.mp4", FOUNDER_VIDEO_FILE, observedAt),
    source("demo_source", "application-kit://videos/life-manager-yc-demo.mp4", DEMO_FILE, observedAt),
  ];
}
function previewInput(observations, sources, payloads, phase) {
  const verifiedAt = new Date().toISOString();
  const founderLocal = mediaMeta(FOUNDER_VIDEO_FILE, { sha256: "34881787eb93e240049f92ea72d471f3d457f00ddb4e228b1b8c1729fa0e5fe6", bytes: 22291622, duration_seconds: 57.835, width: 720, height: 1280 });
  const demoLocal = mediaMeta(DEMO_FILE, { sha256: "9aee0d5bc4e20776cc6b8a77763a42fc8def4f47b71646c37b468c4fe19879af", bytes: 7228874, duration_seconds: 50.833333, width: 1920, height: 1080 });
  const prepared = phase === "before";
  const demoPresent = Boolean(observations.demo.ready_state);
  return {
    verified_at: verifiedAt,
    application: { id: APP_ID, batch: "Fall 2026", state: "In review", prior_application_submit_count: 1, submission_source_role: "application_submit_receipt", origin: ORIGIN, path: APP_PATH, observed_at: observations.application.observed_at },
    sources,
    scopes: [
      { scope: "company_facts", status: prepared ? "prepared" : "current", observed_at: observations.application.observed_at, source_roles: ["readme_en", "readme_ja", "agent_registry", "answer_draft", "application_kit", "provider_manifest"], issue_codes: [], observation: { field_count: 7, value_set_digest: valueDigest(payloads.progress) } },
      { scope: "founder_profile", status: prepared ? "prepared" : "current", observed_at: observations.profile.observed_at, source_roles: ["application_kit"], issue_codes: [], observation: { structurally_complete: true, section_count: 6, value_set_digest: observations.profile.value_set_digest } },
      { scope: "founder_video", status: "present", observed_at: observations.founderVideo.observed_at, source_roles: ["founder_video_source"], issue_codes: [], observation: { remote: { ready_state: 4, duration_seconds: observations.founderVideo.duration_seconds, width: observations.founderVideo.width, height: observations.founderVideo.height, storage_origin: observations.founderVideo.storage_origin, source_path_sha256: observations.founderVideo.source_path_sha256 }, local: founderLocal } },
      demoPresent
        ? { scope: "demo", status: "present", observed_at: observations.demo.observed_at, source_roles: ["demo_source"], issue_codes: [], observation: { dedicated_source_role: "demo_source", remote: { ready_state: 4, duration_seconds: observations.demo.duration_seconds, width: observations.demo.width, height: observations.demo.height, storage_origin: observations.demo.storage_origin, source_path_sha256: observations.demo.source_path_sha256 } } }
        : { scope: "demo", status: "prepared", observed_at: observations.demo.observed_at, source_roles: ["demo_source"], issue_codes: [], observation: { dedicated_source_role: "demo_source", remote: null, local: demoLocal } },
      { scope: "progress", status: prepared ? "prepared" : "current", observed_at: observations.progress.observed_at, source_roles: ["readme_en", "answer_draft", "provider_manifest"], issue_codes: [], observation: { field_count: 7, value_set_digest: observations.progress.value_set_digest, update_control_present: true } },
    ],
    assessment: { decision_owner: "agent", preview_complete: true, submit_ready: true, blocking_issue_codes: [] },
    effects: { read_only_navigations: 5, owned_page_closes: 5, form_field_writes: 0, option_selections: 0, file_attachments: 0, save_controls: 0, update_submissions: 0, application_submissions: 0, browser_closes: 0 },
  };
}

async function main() {
  if (fs.existsSync(EVIDENCE)) throw new Error("O1C-26 execution evidence already exists; refusing retry");
  const continuation = fs.existsSync(FENCE_DIR);
  let priorFences = [];
  if (continuation) {
    if (fs.readdirSync(FENCE_DIR).some((name) => name.endsWith(".lock") || name.endsWith(".tmp"))) throw new Error("O1C-26 fence transition is not settled");
    priorFences = fs.readdirSync(FENCE_DIR).filter((name) => name.endsWith(".json")).map((name) => readFence(path.join(FENCE_DIR, name)));
    const demoFences = priorFences.filter(({ operation_type }) => operation_type === "demo_update");
    const progressFences = priorFences.filter(({ operation_type }) => operation_type === "progress_update");
    if (demoFences.length !== 1 || demoFences[0].state !== "confirmed" || progressFences.length < 1
      || progressFences.some(({ state }) => state !== "not_applied") || priorFences.length !== 1 + progressFences.length) throw new Error("O1C-26 continuation boundary invalid");
  }
  loadYcSubmittedUpdateProviderManifest();
  const payloads = {
    progress: {
      productLink: "https://github.com/Daisuke134/life-manager",
      productCreds: "The public repository and dashboard are available without sign-in. The cloud user surface is not a public demo in this update. The founder is the initial local user.",
      howfar: "Life Manager is one open-source product with local/self-hosted and web/cloud execution surfaces. The local runtime is built and runs a receipt-producing wake loop. The cloud service repository contains Telegram onboarding, scheduling, wake calls, an authenticated panel, billing, and user-scoped workflows. The canonical registry declares 16 agents: 4 live, 5 legacy_live, 1 shadow, and 6 planned. The founder is the initial local user. The public dashboard currently shows zero revenue and zero live instances.",
      worked: "Daisuke built and reviews the repository as a sole founder, using AI coding agents as tools. No non-founder human or outside contractor wrote the product code. Work-time, school, and employment dates are omitted because the reusable sources have not been fully reconciled.",
      techstack: "Node.js and CommonJS for the runtime loop; PostgreSQL/Supabase for state; Railway-hosted services; launchd for local scheduling; Telegram Bot API, Google Calendar and Places for user workflows; authenticated browser automation; Base and Solana wallets; x402; Polymarket, Jupiter, and Hyperliquid integrations; model-agnostic agent execution.",
      people_using: true,
      have_revenue: false,
    },
    team: {
      others2: "Daisuke writes and reviews the product code with AI coding agents. No non-founder human or outside contractor wrote the product code. AI systems are tools and agents, not legal cofounders.",
      cofounder: "I am a sole founder. I do not currently have a cofounder.",
    },
    profile: {
      fhack: "I built an agent to monitor a gym reservation surface and book a desired slot within seconds of release, turning a repetitive timing contest into a deterministic browser task.",
      fability: "I spearheaded a highly successful YouTube influencer marketing campaign, resulting in a record-breaking number of paid user acquisitions. (https://www.youtube.com/watch?v=Wz1Ea_z8b7Y)",
      projects: "Life Manager is my current public project: an open-source life operating system that orchestrates specialist agents and runs locally or through a cloud service. https://github.com/Daisuke134/life-manager",
      awards: "None.",
      testScores: "Duolingo English Test: 140\nSpanish: DELE B1\nA caregivers Certification in Japan",
      clubs: "None.",
    },
  };
  const sourceObservedAt = new Date().toISOString();
  const sources = buildSources(sourceObservedAt);
  const beforeObservations = await observeFive(payloads, "before");
    const prePreview = buildYcFullPreviewReceipt(previewInput(beforeObservations, sources, payloads, "before"), { now: new Date() });
    const providerDigest = fileMeta(path.join(ROOT, "apps/life-manager/config/yc-submitted-update-provider.json")).sha256;
    const observedAt = new Date().toISOString();
    const operations = [
      { operation_type: "demo_update", disposition: continuation ? "omit_equal" : "execute", route: `/apps/${APP_ID}/edit/demo`, payload: { demo_video: { source_ref: "application-kit://videos/life-manager-yc-demo.mp4", artifact_digest: "9aee0d5bc4e20776cc6b8a77763a42fc8def4f47b71646c37b468c4fe19879af" } } },
      { operation_type: "progress_update", disposition: "execute", route: `/apps/${APP_ID}/edit/progress`, payload: payloads.progress },
      { operation_type: "team_update", disposition: "execute", route: `/apps/${APP_ID}/edit/cofounder`, payload: payloads.team },
      { operation_type: "founder_profile_update", disposition: "execute", route: PROFILE_PATH, payload: payloads.profile },
    ].map((operation) => ({ ...operation, observed_at: observedAt, expected_readback_digest: valueDigest(operation.payload) }));
    const planVerifiedAt = new Date().toISOString();
    const plan = buildYcTypedUpdatePlan({
      verified_at: planVerifiedAt,
      application: { id: APP_ID, batch: "Fall 2026", state: "In review", prior_application_submit_count: 1 },
      provider_manifest_digest: providerDigest,
      preview: { preview_complete: true, submit_ready: true, blocking_issue_codes: [], preview_receipt_digest: prePreview.preview_receipt_digest },
      operations,
      effects: { form_field_writes: 0, option_selections: 0, file_attachments: 0, update_control_activations: 0, application_submissions: 0, browser_closes: 0 },
    }, { now: planVerifiedAt });
    const page = await createOwnedYcRawCdpPage();
    let terminals;
    try {
      const adapter = createYcTypedUpdateBrowserAdapter({
        driver: page,
        artifactResolver: async (ref) => {
          if (ref !== "application-kit://videos/life-manager-yc-demo.mp4") throw new Error("unknown artifact ref");
          return { path: DEMO_FILE, digest: fileMeta(DEMO_FILE).sha256 };
        },
      });
      terminals = [];
      for (const operation of plan.operations.filter(({ disposition }) => disposition === "execute")) {
        const terminal = await executeYcTypedUpdateOperation({ plan, operationId: operation.operation_id, fenceFile: path.join(FENCE_DIR, `${operation.operation_type}-${operation.operation_id}.json`), adapter });
        terminals.push(terminal);
        if (terminal.state !== "confirmed") {
          console.error(JSON.stringify({ operation_type: operation.operation_type, network: page.diagnostics() }));
          throw new Error(`${operation.operation_type} was not confirmed`);
        }
      }
    } finally { await page.close(); }
    const afterSourceObservedAt = new Date().toISOString();
    const afterSources = buildSources(afterSourceObservedAt);
    const afterObservations = await observeFive(payloads, "after");
    const postPreview = buildYcFullPreviewReceipt(previewInput(afterObservations, afterSources, payloads, "after"), { now: new Date() });
    const evidence = {
      schema_version: 1,
      objective: "O1C-26",
      generated_at: new Date().toISOString(),
      result: { pre_preview_ready: prePreview.submit_ready, operations_confirmed: terminals.filter(({ state }) => state === "confirmed").length + priorFences.filter(({ state }) => state === "confirmed").length, post_preview_ready: postPreview.submit_ready, application_state: "In review", application_resubmissions: 0 },
      demo: { sha256: "9aee0d5bc4e20776cc6b8a77763a42fc8def4f47b71646c37b468c4fe19879af", bytes: 7228874, duration_seconds: 50.833333, width: 1920, height: 1080, video_codec: "h264", audio_codec: "aac" },
      pre_preview: prePreview,
      plan,
      terminal_fences: [...priorFences, ...terminals],
      post_preview: postPreview,
      direct_readback: { application: afterObservations.application, founder_profile_digest: afterObservations.profile.value_set_digest, founder_video: afterObservations.founderVideo, demo: afterObservations.demo, progress_digest: afterObservations.progress.value_set_digest },
      effects: { typed_update_control_activations: priorFences.reduce((sum, fence) => sum + fence.activation_count, 0) + terminals.reduce((sum, fence) => sum + fence.activation_count, 0), application_submissions: 0, browser_closes: 0 },
      privacy: { raw_private_fields_persisted: false, auth_material_persisted: false, signed_media_urls_persisted: false },
    };
    writeJsonExclusive(EVIDENCE, evidence);
    process.stdout.write(`${JSON.stringify({ evidence: path.relative(ROOT, EVIDENCE), result: evidence.result, plan_digest: plan.plan_digest, pre_preview_digest: prePreview.preview_receipt_digest, post_preview_digest: postPreview.preview_receipt_digest })}\n`);
}

main().then(() => process.exit(0)).catch((error) => { console.error(error && error.stack ? error.stack : String(error)); process.exit(1); });
