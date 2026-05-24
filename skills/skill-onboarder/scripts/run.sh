#!/usr/bin/env bash
# skill-onboarder runtime — drives a target skill's wizard.
# Usage: SKILL=<target> bash run.sh   (uses ~/.openclaw/skills/<target>/SKILL.md)
set -euo pipefail

TARGET="${SKILL:-}"
if [[ -z "$TARGET" ]]; then
  echo "usage: SKILL=<target-skill-name> bash $0" >&2
  exit 2
fi

ROOT="${OPENCLAW_ROOT:-$HOME/.openclaw}"
TARGET_MD="$ROOT/skills/$TARGET/SKILL.md"
STATE_DIR="$ROOT/state"
ANICCA_STATE="$STATE_DIR/anicca.json"
JOBS_FILE="$STATE_DIR/jobs.json"
mkdir -p "$STATE_DIR"

[[ -f "$TARGET_MD" ]] || { echo "[err] $TARGET_MD not found" >&2; exit 3; }
[[ -f "$ANICCA_STATE" ]] || echo '{"slack":{"metrics_channel":"{{profile.channels.reportChannel}}"}}' > "$ANICCA_STATE"
[[ -f "$JOBS_FILE" ]]    || echo '{"jobs":[]}' > "$JOBS_FILE"

TS=$(date -u +%Y%m%d-%H%M%S)
STATE_FILE="$STATE_DIR/${TARGET}.json"
TODO_FILE="$STATE_DIR/${TARGET}.todo.md"

# Backup existing state.
if [[ -f "$STATE_FILE" ]]; then
  cp -p "$STATE_FILE" "${STATE_FILE}.bak.${TS}"
fi
[[ -f "$STATE_FILE" ]] || echo '{}' > "$STATE_FILE"

# Extract questions from SKILL.md '## Setup wizard' section.
QUESTIONS_JSON=$(python3 - "$TARGET_MD" <<'PY'
import json, re, sys
md = open(sys.argv[1]).read()
m = re.search(r'^##\s+Setup wizard.*?\n(.*?)(?=^##\s|\Z)', md, re.M | re.S)
out = []
if m:
    body = m.group(1)
    for q in re.finditer(
        r'^\s*(\d+)\.\s+\*\*(.+?)\*\*\s*[—-]\s*(.+?)(?:\s*Default:\s*`(.+?)`)?\s*\.\s*(?:→\s*`(.+?)`\s*\.)?',
        body, re.M):
        out.append({
            "n": int(q.group(1)),
            "label": q.group(2).strip(),
            "prompt": q.group(3).strip(),
            "default": q.group(4) or "",
            "state_path": q.group(5) or "",
        })
print(json.dumps(out))
PY
)

QCOUNT=$(jq 'length' <<< "$QUESTIONS_JSON")
if [[ "$QCOUNT" == "0" ]]; then
  # Generate default 3-question wizard from frontmatter.
  QUESTIONS_JSON=$(jq -n --arg s "$TARGET" '[
    {"n":1,"label":"Scope","prompt":"What automation scope does this skill cover for you?","default":"","state_path":"\($s).scope"},
    {"n":2,"label":"Cadence","prompt":"daily | weekly | monthly | manual","default":"weekly","state_path":"\($s).cadence"},
    {"n":3,"label":"Slack channel","prompt":"Slack channel ID for output","default":"$(jq -r .slack.metrics_channel ~/.openclaw/state/anicca.json)","state_path":"\($s).slack_channel"}
  ]')
  QCOUNT=3
fi

echo "## skill-onboarder — onboarding '$TARGET' ($QCOUNT questions)"
echo ""

# Prompt loop. Reads from stdin; each line is one answer.
ANSWERS_JSON='{}'
for i in $(seq 0 $((QCOUNT-1))); do
  Q=$(jq ".[$i]" <<< "$QUESTIONS_JSON")
  LABEL=$(jq -r .label <<< "$Q"); PROMPT=$(jq -r .prompt <<< "$Q")
  DEFAULT=$(jq -r .default <<< "$Q"); SPATH=$(jq -r .state_path <<< "$Q")
  printf 'Q%s. %s — %s\n' "$((i+1))" "$LABEL" "$PROMPT"
  [[ -n "$DEFAULT" && "$DEFAULT" != "null" ]] && printf '    [default: %s]\n' "$DEFAULT"
  printf '> '
  read -r ANS || ANS=""
  [[ -z "$ANS" ]] && ANS="$DEFAULT"
  ANSWERS_JSON=$(jq --arg p "$SPATH" --arg v "$ANS" '. + {($p): $v}' <<< "$ANSWERS_JSON")
  printf '\n'
done

# Merge answers into the right state file (skill-specific or anicca.json).
python3 - "$STATE_FILE" "$ANICCA_STATE" "$TARGET" <<PY
import json, sys, os
ans = json.loads('''$(echo "$ANSWERS_JSON")''')
skill_state = json.load(open(sys.argv[1]))
anicca_state = json.load(open(sys.argv[2]))
target = sys.argv[3]
for path, val in ans.items():
    if not path: continue
    parts = path.split(".")
    # Route: paths starting with the target skill name -> anicca.json (canonical)
    # paths starting with state.<skill>.<...> -> per-skill file
    root = anicca_state if parts[0] == target else skill_state
    cursor = root
    for p in parts[:-1]:
        cursor = cursor.setdefault(p, {})
    cursor[parts[-1]] = val
json.dump(skill_state, open(sys.argv[1],"w"), indent=2)
json.dump(anicca_state, open(sys.argv[2],"w"), indent=2)
PY

# Cron proposal — derive cadence from any answer that mentioned it.
CADENCE=$(jq -r 'to_entries[] | select(.key|test("cadence")) | .value' <<< "$ANSWERS_JSON" | head -1)
[[ -z "$CADENCE" || "$CADENCE" == "null" ]] && CADENCE="weekly"
case "$CADENCE" in
  daily)   CRON="0 9 * * *" ;;
  weekly)  CRON="0 9 * * 1" ;;
  monthly) CRON="0 9 1 * *" ;;
  manual|*) CRON="" ;;
esac

CHANNEL=$(jq -r .slack.metrics_channel "$ANICCA_STATE")
PROPOSED=$(jq -n --arg s "$TARGET" --arg c "$CRON" --arg ch "$CHANNEL" \
  '{skill:$s, mode:"default", schedule:$c, delivery:{mode:"announce",target:$ch}, enabled:false, proposed_at:"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'", proposed_by:"skill-onboarder/0.1.0"}')

echo "Proposed cron entry:"
echo "$PROPOSED" | jq .
echo ""
echo "Append to ~/.openclaw/state/jobs.json with enabled=false? [yes/no]"
printf '> '
read -r ACK || ACK=""

if [[ "$ACK" == "yes" || "$ACK" == "y" ]]; then
  python3 - "$JOBS_FILE" "$PROPOSED" <<'PY'
import json, sys
jf = json.load(open(sys.argv[1]))
jf.setdefault("jobs", []).append(json.loads(sys.argv[2]))
json.dump(jf, open(sys.argv[1],"w"), indent=2)
PY
  echo "[ok] cron entry appended (enabled=false). Flip with:"
  echo "  jq '(.jobs[] | select(.skill==\"$TARGET\")) .enabled = true' $JOBS_FILE > /tmp/j && mv /tmp/j $JOBS_FILE"
else
  cat >> "$TODO_FILE" <<EOF
# TODO: cron declined for $TARGET on $TS — re-run skill-onboarder when ready.
proposed entry was:
$(jq . <<< "$PROPOSED")
EOF
  echo "[ok] cron declined; reminder appended to $TODO_FILE"
fi

# Surface env-gate flags (read from frontmatter).
GATES=$(python3 - "$TARGET_MD" <<'PY'
import re, sys, yaml
md = open(sys.argv[1]).read()
m = re.match(r'---\n(.*?)\n---', md, re.S)
if not m:
    print(""); sys.exit(0)
fm = yaml.safe_load(m.group(1)) or {}
gates = (fm.get("metadata",{}).get("requires",{}) or {}).get("env_dryrun_until_flipped",[]) or []
print(",".join(gates))
PY
)
if [[ -n "$GATES" ]]; then
  echo ""
  echo "[gate flags this skill expects in ~/.openclaw/.env when ready: $GATES]"
fi

echo ""
echo "Manual smoke: MODE=<mode-from-SKILL.md> bash ~/.openclaw/skills/$TARGET/scripts/run.sh"
echo "State written: $STATE_FILE"
echo "Canonical state: $ANICCA_STATE"
