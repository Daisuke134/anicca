// lib/outbound-evidence.test.js — the honesty gate's own tests.
//
// The Evidence Contract (spec 2026-07-30-outbound-apply-engine-design.md §4) says success is
// E1 ∧ E2 ∧ E3. These tests exist so that a future "self-improve" pass that loosens the gate
// fails loudly instead of silently learning to lie.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

const EVIDENCE_URL = pathToFileURL(
  path.join(__dirname, "..", "..", "..", "runtime", "loop", "outbound", "evidence.mjs"),
).href;

const loadEvidence = () => import(EVIDENCE_URL);

// A PNG that is both magic-number correct and over the 5000 byte floor.
function goodPng(size = 6000) {
  const bytes = Buffer.alloc(size, 0x11);
  bytes[0] = 0x89;
  bytes[1] = 0x50;
  bytes[2] = 0x4e;
  bytes[3] = 0x47;
  return bytes;
}

function fullEvidence(overrides = {}) {
  return {
    e1: { kind: "http", status: 201 },
    e2: { bytes: goodPng(), path: "/tmp/receipt.png" },
    e3: {
      url: "https://luma.com/8tdfs50y",
      source_url: "https://luma.com/8tdfs50y",
      head_status: 200,
    },
    ...overrides,
  };
}

function codes(result) {
  return result.failures.map((failure) => failure.code);
}

test("evidence: E1 ∧ E2 ∧ E3 present → ok with zero failures", async () => {
  const { verifyEvidence } = await loadEvidence();
  const result = verifyEvidence(fullEvidence());
  assert.equal(result.ok, true);
  assert.deepEqual(result.failures, []);
});

test("evidence missing E1: no external response receipt → failed", async () => {
  const { verifyEvidence } = await loadEvidence();
  const result = verifyEvidence(fullEvidence({ e1: null }));
  assert.equal(result.ok, false);
  assert.ok(codes(result).includes("E1_ABSENT"), `expected E1_ABSENT, got ${codes(result)}`);
});

test("evidence missing E2: artifact absent → failed", async () => {
  const { verifyEvidence } = await loadEvidence();
  const result = verifyEvidence(fullEvidence({ e2: { path: "/tmp/receipt.png" } }));
  assert.equal(result.ok, false);
  assert.ok(codes(result).includes("E2_ABSENT"), `expected E2_ABSENT, got ${codes(result)}`);
});

test("evidence missing E3: canonical URL absent → failed", async () => {
  const { verifyEvidence } = await loadEvidence();
  const result = verifyEvidence(fullEvidence({ e3: null }));
  assert.equal(result.ok, false);
  assert.ok(codes(result).includes("E3_ABSENT"), `expected E3_ABSENT, got ${codes(result)}`);
});

test("E1 accepts a Gmail confirmation-email record and a ticket id", async () => {
  const { verifyEvidence } = await loadEvidence();
  const email = verifyEvidence(fullEvidence({
    e1: { kind: "email", message_id: "19fa9e1cc6f49e56", subject: "Registration confirmed" },
  }));
  assert.equal(email.ok, true);
  const ticket = verifyEvidence(fullEvidence({ e1: { kind: "ticket", ticket_id: "g-lAbPrfciSZzRRgy" } }));
  assert.equal(ticket.ok, true);
});

test("E1 rejects a non-2xx HTTP receipt and an email record with no message id", async () => {
  const { verifyEvidence } = await loadEvidence();
  assert.deepEqual(
    codes(verifyEvidence(fullEvidence({ e1: { kind: "http", status: 302 } }))),
    ["E1_NOT_2XX"],
  );
  assert.deepEqual(
    codes(verifyEvidence(fullEvidence({ e1: { kind: "email", message_id: "" } }))),
    ["E1_EMAIL_UNIDENTIFIED"],
  );
});

test("E2 rejects an artifact whose magic number is not PNG", async () => {
  const { verifyEvidence } = await loadEvidence();
  const notPng = Buffer.alloc(6000, 0x11);
  assert.deepEqual(
    codes(verifyEvidence(fullEvidence({ e2: { bytes: notPng } }))),
    ["E2_NOT_PNG"],
  );
});

test("E2 rejects a PNG under the 5000 byte floor", async () => {
  const { verifyEvidence } = await loadEvidence();
  assert.deepEqual(
    codes(verifyEvidence(fullEvidence({ e2: { bytes: goodPng(4999) } }))),
    ["E2_TOO_SMALL"],
  );
  assert.equal(verifyEvidence(fullEvidence({ e2: { bytes: goodPng(5000) } })).ok, true);
});

test("E3 rejects a /join/complete/ one-shot URL", async () => {
  const { verifyEvidence } = await loadEvidence();
  const result = verifyEvidence(fullEvidence({
    e3: {
      url: "https://luma.com/join/complete/g-lAbPrfciSZzRRgy",
      head_status: 200,
    },
  }));
  assert.equal(result.ok, false);
  assert.ok(codes(result).includes("E3_ONE_SHOT_URL"), `got ${codes(result)}`);
});

test("E3 rejects a URL that lost its subdomain", async () => {
  const { verifyEvidence } = await loadEvidence();
  const result = verifyEvidence(fullEvidence({
    e3: {
      url: "https://connpass.com/event/123456/",
      source_url: "https://sample-community.connpass.com/event/123456/",
      head_status: 200,
    },
  }));
  assert.equal(result.ok, false);
  assert.ok(codes(result).includes("E3_SUBDOMAIN_LOST"), `got ${codes(result)}`);
});

test("E3 keeps a URL that preserved its subdomain", async () => {
  const { verifyEvidence } = await loadEvidence();
  const result = verifyEvidence(fullEvidence({
    e3: {
      url: "https://sample-community.connpass.com/event/123456/",
      source_url: "https://sample-community.connpass.com/event/123456/",
      head_status: 200,
    },
  }));
  assert.equal(result.ok, true);
});

test("E3 requires the observed HEAD status and demands exactly 200", async () => {
  const { verifyEvidence } = await loadEvidence();
  assert.deepEqual(
    codes(verifyEvidence(fullEvidence({ e3: { url: "https://luma.com/x" } }))),
    ["E3_NO_HEAD_STATUS"],
  );
  assert.deepEqual(
    codes(verifyEvidence(fullEvidence({ e3: { url: "https://luma.com/x", head_status: 404 } }))),
    ["E3_HEAD_NOT_200"],
  );
});

test("E3 rejects an unparseable URL", async () => {
  const { verifyEvidence } = await loadEvidence();
  assert.deepEqual(
    codes(verifyEvidence(fullEvidence({ e3: { url: "not a url", head_status: 200 } }))),
    ["E3_UNPARSEABLE"],
  );
});

test("verifyEvidence reports every missing limb at once and never mutates its input", async () => {
  const { verifyEvidence } = await loadEvidence();
  const input = { e1: null, e2: null, e3: null };
  const frozen = JSON.stringify(input);
  const result = verifyEvidence(input);
  assert.equal(result.ok, false);
  assert.deepEqual(codes(result).sort(), ["E1_ABSENT", "E2_ABSENT", "E3_ABSENT"]);
  assert.equal(JSON.stringify(input), frozen);
});

test("the evidence module performs no I/O: it exposes no reader and no writer", async () => {
  const evidence = await loadEvidence();
  const exported = Object.keys(evidence).sort();
  assert.deepEqual(exported, ["ARTIFACT_MIN_BYTES", "PNG_MAGIC", "verifyEvidence"]);
});

test("the evidence module carries the self-improve read-only banner", async () => {
  const source = require("node:fs").readFileSync(
    path.join(__dirname, "..", "..", "..", "runtime", "loop", "outbound", "evidence.mjs"),
    "utf8",
  );
  assert.match(source, /self-improve/i);
  assert.match(source, /never write/i);
});
