#!/usr/bin/env bash
# sync-env-to-plist.sh — propagate ~/.openclaw/.env into the gateway launchd
# plist's EnvironmentVariables, then reload. The gateway reads its env from
# the PLIST (not .env), so any rotated key MUST be synced here or the gateway
# keeps using the stale value. Run after editing .env.
#   bash ~/.openclaw/skills/_shared/sync-env-to-plist.sh
set -euo pipefail
PLIST="$HOME/Library/LaunchAgents/ai.openclaw.gateway.plist"
ENVFILE="$HOME/.openclaw/.env"
cp "$PLIST" "/tmp/gateway.plist.bak.$(date +%s)"
python3 - "$PLIST" "$ENVFILE" <<'PY'
import plistlib, sys
plist_path, env_path = sys.argv[1], sys.argv[2]
with open(plist_path,"rb") as f: pl=plistlib.load(f)
env=dict(pl.get("EnvironmentVariables",{}))
changed=added=0
for line in open(env_path):
    s=line.strip()
    if not s or s.startswith("#"): continue
    if s.startswith("export "): s=s[7:]
    if "=" not in s: continue
    k,v=s.split("=",1); k=k.strip(); v=v.strip().strip('"').strip("'")
    if not k: continue
    if k in env:
        if env[k]!=v: env[k]=v; changed+=1
    else:
        env[k]=v; added+=1
pl["EnvironmentVariables"]=env
with open(plist_path,"wb") as f: plistlib.dump(pl,f)
print(f"synced: {changed} changed, {added} added, {len(env)} total")
PY
plutil -lint "$PLIST" >/dev/null && echo "plist lint OK"
launchctl unload "$PLIST" 2>/dev/null || true
sleep 2
launchctl load "$PLIST"
echo "gateway reloaded — verify with: openclaw gateway status"
