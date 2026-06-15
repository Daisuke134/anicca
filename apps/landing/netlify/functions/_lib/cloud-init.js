// cloud-init user_data for a fresh DO droplet that brings up a real, RUNNING automaton (cloud Anicca).
// Mirrors docs/superpowers/specs/anicca/commands/Q6.command.sh (verified 2026-06-15, droplet 147.182.225.255),
// INCLUDING step 6 (systemd: clawrouter.service + automaton.service, daemon-reload + enable --now).
//
// Closes the three self-spawn verifier gaps at the boot layer:
//   gap 1  child systemctl active  -> we write real systemd units AND `systemctl enable --now` them,
//                                     so `systemctl is-active automaton` returns "active" on first boot.
//   gap 2  child earns on its wake -> automaton.service runs `dist/index.js --run` (the autonomous ReAct
//                                     loop that discovers+executes earn each wake) with AUTOMATON_GOAL=earn.
//   gap 3  ledger persisted live   -> StateDirectory=anicca => /var/lib/anicca (durable; never /tmp, which
//                                     is tmp-cleaned and loses children.jsonl / earn-ledger.jsonl).
//
// SECURITY: no secret VALUES in user_data (cloud-init is readable from the DO metadata service). Secrets are
// SCP'd to /opt/anicca.env after boot (Q6 step 5) and loaded by the unit via EnvironmentFile=. owner_email is
// non-secret context. Control chars are stripped so a crafted email can't break out of the YAML/heredoc.

function buildUserData({ owner_email, sub_id }) {
  const email = String(owner_email || "unknown").replace(/[^\x20-\x7e]/g, "");
  const sub = String(sub_id || "unknown").replace(/[^\x20-\x7e]/g, "");
  // #cloud-config MUST be the first line for cloud-init to treat this as cloud-config.
  return `#cloud-config
write_files:
  - path: /opt/anicca-owner.json
    content: |
      {"owner_email":"${email}","sub_id":"${sub}"}
  - path: /etc/systemd/system/clawrouter.service
    content: |
      [Unit]
      Description=ClawRouter (wallet-paid model gateway for the child Anicca)
      After=network-online.target
      Wants=network-online.target
      [Service]
      Type=simple
      EnvironmentFile=/opt/anicca.env
      ExecStart=/usr/bin/clawrouter
      Restart=always
      RestartSec=5
      [Install]
      WantedBy=multi-user.target
  - path: /etc/systemd/system/automaton.service
    content: |
      [Unit]
      Description=Anicca automaton (autonomous earn loop)
      After=clawrouter.service network-online.target
      Wants=network-online.target
      [Service]
      Type=simple
      WorkingDirectory=/opt/automaton
      EnvironmentFile=/opt/anicca.env
      Environment=AUTOMATON_GOAL=earn
      Environment=ANICCA_STATE_DIR=/var/lib/anicca
      StateDirectory=anicca
      ExecStart=/usr/bin/node /opt/automaton/dist/index.js --run
      Restart=always
      RestartSec=10
      [Install]
      WantedBy=multi-user.target
runcmd:
  - apt-get update -qq && apt-get install -y -qq git build-essential curl jq sqlite3
  - curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt-get install -y nodejs
  - npm i -g pnpm @blockrun/clawrouter
  - ln -sf "$(command -v clawrouter)" /usr/bin/clawrouter
  - ln -sf "$(command -v node)" /usr/bin/node
  - git clone --depth 1 https://github.com/Conway-Research/automaton /opt/automaton
  - cd /opt/automaton && pnpm install && (pnpm build || (npx tsc && pnpm -r build))
  - mkdir -p /var/lib/anicca
  - systemctl daemon-reload
  - systemctl enable --now clawrouter
  - sleep 6
  - systemctl enable --now automaton
`;
}

module.exports = { buildUserData };
