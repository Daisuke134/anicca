"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { createGogLumaConfirmationReader } = require("./gog-luma-confirmation-reader.js");

test("Gmail confirmation reader polls and returns the newest trusted Luma message addressed to the account", async () => {
  const calls = [];
  let searches = 0;
  const read = createGogLumaConfirmationReader({
    attempts: 2,
    sleep: async () => {},
    run: async (args) => {
      calls.push(args);
      if (args[2] === "search") {
        searches += 1;
        return JSON.stringify(searches === 1 ? [] : [{ id: "mail-old" }, { id: "mail-new" }]);
      }
      const id = args[2];
      return JSON.stringify({
        message: { id, internalDate: id === "mail-new" ? 1_784_000_020_000 : 1_784_000_010_000 },
        headers: {
          from: "Luma <hello@t.luma-mail.com>",
          to: "Dais <dais@example.com>",
          subject: id === "mail-new" ? "Event A registration confirmed" : "Event B registration confirmed",
        },
        body: id === "mail-new"
          ? "https://luma.com/event-a?pk=g-abcdefgh https://luma.com/e/ticket/a?pk=g-abcdefgh"
          : "https://luma.com/event-b?pk=g-abcdefgh https://luma.com/e/ticket/b?pk=g-abcdefgh",
      });
    },
  });

  const message = await read({ account: "dais@example.com", afterMs: 1_784_000_000_000 });

  assert.equal(message.id, "mail-new");
  assert.equal(message.internalDate, "2026-07-14T03:33:40.000Z");
  assert.equal(message.from, "Luma <hello@t.luma-mail.com>");
  assert.match(message.body, /event-a/);
  assert.equal(searches, 2);
  assert.deepEqual(calls[0], [
    "gmail", "messages", "search",
    "after:1783999995 (from:luma.com OR from:luma-mail.com)",
    "--account", "dais@example.com",
    "--max", "10", "--json", "--results-only", "--no-input",
  ]);
});

test("Gmail confirmation reader rejects untrusted, misaddressed, and stale messages", async () => {
  const read = createGogLumaConfirmationReader({
    attempts: 1,
    run: async (args) => {
      if (args[2] === "search") return JSON.stringify([{ id: "bad" }]);
      return JSON.stringify({
        message: { id: "bad", internalDate: 1_784_000_000_000 },
        headers: { from: "fake@example.com", to: "other@example.com", subject: "confirmed" },
        body: "https://luma.com/event-a",
      });
    },
  });

  await assert.rejects(
    read({ account: "dais@example.com", afterMs: 1_784_000_010_000 }),
    /confirmation mail unavailable/i,
  );
});
