import assert from "node:assert/strict";
import { test } from "node:test";
import { setEnvironmentContext } from "@netlify/blobs";
import go, { parseClick, targetUrl, clickKey } from "../site/netlify/functions/go.mjs";
import stats, { summarize } from "../site/netlify/functions/go-stats.mjs";

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


test("go saves sanitized attribution, without unrelated query or request headers", async (t) => {
  const previous = process.env.NETLIFY_BLOBS_CONTEXT;
  t.after(() => { if (previous === undefined) delete process.env.NETLIFY_BLOBS_CONTEXT; else process.env.NETLIFY_BLOBS_CONTEXT = previous; });
  setEnvironmentContext({ siteID: "test", token: "test", edgeURL: "https://blobs.test" });
  let stored;
  t.mock.method(globalThis, "fetch", async (url, options) => {
    stored = JSON.parse(options.body);
    return new Response(null, { status: 200 });
  });
  const response = await go(new Request("https://landing.test/go/8123079349/x/post-1?ct=hooklab_x&email=private", { headers: { "user-agent": "private" } }));
  assert.equal(response.status, 302);
  assert.deepEqual(stored, { schema_version: 1, agentId: "8123079349", platform: "x", post: "post-1", ct: "hooklab_x" });
  await go(new Request("https://landing.test/go/8123079349?ct=bad%20token"));
  assert.equal(stored.ct, "");
});

test("detailed attribution counts saved ct, leaves old or invalid bodies unknown, and excludes verified probes", () => {
  const keys = ["clicks/1/1-u", "clicks/1/x/p/2-u", "clicks/1/x/p/3-u", "clicks/1/x/test_hq_4a481d/4-u", "clicks/1/5-u"];
  const bodies = new Map([
    [keys[0], 1],
    [keys[1], { schema_version: 1, agentId: "1", platform: "x", post: "p", ct: "hooklab_x" }],
    [keys[2], { schema_version: 1, agentId: "1", platform: "x", post: "p", ct: "invalid token" }],
    [keys[3], { schema_version: 1, agentId: "1", platform: "x", post: "test_hq_4a481d", ct: "probe" }],
    [keys[4], { schema_version: 1, agentId: "1", platform: "", post: "", ct: "hooklab_x" }],
  ]);
  const { counts, detail } = summarize(keys, ["1"], bodies);
  assert.deepEqual(counts, { 1: 4 });
  assert.deepEqual(JSON.parse(JSON.stringify(detail.attribution)), { recorded: 2, unavailable: 2, agents: { "1": { hooklab_x: 2 } } });
});


test("stats opt-in reads stored bodies through the SDK; default counts need no body fetch", async (t) => {
  const previous = process.env.NETLIFY_BLOBS_CONTEXT;
  t.after(() => { if (previous === undefined) delete process.env.NETLIFY_BLOBS_CONTEXT; else process.env.NETLIFY_BLOBS_CONTEXT = previous; });
  setEnvironmentContext({ siteID: "test", token: "test", edgeURL: "https://blobs.test" });
  const key = "clicks/8123079349/x/p/1-u";
  let reads = 0;
  t.mock.method(globalThis, "fetch", async (url) => {
    if (new URL(url).searchParams.has("prefix")) return Response.json({ blobs: [{ key, etag: "e" }] });
    reads += 1;
    return Response.json({ schema_version: 1, agentId: "8123079349", platform: "x", post: "p", ct: "hooklab_x" });
  });
  const flat = await (await stats(new Request("https://landing.test/go-stats"))).json();
  assert.equal(flat["8123079349"], 1);
  assert.equal(reads, 0);
  const detail = await (await stats(new Request("https://landing.test/go-stats?detail=1&attribution=1"))).json();
  assert.deepEqual(detail.attribution, { recorded: 1, unavailable: 0, agents: { "8123079349": { hooklab_x: 1 } } });
  assert.equal(reads, 1);
});


test("attribution readback does not turn storage failure into zero or success", async (t) => {
  const previous = process.env.NETLIFY_BLOBS_CONTEXT;
  t.after(() => { if (previous === undefined) delete process.env.NETLIFY_BLOBS_CONTEXT; else process.env.NETLIFY_BLOBS_CONTEXT = previous; });
  setEnvironmentContext({ siteID: "test", token: "test", edgeURL: "https://blobs.test" });
  t.mock.method(globalThis, "fetch", async (url) => {
    if (new URL(url).searchParams.has("prefix")) return Response.json({ blobs: [{ key: "clicks/8123079349/1-u", etag: "e" }] });
    return new Response("unavailable", { status: 403 });
  });
  await assert.rejects(stats(new Request("https://landing.test/go-stats?detail=1&attribution=1")));
});
