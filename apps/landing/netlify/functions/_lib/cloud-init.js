// cloud-init user_data for a fresh DO droplet that brings up a real automaton (cloud Anicca).
// Mirrors docs/superpowers/specs/anicca/commands/Q6.command.sh (verified 2026-06-15, droplet 147.182.225.255).
// SECURITY: no secrets in user_data (cloud-init is readable from the DO metadata service). Secrets are
// SCP'd to /opt/anicca.env after boot by the operator/self-spawn skill. owner_email is non-secret context.

function buildUserData({ owner_email, sub_id }) {
  const email = String(owner_email || "unknown").replace(/[^\x20-\x7e]/g, "");
  const sub = String(sub_id || "unknown").replace(/[^\x20-\x7e]/g, "");
  // #cloud-config MUST be the first line for cloud-init to treat this as cloud-config.
  return `#cloud-config
write_files:
  - path: /opt/anicca-owner.json
    content: |
      {"owner_email":"${email}","sub_id":"${sub}"}
runcmd:
  - apt-get update -qq && apt-get install -y -qq git build-essential curl jq sqlite3
  - curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt-get install -y nodejs
  - npm i -g pnpm @blockrun/clawrouter
  - git clone --depth 1 https://github.com/Conway-Research/automaton /opt/automaton
  - cd /opt/automaton && pnpm install && (pnpm build || (npx tsc && pnpm -r build))
`;
}

module.exports = { buildUserData };
