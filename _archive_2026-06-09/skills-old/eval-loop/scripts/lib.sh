# eval-loop lib helpers. Source this from any skill that wants inline gating.
#
# Functions:
#   eval_or_fail <rubric.json> <output-file-or-dash> [input-file]
#     Reads output text from <output-file> (or stdin if "-"). Runs the 4-dim eval
#     using the provided rubric. Echoes the JSON result to stderr. Returns 0 if
#     pass==true, 1 if pass==false, 2 on usage error.
#
# Usage examples:
#   source /path/to/eval-loop/scripts/lib.sh
#   echo "$OUT" | eval_or_fail "$RUBRIC" - "$IN"
#   eval_or_fail "$RUBRIC" "$OUT_FILE" "$IN_FILE"
#
# NOTE: This helper does NOT alter the calling shell's environment.

# shellcheck shell=bash

_eval_loop_skill_dir() {
  # Resolve the directory THIS file lives in, even when sourced.
  local src
  src="${BASH_SOURCE[0]:-${(%):-%x}}"
  # Strip /scripts/lib.sh to get skill root
  ( cd "$(dirname "$src")/.." && pwd )
}

eval_or_fail() {
  local rubric="${1:-}"
  local out_arg="${2:-}"
  local in_file="${3:-}"

  if [ -z "$rubric" ] || [ -z "$out_arg" ]; then
    echo "eval_or_fail: usage: eval_or_fail <rubric.json> <output-file-or-dash> [input-file]" >&2
    return 2
  fi
  if [ ! -r "$rubric" ]; then
    echo "eval_or_fail: rubric not readable: $rubric" >&2
    return 2
  fi

  local skill_dir
  skill_dir="$(_eval_loop_skill_dir)"

  # Materialize stdin to a temp file if "-"
  local tmp_out=""
  if [ "$out_arg" = "-" ]; then
    tmp_out="$(mktemp -t eval_loop_out.XXXXXX)"
    cat > "$tmp_out"
    out_arg="$tmp_out"
  fi

  # Default input = "(no input provided)" file if not given
  local tmp_in=""
  if [ -z "$in_file" ]; then
    tmp_in="$(mktemp -t eval_loop_in.XXXXXX)"
    printf 'evaluate the actual_output on its own merits.\n' > "$tmp_in"
    in_file="$tmp_in"
  fi

  # eval_or_fail is a side-effectful gate (callers branch on its exit code
  # to ship/abort). Default to EVAL_MODE=production so heuristic fallback
  # fails closed (codex P6 round 2 fix). Tests that want the test-mode
  # heuristic-can-pass behavior pre-export EVAL_MODE=test before sourcing.
  local result rc=0
  result="$(EVAL_MODE="${EVAL_MODE:-production}" "$skill_dir/scripts/eval.sh" "$in_file" "$out_arg" "$rubric")" || rc=$?
  echo "$result" >&2

  [ -n "$tmp_out" ] && rm -f "$tmp_out"
  [ -n "$tmp_in" ] && rm -f "$tmp_in"

  if [ "$rc" -ne 0 ]; then
    return "$rc"
  fi
  if echo "$result" | /usr/bin/jq -e '.pass == true' >/dev/null 2>&1; then
    return 0
  fi
  return 1
}
