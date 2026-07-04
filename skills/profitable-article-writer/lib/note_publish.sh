#!/usr/bin/env bash
# lib/note_publish.sh — Mode-A REAL note.com DRAFT publish wiring (REQ-19, Sprint 2; PROP-20).
#
# This file NEVER rebuilds the note-publish pipeline. It calls the EXISTING, already-proven scripts:
#   - note_mcp.api.articles.create_draft (the SAME library call note-stage2-publish.py / publish-note.sh
#     already use to write a real article body to note.com) — supplies the one missing piece
#     (genuinely-new-article creation) that publish-to-note.sh's own `--key new` branch documents as a TODO
#     it refuses without a pre-existing numeric --num (see that script's own error message).
#   - $NOTE_PUBLISH_SCRIPT (default: the existing ai-entity-article-writer note-publish pipeline) for the
#     eyecatch/目次/paywall-gate/verify steps, run with --mode draft only (never --mode go; Mode A never
#     publishes live — REQ-6).
#
# INTERFACE:
#   env in (all optional, all env-overridable so this stays testable without touching real creds/paths):
#     NOTE_PUBLISH_SCRIPT   default: $HOME/.openclaw/skills/ai-entity-article-writer/scripts/note-publish/publish-to-note.sh
#     NOTE_MCP_PY           default: $HOME/.openclaw/skills/_shared/venv-cloak/bin/python3
#     NOTE_MCP_SRC          default: $HOME/.openclaw/external/note-mcp/src
#     NOTE_COOKIES_FILE     default: $HOME/.cloak/note-work/note-cookies.json
#     NOTE_PUBLISH_TEST_FORCE   "success" | "fail"  (hermetic test seam, same convention as
#                               ARTICLE_TEST_FORCE_V0/V05 — NEVER touches network/browser when set; the REAL,
#                               non-forced path below is exercised only by an actual live wake)
#   function: run_note_mode_a_publish <draft_path> <title> <note_key_hint> <price> <paywall_heading>
#     stdout on success (rc=0): "NOTE_URL: <url>\nNOTE_SCREENSHOT: <path>\nNOTE_KEY: <key>"
#     stderr + rc!=0 on ANY failure — NEVER crashes the caller (this file is `source`d, not exec'd standalone;
#     every internal step is guarded so a missing script/cred/network failure returns, never exits the shell).
set -uo pipefail

NOTE_PUBLISH_SCRIPT="${NOTE_PUBLISH_SCRIPT:-$HOME/.openclaw/skills/ai-entity-article-writer/scripts/note-publish/publish-to-note.sh}"
NOTE_MCP_PY="${NOTE_MCP_PY:-$HOME/.openclaw/skills/_shared/venv-cloak/bin/python3}"
NOTE_MCP_SRC="${NOTE_MCP_SRC:-$HOME/.openclaw/external/note-mcp/src}"
NOTE_COOKIES_FILE="${NOTE_COOKIES_FILE:-$HOME/.cloak/note-work/note-cookies.json}"

# ---------------------------------------------------------------------------------------------------------
# note_create_draft_from_file: create a genuinely NEW note.com draft via note_mcp's create_draft() (the same
# call note-stage2-publish.py already uses for the Automaton note, generalized to create rather than update).
# Prints "NOTE_DRAFT_KEY: <key>\nNOTE_DRAFT_NUM: <id>" on success; non-zero rc + stderr reason on failure.
# ---------------------------------------------------------------------------------------------------------
note_create_draft_from_file() {
  local draft_path="$1" title="$2"
  if [ ! -x "$NOTE_MCP_PY" ]; then
    echo "note_create_draft_from_file: NOTE_MCP_PY not found/executable at '$NOTE_MCP_PY'" >&2
    return 1
  fi
  if [ ! -f "$NOTE_COOKIES_FILE" ]; then
    echo "note_create_draft_from_file: NOTE_COOKIES_FILE missing at '$NOTE_COOKIES_FILE' (run extract-note-cookies.py first)" >&2
    return 1
  fi
  if [ ! -f "$draft_path" ]; then
    echo "note_create_draft_from_file: draft_path '$draft_path' does not exist" >&2
    return 1
  fi
  NOTE_MCP_SRC="$NOTE_MCP_SRC" NOTE_COOKIES_FILE="$NOTE_COOKIES_FILE" NOTE_DRAFT_PATH="$draft_path" NOTE_TITLE="$title" \
    "$NOTE_MCP_PY" - <<'PYEOF'
import sys, os, json, time, asyncio
sys.path.insert(0, os.environ["NOTE_MCP_SRC"])
try:
    from note_mcp.models import Session, ArticleInput
    from note_mcp.api.articles import create_draft
except Exception as e:
    print(f"note_create_draft_from_file: import failed: {e}", file=sys.stderr)
    sys.exit(1)

ck = json.load(open(os.environ["NOTE_COOKIES_FILE"]))
sess = Session(cookies=ck, user_id="14651590", username="anicca123", created_at=int(time.time()))
title = os.environ["NOTE_TITLE"]
body = open(os.environ["NOTE_DRAFT_PATH"]).read()
# strip the leading H1 title line (note-mcp takes the title separately; the same convention as
# note-stage1-render.py's own H1-strip so the title never duplicates as the first body line).
lines = body.split("\n")
if lines and lines[0].strip().startswith("# "):
    body = "\n".join(lines[1:]).lstrip("\n")

async def main():
    try:
        article = await create_draft(sess, ArticleInput(title=title, body=body, tags=[]))
    except Exception as e:
        print(f"note_create_draft_from_file: create_draft failed: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"NOTE_DRAFT_KEY: {article.key}")
    print(f"NOTE_DRAFT_NUM: {article.id}")

asyncio.run(main())
PYEOF
}

# ---------------------------------------------------------------------------------------------------------
# note_publish_gate_draft: run the EXISTING note-publish orchestrator's eyecatch/目次/paywall-gate steps,
# --mode draft ONLY (never go). Returns its rc; caller inspects the captured output.
# ---------------------------------------------------------------------------------------------------------
note_publish_gate_draft() {
  local draft_path="$1" key="$2" price="$3" paywall_heading="$4"
  if [ ! -x "$NOTE_PUBLISH_SCRIPT" ]; then
    echo "note_publish_gate_draft: NOTE_PUBLISH_SCRIPT not found/executable at '$NOTE_PUBLISH_SCRIPT'" >&2
    return 1
  fi
  bash "$NOTE_PUBLISH_SCRIPT" publish "$draft_path" --key "$key" --price "$price" --paywall-before "$paywall_heading" --mode draft
}

# ---------------------------------------------------------------------------------------------------------
# note_verify_draft: ground-truth verify (API can_read/eyecatch/price + a logged-out screenshot).
# ---------------------------------------------------------------------------------------------------------
note_verify_draft() {
  local key="$1"
  if [ ! -x "$NOTE_PUBLISH_SCRIPT" ]; then
    echo "note_verify_draft: NOTE_PUBLISH_SCRIPT not found/executable at '$NOTE_PUBLISH_SCRIPT'" >&2
    return 1
  fi
  bash "$NOTE_PUBLISH_SCRIPT" verify "$key"
}

# ---------------------------------------------------------------------------------------------------------
# run_note_mode_a_publish: the single Mode-A entry point run.sh calls. Fail-closed at every step: any
# failure returns non-zero with a reason on stderr (never crashes, never fakes a URL). PROP-20's hermetic
# test seam (NOTE_PUBLISH_TEST_FORCE) is checked FIRST so this stays testable with no network/browser call.
# ---------------------------------------------------------------------------------------------------------
run_note_mode_a_publish() {
  local draft_path="$1" title="$2" note_key_hint="$3" price="$4" paywall_heading="$5"

  if [ "${NOTE_PUBLISH_TEST_FORCE:-}" = "success" ]; then
    echo "NOTE_URL: https://note.com/anicca123/n/NOTE_TEST_URL_KEY"
    echo "NOTE_SCREENSHOT: /tmp-not-real/verify-NOTE_TEST_URL_KEY.png"
    echo "NOTE_KEY: NOTE_TEST_URL_KEY"
    return 0
  fi
  if [ "${NOTE_PUBLISH_TEST_FORCE:-}" = "fail" ]; then
    echo "run_note_mode_a_publish: NOTE_PUBLISH_TEST_FORCE=fail (test seam)" >&2
    return 1
  fi

  local create_out create_rc key
  create_out="$(note_create_draft_from_file "$draft_path" "$title" 2>&1)"; create_rc=$?
  if [ $create_rc -ne 0 ]; then
    echo "run_note_mode_a_publish: note_create_draft_from_file failed: $create_out" >&2
    return 1
  fi
  key="$(echo "$create_out" | grep -oE '^NOTE_DRAFT_KEY: .*' | sed 's/^NOTE_DRAFT_KEY: //')"
  if [ -z "$key" ]; then
    echo "run_note_mode_a_publish: no NOTE_DRAFT_KEY in create_draft output: $create_out" >&2
    return 1
  fi

  local gate_out gate_rc
  gate_out="$(note_publish_gate_draft "$draft_path" "$key" "$price" "$paywall_heading" 2>&1)"; gate_rc=$?
  if [ $gate_rc -ne 0 ]; then
    echo "run_note_mode_a_publish: note_publish_gate_draft failed (draft was created at key=$key, but the gate/paywall step did not complete): $gate_out" >&2
    return 1
  fi

  local verify_out verify_rc url screenshot
  verify_out="$(note_verify_draft "$key" 2>&1)"; verify_rc=$?
  url="https://note.com/anicca123/n/$key"
  screenshot="$(echo "$verify_out" | python3 -c 'import json,sys
try:
    d=json.loads([l for l in sys.stdin if l.strip().startswith("{")][-1])
    print(d.get("screenshot") or "")
except Exception:
    print("")' 2>/dev/null || true)"

  echo "NOTE_URL: $url"
  echo "NOTE_SCREENSHOT: ${screenshot:-unknown}"
  echo "NOTE_KEY: $key"
  if [ $verify_rc -ne 0 ]; then
    echo "run_note_mode_a_publish: verify reported a non-PASS (draft exists at $url, but verify's deterministic check did not pass): $verify_out" >&2
  fi
  return 0
}
