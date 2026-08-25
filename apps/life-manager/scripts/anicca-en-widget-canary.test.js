"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const test = require("node:test");

const { createContentObjectStore, importContentObject } = require("../lib/content-object-store.js");
const { createMarketingLaneManifest, writeMarketingLaneManifest } = require("../lib/marketing-lane-manifest.js");
const {
  compareNativeVideo,
  parseArgs,
  runAniccaEnWidgetCanary,
} = require("./anicca-en-widget-canary.js");

const SLOT = "2026-08-26T07:30:00.000Z";
const FIRST_NOW = "2026-08-26T07:31:00.000Z";
const VERIFIED_AT = "2026-08-26T08:00:00.000Z";
const VERIFIED_NOW = "2026-08-26T08:01:00.000Z";
const PRODUCT = "anicca-ios";
const ACCOUNT = "@anicca.en";
const INTEGRATION_REF = "integration://postiz/instagram/cmn8y95rg02d2qx0y09bbk5pb";
const INTEGRATION_ID = "cmn8y95rg02d2qx0y09bbk5pb";
const CREATIVE_ID = "EN-WIDGET-CANARY-98f4ce8c607a";
const CAPTION = "Since you are always\non your phone\n\n#affirmations #lockscreen #widget #mentalhealth #anicca\n";
const DIRECT_REEL = "https://www.instagram.com/reel/DbInY17DSpI/";
const NATIVE_URL = "https://scontent.cdninstagram.com/anicca-widget-native.mp4";
const NATIVE_BYTES = Buffer.from("native video");

function capturedLiveEmbed({ owner = "anicca.en", caption = CAPTION, videoUrl = NATIVE_URL } = {}) {
  const nested = JSON.stringify({ GraphVideo: { video_url: videoUrl } })
    .replace(/"/g, "\\\"")
    .replace(/\//g, "\\\\/");
  return `<div class="Caption"><a class="CaptionUsername" href="https://www.instagram.com/${owner}/?utm_source=ig_web_copy_link">${owner}</a><br /><br />${caption}</div><script>${nested}</script>`;
}

function fixture() {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-anicca-en-widget-canary-"));
  const objectDir = path.join(dataDir, "objects");
  const objectStore = createContentObjectStore({ objectDir });
  const importBytes = (name, bytes) => {
    const source = path.join(dataDir, name);
    fs.writeFileSync(source, bytes);
    return importContentObject(source, { objectDir }).ref;
  };
  const videoRef = importBytes("widget.mp4", Buffer.from("widget-video-fixture"));
  const captionRef = importBytes("caption.txt", Buffer.from(CAPTION));
  const visualEvidenceRef = importBytes("contact-sheet.txt", Buffer.from("pack contact sheet"));
  const pack = {
    schema_version: 1,
    kind: "marketing_video_asset_pack",
    product_id: PRODUCT,
    locale: "en",
    platform: "instagram",
    account_id: ACCOUNT,
    integration_id: INTEGRATION_ID,
    renderer_id: "reelclaw-widget",
    format_id: "widget-demo-reel",
    form: "lockscreen-affirmation-widget",
    caption: CAPTION,
    caption_ref: captionRef,
    visual_evidence_ref: visualEvidenceRef,
    media: [{ position: 1, role: "hook-then-widget-demo", media_type: "video/mp4", video_ref: videoRef }],
  };
  const packRef = importBytes("pack.json", Buffer.from(JSON.stringify(pack)));
  const approval = {
    schema_version: 1,
    kind: "marketing_video_publication_approval",
    status: "approved",
    tenant_id: "dais-local",
    product_id: PRODUCT,
    format_id: "reelclaw-widget",
    form: "lockscreen-affirmation-widget",
    locale: "en",
    platform: "instagram",
    account_id: ACCOUNT,
    integration_ref: INTEGRATION_REF,
    pack_ref: packRef,
    creative_id: CREATIVE_ID,
    video_sha256: videoRef.slice(-64),
    caption_sha256: captionRef.slice(-64),
  };
  const approvalRef = importBytes("approval.json", Buffer.from(JSON.stringify(approval)));
  const env = {
    LM_DATA_DIR: dataDir,
    LM_RUNTIME_TENANT_ID: "dais-local",
    LM_ANICCA_EN_WIDGET_PACK_REF: packRef,
    LM_ANICCA_EN_WIDGET_VIDEO_REF: videoRef,
    LM_ANICCA_EN_WIDGET_CAPTION_REF: captionRef,
    LM_ANICCA_EN_WIDGET_APPROVAL_REF: approvalRef,
    LM_POSTIZ_API_KEY: "postiz-secret-fixture",
    LM_TELEGRAM_BOT_TOKEN: "telegram-secret-fixture",
    LM_TELEGRAM_ALERT_CHAT_ID: "123456789",
  };
  const value = {
    dataDir,
    env,
    objectStore,
    importBytes,
    packRef,
    videoRef,
    captionRef,
    approvalRef,
    visualEvidenceRef,
  };
  const target = {
    id: INTEGRATION_ID,
    provider: "postiz",
    platform: "instagram",
    profile: ACCOUNT,
    account: "anicca-ios-en-widget-instagram",
    product_id: "anicca",
    locale: "en",
    disabled: false,
    verified: true,
    owner: "life-manager",
    lane_state: "default-off",
    production_armed: false,
    disposition: "target",
    renderer: "reelclaw-widget",
    format: "widget-demo-reel",
    approved_pack: "anicca-ios-reelclaw-widget-en.pack.json",
    canary_state: "pack-ready",
    target_daily_limit: 2,
  };
  const manifest = createMarketingLaneManifest({
    tenant_id: "dais-local",
    integrations: [target],
    holds: [{
      integration_id: "other-instagram-lane",
      platform: "instagram",
      account: "@other",
      provider: "postiz",
      provider_disabled: false,
      owner: "life-manager",
      disposition: "hold",
      target_daily_limit: 0,
      verified: true,
    }],
  }, { tenantId: "dais-local", assignments: [target] });
  const manifestPath = writeMarketingLaneManifest(manifest, { dataDir });
  const fencePath = path.join(dataDir, "marketing", "publication-effect-fence.json");
  fs.writeFileSync(fencePath, `${JSON.stringify({ schema_version: 1, state: "closed", reason: "fixture" })}\n`, { mode: 0o600 });
  return Object.assign(value, {
    manifestPath,
    fencePath,
    originalManifest: fs.readFileSync(manifestPath),
    originalFence: fs.readFileSync(fencePath),
    originalManifestMode: fs.statSync(manifestPath).mode & 0o777,
    originalFenceMode: fs.statSync(fencePath).mode & 0o777,
  });
}

function providerCalls(calls, result = {}) {
  return async (input) => {
    calls.push(input);
    return {
      creative_id: CREATIVE_ID,
      video_sha256: input.videoPath.split("/").at(-1),
      caption_sha256: input.captionPath.split("/").at(-1),
      platform: "instagram",
      public_url: DIRECT_REEL,
      provider_post_id: "postiz-widget-canary-1",
      provider_route: "postiz",
      provider_reconciled: true,
      ...result,
    };
  };
}

function replaceJson(value, name, patch) {
  const parsed = JSON.parse(fs.readFileSync(value.objectStore.resolve(value[name]), "utf8"));
  const next = { ...parsed, ...patch };
  return value.importBytes(`${name}-replacement.json`, Buffer.from(JSON.stringify(next)));
}

function verification(value, receipt, overrides = {}, evidenceOverrides = {}) {
  const nativeVideoRef = value.importBytes("native-video.mp4", NATIVE_BYTES);
  const nativeContactSheetRef = value.importBytes("native-contact-sheet.jpg", Buffer.from("native contact sheet"));
  const evidence = typeof evidenceOverrides === "string" ? null : {
    schema_version: 1,
    kind: "marketing_video_native_evidence",
    status: "verified",
    platform: "instagram",
    public_url: receipt.public_url,
    account_id: ACCOUNT,
    integration_ref: INTEGRATION_REF,
    caption: CAPTION,
    caption_sha256: value.captionRef.slice(-64),
    video_sha256: value.videoRef.slice(-64),
    observation_method: "instagram-captioned-embed+native-video-frame-comparison",
    source_contact_sheet_ref: value.visualEvidenceRef,
    native_video_ref: nativeVideoRef,
    native_contact_sheet_ref: nativeContactSheetRef,
    observed_at: "2026-08-26T07:45:00.000Z",
    ...evidenceOverrides,
  };
  const evidenceRef = typeof evidenceOverrides === "string"
    ? value.importBytes("native-evidence.txt", Buffer.from(evidenceOverrides))
    : value.importBytes("native-evidence.json", Buffer.from(JSON.stringify(evidence)));
  return value.importBytes("verification.json", Buffer.from(JSON.stringify({
    schema_version: 1,
    kind: "marketing_video_native_verification",
    status: "verified",
    product_id: PRODUCT,
    account_id: ACCOUNT,
    integration_ref: INTEGRATION_REF,
    public_url: receipt.public_url,
    pack_sha256: value.packRef.slice(-64),
    video_sha256: value.videoRef.slice(-64),
    caption_sha256: value.captionRef.slice(-64),
    evidence_ref: evidenceRef,
    verified_at: VERIFIED_AT,
    ...overrides,
  })));
}

function genericOptions(value, publicationCalls, telegramCalls = [], overrides = {}) {
  return {
    env: value.env,
    runDistribution: providerCalls(publicationCalls),
    sendTelegram: async (...args) => {
      telegramCalls.push(args);
      return { ok: true, result: { message_id: 42 } };
    },
    fetchImpl: async (url) => (String(url).endsWith("embed/captioned/")
      ? { status: 200, text: async () => `<a class="CaptionUsername" href="https://www.instagram.com/${ACCOUNT.slice(1)}/">${ACCOUNT}</a><div data-testid="caption">${CAPTION}</div><script>{"GraphVideo":{"video_url":"${NATIVE_URL}"}}</script>` }
      : { status: 200, arrayBuffer: async () => NATIVE_BYTES.buffer.slice(NATIVE_BYTES.byteOffset, NATIVE_BYTES.byteOffset + NATIVE_BYTES.byteLength) }),
    videoComparator: async () => true,
    now: () => FIRST_NOW,
    ...overrides,
  };
}

test("default native comparator accepts same/transcoded video but rejects visible differences", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-native-video-"));
  const red = path.join(dir, "red.mp4");
  const transcoded = path.join(dir, "red-transcoded.mp4");
  const green = path.join(dir, "green.mp4");
  const splitA = path.join(dir, "split-a.mp4");
  const splitB = path.join(dir, "split-b.mp4");
  const splitATranscoded = path.join(dir, "split-a-transcoded.mp4");
  const splitATruncated = path.join(dir, "split-a-truncated.mp4");
  for (const [file, color] of [[red, "red"], [green, "green"]]) {
    execFileSync("ffmpeg", ["-loglevel", "error", "-y", "-f", "lavfi", "-i", `color=c=${color}:s=64x64:d=1:r=10`, "-pix_fmt", "yuv420p", file]);
  }
  execFileSync("ffmpeg", ["-loglevel", "error", "-y", "-i", red, "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", transcoded]);
  for (const [file, tail] of [[splitA, "blue"], [splitB, "green"]]) {
    execFileSync("ffmpeg", ["-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=64x64:d=1:r=30", "-f", "lavfi", "-i", `color=c=${tail}:s=64x64:d=14:r=30`, "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0,format=yuv420p[v]", "-map", "[v]", file]);
  }
  execFileSync("ffmpeg", ["-loglevel", "error", "-y", "-i", splitA, "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", splitATranscoded]);
  execFileSync("ffmpeg", ["-loglevel", "error", "-y", "-i", splitA, "-t", "13.5", "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", splitATruncated]);
  assert.equal(compareNativeVideo(red, transcoded), true);
  assert.equal(compareNativeVideo(red, green), false);
  assert.equal(compareNativeVideo(splitA, splitATranscoded), true);
  assert.equal(compareNativeVideo(splitA, splitB), false);
  assert.equal(compareNativeVideo(splitATruncated, splitA), false);
});

test("CLI accepts only run with a mandatory exact ISO slot", () => {
  assert.deepEqual(parseArgs(["run", "--slot", SLOT]), { command: "run", slot: SLOT });
  assert.throws(() => parseArgs(["run"]), /usage/i);
  assert.throws(() => parseArgs(["run", "--slot"]), /usage/i);
  assert.throws(() => parseArgs(["run", "--slot", "2026-08-26T07:30:00Z"]), /invalid|usage/i);
  assert.throws(() => parseArgs(["publish"]), /usage/i);
});

test("first publication is one exact Reel and holds Telegram", async () => {
  const value = fixture();
  const publicationCalls = [];
  const telegramCalls = [];
  const result = await runAniccaEnWidgetCanary(
    ["run", "--slot", SLOT],
    genericOptions(value, publicationCalls, telegramCalls),
  );
  assert.deepEqual(result, {
    slot: SLOT,
    publication: {
      created: true,
      public_url: DIRECT_REEL,
      provider_post_id: "postiz-widget-canary-1",
    },
    telegram: { created: false, held: true, message_id: null },
  });
  assert.equal(publicationCalls.length, 1);
  assert.equal(publicationCalls[0].instagramIntegration, INTEGRATION_ID);
  assert.equal(publicationCalls[0].instagramProfileStatePath, "");
  assert.equal(telegramCalls.length, 0);
  assert.doesNotMatch(JSON.stringify(result), /postiz-secret|telegram-secret|openclaw|\/Users\//i);
  const jobs = fs.readFileSync(path.join(value.dataDir, "marketing", "jobs.jsonl"), "utf8");
  assert.doesNotMatch(jobs, /postiz-secret|telegram-secret|openclaw|\/Users\//i);
});

test("first effect opens only the exact lane/fence and restores bytes after success", async () => {
  const value = fixture();
  const publicationCalls = [];
  let during;
  const result = await runAniccaEnWidgetCanary(["run", "--slot", SLOT], genericOptions(value, publicationCalls, [], {
    runDistribution: async (input) => {
      const manifest = JSON.parse(fs.readFileSync(value.manifestPath, "utf8"));
      const fence = JSON.parse(fs.readFileSync(value.fencePath, "utf8"));
      during = { manifest, fence, input };
      return providerCalls(publicationCalls)(input);
    },
  }));
  assert.equal(result.publication.created, true);
  assert.equal(during.fence.state, "open");
  assert.equal(during.fence.allowed_effect_key, `marketing:video:${PRODUCT}:instagram:${CREATIVE_ID}:${value.videoRef.slice(-64)}:${value.captionRef.slice(-64)}`);
  assert.deepEqual(during.manifest.lanes.map(({ integration_id, production_armed, lane_state }) => ({ integration_id, production_armed, lane_state })), [{ integration_id: INTEGRATION_ID, production_armed: true, lane_state: "production-armed" }]);
  assert.deepEqual(fs.readFileSync(value.manifestPath), value.originalManifest);
  assert.deepEqual(fs.readFileSync(value.fencePath), value.originalFence);
  assert.equal(fs.statSync(value.manifestPath).mode & 0o777, value.originalManifestMode);
  assert.equal(fs.statSync(value.fencePath).mode & 0o777, value.originalFenceMode);
});

test("provider failure restores exact manifest/fence and remains unknown", async () => {
  const value = fixture();
  const publicationCalls = [];
  await assert.rejects(runAniccaEnWidgetCanary(["run", "--slot", SLOT], genericOptions(value, publicationCalls, [], {
    runDistribution: async () => { publicationCalls.push(true); throw new Error("provider boundary failed"); },
  })), (error) => error.unknownEffect === true);
  assert.equal(publicationCalls.length, 1);
  assert.deepEqual(fs.readFileSync(value.manifestPath), value.originalManifest);
  assert.deepEqual(fs.readFileSync(value.fencePath), value.originalFence);
});

test("pack or approval mismatch blocks before secret/provider boundaries", async () => {
  for (const [target, patch, message] of [
    ["packRef", { renderer_id: "wrong-renderer" }, /pack/i],
    ["packRef", { caption_ref: "object://sha256/" + "f".repeat(64) }, /pack/i],
    ["approvalRef", { integration_ref: "integration://postiz/instagram/wrong" }, /approval/i],
    ["approvalRef", { video_sha256: "f".repeat(64) }, /approval/i],
  ]) {
    const value = fixture();
    value.env[`LM_ANICCA_EN_WIDGET_${target === "packRef" ? "PACK" : "APPROVAL"}_REF`] = replaceJson(value, target, patch);
    const publicationCalls = [];
    const secretCalls = [];
    const integrationCalls = [];
    await assert.rejects(
      runAniccaEnWidgetCanary(["run", "--slot", SLOT], genericOptions(value, publicationCalls, [], {
        secretProvider: { get: async (...args) => { secretCalls.push(args); return "secret"; } },
        integrationProvider: { get: async (...args) => { integrationCalls.push(args); return INTEGRATION_ID; } },
      })),
      message,
    );
    assert.equal(publicationCalls.length, 0);
    assert.equal(secretCalls.length, 0);
    assert.equal(integrationCalls.length, 0);
  }
});

test("missing, mismatched, and time-invalid native verification hold Telegram", async () => {
  const value = fixture();
  const publicationCalls = [];
  const telegramCalls = [];
  const options = genericOptions(value, publicationCalls, telegramCalls);
  const first = await runAniccaEnWidgetCanary(["run", "--slot", SLOT], options);
  const receipt = JSON.parse(fs.readFileSync(path.join(value.dataDir, "marketing", "receipts.jsonl"), "utf8")).receipt;
  for (const overrides of [
    { pack_sha256: "f".repeat(64) },
    { account_id: "@other.account" },
    { verified_at: receipt.published_at },
    { verified_at: "2026-08-26T07:30:59.000Z" },
    { verified_at: "2026-08-26T08:02:00.000Z" },
  ]) {
    value.env.LM_ANICCA_EN_WIDGET_NATIVE_VERIFICATION_REF = verification(value, receipt, overrides);
    const held = await runAniccaEnWidgetCanary(["run", "--slot", SLOT], {
      ...options,
      now: () => VERIFIED_NOW,
    });
    assert.equal(held.publication.created, false);
    assert.deepEqual(held.telegram, { created: false, held: true, message_id: null });
  }
  for (const evidenceOverrides of [
    "arbitrary evidence bytes",
    { caption_match: false },
    { native_video_ref: "object://sha256/" + "f".repeat(64) },
    { observed_at: receipt.published_at },
    { observed_at: "2026-08-26T08:00:01.000Z" },
  ]) {
    value.env.LM_ANICCA_EN_WIDGET_NATIVE_VERIFICATION_REF = verification(value, receipt, {}, evidenceOverrides);
    const held = await runAniccaEnWidgetCanary(["run", "--slot", SLOT], { ...options, now: () => VERIFIED_NOW });
    assert.equal(held.telegram.held, true);
  }
  assert.equal(publicationCalls.length, 1);
  assert.equal(telegramCalls.length, 0);
});

test("exact native verification sends one natural Telegram and replay is zero", async () => {
  const value = fixture();
  const publicationCalls = [];
  const telegramCalls = [];
  const options = genericOptions(value, publicationCalls, telegramCalls);
  const first = await runAniccaEnWidgetCanary(["run", "--slot", SLOT], options);
  const publicationReceipt = JSON.parse(fs.readFileSync(path.join(value.dataDir, "marketing", "receipts.jsonl"), "utf8")).receipt;
  value.env.LM_ANICCA_EN_WIDGET_NATIVE_VERIFICATION_REF = verification(value, publicationReceipt);
  const second = await runAniccaEnWidgetCanary(["run", "--slot", SLOT], {
    ...options,
    now: () => VERIFIED_NOW,
  });
  const third = await runAniccaEnWidgetCanary(["run", "--slot", SLOT], {
    ...options,
    now: () => VERIFIED_NOW,
  });
  assert.equal(first.telegram.held, true);
  assert.deepEqual(second.telegram, { created: true, held: false, message_id: 42 });
  assert.deepEqual(third.telegram, { created: false, held: false, message_id: 42 });
  assert.equal(second.publication.created, false);
  assert.equal(third.publication.created, false);
  assert.equal(publicationCalls.length, 1);
  assert.equal(telegramCalls.length, 1);
});

test("literal evidence and wrong live owner/caption/media never release Telegram", async () => {
  for (const live of [
    { owner: "@other", caption: CAPTION, bytes: NATIVE_BYTES },
    { owner: "@aniccaXen", caption: CAPTION, bytes: NATIVE_BYTES },
    { owner: ACCOUNT, caption: "wrong caption", bytes: NATIVE_BYTES },
    { owner: ACCOUNT, caption: CAPTION, bytes: Buffer.from("wrong media") },
  ]) {
    const value = fixture();
    const publicationCalls = [];
    const telegramCalls = [];
    const first = await runAniccaEnWidgetCanary(["run", "--slot", SLOT], genericOptions(value, publicationCalls, telegramCalls));
    const receipt = JSON.parse(fs.readFileSync(path.join(value.dataDir, "marketing", "receipts.jsonl"), "utf8")).receipt;
    value.env.LM_ANICCA_EN_WIDGET_NATIVE_VERIFICATION_REF = verification(value, receipt);
    const held = await runAniccaEnWidgetCanary(["run", "--slot", SLOT], genericOptions(value, publicationCalls, telegramCalls, {
      now: () => VERIFIED_NOW,
      fetchImpl: async (url) => (String(url).endsWith("embed/captioned/")
        ? { status: 200, text: async () => `<a href="https://www.instagram.com/${live.owner.slice(1)}/">${live.owner}</a><div data-testid="caption">${live.caption}</div><script>{"GraphVideo":{"video_url":"${NATIVE_URL}"}}</script>` }
        : { status: 200, arrayBuffer: async () => live.bytes.buffer.slice(live.bytes.byteOffset, live.bytes.byteOffset + live.bytes.byteLength) }),
    }));
    assert.equal(first.telegram.held, true);
    assert.equal(held.telegram.held, true);
    assert.equal(telegramCalls.length, 0);
  }
});

test("captured Instagram Caption embed shape releases with escaped GraphVideo URL", async () => {
  const value = fixture();
  const publicationCalls = [];
  const telegramCalls = [];
  const first = await runAniccaEnWidgetCanary(["run", "--slot", SLOT], genericOptions(value, publicationCalls, telegramCalls));
  const receipt = JSON.parse(fs.readFileSync(path.join(value.dataDir, "marketing", "receipts.jsonl"), "utf8")).receipt;
  value.env.LM_ANICCA_EN_WIDGET_NATIVE_VERIFICATION_REF = verification(value, receipt);
  const released = await runAniccaEnWidgetCanary(["run", "--slot", SLOT], genericOptions(value, publicationCalls, telegramCalls, {
    now: () => VERIFIED_NOW,
    fetchImpl: async (url) => (String(url).endsWith("embed/captioned/")
      ? { status: 200, text: async () => capturedLiveEmbed() }
      : { status: 200, arrayBuffer: async () => NATIVE_BYTES.buffer.slice(NATIVE_BYTES.byteOffset, NATIVE_BYTES.byteOffset + NATIVE_BYTES.byteLength) }),
  }));
  assert.equal(first.telegram.held, true);
  assert.deepEqual(released.telegram, { created: true, held: false, message_id: 42 });
  assert.equal(telegramCalls.length, 1);
});

test("CaptionUsername owner is required and embed redirects hold", async () => {
  const value = fixture();
  const publicationCalls = [];
  const telegramCalls = [];
  await runAniccaEnWidgetCanary(["run", "--slot", SLOT], genericOptions(value, publicationCalls, telegramCalls));
  const receipt = JSON.parse(fs.readFileSync(path.join(value.dataDir, "marketing", "receipts.jsonl"), "utf8")).receipt;
  value.env.LM_ANICCA_EN_WIDGET_NATIVE_VERIFICATION_REF = verification(value, receipt);
  const heldOwner = await runAniccaEnWidgetCanary(["run", "--slot", SLOT], genericOptions(value, publicationCalls, telegramCalls, {
    now: () => VERIFIED_NOW,
    fetchImpl: async (url) => (String(url).endsWith("embed/captioned/")
      ? { status: 200, text: async () => `<div class="Caption"><a class="CaptionUsername" href="https://www.instagram.com/other/?utm_source=x">other</a><a href="https://www.instagram.com/anicca.en/">mention</a><br /><br />${CAPTION}</div><script>${JSON.stringify({ GraphVideo: { video_url: NATIVE_URL } }).replace(/"/g, "\\\"")}</script>` }
      : { status: 200, arrayBuffer: async () => NATIVE_BYTES.buffer.slice(NATIVE_BYTES.byteOffset, NATIVE_BYTES.byteOffset + NATIVE_BYTES.byteLength) }),
  }));
  assert.equal(heldOwner.telegram.held, true);
  const heldRedirect = await runAniccaEnWidgetCanary(["run", "--slot", SLOT], genericOptions(value, publicationCalls, telegramCalls, {
    now: () => VERIFIED_NOW,
    fetchImpl: async (url) => (String(url).endsWith("embed/captioned/")
      ? { status: 200, url: "https://www.instagram.com/reel/Other/embed/captioned/", text: async () => capturedLiveEmbed() }
      : { status: 200, arrayBuffer: async () => NATIVE_BYTES.buffer.slice(NATIVE_BYTES.byteOffset, NATIVE_BYTES.byteOffset + NATIVE_BYTES.byteLength) }),
  }));
  assert.equal(heldRedirect.telegram.held, true);
  assert.equal(telegramCalls.length, 0);
});

test("/p/, profile, and numeric Reel URLs become unknown and never notify", async () => {
  for (const public_url of [
    "https://www.instagram.com/p/DbInY17DSpI/",
    "https://www.instagram.com/anicca.en",
    "https://www.instagram.com/reel/1234567890/",
  ]) {
    const value = fixture();
    const publicationCalls = [];
    const telegramCalls = [];
    await assert.rejects(
      runAniccaEnWidgetCanary(["run", "--slot", SLOT], genericOptions(value, publicationCalls, telegramCalls, {
        runDistribution: providerCalls(publicationCalls, { public_url }),
      })),
      /unknown|receipt|provider|publication/i,
    );
    assert.equal(publicationCalls.length, 1);
    assert.equal(telegramCalls.length, 0);
    const jobs = fs.readFileSync(path.join(value.dataDir, "marketing", "jobs.jsonl"), "utf8");
    assert.match(jobs, /"unknown_effect":true/);
  }
});
