import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  POSTIZ_EQUIVALENCE_FIELDS,
  buildPublishedResult,
  classifyUploadPage,
  directMigrationStatus,
  exactContract,
  loggedOutReadback,
  validatePublicVideoUrl,
} from "../lm-distribution/tiktok_direct.mjs";


test("direct adapter preserves the Postiz terminal output contract", () => {
  assert.deepEqual(POSTIZ_EQUIVALENCE_FIELDS, ["state", "post_url", "post_id"]);
  assert.deepEqual(
    buildPublishedResult("https://www.tiktok.com/@life/video/123", "123"),
    {
      state: "PUBLISHED",
      post_url: "https://www.tiktok.com/@life/video/123",
      post_id: "123",
      route: "direct_browser",
      provider_cost_usd: 0,
    },
  );
});

test("only an individual public TikTok video URL is accepted", () => {
  assert.equal(validatePublicVideoUrl("https://www.tiktok.com/@life/video/123"), true);
  assert.equal(validatePublicVideoUrl("https://www.tiktok.com/@life"), false);
  assert.equal(validatePublicVideoUrl("https://example.com/@life/video/123"), false);
});

test("upload preflight distinguishes login, verification, unavailable UI, and ready UI", () => {
  assert.equal(classifyUploadPage("https://www.tiktok.com/login", "", 0), "authentication_required");
  assert.equal(
    classifyUploadPage("https://www.tiktok.com/tiktokstudio/upload", "本人確認をお願いします", 0),
    "verification_required",
  );
  assert.equal(
    classifyUploadPage("https://www.tiktok.com/tiktokstudio/upload", "Creator Center", 0),
    "upload_unavailable",
  );
  assert.equal(
    classifyUploadPage("https://www.tiktok.com/tiktokstudio/upload", "Creator Center", 1),
    "ready",
  );
});

test("exact video and caption bytes are hashed before browser mutation", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "lm-9e-"));
  const video = path.join(root, "a.mp4");
  const caption = path.join(root, "a.txt");
  await writeFile(video, "exact-video");
  await writeFile(caption, "exact caption");
  const contract = await exactContract(video, caption);
  assert.equal(contract.video_sha256, "5512bdf8b6a6e465108fdbd6c4d5fce70c1624a6f37d58c81b9b7883da6576f8");
  assert.equal(contract.caption_sha256, "ac163a08cbd924500b08aabcf8dc6a5395e1a0084ffcc7a771bab916d236d293");
  assert.equal(contract.caption, "exact caption");
  await assert.rejects(() => exactContract(path.join(root, "missing.mp4"), caption));
});

test("logged-out readback requires exact post id and matching caption", () => {
  const runner = () => ({
    status: 0,
    stdout: JSON.stringify({
      id: "123",
      webpage_url: "https://www.tiktok.com/@life/video/123",
      description: "Exact caption\n#LifeManager",
    }),
  });
  assert.equal(
    loggedOutReadback(
      "https://www.tiktok.com/@life/video/123",
      "Exact caption\n#LifeManager",
      runner,
    ),
    true,
  );
  assert.equal(
    loggedOutReadback(
      "https://www.tiktok.com/@life/video/999",
      "Exact caption\n#LifeManager",
      runner,
    ),
    false,
  );
  assert.equal(
    loggedOutReadback(
      "https://www.tiktok.com/@life/video/123",
      "Different caption",
      runner,
    ),
    false,
  );
});

test("migration requires two consecutive real dates, logged-out readback, and zero direct cost", () => {
  const rows = [
    {
      date: "2026-07-24",
      route: "direct_browser",
      public_url: "https://www.tiktok.com/@life/video/123",
      logged_out_readback: true,
      provider_cost_usd: 0,
    },
  ];
  assert.deepEqual(directMigrationStatus(rows), {
    status: "started",
    day_index: 1,
    streak_dates: ["2026-07-24"],
  });
  assert.deepEqual(
    directMigrationStatus([
      ...rows,
      {
        ...rows[0],
        date: "2026-07-25",
        public_url: "https://www.tiktok.com/@life/video/456",
      },
    ]),
    {
      status: "done",
      day_index: 2,
      streak_dates: ["2026-07-24", "2026-07-25"],
    },
  );
});

test("invalid, duplicate, simulated, costly, or gapped rows cannot retire Postiz", () => {
  const valid = {
    date: "2026-07-24",
    route: "direct_browser",
    public_url: "https://www.tiktok.com/@life/video/123",
    logged_out_readback: true,
    provider_cost_usd: 0,
  };
  for (const bad of [
    { ...valid, date: "2026-07-25", route: "postiz" },
    { ...valid, date: "2026-07-25", logged_out_readback: false },
    { ...valid, date: "2026-07-25", provider_cost_usd: 0.01 },
    { ...valid, date: "2026-07-25", simulated: true },
  ]) {
    assert.equal(directMigrationStatus([valid, bad]).status, "started");
  }
  assert.equal(
    directMigrationStatus([valid, { ...valid, date: "2026-07-26", public_url: "https://www.tiktok.com/@life/video/789" }]).day_index,
    1,
  );
  assert.equal(directMigrationStatus([valid, valid]).day_index, 1);
});

test("CLI always emits one closed JSON failure instead of silently succeeding", () => {
  const script = new URL("../lm-distribution/tiktok_direct.mjs", import.meta.url);
  const result = spawnSync(
    process.execPath,
    [path.relative(process.cwd(), script.pathname)],
    { encoding: "utf8" },
  );
  assert.equal(result.status, 1);
  const lines = result.stdout.trim().split("\n");
  assert.equal(lines.length, 1);
  assert.deepEqual(Object.keys(JSON.parse(lines[0])).sort(), ["error", "state"]);
});
