#!/usr/bin/env bash
# Emit the #cloud-config user_data for a fresh DO droplet that brings up a real, RUNNING child Anicca.
# Verbatim port of apps/landing/netlify/functions/_lib/cloud-init.js (proven 2026-06-15, droplet
# 147.182.225.255), INCLUDING the systemd units (clawrouter.service + automaton.service) so the child
# runs a real restart-always service — not just an installed build.
#
#   gap 1 child systemctl active  -> systemd units written AND `systemctl enable --now` -> is-active=active
#   gap 2 child earns on its wake -> automaton.service ExecStart=node dist/index.js --run, AUTOMATON_GOAL=earn
#   gap 3 ledger persisted live   -> StateDirectory=anicca => /var/lib/anicca (durable; never /tmp)
#
# SECURITY: NO secret VALUES in user_data (DO metadata is readable). Secrets are SCP'd to /opt/anicca.env
# after boot and loaded via EnvironmentFile=. owner_email/sub_id are non-secret; control chars stripped so
# a crafted value can't break out of the YAML/heredoc.
set -euo pipefail

CHILD_ID="${1:?cloud-init.sh: CHILD_ID required}"
OWNER_EMAIL="${2:-${CHILD_ID}@agentmail.to}"

# strip everything outside printable ASCII (matches the JS /[^\x20-\x7e]/g guard)
sanitize() { printf '%s' "$1" | LC_ALL=C tr -cd '\40-\176'; }
EMAIL="$(sanitize "$OWNER_EMAIL")"
SUB="$(sanitize "$CHILD_ID")"

cat <<CLOUDINIT
#cloud-config
write_files:
  - path: /opt/anicca-owner.json
    content: |
      {"owner_email":"${EMAIL}","sub_id":"${SUB}"}
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
  - ln -sf "\$(command -v clawrouter)" /usr/bin/clawrouter
  - ln -sf "\$(command -v node)" /usr/bin/node
  - git clone --depth 1 https://github.com/Conway-Research/automaton /opt/automaton
  - cd /opt/automaton && pnpm install && (pnpm build || (npx tsc && pnpm -r build))
  - mkdir -p /var/lib/anicca
  - systemctl daemon-reload
  - systemctl enable --now clawrouter
  - sleep 6
  - systemctl enable --now automaton
CLOUDINIT
