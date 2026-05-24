#!/usr/bin/env bash
# lib/camofox.sh — clean wrapper around camofox-{{profile.lateness.stakeholders.channel}} :9377 REST API.
#
# Why: agent-{{profile.lateness.stakeholders.channel}} is rejected by Google OAuth bot detection. camofox uses
#      Firefox-level fingerprint spoofing → bypasses Google / reCAPTCHA /
#      Cloudflare. All Cafe (and other AI brand) flows that need OAuth or
#      CAPTCHA-protected forms MUST use this wrapper.
#
# Usage: source this file, then call functions:
#
#   cf_init "<userId>" "<sessionKey>"           # set globals (default anicca/default)
#   cf_health                                    # check :9377 is up
#   cf_open <url>                                # open new tab, returns tabId in $CF_TAB
#   cf_navigate <url>                            # navigate current tab
#   cf_snapshot [--limit N]                      # accessibility tree with @eN refs
#   cf_snapshot_url                              # just current URL
#   cf_click <ref>                               # click @eN
#   cf_fill <ref> <text>                         # fill ref (clear + type)
#   cf_fill_selector <css_sel> <text>           # fill via CSS selector (textbox without ref)
#   cf_press <key>                               # press Enter / Tab / Control+a etc.
#   cf_screenshot <out.png>                      # save PNG screenshot
#   cf_close                                     # close current tab
#   cf_assert_status <pattern>                   # grep snapshot for pattern (assertion)
#
# Idempotency helper:
#   cf_idempotent <state_file> <state_key> <state_value> <flow_function>
#     → if state_file[state_key] == state_value, skip flow_function
#     → else run flow_function and on success write state_file[state_key]=state_value

CF_API="${CF_API:-http://localhost:9377}"
CF_USER="${CF_USER:-anicca}"
CF_SESSION="${CF_SESSION:-default}"
CF_TAB="${CF_TAB:-}"

cf_init() {
  CF_USER="${1:-$CF_USER}"
  CF_SESSION="${2:-$CF_SESSION}"
  export CF_USER CF_SESSION
}

cf_health() {
  local out
  out=$(curl -sS --max-time 3 "$CF_API/health" 2>/dev/null || echo '{"ok":false}')
  if ! echo "$out" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('ok') else 1)"; then
    echo "❌ camofox not running on $CF_API. Start: bash ~/.openclaw/skills/camofox-{{profile.lateness.stakeholders.channel}}/scripts/start.sh" >&2
    return 1
  fi
  echo "$out"
}

cf_open() {
  local url="${1:?cf_open: url required}"
  local payload
  payload=$(python3 -c "
import json, sys
print(json.dumps({'url': sys.argv[1], 'userId': sys.argv[2], 'sessionKey': sys.argv[3]}))
" "$url" "$CF_USER" "$CF_SESSION")
  local resp
  resp=$(curl -sS -X POST "$CF_API/tabs" \
    -H 'Content-Type: application/json' \
    -d "$payload")
  CF_TAB=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tabId',''))" 2>/dev/null)
  if [ -z "$CF_TAB" ]; then
    echo "❌ cf_open failed: $resp" >&2
    return 1
  fi
  export CF_TAB
  echo "$CF_TAB"
}

cf_navigate() {
  local url="${1:?cf_navigate: url required}"
  curl -sS -X POST "$CF_API/tabs/$CF_TAB/navigate" \
    -H 'Content-Type: application/json' \
    -d "$(python3 -c "import json,sys; print(json.dumps({'url':sys.argv[1],'userId':sys.argv[2],'sessionKey':sys.argv[3]}))" "$url" "$CF_USER" "$CF_SESSION")" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('url',''))"
}

cf_snapshot() {
  curl -sS "$CF_API/tabs/$CF_TAB/snapshot?userId=$CF_USER&sessionKey=$CF_SESSION" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('snapshot',''))"
}

cf_snapshot_url() {
  curl -sS "$CF_API/tabs/$CF_TAB/snapshot?userId=$CF_USER&sessionKey=$CF_SESSION" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('url',''))"
}

cf_click() {
  local ref="${1:?cf_click: ref required}"
  curl -sS -X POST "$CF_API/tabs/$CF_TAB/click" \
    -H 'Content-Type: application/json' \
    -d "$(python3 -c "import json,sys; print(json.dumps({'ref':sys.argv[1],'userId':sys.argv[2],'sessionKey':sys.argv[3]}))" "$ref" "$CF_USER" "$CF_SESSION")" \
    >/dev/null
}

# Click via CSS selector (when ref not available)
cf_click_selector() {
  local sel="${1:?cf_click_selector: selector required}"
  curl -sS -X POST "$CF_API/tabs/$CF_TAB/click" \
    -H 'Content-Type: application/json' \
    -d "$(python3 -c "import json,sys; print(json.dumps({'selector':sys.argv[1],'userId':sys.argv[2],'sessionKey':sys.argv[3]}))" "$sel" "$CF_USER" "$CF_SESSION")" \
    >/dev/null
}

cf_fill() {
  local ref="${1:?cf_fill: ref required}"
  local text="${2:?cf_fill: text required}"
  curl -sS -X POST "$CF_API/tabs/$CF_TAB/type" \
    -H 'Content-Type: application/json' \
    -d "$(python3 -c "import json,sys; print(json.dumps({'ref':sys.argv[1],'text':sys.argv[2],'userId':sys.argv[3],'sessionKey':sys.argv[4]}))" "$ref" "$text" "$CF_USER" "$CF_SESSION")" \
    >/dev/null
}

cf_fill_selector() {
  local sel="${1:?cf_fill_selector: selector required}"
  local text="${2:?cf_fill_selector: text required}"
  curl -sS -X POST "$CF_API/tabs/$CF_TAB/type" \
    -H 'Content-Type: application/json' \
    -d "$(python3 -c "import json,sys; print(json.dumps({'selector':sys.argv[1],'text':sys.argv[2],'userId':sys.argv[3],'sessionKey':sys.argv[4]}))" "$sel" "$text" "$CF_USER" "$CF_SESSION")" \
    >/dev/null
}

cf_press() {
  local key="${1:?cf_press: key required}"
  curl -sS -X POST "$CF_API/tabs/$CF_TAB/press" \
    -H 'Content-Type: application/json' \
    -d "$(python3 -c "import json,sys; print(json.dumps({'key':sys.argv[1],'userId':sys.argv[2],'sessionKey':sys.argv[3]}))" "$key" "$CF_USER" "$CF_SESSION")" \
    >/dev/null
}

cf_screenshot() {
  local out="${1:?cf_screenshot: out path required}"
  curl -sS "$CF_API/tabs/$CF_TAB/screenshot?userId=$CF_USER&sessionKey=$CF_SESSION" -o "$out"
}

cf_close() {
  [ -n "$CF_TAB" ] && curl -sS -X DELETE "$CF_API/tabs/$CF_TAB?userId=$CF_USER&sessionKey=$CF_SESSION" >/dev/null
  CF_TAB=""
}

cf_assert_status() {
  local pattern="${1:?cf_assert_status: pattern required}"
  local snap
  snap=$(cf_snapshot)
  if echo "$snap" | grep -q "$pattern"; then
    return 0
  fi
  return 1
}

# Idempotency check: if state_file[state_key] == state_value, skip flow
# Usage: cf_idempotent <state_file> <key> <expected_value>
#        → returns 0 if already done (caller should skip)
#        → returns 1 if not done (caller should execute flow)
cf_idempotent() {
  local state_file="$1"
  local key="$2"
  local expected="$3"
  [ ! -f "$state_file" ] && return 1
  local actual
  actual=$(python3 -c "
import json,sys
try:
    d=json.load(open('$state_file'))
    print(d.get('$key',''))
except Exception:
    print('')
")
  [ "$actual" = "$expected" ] && return 0
  return 1
}

# Persist state value into state_file (creates if missing)
cf_state_set() {
  local state_file="$1"
  local key="$2"
  local value="$3"
  python3 - "$state_file" "$key" "$value" <<'PY'
import sys, json, pathlib, datetime
p = pathlib.Path(sys.argv[1])
key, value = sys.argv[2], sys.argv[3]
db = json.loads(p.read_text()) if p.exists() else {}
db[key] = value
db["_updated_at"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(db, ensure_ascii=False, indent=2))
PY
}
