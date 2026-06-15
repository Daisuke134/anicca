#!/usr/bin/env bash
# Q6 — bring up real automaton on a fresh DO droplet (verified working 2026-06-15, droplet 147.182.225.255)
# 1) create droplet (DO API, ssh key anicca-mac)
#    POST https://api.digitalocean.com/v2/droplets {name,region:sfo3,size:s-2vcpu-2gb,image:ubuntu-24-04-x64,ssh_keys:[fp]}
# 2) on droplet, provision (no secrets in user-data; SCP secrets after):
apt-get update -qq && apt-get install -y -qq git build-essential curl jq sqlite3
curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt-get install -y nodejs
npm i -g pnpm @blockrun/clawrouter
git clone --depth 1 https://github.com/Conway-Research/automaton /opt/automaton
cd /opt/automaton && pnpm install && (pnpm build || (npx tsc && pnpm -r build))
# 3) overlay OUR patched dist (OPENAI_BASE_URL/AUTOMATON_FORCE_MODEL support) — scp from ~/automaton/dist
# 4) SCP config: automaton.json(genesis=SOUL.md, conwayApiUrl=http://localhost:8402), wallet.json, heartbeat.yml
# 5) /opt/anicca.env: BLOCKRUN_WALLET_KEY, AGENTMAIL_API_KEY, OPENAI_API_KEY=clawrouter, OPENAI_BASE_URL=http://localhost:8402/v1, AUTOMATON_FORCE_MODEL=auto, HOME=/root
# 6) systemd: clawrouter.service + automaton.service(node dist/index.js --run) + report (agent self-invokes /opt/anicca-report.sh pre-sleep)
systemctl daemon-reload && systemctl enable --now clawrouter && sleep 6 && systemctl enable --now automaton
