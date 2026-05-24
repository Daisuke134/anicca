#!/usr/bin/env bash
# agent_{{profile.lateness.stakeholders.channel}}.sh — thin wrapper around /opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}.
# Sourced by monitor.sh / bill_tracker.sh / opensecrets.sh after
# api_clients.sh and slack_format.sh.
#
# Goals:
#   1. Public-web scraping (no API keys required) for civic-data monitors.
#   2. Per-monitor isolated session so cron-run state never leaks between modes.
#   3. Best-effort failure: if agent-{{profile.lateness.stakeholders.channel}} is missing, slack_skip cleanly.

AB_BIN="${AB_BIN:-/opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}}"

# Per-monitor isolated {{profile.lateness.stakeholders.channel}} session — prevents cookie/state leak across crons.
# MODE is set by each mode script; fall back to a generic name.
_ab_session() { printf 'politician-%s' "${MODE:-generic}"; }

# Returns 0 if the binary exists and is executable.
ab_available() { [[ -x "$AB_BIN" ]]; }

# ab_open <url> — open a fresh page in this monitor's session.
ab_open() {
  local url="$1"
  AGENT_BROWSER_SESSION="$(_ab_session)" "$AB_BIN" open "$url"
}

# ab_snapshot — interactive elements only, compact, with hrefs.
ab_snapshot() {
  AGENT_BROWSER_SESSION="$(_ab_session)" "$AB_BIN" snapshot -i -u -c
}

# ab_text — visible-text dump of the whole page (no refs needed for scraping).
# Uses `eval --stdin` so it survives quoted/special chars in the page.
ab_text() {
  AGENT_BROWSER_SESSION="$(_ab_session)" "$AB_BIN" eval --stdin <<'JS'
document.body && document.body.innerText ? document.body.innerText : ""
JS
}

# ab_close — release this session's {{profile.lateness.stakeholders.channel}} tab.
ab_close() {
  AGENT_BROWSER_SESSION="$(_ab_session)" "$AB_BIN" close 2>/dev/null || true
}

# ab_planned_invocation <url> — for DRY mode: print what we WOULD run.
ab_planned_invocation() {
  local url="$1"
  printf '[would-run] AGENT_BROWSER_SESSION=%q %q open %q\n' \
    "$(_ab_session)" "$AB_BIN" "$url"
  printf '[would-run] AGENT_BROWSER_SESSION=%q %q snapshot -i -u -c\n' \
    "$(_ab_session)" "$AB_BIN"
  printf '[would-run] AGENT_BROWSER_SESSION=%q %q eval --stdin  # body.innerText\n' \
    "$(_ab_session)" "$AB_BIN"
  printf '[would-run] AGENT_BROWSER_SESSION=%q %q close\n' \
    "$(_ab_session)" "$AB_BIN"
}

# pol_seen_path <key> — per-monitor dedupe state file.
pol_seen_path() {
  local key="$1"
  printf '%s/state/politician/%s-seen.json' "$HOME/.openclaw" "$key"
}

# pol_dedupe <key> <ids…on stdin>
# Reads candidate IDs (one per line) on stdin, prints only the NEW ones,
# and atomically updates the seen-set on disk.
pol_dedupe() {
  local key="$1"
  local seen="$(pol_seen_path "$key")"
  mkdir -p "$(dirname "$seen")"
  [[ -f "$seen" ]] || echo '[]' > "$seen"
  python3 - "$seen" <<'PY'
import json, sys, pathlib, os
seen_path = pathlib.Path(sys.argv[1])
seen = set(json.loads(seen_path.read_text() or "[]"))
new_ids = [ln.strip() for ln in sys.stdin if ln.strip()]
fresh = [i for i in new_ids if i not in seen]
for i in fresh:
    print(i)
seen.update(new_ids)
# cap the seen-set so it doesn't grow forever (keep newest 500)
keep = list(seen)[-500:]
tmp = seen_path.with_suffix(seen_path.suffix + ".tmp")
tmp.write_text(json.dumps(keep))
os.replace(tmp, seen_path)
PY
}
