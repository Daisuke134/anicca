"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { createGogLumaCodeReader } = require("./gog-luma-code-reader.js");

function message(overrides = {}) {
  return {
    body: "Your Luma verification code is 123456.",
    headers: {
      from: "Luma <login@calendar.luma-mail.com>",
      to: "dais@example.test",
      subject: "Your Luma verification code",
    },
    message: {
      id: "message-valid",
      internalDate: "1722500001000",
    },
    ...overrides,
  };
}

test("reads only a post-request Luma code from the selected gog account", async () => {
  const calls = [];
  const details = {
    stale: message({ message: { id: "stale", internalDate: "1722490000000" } }),
    foreign: message({
      headers: {
        from: "Attacker <login@evilluma-mail.com>",
        to: "dais@example.test",
        subject: "Luma verification code",
      },
      message: { id: "foreign", internalDate: "1722500003000" },
    }),
    valid: message(),
  };
  const reader = createGogLumaCodeReader({
    async run(args) {
      calls.push(args);
      if (args[1] === "messages") {
        return JSON.stringify([
          { id: "stale" },
          { id: "foreign" },
          { id: "valid" },
        ]);
      }
      return JSON.stringify(details[args[2]]);
    },
  });

  assert.equal(await reader({
    afterMs: 1_722_500_000_000,
    account: "dais@example.test",
  }), "123456");
  assert.deepEqual(calls[0], [
    "gmail", "messages", "search",
    "after:1722499995 (from:luma.com OR from:luma-mail.com)",
    "--account", "dais@example.test",
    "--max", "10", "--json", "--results-only", "--no-input",
  ]);
  assert.equal(calls.every((args) => args.includes("dais@example.test")), true);
});

test("rejects a code addressed to another account or hidden in non-Luma mail", async () => {
  for (const detail of [
    message({ headers: { ...message().headers, to: "other@example.test" } }),
    message({ headers: { ...message().headers, from: "Luma <login@luma.com.evil>" } }),
  ]) {
    const reader = createGogLumaCodeReader({
      async run(args) {
        return args[1] === "messages"
          ? JSON.stringify([{ id: "candidate" }])
          : JSON.stringify(detail);
      },
    });
    await assert.rejects(reader({
      afterMs: 1_722_500_000_000,
      account: "dais@example.test",
    }), /authentication mail unavailable/i);
  }
});

test("fails generically without leaking a malformed message or code", async () => {
  const reader = createGogLumaCodeReader({
    async run(args) {
      return args[1] === "messages"
        ? JSON.stringify([{ id: "candidate" }])
        : JSON.stringify(message({ body: "Luma code: abc123" }));
    },
  });
  await assert.rejects(reader({
    afterMs: 1_722_500_000_000,
    account: "dais@example.test",
  }), (error) => {
    assert.equal(error.message, "Luma authentication mail unavailable");
    assert.equal(error.message.includes("abc123"), false);
    return true;
  });
});
