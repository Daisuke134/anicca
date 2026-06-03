#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# boot.sh — entrypoint baked into anicca-002 image (Dockerfile.hermes CMD).
#
# Sequence:
#   1. Verify CONSTITUTION.md hash matches EXPECTED_CONSTITUTION_HASH baked at
#      build time. Hard abort on mismatch.
#   2. Start a tiny HTTP /health server so Akash provider can probe liveness.
#   3. Tail the heartbeat process; restart on exit.

set -euo pipefail

INSTANCE_ID="${ANICCA_INSTANCE_ID:-anicca-002}"
echo "[boot] anicca-N starting: $INSTANCE_ID"

# 1. Constitution gate
if ! /anicca/constitution-hash.sh; then
  echo "[boot] constitution check failed — refusing to run"
  exit 30
fi

# 2. Inline /health server (python one-liner; will be replaced by full Hermes
# runtime in a later release).
python3 - <<'PYEOF' &
import http.server
import json
import socketserver
import time

START = time.time()

class Health(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({
                "ok": True,
                "instance_id": __import__("os").environ.get("ANICCA_INSTANCE_ID", "anicca-002"),
                "uptime_s": round(time.time() - START, 1),
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, *args, **kwargs):
        pass

with socketserver.TCPServer(("0.0.0.0", 8080), Health) as httpd:
    httpd.serve_forever()
PYEOF
HEALTH_PID=$!
echo "[boot] /health server pid=$HEALTH_PID"

# 3. Register with anicca-001 if peer-api reachable
if [[ -n "${PEER_API_BASE_URL:-}" ]]; then
  echo "[boot] registering with $PEER_API_BASE_URL"
  STATE_DIR="${ANICCA_HOME:-/anicca}/state"
  mkdir -p "$STATE_DIR"
  # Minimal payload — wallet/inbox/constitution are provided via env from spawn.sh
  printf '{"smart_account":"%s","network":"base-mainnet","broadcast":false}\n' \
    "${ANICCA_SMART_ACCOUNT:-unknown}" > "$STATE_DIR/wallet.json"
  printf '{"inbox_email":"%s","inbox_id":"%s","custom_address_succeeded":true}\n' \
    "${ANICCA_INBOX_EMAIL:-unknown}" "${ANICCA_INBOX_ID:-unknown}" > "$STATE_DIR/inbox.json"
  printf '{"sha256":"%s","captured_at":"%s"}\n' \
    "$(/anicca/constitution-hash.sh | awk '{print $NF}')" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$STATE_DIR/constitution.json"
  python3 /anicca/register.py --instance-id "$INSTANCE_ID" --state-dir "$STATE_DIR" \
    --peer-api "$PEER_API_BASE_URL" || true
fi

# 4. Heartbeat loop placeholder — in production this runs the Hermes agent.
echo "[boot] entering heartbeat loop"
while true; do
  echo "[heartbeat] $(date -u +%Y-%m-%dT%H:%M:%SZ) — anicca-002 alive"
  sleep 60
done

wait "$HEALTH_PID"
