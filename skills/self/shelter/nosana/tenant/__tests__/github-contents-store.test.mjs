// node:test — github-contents-store.mjs: the RemoteStateStore over GitHub's REST Contents API.
// No real network — fetchImpl is a fake in-memory GitHub simulator so these tests are hermetic and
// exercise the same getText/putText/putTextWithMerge/close contract store.mjs documents.
import { test } from "node:test";
import assert from "node:assert/strict";

import { createGithubContentsStore } from "../github-contents-store.mjs";

/** A tiny fake GitHub Contents API: one file, one sha, real conflict detection. */
function makeFakeGithub({ initialFiles = {} } = {}) {
  const files = new Map(Object.entries(initialFiles).map(([k, v]) => [k, { text: v, sha: "sha-0" }]));
  let shaCounter = 0;
  const calls = [];

  async function fetchImpl(url, options = {}) {
    calls.push({ url, method: options.method || "GET" });
    const match = url.match(/\/repos\/([^/]+)\/([^/]+)\/contents\/(.+?)(?:\?ref=.*)?$/);
    const key = decodeURIComponent(match[3]);

    if (!options.method || options.method === "GET") {
      const entry = files.get(key);
      if (!entry) return { ok: false, status: 404, json: async () => ({}) };
      return {
        ok: true,
        status: 200,
        json: async () => ({ content: Buffer.from(entry.text, "utf8").toString("base64"), sha: entry.sha }),
      };
    }

    if (options.method === "PUT") {
      const body = JSON.parse(options.body);
      const existing = files.get(key);
      if (existing && existing.sha !== body.sha) {
        return { ok: false, status: 409, json: async () => ({ message: "sha mismatch" }) };
      }
      if (!existing && body.sha) {
        return { ok: false, status: 422, json: async () => ({ message: "sha provided for new file" }) };
      }
      shaCounter += 1;
      const newSha = `sha-${shaCounter}`;
      files.set(key, { text: Buffer.from(body.content, "base64").toString("utf8"), sha: newSha });
      return { ok: true, status: existing ? 200 : 201, json: async () => ({ content: { sha: newSha } }) };
    }

    throw new Error(`unexpected method ${options.method}`);
  }

  return { fetchImpl, files, calls };
}

test("getText: returns null for a key that does not exist (404)", async () => {
  const { fetchImpl } = makeFakeGithub();
  const store = createGithubContentsStore({ repo: "o/r", token: "t", fetchImpl });
  assert.equal(await store.getText("missing.jsonl"), null);
});

test("getText: decodes base64 content back to the original text", async () => {
  const { fetchImpl } = makeFakeGithub({ initialFiles: { "nosana/x.jsonl": "hello\nworld\n" } });
  const store = createGithubContentsStore({ repo: "o/r", token: "t", fetchImpl });
  assert.equal(await store.getText("nosana/x.jsonl"), "hello\nworld\n");
});

test("putText then getText round-trips exactly", async () => {
  const { fetchImpl } = makeFakeGithub();
  const store = createGithubContentsStore({ repo: "o/r", token: "t", fetchImpl });
  await store.putText("nosana/y.jsonl", "row1\nrow2\n");
  assert.equal(await store.getText("nosana/y.jsonl"), "row1\nrow2\n");
});

test("putTextWithMerge: mergeFn deciding 'nothing new' (next === current) never issues a PUT", async () => {
  const { fetchImpl, calls } = makeFakeGithub({ initialFiles: { "k.jsonl": "same\n" } });
  const store = createGithubContentsStore({ repo: "o/r", token: "t", fetchImpl });
  const result = await store.putTextWithMerge("k.jsonl", async (current) => current);
  assert.equal(result, "same\n");
  assert.equal(calls.filter((c) => c.method === "PUT").length, 0);
});

test("putTextWithMerge: retries against fresh content on a 409 conflict, never silently dropping a row", async () => {
  const { fetchImpl, files } = makeFakeGithub({ initialFiles: { "k.jsonl": "a\n" } });
  const store = createGithubContentsStore({ repo: "o/r", token: "t", fetchImpl, maxPutRetries: 5 });

  let attempt = 0;
  const result = await store.putTextWithMerge("k.jsonl", async (current) => {
    attempt += 1;
    if (attempt === 1) {
      // Simulate a concurrent writer landing between our GET and our PUT.
      files.set("k.jsonl", { text: "a\nb\n", sha: "sha-racer" });
    }
    return `${current}new\n`;
  });
  assert.equal(result, "a\nb\nnew\n");
  assert.equal(attempt, 2, "mergeFn must be re-invoked with the fresh content after the conflict");
});

test("token is sent as a Bearer Authorization header, never in the URL", async () => {
  let sawAuthHeader = null;
  const fetchImpl = async (url, options) => {
    sawAuthHeader = options.headers.Authorization;
    assert.doesNotMatch(url, /secret-token/);
    return { ok: false, status: 404, json: async () => ({}) };
  };
  const store = createGithubContentsStore({ repo: "o/r", token: "secret-token-value", fetchImpl });
  await store.getText("k.jsonl");
  assert.equal(sawAuthHeader, "Bearer secret-token-value");
});

test("createGithubContentsStore: throws when token is missing", () => {
  assert.throws(() => createGithubContentsStore({ repo: "o/r", fetchImpl: async () => {} }), /token is required/);
});

test("createGithubContentsStore: throws on a malformed repo string", () => {
  assert.throws(() => createGithubContentsStore({ repo: "not-owner-slash-name", token: "t" }), /owner\/name/);
});

test("close(): resolves without throwing (no cleanup state to leak)", async () => {
  const { fetchImpl } = makeFakeGithub();
  const store = createGithubContentsStore({ repo: "o/r", token: "t", fetchImpl });
  await assert.doesNotReject(() => store.close());
});
