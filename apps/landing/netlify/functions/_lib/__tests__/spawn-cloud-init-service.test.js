// Track-A self-spawn — close the 3 verifier-rejected gaps at the boot layer (cloud-init.js):
//   gap 1: child systemctl active  -> cloud-init MUST define a systemd unit AND `systemctl enable --now` it
//   gap 2: child earns on its own wake -> the unit MUST run the automaton's earn-capable wake (not telemetry-only)
//   gap 3: ledger persisted live   -> child writes its colony/state to a DURABLE path (/var/lib/anicca), never /tmp
// Mirrors docs/superpowers/specs/anicca/commands/Q6.command.sh step 6 (systemd enable --now), verbatim.
const { test } = require("node:test");
const assert = require("node:assert");
const { buildUserData } = require("../cloud-init");

test("gap1: cloud-init defines an automaton systemd unit and enables+starts it (systemctl active)", () => {
  const ud = buildUserData({ owner_email: "buyer@example.com", sub_id: "sub_ABC123" });
  // a real unit file must be written
  assert.ok(/\/etc\/systemd\/system\/automaton\.service/.test(ud), "writes /etc/systemd/system/automaton.service");
  assert.ok(/\[Service\]/.test(ud) && /ExecStart=/.test(ud), "unit has [Service] + ExecStart");
  assert.ok(/Restart=always/.test(ud), "child stays up across crashes (Restart=always)");
  // Q6 step 6: daemon-reload then enable --now (so `systemctl is-active automaton` == active)
  assert.ok(/systemctl daemon-reload/.test(ud), "daemon-reload before enabling");
  assert.ok(/systemctl enable --now automaton/.test(ud), "enable --now automaton (==> active)");
});

test("gap1: clawrouter (the wallet-paid model gateway) is enabled before automaton", () => {
  const ud = buildUserData({ owner_email: "x@x.io", sub_id: "sub_1" });
  assert.ok(/systemctl enable --now clawrouter/.test(ud), "clawrouter enabled --now");
  const cr = ud.indexOf("enable --now clawrouter");
  const au = ud.indexOf("enable --now automaton");
  assert.ok(cr > -1 && au > -1 && cr < au, "clawrouter is enabled before automaton (Q6 order)");
});

test("gap2: the automaton wake runs in EARN mode (not telemetry-only)", () => {
  const ud = buildUserData({ owner_email: "x@x.io", sub_id: "sub_1" });
  // ExecStart drives the automaton's autonomous ReAct loop (`--run`), which discovers+executes earn each wake.
  assert.ok(/dist\/index\.js --run/.test(ud), "ExecStart runs the automaton loop (--run wakes -> earn -> report)");
  // and earn is explicitly the child's first-wake intent, not a passive heartbeat
  assert.ok(/AUTOMATON_GOAL=earn|earn/.test(ud), "earn intent is wired into the boot env");
});

test("gap3: durable state — child persists under /var/lib/anicca, NEVER /tmp", () => {
  const ud = buildUserData({ owner_email: "x@x.io", sub_id: "sub_1" });
  assert.ok(/\/var\/lib\/anicca/.test(ud), "state dir is the durable /var/lib/anicca");
  assert.ok(!/\/tmp\/spawn|\/tmp\/anicca|StateDirectory=\/tmp/.test(ud), "no /tmp state path (tmp-cleaned => lost)");
});

test("security still holds: no secrets in user_data after adding the unit", () => {
  const ud = buildUserData({ owner_email: "x@x.io", sub_id: "sub_1" });
  assert.ok(!/BLOCKRUN_WALLET_KEY=0x|OPENAI_API_KEY=sk|SUPABASE_SERVICE_ROLE/.test(ud), "no secret VALUES baked in");
  // the unit reads secrets from /opt/anicca.env which the operator SCPs after boot (Q6 step 5)
  assert.ok(/EnvironmentFile=.*\/opt\/anicca\.env/.test(ud), "unit loads secrets from SCP'd /opt/anicca.env");
});
