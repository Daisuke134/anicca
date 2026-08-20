#!/usr/bin/env bash
# Execute JSONL argv jobs in the foreground, recording every result after preflight passes.
set -uo pipefail

MANIFEST=""
RESULTS=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --manifest) MANIFEST="$2"; shift 2 ;;
    --results) RESULTS="$2"; shift 2 ;;
    *) echo "FATAL: unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -f "$MANIFEST" ] && [ -n "$RESULTS" ] || { echo "FATAL: --manifest and --results required" >&2; exit 2; }

# Validate the complete plan before the first mutation. JSON argv preserves literal dollars and
# cannot be reinterpreted by a second shell. Shell -c forms are rejected because they can detach
# background work and let the dispatcher report completion early.
if ! python3 - "$MANIFEST" <<'PY'
import json, os, re, sys
from pathlib import Path

manifest = Path(sys.argv[1])
errors = []
rows = []
for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
    if not line.strip():
        continue
    try:
        row = json.loads(line)
    except json.JSONDecodeError as exc:
        errors.append(f"line {number}: invalid JSON: {exc}")
        continue
    rows.append((number, row))

for number, row in rows:
    platform = row.get("platform")
    lang = row.get("lang")
    argv = row.get("argv")
    env = row.get("env", {})
    if not isinstance(platform, str) or not platform or lang not in {"ja", "en"}:
        errors.append(f"line {number}: platform/lang required")
        continue
    if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) for arg in argv):
        errors.append(f"line {number}: argv must be a non-empty JSON string array")
        continue
    if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
        errors.append(f"line {number}: env must be a JSON string object")
        continue
    shell = os.path.basename(argv[0])
    if shell in {"bash", "sh", "zsh", "dash", "ksh"} and len(argv) > 1 and argv[1] in {"-c", "-lc", "-cl"}:
        errors.append(f"line {number}: shell -c/background dispatch is forbidden; provide foreground argv")
    if platform in {"x", "x-ja", "x-en"}:
        cover = env.get("X_COVER", "")
        if not cover or not Path(cover).is_file():
            errors.append(f"line {number}: X_COVER must name an existing file")
    if platform == "devto":
        try:
            markdown = Path(argv[argv.index("--markdown-file") + 1])
        except (ValueError, IndexError):
            errors.append(f"line {number}: Dev.to argv must include --markdown-file")
        else:
            try:
                content = markdown.read_text(encoding="utf-8")
            except OSError:
                errors.append(f"line {number}: Dev.to markdown file is unreadable: {markdown}")
            else:
                if not re.search(r"^tags:\s*\S", content, re.MULTILINE):
                    errors.append(f"line {number}: Dev.to markdown requires non-empty tags frontmatter")

if errors:
    for error in errors:
        print(f"PREFLIGHT: {error}", file=sys.stderr)
    raise SystemExit(2)
if not rows:
    print("PREFLIGHT: manifest has no jobs", file=sys.stderr)
    raise SystemExit(2)
PY
then
  exit 2
fi

mkdir -p "$(dirname "$RESULTS")"
: >"$RESULTS"
failed=0
while IFS= read -r job_json; do
  [ -n "$job_json" ] || continue
  platform=$(printf '%s' "$job_json" | jq -r '.platform')
  lang=$(printf '%s' "$job_json" | jq -r '.lang')
  raw_file="$(mktemp /tmp/article-dispatch.XXXXXX)" || exit 2
  python3 - "$job_json" >"$raw_file" 2>&1 <<'PY'
import json, os, subprocess, sys
job = json.loads(sys.argv[1])
env = os.environ.copy()
env.update(job.get("env", {}))
completed = subprocess.run(job["argv"], env=env, check=False)
raise SystemExit(completed.returncode)
PY
  rc=$?
  cat "$raw_file"
  [ "$rc" -eq 0 ] || failed=1
  python3 - "$RESULTS" "$platform" "$lang" "$rc" "$raw_file" <<'PY'
import json, sys
from datetime import datetime, timezone
path, platform, lang, rc, raw_path = sys.argv[1:]
raw = open(raw_path, encoding="utf-8", errors="replace").read()
row = {
    "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "platform": platform,
    "lang": lang,
    "status": "ok" if int(rc) == 0 else "failed",
    "exit_code": int(rc),
    "raw_output": raw,
}
with open(path, "a", encoding="utf-8") as handle:
    handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
PY
  rm -f "$raw_file"
done < <(python3 - "$MANIFEST" <<'PY'
import json, sys

rows = [
    json.loads(line)
    for line in open(sys.argv[1], encoding="utf-8")
    if line.strip()
]

def priority(row):
    platform = row["platform"]
    if platform == "note":
        return 0
    if platform.startswith("substack"):
        return 1
    if platform == "zenn":
        return 3
    return 2

for _, row in sorted(enumerate(rows), key=lambda item: (priority(item[1]), item[0])):
    print(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
PY
)

[ "$failed" -eq 0 ]
