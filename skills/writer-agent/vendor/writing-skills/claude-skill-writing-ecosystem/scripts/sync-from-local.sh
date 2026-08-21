#!/usr/bin/env bash
# sync-from-local.sh — one-way export from the live Claude Code harness
# (~/.claude) into this skill repo.
#
# The set of skills to sync is derived from the skill directories already
# present under this repo's skills/ — the repo declares what it publishes
# by containing it. For each published skill the harness copy must exist
# and carry the expected origin marker; otherwise the script aborts (it
# never silently drops a published skill). Root files (README, LICENSE,
# llms*.txt, CHANGELOG) are never touched. The script never commits —
# `git diff` in this repo is the review gate.
#
# This script is vendored byte-identical across skill repos that publish
# a harness-canonical skill. Do not add repo-specific logic here.
#
# Usage:
#   scripts/sync-from-local.sh --dry-run   # report differences only
#   scripts/sync-from-local.sh             # apply to working tree
#
# Config (env overrides):
#   HARNESS_SYNC_SOURCE  source harness dir      (default: ~/.claude)
#   HARNESS_SYNC_ORIGIN  origin value to require (default: shimo4228)

set -euo pipefail

SOURCE_DIR="${HARNESS_SYNC_SOURCE:-$HOME/.claude}"
ORIGIN="${HARNESS_SYNC_ORIGIN:-shimo4228}"
TARGET_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DRY_RUN=0
[[ "${1:-}" == "--dry-run" || "${1:-}" == "-n" ]] && DRY_RUN=1

# --- derive the skill set from this repo's own skills/ directory ---
SKILLS=()
for dir in "$TARGET_DIR"/skills/*/; do
  [[ -d "$dir" ]] || continue
  SKILLS+=("$(basename "$dir")")
done
if (( ${#SKILLS[@]} == 0 )); then
  echo "ABORT: no skill directories under $TARGET_DIR/skills/ — nothing to sync." >&2
  exit 1
fi

# --- guard: skills/ must be clean so the sync delta is reviewable ---
if (( ! DRY_RUN )); then
  if ! git -C "$TARGET_DIR" diff --quiet -- skills ||
     ! git -C "$TARGET_DIR" diff --cached --quiet -- skills; then
    echo "ABORT: uncommitted changes in skills/ — commit or stash first," >&2
    echo "       so that 'git diff' after sync shows exactly the sync delta." >&2
    exit 1
  fi
fi

has_origin() { head -15 "$1" | grep -q "origin: $ORIGIN"; }

# --- staging ---
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT
mkdir -p "$STAGING/skills"

for name in "${SKILLS[@]}"; do
  src="$SOURCE_DIR/skills/$name"
  if [[ ! -f "$src/SKILL.md" ]]; then
    echo "ABORT: $src/SKILL.md not found — harness copy missing for published skill '$name'." >&2
    exit 1
  fi
  if ! has_origin "$src/SKILL.md"; then
    echo "ABORT: $src/SKILL.md does not declare 'origin: $ORIGIN'." >&2
    exit 1
  fi
  cp -R "$src" "$STAGING/skills/"
done

# --- prune runtime artifacts from the staged payload ---
find "$STAGING" \( -name results.json -o -name '*.log' -o -name '*.pyc' \
  -o -name .DS_Store -o -name .coverage -o -name '.coverage.*' \) -delete
find "$STAGING" \( -name __pycache__ -o -name .pytest_cache -o -name .venv \
  -o -name node_modules -o -name .mypy_cache -o -name .ruff_cache \
  -o -name htmlcov \) -type d -prune -exec rm -rf {} + 2>/dev/null || true

# --- frontmatter YAML validation (GitHub / SkillsMP parse strictly; abort on invalid) ---
if command -v python3 >/dev/null 2>&1 && python3 -c 'import yaml' >/dev/null 2>&1; then
  python3 - "$STAGING" <<'PYEOF' || exit 1
import glob, re, sys
import yaml
bad = []
for path in sorted(glob.glob(f"{sys.argv[1]}/**/*.md", recursive=True)):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r"^---\n(.*?)\n---(\n|$)", text, re.S)
    if not m:
        continue
    try:
        yaml.safe_load(m.group(1))
    except yaml.YAMLError as exc:
        bad.append(f"  {path}: {str(exc).splitlines()[0]}")
if bad:
    print("ABORT: invalid YAML frontmatter in staged payload"
          " (strict parsers like GitHub's will fail to render):", file=sys.stderr)
    print("\n".join(bad), file=sys.stderr)
    sys.exit(1)
PYEOF
else
  echo "WARN: python3 + PyYAML not available — skipping frontmatter YAML validation" >&2
fi

# --- secret scan (high-confidence patterns; abort on any hit) ---
SECRET_RE='sk-ant-api[0-9A-Za-z_-]+|ghp_[0-9A-Za-z]{36}|github_pat_[0-9A-Za-z_]{20,}|AKIA[0-9A-Z]{16}|xox[bporas]-[0-9A-Za-z-]{10,}|AIza[0-9A-Za-z_-]{35}|hf_[A-Za-z]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY'
if hits="$(grep -rEl "$SECRET_RE" "$STAGING" 2>/dev/null)"; then
  echo "ABORT: potential secrets detected in staged payload:" >&2
  echo "$hits" >&2
  exit 1
fi

# --- report / apply ---
if (( DRY_RUN )); then
  echo "# DRY-RUN (origin: $ORIGIN) — differences staging vs $TARGET_DIR"
  for name in "${SKILLS[@]}"; do
    diff -rq "$STAGING/skills/$name" "$TARGET_DIR/skills/$name" 2>/dev/null || true
  done
  exit 0
fi

for name in "${SKILLS[@]}"; do
  rm -rf "${TARGET_DIR:?}/skills/$name"
done
cp -R "$STAGING"/skills/. "$TARGET_DIR"/skills/

echo "# APPLIED (origin: $ORIGIN). Review before committing:"
git -C "$TARGET_DIR" status --short
