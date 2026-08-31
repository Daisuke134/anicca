"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  importMarketingVideoPack,
} = require("./import-marketing-video-pack.js");
const { resolveContentObject } = require("../lib/content-object-store.js");

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-video-pack-import-"));
  const hooks = path.join(root, "legacy-hooks.json");
  const media = path.join(root, "media");
  fs.mkdirSync(media);
  fs.writeFileSync(hooks, JSON.stringify({
    hooksByVideo: {
      "one.mp4": [
        {
          id: "HJA-002",
          lines: ["line one", "line two"],
          status: "preferred",
          lastUsed: "2026-07-29T12:30:00+09:00",
        },
        {
          id: "HJA-001",
          text: "unused hook",
        },
      ],
    },
  }));
  fs.writeFileSync(path.join(media, "v2.mp4"), Buffer.from("0000ftyp-video-two"));
  fs.writeFileSync(path.join(media, "v1.mp4"), Buffer.from("0000ftyp-video-one"));
  return { root, hooks, media };
}

test("one-time import creates a canonical product/format pack and sorted media refs", () => {
  const { root, hooks, media } = fixture();
  const dataDir = path.join(root, "runtime");
  const result = importMarketingVideoPack([
    "--data-dir", dataDir,
    "--tenant", "tenant-a",
    "--product", "honne-ai",
    "--format", "reelclaw",
    "--form", "relationship-confession",
    "--locale", "ja",
    "--title", "Honne — 言いたいこと、翻訳します",
    "--hooks", hooks,
    "--media-dir", media,
  ]);

  assert.equal(result.tenant_id, "tenant-a");
  assert.equal(result.product_id, "honne-ai");
  assert.equal(result.format_id, "reelclaw");
  assert.match(result.pack_ref, /^object:\/\/sha256\/[0-9a-f]{64}$/);
  assert.equal(result.media_refs.length, 2);
  assert.ok(result.media_refs.every((ref) => /^object:\/\/sha256\/[0-9a-f]{64}$/.test(ref)));
  assert.doesNotMatch(JSON.stringify(result), /legacy-hooks|\/Users\/|\.openclaw/);

  const objectDir = path.join(dataDir, "objects");
  const pack = JSON.parse(fs.readFileSync(
    resolveContentObject(result.pack_ref, { objectDir }),
    "utf8",
  ));
  assert.deepEqual(pack, {
    schema_version: 1,
    product_id: "honne-ai",
    format_id: "reelclaw",
    form: "relationship-confession",
    locale: "ja",
    title: "Honne — 言いたいこと、翻訳します",
    hashtags: [],
    hooks: [
      {
        id: "HJA-001",
        text: "unused hook",
        status: "active",
        prior_used_at: null,
      },
      {
        id: "HJA-002",
        text: "line one\nline two",
        status: "preferred",
        prior_used_at: "2026-07-29T03:30:00.000Z",
      },
    ],
  });
  const manifest = path.join(
    dataDir,
    "tenants",
    "tenant-a",
    "marketing",
    "imports",
    "honne-ai-reelclaw-ja.json",
  );
  assert.equal(fs.statSync(manifest).mode & 0o777, 0o600);
  assert.deepEqual(JSON.parse(fs.readFileSync(manifest, "utf8")), result);
});

test("import rejects non-MP4 media and duplicate hook identities", () => {
  const first = fixture();
  fs.writeFileSync(path.join(first.media, "v3.mp4"), Buffer.from("not-an-mp4"));
  assert.throws(() => importMarketingVideoPack([
    "--data-dir", path.join(first.root, "runtime"),
    "--tenant", "tenant-a",
    "--product", "honne-ai",
    "--format", "reelclaw",
    "--form", "relationship-confession",
    "--locale", "ja",
    "--title", "Honne",
    "--hooks", first.hooks,
    "--media-dir", first.media,
  ]), /MP4/i);

  const second = fixture();
  fs.writeFileSync(second.hooks, JSON.stringify({
    hooks: [
      { id: "same", text: "one" },
      { id: "same", text: "two" },
    ],
  }));
  assert.throws(() => importMarketingVideoPack([
    "--data-dir", path.join(second.root, "runtime"),
    "--tenant", "tenant-a",
    "--product", "honne-ai",
    "--format", "reelclaw",
    "--form", "relationship-confession",
    "--locale", "ja",
    "--title", "Honne",
    "--hooks", second.hooks,
    "--media-dir", second.media,
  ]), /duplicate/i);
});
