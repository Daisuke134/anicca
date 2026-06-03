# state/

Runtime-mutated state files. `tunnel.sh` writes the live cloudflared public URL
to `public-url.txt` on every tunnel boot (atomic mv from a `.tmp.<pid>` sibling).

**Caveat**: this is a quick-tunnel URL — it rotates if the `ai.anicca.x402-tunnel`
launchd job is killed and respawned. The hourly `anicca-x402-uptime-check` cron
detects rotation and self-heals; for a truly stable host (e.g. `x402.aniccaai.com`)
see the round-4b notes in the spec about the NS1 + no-CF-zone blocker.

Canonical-store copy: `~/.openclaw/state/anicca_x402_url.txt` (mirrored at every
write by `tunnel.sh`).
