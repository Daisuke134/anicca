// TDD for the self-spawn boot contract (spec27 §2 WF-A gap-fix #1 systemctl-active + #2 earn-on-wake).
// The verifier's core complaint was that a self-spawn DO droplet would boot a BARE docker image with no
// automaton.service => no `systemctl is-active` and no earn-on-wake. createDroplet() (reused by the
// self-spawn runner) embeds buildUserData() as cloud-init user_data; these assertions lock that the
// emitted cloud-config actually brings up a RUNNING, earning automaton.
const test = require("node:test");
const assert = require("node:assert");
const { buildUserData } = require("../../cloud-init.js");
const { createDroplet } = require("../../spawn-droplet.js");

const ud = buildUserData({ owner_email: "anicca-c003@agentmail.to", sub_id: "anicca-c003" });

test("cloud-init is a valid #cloud-config (first line)", () => {
  assert.ok(ud.startsWith("#cloud-config\n"), "must start with #cloud-config");
});

test("gap1: writes the automaton systemd unit and enables it on first boot (systemctl is-active)", () => {
  assert.match(ud, /\/etc\/systemd\/system\/automaton\.service/);
  assert.match(ud, /systemctl daemon-reload/);
  assert.match(ud, /systemctl enable --now automaton/);
});

test("gap1: writes the clawrouter unit too (the wallet-paid model gateway the loop needs)", () => {
  assert.match(ud, /\/etc\/systemd\/system\/clawrouter\.service/);
  assert.match(ud, /systemctl enable --now clawrouter/);
});

test("gap2: the automaton runs the autonomous earn loop on its own wake (not a telemetry-only heartbeat)", () => {
  assert.match(ud, /Environment=AUTOMATON_GOAL=earn/);
  assert.match(ud, /ExecStart=\/usr\/bin\/node \/opt\/automaton\/dist\/index\.js --run/);
});

test("gap3: durable StateDirectory (never /tmp) so children/earn ledgers survive a reboot", () => {
  assert.match(ud, /StateDirectory=anicca/);
  assert.match(ud, /ANICCA_STATE_DIR=\/var\/lib\/anicca/);
  assert.ok(!/(^|\s)\/tmp\/anicca/.test(ud), "must not stash durable state under /tmp");
});

test("createDroplet POSTs the cloud-init user_data (a self-spawn child is NOT a bare image)", async () => {
  let captured = null;
  const fakeFetch = async (url, opts) => {
    captured = JSON.parse(opts.body);
    return { ok: true, status: 201, json: async () => ({ droplet: { id: 999 } }) };
  };
  const id = await createDroplet({ owner_email: "anicca-c003@agentmail.to", sub_id: "anicca-c003" }, { token: "tok", f: fakeFetch });
  assert.strictEqual(id, 999);
  assert.ok(captured.user_data && captured.user_data.startsWith("#cloud-config"), "droplet must boot with cloud-init");
  assert.match(captured.user_data, /systemctl enable --now automaton/);
});
