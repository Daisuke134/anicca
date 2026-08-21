#!/usr/bin/env bash
# resolve-form.sh — map a form name (or a topic card path) to its form spec from config/forms.json.
# spec 47 §8: the gate skeleton is form-agnostic; only length/exits/monetization change per form.
# Usage:
#   resolve-form.sh --name <xpost|article|ebook>
#   resolve-form.sh --card <path-to-topic-card.md>   # reads the card's `form:` frontmatter, default article
# stdout: the form spec as JSON (with a resolved "name" key). Unknown/empty -> the default form.
set -uo pipefail
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORMS_JSON="$SKILL_DIR/config/forms.json"

mode="${1:-}"; arg="${2:-}"
name=""
case "$mode" in
  --name) name="$arg" ;;
  --card)
    if [ -f "$arg" ]; then
      # read `form:` from YAML frontmatter (first occurrence), tolerate quotes/spaces
      name="$(awk -F: '/^form:[[:space:]]*/{gsub(/[[:space:]"'"'"']/,"",$2); print $2; exit}' "$arg")"
    fi
    ;;
  *) echo '{"error":"usage: resolve-form.sh --name <form> | --card <path>"}'; exit 2 ;;
esac

python3 - "$FORMS_JSON" "$name" <<'PY'
import json, sys
forms_path, name = sys.argv[1], sys.argv[2].strip()
try:
    cfg = json.load(open(forms_path, encoding='utf-8'))
except Exception as e:
    print(json.dumps({"error": f"cannot read forms.json: {e}"})); sys.exit(1)
forms = cfg.get("forms", {})
default = cfg.get("default", "article")
resolved = name if name in forms else default
spec = dict(forms.get(resolved, {}))
spec["name"] = resolved
spec["was_default_fallback"] = (name not in forms)
print(json.dumps(spec, ensure_ascii=False))
PY
