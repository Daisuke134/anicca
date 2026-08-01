"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  canonicalEventUrl,
  connpassEventUrlsFromText,
} = require("./canonical-event-url.js");

test("connpass canonical URL preserves the discovered group subdomain", () => {
  assert.equal(
    canonicalEventUrl(
      "https://data-learning-guild.connpass.com/event/400425?utm_source=search#about",
    ),
    "https://data-learning-guild.connpass.com/event/400425/",
  );
});

test("connpass URLs extracted from discovery text retain each original host", () => {
  const text = [
    "https://tokyo-ai.connpass.com/event/400001",
    "https://connpass.com/event/400002/",
    "https://web3-tokyo.connpass.com/event/400003/?utm_campaign=test",
  ].join("\n");

  assert.deepEqual(connpassEventUrlsFromText(text), [
    "https://tokyo-ai.connpass.com/event/400001/",
    "https://connpass.com/event/400002/",
    "https://web3-tokyo.connpass.com/event/400003/",
  ]);
});

test("one-shot, credential-bearing, non-HTTPS, and non-event connpass URLs are refused", () => {
  assert.equal(
    canonicalEventUrl("https://group.connpass.com/event/400425/join/complete/"),
    null,
  );
  assert.equal(canonicalEventUrl("https://user:secret@lu.ma/tokyo-ai"), null);
  assert.equal(canonicalEventUrl("http://lu.ma/tokyo-ai"), null);
  assert.equal(canonicalEventUrl("https://group.connpass.com/search/?q=AI"), null);
});

test("Luma and other HTTPS event URLs keep their path and lose only the fragment", () => {
  assert.equal(
    canonicalEventUrl("https://lu.ma/tokyo-ai?tk=public#details"),
    "https://lu.ma/tokyo-ai?tk=public",
  );
  assert.equal(
    canonicalEventUrl("https://events.example.com/tokyo/founders#tickets"),
    "https://events.example.com/tokyo/founders",
  );
});
