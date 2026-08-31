"use strict";

const { makeSteelCdpClient } = require("../lib/steel-cdp-client.js");

const DEFAULT_TARGET_URL = "https://example.com/";
const DEFAULT_MARKER = "Example Domain";

function safeTargetUrl(value) {
  const parsed = new URL(value);
  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new Error("steel smoke target must use http or https");
  }
  if (parsed.username || parsed.password) {
    throw new Error("steel smoke target must not contain credentials");
  }
  return parsed.href;
}

function messageOf(error) {
  return String(error && error.message ? error.message : error).slice(0, 500);
}

async function runSteelCloudSmoke({
  client = makeSteelCdpClient(),
  targetUrl = DEFAULT_TARGET_URL,
  marker = DEFAULT_MARKER,
  now = () => new Date().toISOString(),
} = {}) {
  const target = safeTargetUrl(targetUrl);
  const evidence = {
    started_at: now(),
    target_url: target,
    steel_base_url: client.baseUrl || null,
    health: false,
    session_id: null,
    websocket_scheme: null,
    readback: null,
    released: false,
    ok: false,
  };
  let session = null;

  try {
    evidence.health = await client.health();
    if (!evidence.health) throw new Error("steel health check failed");

    session = await client.createSession({
      timezone: "Asia/Tokyo",
      dimensions: { width: 1280, height: 800 },
    });
    evidence.session_id = session.id;
    evidence.websocket_scheme = new URL(session.websocketUrl).protocol;

    await client.navigate(session.id, target);
    const page = await client.readConfirmation(session.id);
    evidence.readback = {
      final_url: safeTargetUrl(page.url),
      marker_present: typeof page.text === "string" && page.text.includes(marker),
    };
    evidence.ok = evidence.health
      && evidence.readback.final_url === target
      && evidence.readback.marker_present;
  } catch (error) {
    evidence.error = messageOf(error);
    evidence.ok = false;
  } finally {
    if (session && session.id) {
      try {
        evidence.released = await client.releaseSession(session.id);
      } catch (error) {
        evidence.release_error = messageOf(error);
        evidence.released = false;
      }
    }
    evidence.ok = evidence.ok && evidence.released;
    evidence.finished_at = now();
  }

  return evidence;
}

async function main() {
  const result = await runSteelCloudSmoke({
    targetUrl: process.env.STEEL_SMOKE_URL || DEFAULT_TARGET_URL,
    marker: process.env.STEEL_SMOKE_MARKER || DEFAULT_MARKER,
  });
  process.stdout.write(`${JSON.stringify(result)}\n`);
  if (!result.ok) process.exitCode = 1;
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${JSON.stringify({ ok: false, error: messageOf(error) })}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  DEFAULT_MARKER,
  DEFAULT_TARGET_URL,
  runSteelCloudSmoke,
  safeTargetUrl,
};
