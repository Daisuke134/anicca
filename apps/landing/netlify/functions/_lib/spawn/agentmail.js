// AgentMail inbox provisioning for a child (its OWN sovereign inbox, like its OWN wallet). spec27b.
// Injectable fetch for tests; no fake success — a missing key or non-ok response throws.
async function createInbox(username, { apiKey, f = fetch } = {}) {
  if (!apiKey) throw new Error("agentmail: missing api key");
  const r = await f("https://api.agentmail.to/v0/inboxes", {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({ username }),
  });
  if (!r.ok) throw new Error(`agentmail ${r.status} ${await r.text()}`);
  const j = await r.json();
  const addr = j.inbox_id || j.address || j.email || "";
  if (!addr) throw new Error("agentmail: no inbox address in response");
  return addr;
}

module.exports = { createInbox };
