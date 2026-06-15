const { test } = require("node:test");
const assert = require("node:assert");
const { buildUserData } = require("../cloud-init");

test("buildUserData starts with #cloud-config and embeds non-secret owner context", () => {
  const ud = buildUserData({ owner_email: "buyer@example.com", sub_id: "sub_ABC123" });
  assert.ok(ud.startsWith("#cloud-config"), "first line must be #cloud-config");
  assert.ok(ud.includes("buyer@example.com"));
  assert.ok(ud.includes("sub_ABC123"));
  assert.ok(ud.includes("Conway-Research/automaton"), "provisions the automaton (Q6)");
});

test("buildUserData contains NO secrets and strips control chars", () => {
  const ud = buildUserData({ owner_email: "x@x.io\n  malicious: true", sub_id: "sub_1" });
  assert.ok(!/BLOCKRUN_WALLET_KEY|OPENAI_API_KEY|SUPABASE_SERVICE_ROLE/.test(ud), "no secrets in user_data");
  // newline injection from email must not break out into a new yaml key
  assert.ok(!ud.includes('"x@x.io\n'), "control chars stripped from email");
});

test("buildUserData tolerates missing fields", () => {
  const ud = buildUserData({});
  assert.ok(ud.startsWith("#cloud-config"));
  assert.ok(ud.includes("unknown"));
});
