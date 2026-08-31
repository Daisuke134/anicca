"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  classifyTalkFormSnapshot,
  createTalkBrowserProvider,
} = require("./connector-talk-browser-provider.js");

test("form snapshot maps only ordinary talk fields and reports safety blockers", () => {
  assert.deepEqual(classifyTalkFormSnapshot({
    visible_text: "Lightning Talk application",
    fields: [
      { label: "Talk title", name: "entry.1", type: "text", required: true },
      { label: "Abstract", name: "entry.2", type: "textarea", required: true },
      { label: "Speaker bio", name: "entry.3", type: "textarea", required: true },
    ],
  }), { required_fields: ["title", "abstract", "bio"], blocking_flags: [] });
  assert.deepEqual(classifyTalkFormSnapshot({
    visible_text: "Payment required. Complete CAPTCHA and identity verification.",
    fields: [{ label: "Employer legal attestation", name: "entry.9", type: "text", required: true }],
  }), {
    required_fields: ["unknown_required_field"],
    blocking_flags: ["payment", "captcha", "identity_verification"],
  });
});

test("browser provider verifies fill, one submit control, and official confirmation readback", async () => {
  const calls = [];
  const page = {
    async evaluate(fn, arg) {
      calls.push([fn.name, arg]);
      if (fn.name === "snapshotTalkForm") return { visible_text: "LT application", fields: [{ label: "Talk title", name: "entry.1", type: "text", required: true }] };
      if (fn.name === "fillTalkForm") return { filled: Object.keys(arg) };
      if (fn.name === "submitTalkForm") return { clicked: 1 };
      if (fn.name === "readTalkConfirmation") return { url: "https://forms.example.com/talk-response", text: "Your response has been recorded.", active_form: false };
      assert.fail(`unexpected browser function ${fn.name}`);
    },
  };
  const provider = createTalkBrowserProvider();
  assert.deepEqual(await provider.inspectForm({ page }), { required_fields: ["title"], blocking_flags: [] });
  await provider.fillFields({ page, values: { title: "Mr.bot talk" } });
  await provider.clickSubmit({ page });
  const state = await provider.readProviderState({ page });
  assert.equal(state.status, "provider_verified");
  assert.match(state.receipt_ref, /^provider-receipt:\/\/connector\/talk\/[0-9a-f]{64}$/);
  assert.doesNotMatch(JSON.stringify(state), /Your response|Mr.bot talk/);
});

test("active form or ambiguous submit never becomes verified", async () => {
  const provider = createTalkBrowserProvider();
  const page = { async evaluate(fn) {
    if (fn.name === "readTalkConfirmation") return { url: "https://forms.example.com/talk", text: "Submit", active_form: true };
    if (fn.name === "submitTalkForm") return { clicked: 2 };
    return { visible_text: "", fields: [] };
  } };
  assert.deepEqual(await provider.readProviderState({ page }), { status: "unavailable" });
  await assert.rejects(provider.clickSubmit({ page }), /talk browser provider unavailable/i);
});
