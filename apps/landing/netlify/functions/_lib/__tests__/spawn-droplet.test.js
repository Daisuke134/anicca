const { test } = require("node:test");
const assert = require("node:assert");
const { createDroplet, destroyDroplet, dropletName } = require("../spawn-droplet");

test("dropletName is deterministic per subscription (retry-safe, DNS-safe)", () => {
  assert.strictEqual(dropletName("sub_ABC123"), dropletName("sub_ABC123"));
  assert.ok(/^anicca-[a-z0-9]+$/.test(dropletName("sub_ABC123!@#")));
});

test("createDroplet POSTs the DO API with cloud-init user_data and returns the id", async () => {
  let captured;
  const f = async (url, opts) => {
    captured = { url, opts };
    return { ok: true, json: async () => ({ droplet: { id: 999111 } }) };
  };
  const id = await createDroplet({ owner_email: "b@x.io", sub_id: "sub_9" }, { token: "tok", sshKeyFp: "fp:1", f });
  assert.strictEqual(id, 999111);
  assert.ok(captured.url.endsWith("/v2/droplets"));
  assert.strictEqual(captured.opts.method, "POST");
  const body = JSON.parse(captured.opts.body);
  assert.strictEqual(body.region, "sfo3");
  assert.strictEqual(body.size, "s-2vcpu-2gb");
  assert.deepStrictEqual(body.ssh_keys, ["fp:1"]);
  assert.ok(body.user_data.startsWith("#cloud-config"));
  assert.strictEqual(captured.opts.headers.Authorization, "Bearer tok");
});

test("createDroplet throws on non-ok DO response", async () => {
  const f = async () => ({ ok: false, status: 422, text: async () => "bad size" });
  await assert.rejects(() => createDroplet({ sub_id: "s" }, { token: "t", f }), /DO create 422/);
});

test("createDroplet throws when response has no droplet id", async () => {
  const f = async () => ({ ok: true, json: async () => ({}) });
  await assert.rejects(() => createDroplet({ sub_id: "s" }, { token: "t", f }), /no droplet id/);
});

test("destroyDroplet DELETEs and tolerates 204 + 404", async () => {
  let url, method;
  const f = async (u, o) => { url = u; method = o.method; return { ok: false, status: 404, text: async () => "gone" }; };
  const ok = await destroyDroplet(555, { token: "t", f });
  assert.strictEqual(ok, true);
  assert.ok(url.endsWith("/v2/droplets/555"));
  assert.strictEqual(method, "DELETE");
});

test("destroyDroplet throws on a real error (not 404)", async () => {
  const f = async () => ({ ok: false, status: 500, text: async () => "boom" });
  await assert.rejects(() => destroyDroplet(1, { token: "t", f }), /DO destroy 500/);
});
