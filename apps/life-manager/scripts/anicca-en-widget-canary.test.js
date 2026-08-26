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
  curlResponse,
  defaultLiveFetch,
  embedVideoUrl,
  EN_LANE,
  JA_LANE,
  parseArgs,
  runAniccaEnWidgetCanary,
  runAniccaWidgetCanary,
  resolvePublicIPv4,
} = require("./anicca-en-widget-canary.js");
const { parseArgs: parseJaArgs, runAniccaJaWidgetCanary } = require("./anicca-ja-widget-canary.js");
const { JA_CARD_LANE, parseArgs: parseJaCardArgs, runAniccaJaCardInstagramCanary } = require("./anicca-ja-card-instagram-canary.js");

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

test("double-escaped GraphVideo URL decodes JSON unicode escapes before validation", () => {
  const html = '<script>{"GraphVideo":{"video_url":"https:\\/\\/scontent.cdninstagram.com\\/video.mp4?efg=abc\\\\u00253Ddef"}}</script>';
  assert.equal(embedVideoUrl(html), "https://scontent.cdninstagram.com/video.mp4?efg=abc%3Ddef");
  for (const url of [
    "https://user:pass@scontent.cdninstagram.com/video.mp4",
    "https://scontent.cdninstagram.com:444/video.mp4",
    "https://scontent.cdninstagram.com/video.mp4#fragment",
  ]) {
    assert.equal(embedVideoUrl(`<script>{"GraphVideo":{"video_url":"${url}"}}</script>`), null);
  }
});

test("default live DNS fallback is exact-host, public-IP, HTTPS-only, and no-redirect", async () => {
  const digCalls = [];
  const curlCalls = [];
  const response = await defaultLiveFetch("https://www.instagram.com/reel/DcetvubDA4Z/embed/captioned/", { method: "GET", redirect: "follow" }, {
    defaultFetch: async () => { throw Object.assign(new Error("getaddrinfo ENOTFOUND"), { code: "ENOTFOUND" }); },
    digRunner: (args) => { digCalls.push(args); return { status: 0, stdout: "93.184.216.34\n" }; },
    curlRunner: (args) => {
      curlCalls.push(args);
      return { status: 0, stdout: Buffer.from("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\nembed") };
    },
  });
  assert.equal(response.status, 200);
  assert.equal(response.url, "https://www.instagram.com/reel/DcetvubDA4Z/embed/captioned/");
  assert.equal(await response.text(), "embed");
  assert.deepEqual(digCalls, [["@1.1.1.1", "+short", "A", "www.instagram.com"]]);
  assert.equal(curlCalls.length, 1);
  assert.deepEqual(curlCalls[0].slice(curlCalls[0].indexOf("--resolve"), curlCalls[0].indexOf("--resolve") + 2), ["--resolve", "www.instagram.com:443:93.184.216.34"]);
  assert.equal(curlCalls[0].includes("--proto"), true);
  assert.equal(curlCalls[0].includes("=https"), true);
  assert.equal(curlCalls[0].includes("--max-time"), true);
  assert.equal(curlCalls[0].includes("--max-redirs"), true);
  assert.deepEqual(curlCalls[0].slice(curlCalls[0].indexOf("--noproxy"), curlCalls[0].indexOf("--noproxy") + 2), ["--noproxy", "*"]);
  assert.equal(curlCalls[0].includes("--location") || curlCalls[0].includes("-L"), false);
});

test("fallback accepts valid CNAME and public A rows but rejects unsafe DNS and arbitrary hosts", () => {
  for (const stdout of ["10.0.0.1\n", "127.0.0.1\n", "169.254.1.1\n", "224.0.0.1\n", "240.0.0.1\n", "valid.example.\n93.184.216.34\n10.0.0.1\n", "not a dns row\n93.184.216.34\n"]) {
    assert.throws(() => resolvePublicIPv4("www.instagram.com", { digRunner: () => ({ status: 0, stdout }) }), /fallback DNS/i);
  }
  assert.equal(resolvePublicIPv4("www.instagram.com", {
    digRunner: () => ({ status: 0, stdout: "z-p42-instagram.c10r.instagram.com.\n57.144.44.34\n157.240.31.63\n" }),
  }), "57.144.44.34");
  let called = false;
  assert.throws(() => resolvePublicIPv4("evil.example", { digRunner: () => { called = true; return { status: 0, stdout: "93.184.216.34" }; } }), /host is not allowed/i);
  assert.equal(called, false);
});

test("default fallback is only for DNS errors, not HTTP or other network errors", async () => {
  let digCalls = 0;
  const options = {
    digRunner: () => { digCalls += 1; return { status: 0, stdout: "93.184.216.34" }; },
    curlRunner: () => ({ status: 0, stdout: Buffer.from("HTTP/1.1 200 OK\r\n\r\nshould-not-run") }),
  };
  const http = await defaultLiveFetch("https://www.instagram.com/reel/DcetvubDA4Z/embed/captioned/", {}, { ...options, defaultFetch: async () => ({ status: 503, url: "requested" }) });
  assert.equal(http.status, 503);
  await assert.rejects(defaultLiveFetch("https://www.instagram.com/reel/DcetvubDA4Z/embed/captioned/", {}, { ...options, defaultFetch: async () => { throw Object.assign(new Error("connection reset"), { code: "ECONNRESET" }); } }), /connection reset/);
  assert.equal(digCalls, 0);
});

test("fallback response output is bounded before media verification", () => {
  const oversized = Buffer.concat([Buffer.from("HTTP/1.1 200 OK\r\n\r\n"), Buffer.alloc(50 * 1024 * 1024 + 1)]);
  assert.throws(() => curlResponse("https://scontent.cdninstagram.com/video.mp4", {
    digRunner: () => ({ status: 0, stdout: "93.184.216.34" }),
    curlRunner: () => ({ status: 0, stdout: oversized }),
  }), /too large/i);
  assert.throws(() => curlResponse("https://scontent.cdninstagram.com/video.mp4", {
    digRunner: () => ({ status: 0, stdout: "93.184.216.34" }),
    curlRunner: () => ({ status: 6, stdout: Buffer.alloc(0), stderr: "Could not resolve host" }),
  }), /transport failed/i);
});

function capturedLiveEmbed({ owner = "anicca.en", caption = CAPTION, videoUrl = NATIVE_URL } = {}) {
  const nested = JSON.stringify({ GraphVideo: { video_url: videoUrl } })
    .replace(/"/g, "\\\"")
    .replace(/\//g, "\\\\/");
  return `<div class="Caption"><a class="CaptionUsername" href="https://www.instagram.com/${owner}/?utm_source=ig_web_copy_link">${owner}</a><br /><br />${caption}</div><script>${nested}</script>`;
}

function fixture(lane = EN_LANE, laneCaption = CAPTION) {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), `lm-anicca-${lane.name.toLowerCase()}-widget-canary-`));
  const objectDir = path.join(dataDir, "objects");
  const objectStore = createContentObjectStore({ objectDir });
  const importBytes = (name, bytes) => {
    const source = path.join(dataDir, name);
    fs.writeFileSync(source, bytes);
    return importContentObject(source, { objectDir }).ref;
  };
  const videoRef = importBytes("widget.mp4", Buffer.from("widget-video-fixture"));
  const captionRef = importBytes("caption.txt", Buffer.from(laneCaption));
  const visualEvidenceRef = importBytes("contact-sheet.txt", Buffer.from("pack contact sheet"));
  const pack = {
    schema_version: 1,
    kind: "marketing_video_asset_pack",
    product_id: lane.product,
    locale: lane.locale,
    platform: lane.platform,
    account_id: lane.account,
    integration_id: lane.integrationId,
    renderer_id: lane.renderer,
    format_id: lane.packFormat,
    form: lane.form,
    caption: laneCaption,
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
    format_id: lane.format,
    form: lane.form,
    locale: lane.locale,
    platform: lane.platform,
    account_id: lane.account,
    integration_ref: lane.integrationRef,
    pack_ref: packRef,
    creative_id: lane.creativeId,
    video_sha256: videoRef.slice(-64),
    caption_sha256: captionRef.slice(-64),
  };
  const approvalRef = importBytes("approval.json", Buffer.from(JSON.stringify(approval)));
  const env = {
    LM_DATA_DIR: dataDir,
    LM_RUNTIME_TENANT_ID: "dais-local",
    [lane.packEnv]: packRef,
    [lane.videoEnv]: videoRef,
    [lane.captionEnv]: captionRef,
    [lane.approvalEnv]: approvalRef,
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
    lane,
    caption: laneCaption,
  };
  const target = {
    id: lane.integrationId,
    provider: "postiz",
    platform: "instagram",
    profile: lane.account,
    account: lane.manifestAccount,
    product_id: "anicca",
    locale: lane.locale,
    disabled: false,
    verified: true,
    owner: "life-manager",
    lane_state: "default-off",
    production_armed: false,
    disposition: "target",
    renderer: lane.renderer,
    format: lane.packFormat,
    approved_pack: lane.approvedPackName,
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

function providerCalls(calls, result = {}, lane = EN_LANE) {
  return async (input) => {
    calls.push(input);
    return {
      creative_id: lane.creativeId,
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

function verification(value, receipt, overrides = {}, evidenceOverrides = {}, lane = EN_LANE) {
  const nativeVideoRef = value.importBytes("native-video.mp4", NATIVE_BYTES);
  const nativeContactSheetRef = value.importBytes("native-contact-sheet.jpg", Buffer.from("native contact sheet"));
  const evidence = typeof evidenceOverrides === "string" ? null : {
    schema_version: 1,
    kind: "marketing_video_native_evidence",
    status: "verified",
    platform: lane.platform,
    public_url: receipt.public_url,
    account_id: lane.nativeAccount || lane.account,
    integration_ref: lane.integrationRef,
    caption: value.caption,
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
    product_id: lane.product,
    account_id: lane.account,
    integration_ref: lane.integrationRef,
    public_url: receipt.public_url,
    pack_sha256: value.packRef.slice(-64),
    video_sha256: value.videoRef.slice(-64),
    caption_sha256: value.captionRef.slice(-64),
    evidence_ref: evidenceRef,
    verified_at: VERIFIED_AT,
    ...overrides,
  })));
}

function genericOptionsFor(value, publicationCalls, telegramCalls = [], lane = EN_LANE, overrides = {}) {
  return {
    env: value.env,
    runDistribution: providerCalls(publicationCalls, {}, lane),
    sendTelegram: async (...args) => {
      telegramCalls.push(args);
      return { ok: true, result: { message_id: 42 } };
    },
    fetchImpl: async (url) => (String(url).endsWith("embed/captioned/")
      ? { status: 200, text: async () => `<a class="CaptionUsername" href="https://www.instagram.com/${(lane.nativeAccount || lane.account).slice(1)}/">${lane.nativeAccount || lane.account}</a><div data-testid="caption">${value.caption}</div><script>{"GraphVideo":{"video_url":"${NATIVE_URL}"}}</script>` }
      : { status: 200, arrayBuffer: async () => NATIVE_BYTES.buffer.slice(NATIVE_BYTES.byteOffset, NATIVE_BYTES.byteOffset + NATIVE_BYTES.byteLength) }),
    videoComparator: async () => true,
    now: () => FIRST_NOW,
    ...overrides,
  };
}

function genericOptions(value, publicationCalls, telegramCalls = [], overrides = {}) {
  return genericOptionsFor(value, publicationCalls, telegramCalls, EN_LANE, overrides);
}

test("default native comparator accepts same/transcoded video but rejects visible differences", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-native-video-"));
  const red = path.join(dir, "red.mp4");
  const transcoded = path.join(dir, "red-transcoded.mp4");
  const green = path.join(dir, "green.mp4");
  const splitA = path.join(dir, "split-a.mp4");
  const splitB = path.join(dir, "split-b.mp4");
  const splitATranscoded = path.join(dir, "split-a-transcoded.mp4");
  const pattern = path.join(dir, "pattern.mp4");
  const patternInstagramLike = path.join(dir, "pattern-instagram-like.mp4");
  const splitATruncated = path.join(dir, "split-a-truncated.mp4");
  for (const [file, color] of [[red, "red"], [green, "green"]]) {
    execFileSync("ffmpeg", ["-loglevel", "error", "-y", "-f", "lavfi", "-i", `color=c=${color}:s=64x64:d=1:r=10`, "-pix_fmt", "yuv420p", file]);
  }
  execFileSync("ffmpeg", ["-loglevel", "error", "-y", "-i", red, "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", transcoded]);
  for (const [file, tail] of [[splitA, "blue"], [splitB, "green"]]) {
    execFileSync("ffmpeg", ["-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=64x64:d=1:r=30", "-f", "lavfi", "-i", `color=c=${tail}:s=64x64:d=14:r=30`, "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0,format=yuv420p[v]", "-map", "[v]", file]);
  }
  execFileSync("ffmpeg", ["-loglevel", "error", "-y", "-i", splitA, "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", splitATranscoded]);
  execFileSync("ffmpeg", ["-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=64x64:d=15:r=10", "-pix_fmt", "yuv420p", pattern]);
  execFileSync("ffmpeg", ["-loglevel", "error", "-y", "-i", pattern, "-vf", "eq=brightness=0.04:contrast=1.03:saturation=1.05", "-c:v", "libx264", "-crf", "28", "-pix_fmt", "yuv420p", patternInstagramLike]);
  execFileSync("ffmpeg", ["-loglevel", "error", "-y", "-i", splitA, "-t", "13.5", "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", splitATruncated]);
  assert.equal(compareNativeVideo(red, transcoded), true);
  assert.equal(compareNativeVideo(red, green), false);
  assert.equal(compareNativeVideo(splitA, splitATranscoded), true);
  assert.equal(compareNativeVideo(patternInstagramLike, pattern), true);
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

const JA_CAPTION = "ロック画面にアファメーション\n置けるの知らなかった\n\n#ロック画面 #アファメーション #ウィジェット #メンタルヘルス #アニッチャ\n";
const JA_CARD_CAPTION = "怠けてるんじゃない。\n脳が限界なだけ。\n\n#anicca #セルフケア #習慣 #AI\n";

test("JA widget wrapper is exact-lane and exact-slot only", () => {
  assert.deepEqual(parseJaArgs(["run", "--slot", SLOT]), { command: "run", slot: SLOT });
  assert.throws(() => parseJaArgs(["run", "--slot", "2026-08-26T07:30:00Z"]), /invalid|usage/i);
  assert.throws(() => parseJaArgs(["publish"]), /usage/i);
  assert.deepEqual(
    {
      tenant: JA_LANE.tenant,
      product: JA_LANE.product,
      locale: JA_LANE.locale,
      platform: JA_LANE.platform,
      account: JA_LANE.account,
      manifestAccount: JA_LANE.manifestAccount,
      profileRef: JA_LANE.profileRef,
      integrationId: JA_LANE.integrationId,
      integrationRef: JA_LANE.integrationRef,
      renderer: JA_LANE.renderer,
      format: JA_LANE.format,
      packFormat: JA_LANE.packFormat,
      form: JA_LANE.form,
      lane: JA_LANE.lane,
      creativeId: JA_LANE.creativeId,
      packEnv: JA_LANE.packEnv,
      videoEnv: JA_LANE.videoEnv,
      captionEnv: JA_LANE.captionEnv,
      approvalEnv: JA_LANE.approvalEnv,
      verificationEnv: JA_LANE.verificationEnv,
      approvedPackName: JA_LANE.approvedPackName,
      workerLabel: JA_LANE.workerLabel,
    },
    {
      tenant: "dais-local",
      product: "anicca-ios",
      locale: "ja",
      platform: "instagram",
      account: "@anicca.jp.videos",
      manifestAccount: "anicca-ios-ja-widget-instagram",
      profileRef: "profile://instagram/anicca.jp.videos",
      integrationId: "cmmzzg2es0539p30ycb94ayx0",
      integrationRef: "integration://postiz/instagram/cmmzzg2es0539p30ycb94ayx0",
      renderer: "reelclaw-widget",
      format: "reelclaw-widget",
      packFormat: "widget-demo-reel",
      form: "lockscreen-affirmation-widget",
      lane: "anicca-ja-widget-instagram",
      creativeId: "JA-WIDGET-CANARY-0c67b0a4d1de",
      packEnv: "LM_ANICCA_JA_WIDGET_PACK_REF",
      videoEnv: "LM_ANICCA_JA_WIDGET_VIDEO_REF",
      captionEnv: "LM_ANICCA_JA_WIDGET_CAPTION_REF",
      approvalEnv: "LM_ANICCA_JA_WIDGET_APPROVAL_REF",
      verificationEnv: "LM_ANICCA_JA_WIDGET_NATIVE_VERIFICATION_REF",
      approvedPackName: "anicca-ios-reelclaw-widget-ja.pack.json",
      workerLabel: "anicca-ja-widget-canary",
    },
  );
});

test("JA first publication binds exact integration and holds Telegram", async () => {
  const value = fixture(JA_LANE, JA_CAPTION);
  const publicationCalls = [];
  const telegramCalls = [];
  const result = await runAniccaJaWidgetCanary(
    ["run", "--slot", SLOT],
    genericOptionsFor(value, publicationCalls, telegramCalls, JA_LANE),
  );
  assert.equal(result.publication.created, true);
  assert.deepEqual(result.telegram, { created: false, held: true, message_id: null });
  assert.equal(publicationCalls.length, 1);
  assert.equal(publicationCalls[0].instagramIntegration, JA_LANE.integrationId);
  assert.equal(publicationCalls[0].instagramProfileStatePath, "");
  assert.equal(telegramCalls.length, 0);
  assert.doesNotMatch(fs.readFileSync(path.join(value.dataDir, "marketing", "jobs.jsonl"), "utf8"), /postiz-secret|telegram-secret|openclaw|\/Users\//i);
});

test("JA first effect arms only the target and restores exact controls", async () => {
  const value = fixture(JA_LANE, JA_CAPTION);
  const publicationCalls = [];
  let during;
  const result = await runAniccaJaWidgetCanary(["run", "--slot", SLOT], genericOptionsFor(value, publicationCalls, [], JA_LANE, {
    runDistribution: async (input) => {
      during = {
        manifest: JSON.parse(fs.readFileSync(value.manifestPath, "utf8")),
        fence: JSON.parse(fs.readFileSync(value.fencePath, "utf8")),
      };
      return providerCalls(publicationCalls, {}, JA_LANE)(input);
    },
  }));
  assert.equal(result.publication.created, true);
  assert.equal(during.fence.state, "open");
  assert.equal(during.fence.allowed_effect_key, `marketing:video:${JA_LANE.product}:instagram:${JA_LANE.creativeId}:${value.videoRef.slice(-64)}:${value.captionRef.slice(-64)}`);
  assert.deepEqual(during.manifest.lanes.map(({ integration_id, production_armed, lane_state }) => ({ integration_id, production_armed, lane_state })), [{ integration_id: JA_LANE.integrationId, production_armed: true, lane_state: "production-armed" }]);
  assert.deepEqual(fs.readFileSync(value.manifestPath), value.originalManifest);
  assert.deepEqual(fs.readFileSync(value.fencePath), value.originalFence);
  assert.equal(fs.statSync(value.manifestPath).mode & 0o777, value.originalManifestMode);
  assert.equal(fs.statSync(value.fencePath).mode & 0o777, value.originalFenceMode);
});

test("JA provider failure restores controls and is unknown effect", async () => {
  const value = fixture(JA_LANE, JA_CAPTION);
  const publicationCalls = [];
  await assert.rejects(runAniccaJaWidgetCanary(["run", "--slot", SLOT], genericOptionsFor(value, publicationCalls, [], JA_LANE, {
    runDistribution: async () => { publicationCalls.push(true); throw new Error("JA provider boundary failed"); },
  })), (error) => error.unknownEffect === true);
  assert.equal(publicationCalls.length, 1);
  assert.deepEqual(fs.readFileSync(value.manifestPath), value.originalManifest);
  assert.deepEqual(fs.readFileSync(value.fencePath), value.originalFence);
  assert.equal(fs.statSync(value.manifestPath).mode & 0o777, value.originalManifestMode);
  assert.equal(fs.statSync(value.fencePath).mode & 0o777, value.originalFenceMode);
});

test("JA identity mismatch blocks before secret and provider", async () => {
  for (const [target, patch, message] of [
    ["packRef", { account_id: "@wrong.ja" }, /pack/i],
    ["approvalRef", { integration_ref: "integration://postiz/instagram/wrong" }, /approval/i],
  ]) {
    const value = fixture(JA_LANE, JA_CAPTION);
    value.env[target === "packRef" ? JA_LANE.packEnv : JA_LANE.approvalEnv] = replaceJson(value, target, patch);
    const publicationCalls = [];
    const secretCalls = [];
    const integrationCalls = [];
    await assert.rejects(
      runAniccaJaWidgetCanary(["run", "--slot", SLOT], genericOptionsFor(value, publicationCalls, [], JA_LANE, {
        secretProvider: { get: async (...args) => { secretCalls.push(args); return "secret"; } },
        integrationProvider: { get: async (...args) => { integrationCalls.push(args); return JA_LANE.integrationId; } },
      })),
      message,
    );
    assert.equal(publicationCalls.length, 0);
    assert.equal(secretCalls.length, 0);
    assert.equal(integrationCalls.length, 0);
  }
});

test("JA verified native release sends one Telegram and same-slot replay is zero", async () => {
  const value = fixture(JA_LANE, JA_CAPTION);
  const publicationCalls = [];
  const telegramCalls = [];
  const options = genericOptionsFor(value, publicationCalls, telegramCalls, JA_LANE);
  const first = await runAniccaJaWidgetCanary(["run", "--slot", SLOT], options);
  const receipt = JSON.parse(fs.readFileSync(path.join(value.dataDir, "marketing", "receipts.jsonl"), "utf8")).receipt;
  value.env[JA_LANE.verificationEnv] = verification(value, receipt, {}, {}, JA_LANE);
  const second = await runAniccaJaWidgetCanary(["run", "--slot", SLOT], { ...options, now: () => VERIFIED_NOW });
  const third = await runAniccaJaWidgetCanary(["run", "--slot", SLOT], { ...options, now: () => VERIFIED_NOW });
  assert.equal(first.telegram.held, true);
  assert.deepEqual(second.telegram, { created: true, held: false, message_id: 42 });
  assert.deepEqual(third.telegram, { created: false, held: false, message_id: 42 });
  assert.equal(second.publication.created, false);
  assert.equal(third.publication.created, false);
  assert.equal(publicationCalls.length, 1);
  assert.equal(telegramCalls.length, 1);
});

test("JA Card wrapper is exact-lane and exact-slot only", () => {
  assert.deepEqual(parseJaCardArgs(["run", "--slot", SLOT]), { command: "run", slot: SLOT });
  assert.throws(() => parseJaCardArgs(["run", "--slot", "2026-08-26T07:30:00Z"]), /invalid|usage/i);
  assert.throws(() => parseJaCardArgs(["publish"]), /usage/i);
  assert.deepEqual(
    {
      name: JA_CARD_LANE.name,
      tenant: JA_CARD_LANE.tenant,
      product: JA_CARD_LANE.product,
      locale: JA_CARD_LANE.locale,
      platform: JA_CARD_LANE.platform,
      account: JA_CARD_LANE.account,
      nativeAccount: JA_CARD_LANE.nativeAccount,
      manifestAccount: JA_CARD_LANE.manifestAccount,
      profileRef: JA_CARD_LANE.profileRef,
      integrationRef: JA_CARD_LANE.integrationRef,
      integrationId: JA_CARD_LANE.integrationId,
      renderer: JA_CARD_LANE.renderer,
      format: JA_CARD_LANE.format,
      packFormat: JA_CARD_LANE.packFormat,
      form: JA_CARD_LANE.form,
      lane: JA_CARD_LANE.lane,
      creativeId: JA_CARD_LANE.creativeId,
      tokenRef: JA_CARD_LANE.tokenRef,
      telegramTokenRef: JA_CARD_LANE.telegramTokenRef,
      chatRef: JA_CARD_LANE.chatRef,
      packEnv: JA_CARD_LANE.packEnv,
      videoEnv: JA_CARD_LANE.videoEnv,
      captionEnv: JA_CARD_LANE.captionEnv,
      approvalEnv: JA_CARD_LANE.approvalEnv,
      verificationEnv: JA_CARD_LANE.verificationEnv,
      approvedPackName: JA_CARD_LANE.approvedPackName,
      workerLabel: JA_CARD_LANE.workerLabel,
      enforceApprovedPack: JA_CARD_LANE.enforceApprovedPack,
    },
    {
      name: "JACARD",
      tenant: "dais-local",
      product: "anicca-ios",
      locale: "ja",
      platform: "instagram",
      account: "@anicca.jp1",
      nativeAccount: "@anicca.ios.jp",
      manifestAccount: "anicca-ios-ja-instagram",
      profileRef: "profile://instagram/anicca.jp1",
      integrationRef: "integration://postiz/instagram/cmn8ycvtn02djqx0ytuisn9mw",
      integrationId: "cmn8ycvtn02djqx0ytuisn9mw",
      renderer: "reelclaw-card",
      format: "reelclaw-card",
      packFormat: "nudge-card-reel",
      form: "nudge-card",
      lane: "anicca-ja-card-instagram",
      creativeId: "JA-CARD-CANARY-35a15c7ce990",
      tokenRef: "secret://postiz/api-key",
      telegramTokenRef: "secret://telegram/bot-token",
      chatRef: "telegram-chat://owner",
      packEnv: "LM_ANICCA_JA_CARD_INSTAGRAM_PACK_REF",
      videoEnv: "LM_ANICCA_JA_CARD_INSTAGRAM_VIDEO_REF",
      captionEnv: "LM_ANICCA_JA_CARD_INSTAGRAM_CAPTION_REF",
      approvalEnv: "LM_ANICCA_JA_CARD_INSTAGRAM_APPROVAL_REF",
      verificationEnv: "LM_ANICCA_JA_CARD_INSTAGRAM_NATIVE_VERIFICATION_REF",
      approvedPackName: "anicca-ios-reelclaw-card-ja.pack.json",
      workerLabel: "anicca-ja-card-instagram-canary",
      enforceApprovedPack: true,
    },
  );
});

test("JA Card first publication uses dedicated refs, raw integration, empty profile state, and holds Telegram", async () => {
  const value = fixture(JA_CARD_LANE, JA_CARD_CAPTION);
  value.env.LM_ANICCA_MAIN_PACK_REF = "object://sha256/" + "f".repeat(64);
  value.env.LM_ANICCA_MAIN_MEDIA_REFS = JSON.stringify(["object://sha256/" + "e".repeat(64)]);
  value.env.LM_ANICCA_MAIN_INSTAGRAM_APPROVAL_REF = "object://sha256/" + "d".repeat(64);
  const publicationCalls = [];
  const telegramCalls = [];
  const result = await runAniccaJaCardInstagramCanary(
    ["run", "--slot", SLOT],
    genericOptionsFor(value, publicationCalls, telegramCalls, JA_CARD_LANE),
  );
  assert.equal(result.publication.created, true);
  assert.deepEqual(result.telegram, { created: false, held: true, message_id: null });
  assert.equal(publicationCalls.length, 1);
  assert.equal(publicationCalls[0].instagramIntegration, JA_CARD_LANE.integrationId);
  assert.equal(publicationCalls[0].instagramProfileStatePath, "");
  assert.equal(publicationCalls[0].videoPath, value.objectStore.resolve(value.videoRef));
  assert.equal(publicationCalls[0].captionPath, value.objectStore.resolve(value.captionRef));
  assert.equal(publicationCalls[0].approvalPath, value.objectStore.resolve(value.approvalRef));
  assert.equal(telegramCalls.length, 0);
});

test("JA Card missing or wrong dedicated pack/approval fails before secret and provider", async () => {
  for (const scenario of [
    { envKey: JA_CARD_LANE.packEnv, target: "packRef", patch: { account_id: "@wrong.card" } },
    { envKey: JA_CARD_LANE.approvalEnv, target: "approvalRef", patch: { integration_ref: "integration://postiz/instagram/wrong" } },
    { envKey: JA_CARD_LANE.packEnv, target: null, patch: null },
    { envKey: JA_CARD_LANE.approvalEnv, target: null, patch: null },
  ]) {
    const value = fixture(JA_CARD_LANE, JA_CARD_CAPTION);
    value.env.LM_ANICCA_MAIN_PACK_REF = "object://sha256/" + "f".repeat(64);
    value.env.LM_ANICCA_MAIN_MEDIA_REFS = JSON.stringify(["object://sha256/" + "e".repeat(64)]);
    value.env.LM_ANICCA_MAIN_INSTAGRAM_APPROVAL_REF = "object://sha256/" + "d".repeat(64);
    if (scenario.target) value.env[scenario.envKey] = replaceJson(value, scenario.target, scenario.patch);
    else delete value.env[scenario.envKey];
    const publicationCalls = [];
    const secretCalls = [];
    const integrationCalls = [];
    await assert.rejects(
      runAniccaJaCardInstagramCanary(["run", "--slot", SLOT], genericOptionsFor(value, publicationCalls, [], JA_CARD_LANE, {
        secretProvider: { get: async (...args) => { secretCalls.push(args); return "secret"; } },
        integrationProvider: { get: async (...args) => { integrationCalls.push(args); return JA_CARD_LANE.integrationId; } },
      })),
      /pack|approval/i,
    );
    assert.equal(publicationCalls.length, 0);
    assert.equal(secretCalls.length, 0);
    assert.equal(integrationCalls.length, 0);
  }
});

test("JA Card wrong native owner holds, exact native owner sends one Telegram, and same-slot replay is zero", async () => {
  const value = fixture(JA_CARD_LANE, JA_CARD_CAPTION);
  const publicationCalls = [];
  const telegramCalls = [];
  const options = genericOptionsFor(value, publicationCalls, telegramCalls, JA_CARD_LANE);
  const first = await runAniccaJaCardInstagramCanary(["run", "--slot", SLOT], options);
  const receipt = JSON.parse(fs.readFileSync(path.join(value.dataDir, "marketing", "receipts.jsonl"), "utf8")).receipt;
  value.env[JA_CARD_LANE.verificationEnv] = verification(value, receipt, {}, {}, JA_CARD_LANE);
  const wrongOwner = await runAniccaJaCardInstagramCanary(["run", "--slot", SLOT], {
    ...options,
    now: () => VERIFIED_NOW,
    fetchImpl: async (url) => (String(url).endsWith("embed/captioned/")
      ? { status: 200, text: async () => `<a class="CaptionUsername" href="https://www.instagram.com/${JA_CARD_LANE.account.slice(1)}/">${JA_CARD_LANE.account}</a><div data-testid="caption">${value.caption}</div><script>{"GraphVideo":{"video_url":"${NATIVE_URL}"}}</script>` }
      : { status: 200, arrayBuffer: async () => NATIVE_BYTES.buffer.slice(NATIVE_BYTES.byteOffset, NATIVE_BYTES.byteOffset + NATIVE_BYTES.byteLength) }),
  });
  const second = await runAniccaJaCardInstagramCanary(["run", "--slot", SLOT], {
    ...options,
    now: () => VERIFIED_NOW,
  });
  const third = await runAniccaJaCardInstagramCanary(["run", "--slot", SLOT], {
    ...options,
    now: () => VERIFIED_NOW,
  });
  assert.equal(first.telegram.held, true);
  assert.equal(wrongOwner.telegram.held, true);
  assert.deepEqual(second.telegram, { created: true, held: false, message_id: 42 });
  assert.deepEqual(third.telegram, { created: false, held: false, message_id: 42 });
  assert.equal(second.publication.created, false);
  assert.equal(third.publication.created, false);
  assert.equal(publicationCalls.length, 1);
  assert.equal(telegramCalls.length, 1);
});

test("default native verification uses DNS fallback for embed and media only", async () => {
  const value = fixture();
  const publicationCalls = [];
  const telegramCalls = [];
  const first = await runAniccaEnWidgetCanary(["run", "--slot", SLOT], genericOptions(value, publicationCalls, telegramCalls));
  const receipt = JSON.parse(fs.readFileSync(path.join(value.dataDir, "marketing", "receipts.jsonl"), "utf8")).receipt;
  value.env[EN_LANE.verificationEnv] = verification(value, receipt);
  const digHosts = [];
  const curlHosts = [];
  const fallbackOptions = {
    env: value.env,
    now: () => VERIFIED_NOW,
    defaultFetch: async () => { throw Object.assign(new Error("getaddrinfo ENOTFOUND"), { code: "ENOTFOUND" }); },
    digRunner: (args) => { digHosts.push(args.at(-1)); return { status: 0, stdout: "93.184.216.34" }; },
    curlRunner: (args) => {
      const url = args.at(-1);
      curlHosts.push(args[args.indexOf("--resolve") + 1]);
      const body = url.endsWith("embed/captioned/")
        ? `<a class="CaptionUsername" href="https://www.instagram.com/${ACCOUNT.slice(1)}/">${ACCOUNT}</a><div data-testid="caption">${CAPTION}</div><script>{"GraphVideo":{"video_url":"${NATIVE_URL}"}}</script>`
        : NATIVE_BYTES;
      return { status: 0, stdout: Buffer.concat([Buffer.from("HTTP/1.1 200 OK\r\n\r\n"), Buffer.from(body)]) };
    },
    sendTelegram: async (...args) => { telegramCalls.push(args); return { ok: true, result: { message_id: 42 } }; },
    videoComparator: async () => true,
  };
  const released = await runAniccaEnWidgetCanary(["run", "--slot", SLOT], fallbackOptions);
  assert.equal(first.telegram.held, true);
  assert.deepEqual(released.telegram, { created: true, held: false, message_id: 42 });
  assert.deepEqual(digHosts, ["www.instagram.com", "scontent.cdninstagram.com"]);
  assert.deepEqual(curlHosts, ["www.instagram.com:443:93.184.216.34", "scontent.cdninstagram.com:443:93.184.216.34"]);
});

test("lane clones are rejected before JA secret/provider/state access", async () => {
  const value = fixture(JA_LANE, JA_CAPTION);
  const untrusted = { ...JA_LANE };
  const secretCalls = [];
  const providerCallsSeen = [];
  assert.throws(() => parseArgs(["run", "--slot", SLOT], untrusted), /trusted|identity/i);
  await assert.rejects(
    runAniccaWidgetCanary(["run", "--slot", SLOT], {
      env: value.env,
      secretProvider: { get: async (...args) => { secretCalls.push(args); return "secret"; } },
      runDistribution: async (input) => { providerCallsSeen.push(input); return {}; },
    }, untrusted),
    /trusted|identity/i,
  );
  assert.equal(secretCalls.length, 0);
  assert.equal(providerCallsSeen.length, 0);
  assert.deepEqual(fs.readFileSync(value.manifestPath), value.originalManifest);
  assert.deepEqual(fs.readFileSync(value.fencePath), value.originalFence);
});
