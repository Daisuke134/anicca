#!/usr/bin/env bash
set -euo pipefail

GOG_BIN="${GOG_BIN:-/opt/homebrew/bin/gog}"
GMAIL_ACCOUNT="${GMAIL_ACCOUNT:-{{profile.contact.personalEmail}}}"

# Search Gmail with a Gmail query string. Returns JSON array of threads.
inbox_search() {
  local query="$1"
  : "${GOG_KEYRING_PASSWORD:?required}"
  GOG_KEYRING_PASSWORD="$GOG_KEYRING_PASSWORD" "$GOG_BIN" gmail search "$query" \
    -a "$GMAIL_ACCOUNT" --max 25 -j --results-only 2>/dev/null || echo "[]"
}

# Get a thread's full structure as JSON.
inbox_thread_get() {
  local thread_id="$1"
  : "${GOG_KEYRING_PASSWORD:?required}"
  GOG_KEYRING_PASSWORD="$GOG_KEYRING_PASSWORD" "$GOG_BIN" gmail thread get "$thread_id" \
    -a "$GMAIL_ACCOUNT" -j --results-only 2>/dev/null || echo "{}"
}

# Classify a thread → "replied" | "bounced" | "sent" (no incoming yet)
# Output: <classification>\t<latest_inbox_msg_id>\t<latest_inbox_subject>\t<latest_inbox_from>\t<latest_inbox_internal_date>
inbox_classify_thread() {
  local thread_id="$1"
  THREAD_JSON="$(inbox_thread_get "$thread_id")" python3 - "$thread_id" <<'PY'
import json, os, sys
data = json.loads(os.environ.get("THREAD_JSON", "{}") or "{}")
thread = (data or {}).get("thread") or {}
msgs = thread.get("messages") or []
incoming = []
for m in msgs:
    labels = m.get("labelIds") or []
    if "SENT" in labels and "INBOX" not in labels:
        continue
    if "INBOX" not in labels and "SPAM" not in labels:
        continue
    incoming.append(m)

def header(m, name):
    for h in (((m.get("payload") or {}).get("headers")) or []):
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""

if not incoming:
    print("sent\t\t\t\t")
    sys.exit(0)

# Sort by internalDate ascending; pick latest
incoming.sort(key=lambda x: int(x.get("internalDate", 0)))
latest = incoming[-1]
mid = latest.get("id", "")
subj = header(latest, "Subject")
sender = header(latest, "From")
idate = latest.get("internalDate", "0")

# Bounce heuristics
is_bounce = False
sender_l = (sender or "").lower()
subj_l = (subj or "").lower()
bounce_senders = ["mailer-daemon", "postmaster@", "noreply@gmail.com"]
bounce_subjects = ["delivery status notification", "undelivered mail", "mail delivery", "delivery failure", "returned mail", "address rejected"]
if any(b in sender_l for b in bounce_senders):
    is_bounce = True
elif any(b in subj_l for b in bounce_subjects):
    is_bounce = True

print(f"{'bounced' if is_bounce else 'replied'}\t{mid}\t{subj}\t{sender}\t{idate}")
PY
}
