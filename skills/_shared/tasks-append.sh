#!/usr/bin/env bash
# tasks-append.sh — atomic appender for ~/.openclaw/workspace/tasks.json.
#
# Args:
#   $1 = task id (e.g. "tc-d2-shonan-bishu-skill-create")
#   $2 = task title (human-readable)
#   $3 = priority (critical | high | medium | low)
#   $@ (rest) = metadata key=value pairs with dot syntax,
#                e.g. metadata.skill=foo metadata.dueTs=2026-12-31T00:00:00Z
#
# Notes:
#   - Status is always "pending"; dependencies is always [].
#   - Atomic write via mktemp + mv (no half-written file).
#   - claude-task-master schema preserved: {"master": {"tasks": [...]}}.

set -uo pipefail

TASKS="$HOME/.openclaw/workspace/tasks.json"

if [ "$#" -lt 3 ]; then
  echo "[tasks-append] usage: $0 <id> <title> <priority> [<key.path=value>...]" >&2
  exit 2
fi

ID="$1"; TITLE="$2"; PRIORITY="$3"
shift 3

TMP=$(mktemp)
python3 - "$TASKS" "$ID" "$TITLE" "$PRIORITY" "$TMP" "$@" <<'PY'
import json, sys

path, tid, title, priority, tmp_out, *kvs = sys.argv[1:]

with open(path) as f:
    data = json.load(f)

metadata = {}
for kv in kvs:
    if "=" not in kv:
        continue
    k, v = kv.split("=", 1)
    parts = k.split(".")
    if parts and parts[0] == "metadata":
        parts = parts[1:]
    if not parts:
        continue
    cur = metadata
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = v

task = {
    "id": tid,
    "title": title,
    "status": "pending",
    "priority": priority,
    "dependencies": [],
    "description": "Created by tasks-append.sh",
    "metadata": metadata,
}

data.setdefault("master", {}).setdefault("tasks", []).append(task)

with open(tmp_out, "w") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
PY

mv "$TMP" "$TASKS"
echo "appended task $ID"
