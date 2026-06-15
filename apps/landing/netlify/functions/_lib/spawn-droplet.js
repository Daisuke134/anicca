// DigitalOcean droplet provision/destroy via REST API v2. `f` is injectable for tests
// (defaults to the platform fetch — Node 20 global). Same injectable-fetch pattern as telemetry-store.js.
const { buildUserData } = require("./cloud-init");

const DO_API = "https://api.digitalocean.com/v2";

function doHeaders(token) {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

// Deterministic per-subscription droplet name so a Stripe retry can never spin up two droplets
// for the same subscription (second line of defense behind the markEventSeen idempotency ledger).
function dropletName(sub_id) {
  const tail = String(sub_id || "x").replace(/[^a-zA-Z0-9]/g, "").slice(-12).toLowerCase() || "x";
  return `anicca-${tail}`;
}

async function createDroplet({ owner_email, sub_id }, { token, sshKeyFp, f = fetch }) {
  const body = {
    name: dropletName(sub_id),
    region: "sfo3",
    size: "s-2vcpu-2gb",
    image: "ubuntu-24-04-x64",
    ssh_keys: sshKeyFp ? [sshKeyFp] : [],
    user_data: buildUserData({ owner_email, sub_id }),
    tags: ["anicca", "cloud-spawn"],
  };
  const r = await f(`${DO_API}/droplets`, { method: "POST", headers: doHeaders(token), body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`DO create ${r.status} ${await r.text()}`);
  const j = await r.json();
  const id = j && j.droplet && j.droplet.id;
  if (!id) throw new Error("DO create: no droplet id in response");
  return id;
}

async function destroyDroplet(droplet_id, { token, f = fetch }) {
  const r = await f(`${DO_API}/droplets/${encodeURIComponent(droplet_id)}`, { method: "DELETE", headers: doHeaders(token) });
  // DO returns 204 on delete, 404 if already gone — both are "destroyed" for our purposes.
  if (!r.ok && r.status !== 404) throw new Error(`DO destroy ${r.status} ${await r.text()}`);
  return true;
}

module.exports = { createDroplet, destroyDroplet, dropletName };
