"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { fundraiserUserOnce } = require("./fundraiser-runtime.js");

test("fundraiser runtime queues one shared browser job from the durable runtime identity", async () => {
  let browserInput;
  const result = await fundraiserUserOnce({ uid: "tenant-1", telegram_chat_id: "42" }, Date.UTC(2026, 7, 26, 8, 2), {
    enqueueJob: async (job) => ({ created: true, job }),
    enqueueBrowserJob: async (input) => {
      browserInput = input;
      return { created: true, job: { id: "browser-1" } };
    },
  });

  assert.equal(result.status, "queued");
  assert.equal(result.browserStatus, "queued");
  assert.equal(result.browserJobId, "browser-1");
  assert.equal(browserInput.sourceKind, "runtime");
  assert.match(browserInput.sourceRef, /^runtime-job:\/\/fundraiser:/);
  assert.equal(browserInput.chatId, "42");
  assert.equal(browserInput.classification.actionKind, "fundraiser.acquire");
});

test("same 30-minute runtime slot repairs a missing browser enqueue idempotently", async () => {
  const sourceRefs = [];
  const deps = {
    enqueueJob: async (job) => ({ created: false, job }),
    enqueueBrowserJob: async (input) => {
      sourceRefs.push(input.sourceRef);
      return { created: false, job: { id: "browser-existing" } };
    },
  };
  const first = await fundraiserUserOnce({ uid: "tenant-1", telegram_chat_id: "42" }, 0, deps);
  const second = await fundraiserUserOnce({ uid: "tenant-1", telegram_chat_id: "42" }, 60_000, deps);

  assert.equal(first.status, "already_queued");
  assert.equal(second.browserStatus, "already_queued");
  assert.deepEqual(sourceRefs, [sourceRefs[0], sourceRefs[0]]);
});

test("fundraiser refuses to queue an unreportable browser job", async () => {
  await assert.rejects(
    fundraiserUserOnce({ uid: "tenant-1" }, 0, {}),
    /Telegram chat unavailable/,
  );
});
