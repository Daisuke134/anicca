#!/usr/bin/env bash
# install.sh — bundle this repo's skills AND agents into ~/.claude
# Idempotent. Backs up any pre-existing target before overwriting (default).
#
#   ./install.sh            # install; back up replaced files to *.bak-<ts>
#   ./install.sh --force    # overwrite without backups
#   ./install.sh --dry-run  # print what would happen, change nothing
set -eu

# --- locate repo root (the dir this script lives in) -------------------------
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cd "$SCRIPT_DIR"

CLAUDE_DIR="${CLAUDE_HOME:-$HOME/.claude}"
SKILLS_DST="$CLAUDE_DIR/skills"
AGENTS_DST="$CLAUDE_DIR/agents"
TS=$(date +%Y%m%d-%H%M%S)

FORCE=0
DRY=0
for arg in "$@"; do
  case "$arg" in
    --force)   FORCE=1 ;;
    --dry-run) DRY=1 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

run()  { if [ "$DRY" -eq 1 ]; then echo "  [dry-run] $*"; else "$@"; fi; }
say()  { printf '%s\n' "$*"; }

# Identical content? skip entirely (true idempotency, no spurious .bak).
same() {
  # $1 = src (file or dir), $2 = dst
  [ -e "$2" ] || return 1
  diff -rq "$1" "$2" >/dev/null 2>&1
}

backup() {
  # $1 = existing target to preserve
  bak="$1.bak-$TS"
  say "  backup: $1 -> $bak"
  run mv "$1" "$bak"
}

install_one() {
  # $1 = src path, $2 = dst path, $3 = label
  src="$1"; dst="$2"; label="$3"
  if same "$src" "$dst"; then
    say "  unchanged: $label"
    return
  fi
  if [ -e "$dst" ]; then
    if [ "$FORCE" -eq 1 ]; then
      say "  overwrite (--force): $label"
      run rm -rf "$dst"
    else
      backup "$dst"
    fi
  else
    say "  install: $label"
  fi
  run cp -R "$src" "$dst"
}

say "Installing from: $SCRIPT_DIR"
say "Target:          $CLAUDE_DIR"
[ "$DRY" -eq 1 ] && say "(dry-run: no changes will be made)"
run mkdir -p "$SKILLS_DST" "$AGENTS_DST"

# --- skills ------------------------------------------------------------------
if [ -d skills ]; then
  say ""
  say "Skills:"
  for d in skills/*/; do
    [ -d "$d" ] || continue
    name=$(basename "$d")
    install_one "$d" "$SKILLS_DST/$name" "skills/$name"
  done
fi

# --- agents ------------------------------------------------------------------
if [ -d agents ]; then
  say ""
  say "Agents:"
  for f in agents/*.md; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    install_one "$f" "$AGENTS_DST/$name" "agents/$name"
  done
fi

# --- uv sync for THIS repo's skills that declare Python deps ------------------
if [ -d skills ] && command -v uv >/dev/null 2>&1; then
  synced=0
  for p in skills/*/pyproject.toml; do
    [ -f "$p" ] || continue
    if [ "$synced" -eq 0 ]; then say ""; say "Python deps (uv sync):"; synced=1; fi
    name=$(basename "$(dirname "$p")")
    say "  uv sync: $name"
    run sh -c "cd '$SKILLS_DST/$name' && uv sync"
  done
elif [ -d skills ] && ! command -v uv >/dev/null 2>&1; then
  say ""
  say "note: 'uv' not found — skipped dependency sync."
  say "      install uv (https://docs.astral.sh/uv/) and re-run if any skill needs it."
fi

say ""
if [ "$DRY" -eq 1 ]; then
  say "Dry run complete. No changes made."
else
  say "Done. Backed-up files (if any) are alongside the originals as *.bak-$TS."
fi
