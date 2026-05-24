#!/usr/bin/env bash
# auto-research dispatcher. Picks one project from projects.yaml via round-robin cursor,
# then invokes the right {{profile.lateness.stakeholders.senderType}} script with that project's metadata.
# AUTO_RESEARCH_DRY_RUN=true short-circuits every heavy call.
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS="$SKILL_DIR/scripts"
WORKSPACE="${HOME}/.openclaw/workspace/auto-research"
mkdir -p "$WORKSPACE/literature" "$WORKSPACE/hypotheses" "$WORKSPACE/experiments" "$WORKSPACE/papers" "$WORKSPACE/grants" "$WORKSPACE/acks"

MODE="${MODE:-literature}"
DRY="${AUTO_RESEARCH_DRY_RUN:-false}"
CURSOR="$WORKSPACE/.cursor.json"
PROJECTS_YAML="$SKILL_DIR/projects.yaml"

if [ ! -f "$PROJECTS_YAML" ]; then
  echo "auto-research: $PROJECTS_YAML missing." >&2
  exit 66
fi

# Pick project (python because YAML and stdlib jq is awkward)
PROJECT_JSON="$(python3 - "$PROJECTS_YAML" "$CURSOR" <<'PY'
import json, os, sys, datetime as dt
try:
    import yaml
except ImportError:
    # Minimal YAML fallback for the projects.yaml shape we control.
    import re
    text = open(sys.argv[1]).read()
    projects, cur = [], None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#") or line.strip() == "projects:":
            continue
        if line.startswith("  - id:"):
            if cur: projects.append(cur)
            cur = {"id": line.split(":",1)[1].strip()}
        elif cur is not None and line.startswith("    "):
            k, _, v = line.strip().partition(":")
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                v = [x.strip().strip('"') for x in v[1:-1].split(",") if x.strip()]
            else:
                v = v.strip().strip('"')
            cur[k.strip()] = v
    if cur: projects.append(cur)
    data = {"projects": projects}
else:
    with open(sys.argv[1]) as f: data = yaml.safe_load(f)

projects = data["projects"]
cursor_path = sys.argv[2]
try:
    cursor = json.loads(open(cursor_path).read())
except Exception:
    cursor = {"next_index": 0, "last_run": None}
i = cursor.get("next_index", 0) % len(projects)
print(json.dumps({"project": projects[i], "index": i, "total": len(projects)}, ensure_ascii=False))
PY
)"

INDEX="$(echo "$PROJECT_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["index"])')"
TOTAL="$(echo "$PROJECT_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["total"])')"
PROJECT_ID="$(echo "$PROJECT_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["project"]["id"])')"

echo "[auto-research:$MODE] project=$PROJECT_ID  cursor=$INDEX/$TOTAL  dry_run=$DRY"

case "$MODE" in
  # E2E pipeline (chassis-free, real arXiv + Gemini/OpenAI): runs literature + hypothesise + draft + publish in one shot.
  # This is the production path now that the AutoResearchClaw chassis is incomplete.
  e2e)         AUTO_RESEARCH_DRY_RUN="$DRY" PROJECT_ID="$PROJECT_ID" python3 "$SCRIPTS/run-e2e.py" ;;
  # Legacy per-{{profile.lateness.stakeholders.senderType}} modes (still call the original stub scripts that depend on the chassis).
  literature)  AUTO_RESEARCH_DRY_RUN="$DRY" PROJECT_ID="$PROJECT_ID" python3 "$SCRIPTS/literature-pull.py" "$PROJECT_JSON" ;;
  hypothesise) AUTO_RESEARCH_DRY_RUN="$DRY" PROJECT_ID="$PROJECT_ID" python3 "$SCRIPTS/hypothesise.py"      "$PROJECT_JSON" ;;
  experiment)  AUTO_RESEARCH_DRY_RUN="$DRY" PROJECT_ID="$PROJECT_ID" python3 "$SCRIPTS/experiment-bfts.py"  "$PROJECT_JSON" ;;
  write)       AUTO_RESEARCH_DRY_RUN="$DRY" PROJECT_ID="$PROJECT_ID" python3 "$SCRIPTS/draft-paper.py"      "$PROJECT_JSON" ;;
  publish)     AUTO_RESEARCH_DRY_RUN="$DRY" PROJECT_ID="$PROJECT_ID" python3 "$SCRIPTS/publish-3channel.py" "$PROJECT_JSON" ;;
  grant)       AUTO_RESEARCH_DRY_RUN="$DRY" PROJECT_ID="$PROJECT_ID" python3 "$SCRIPTS/draft-grant.py"      "$PROJECT_JSON" ;;
  *) echo "unknown MODE=$MODE" >&2; exit 64 ;;
esac

# Advance cursor (atomic)
NEXT=$(( (INDEX + 1) % TOTAL ))
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TMP="$CURSOR.tmp.$$"
printf '{"next_index": %d, "last_run": "%s", "last_mode": "%s", "last_project": "%s"}\n' "$NEXT" "$TS" "$MODE" "$PROJECT_ID" > "$TMP"
mv "$TMP" "$CURSOR"

echo "[auto-research:$MODE] cursor → $NEXT  done."
