import assert from "node:assert/strict";
import { test } from "node:test";
import { setEnvironmentContext } from "@netlify/blobs";
import go, { parseClick, targetUrl, clickKey } from "../site/netlify/functions/go.mjs";
import { summarize } from "../site/netlify/functions/go-stats.mjs";

test("go handler routes the continuity planner, preserves tracking, and rejects unknown IDs", async (t) => {
  const previousContext = process.env.NETLIFY_BLOBS_CONTEXT;
  t.after(() => {
    if (previousContext === undefined) delete process.env.NETLIFY_BLOBS_CONTEXT;
    else process.env.NETLIFY_BLOBS_CONTEXT = previousContext;
  });
  setEnvironmentContext({ siteID: "test", token: "test", edgeURL: "https://blobs.test" });
  t.mock.method(globalThis, "fetch", async () => new Response(null, { status: 200 }));

  const cases = [
    ["8123079349?ct=hooklab_x", "https://capafy.ai/agent/8123079349?utm_source=instagram_bio&utm_medium=bio_link&utm_campaign=capafy_marketing&ct=hooklab_x"],
    ["0000000000?ct=unknown", "https://capafy.ai/"],
    ["9425449917?ct=tiktok_series_blog", "https://capafy.ai/agent/9425449917?utm_source=instagram_bio&utm_medium=bio_link&utm_campaign=capafy_marketing&ct=tiktok_series_blog"],
    ["9425449917/x/continuity-20261102?ct=tiktok_series_x", "https://capafy.ai/agent/9425449917?utm_source=x&utm_medium=capafy_distribute&utm_campaign=capafy_marketing&utm_content=continuity-20261102&ct=tiktok_series_x"],
  ];
  for (const [path, location] of cases) {
    const response = await go(new Request(`https://capafy-skills-daily.netlify.app/go/${path}`));
    assert.equal(response.status, 302, path);
    assert.equal(response.headers.get("location"), location, path);
    assert.equal(response.headers.get("cache-control"), "no-store", path);
  }
});

test("legacy link keeps the exact old redirect and key shape", () => {
  const click = parseClick("https://x.app/.netlify/functions/go/8123079349");
  assert.equal(
    targetUrl(click),
    "https://capafy.ai/agent/8123079349?utm_source=instagram_bio&utm_medium=bio_link&utm_campaign=capafy_marketing",
  );
  assert.equal(clickKey(click, 1, "u"), "clicks/8123079349/1-u");
});

test("tracked link records platform/post and forwards ct", () => {
  const click = parseClick("https://x.app/go/8123079349/x/x-hook-lab-2026-10-31-am?ct=hooklab_x");
  assert.deepEqual(click, { agentId: "8123079349", platform: "x", post: "x-hook-lab-2026-10-31-am", ct: "hooklab_x" });
  assert.equal(clickKey(click, 1, "u"), "clicks/8123079349/x/x-hook-lab-2026-10-31-am/1-u");
  const target = new URL(targetUrl(click));
  assert.equal(target.searchParams.get("ct"), "hooklab_x");
  assert.equal(target.searchParams.get("utm_source"), "x");
  assert.equal(target.searchParams.get("utm_content"), "x-hook-lab-2026-10-31-am");
});

test("unsafe platform/post/ct tokens are dropped", () => {
  const click = parseClick("https://x.app/go/1/a%20b/c?ct=%3Cs%3E");
  assert.equal(click.platform, "");
  assert.equal(click.ct, "");
});

test("stats summarize legacy and tracked keys", () => {
  const { counts, detail } = summarize(
    ["clicks/1/5-u", "clicks/1/x/p1/6-u", "clicks/1/article/a1/7-u", "clicks/1/x/p1/8-u"],
    ["1", "2"],
  );
  assert.deepEqual(counts, { 1: 4, 2: 0 });
  assert.equal(detail.total, 4);
  assert.deepEqual(detail.platforms, { legacy: 1, x: 2, article: 1 });
  assert.deepEqual(detail.agents["1"].posts, { "x/p1": 2, "article/a1": 1 });
});


test("stats separate only the officially verified synthetic campaign and retain raw accounting", () => {
  const probes = Array.from({ length: 9 }, (_, i) => `clicks/1/x/test_hq_4a481d/${i}-u`);
  const keys = [...probes, "clicks/1/10-u", "clicks/1/x/real-post/11-u",
    "clicks/1/x/test_hq_4a481d_extra/12-u", "clicks/1/article/test_hq_4a481d/13-u"];
  const before = [...keys];
  const { counts, detail } = summarize(keys, ["1", "2"]);
  assert.deepEqual(counts, { 1: 4, 2: 0 });
  assert.equal(detail.total, 4);
  assert.deepEqual(detail.excluded_synthetic, { total: 9, posts: { "x/test_hq_4a481d": 9 } });
  assert.deepEqual(detail.platforms, { legacy: 1, x: 2, article: 1 });
  assert.equal(detail.agents["1"].posts["x/test_hq_4a481d"], undefined);
  assert.deepEqual(keys, before);
});
