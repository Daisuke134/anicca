#!/usr/bin/env bash
# apply-to-funder runtime entry. Mode dispatch.
#
# Usage:
#   MODE=prepare bash scripts/run.sh --funder yc-w26
#   MODE=submit  bash scripts/run.sh --funder yc-w26
#   MODE=submit DRY_RUN=true bash scripts/run.sh --funder yc-w26
#
# Modes:
#   prepare — load funder spec, draft K-Dense fields, build pitch payload, write
#             to data/drafts/<funder>/. Does NOT touch {{profile.lateness.stakeholders.channel}}.
#   submit  — run prepare, then drive {{profile.lateness.stakeholders.channel}}-harness via lib/form_filler.sh,
#             click submit (unless DRY_RUN=true).
#
# Env:
#   MODE      prepare | submit                (default: submit)
#   DRY_RUN   true | false                    (default: false; never submits in true)
#   FUNDER    funder id (overrides --funder)
#   SKILL_DIR override skill base directory

set -uo pipefail

SKILL_DIR="${SKILL_DIR:-$HOME/.openclaw/skills/apply-to-funder}"
MODE="${MODE:-submit}"
DRY_RUN="${DRY_RUN:-false}"
FUNDER="${FUNDER:-}"

# --- arg parsing ---
while [ $# -gt 0 ]; do
  case "$1" in
    --funder) FUNDER="$2"; shift 2;;
    --mode)   MODE="$2";   shift 2;;
    --dry-run) DRY_RUN=true; shift;;
    *) echo "[apply-to-funder] unknown arg: $1"; shift;;
  esac
done

[ -z "$FUNDER" ] && { echo "🚨 FUNDER not set (use --funder <id>)"; exit 2; }

LIB="$SKILL_DIR/scripts/lib"
SPEC_FILE="$SKILL_DIR/funders/$FUNDER.json"

[ ! -f "$SPEC_FILE" ] && {
  echo "🚨 funder spec missing for '$FUNDER' — please add funders/$FUNDER.json first"
  echo "   See $SKILL_DIR/funders/yc-w26.json for the schema."
  exit 3
}

echo "▶ apply-to-funder  funder=$FUNDER  mode=$MODE  dry_run=$DRY_RUN"
echo "  spec: $SPEC_FILE"

source "$LIB/funder_loader.sh"
funder_load "$SPEC_FILE"
LOAD_RC=$?

# Guardrail: if loader vetoed (CAPTCHA / 2FA-blocking) and we're in live submit, abort.
# In DRY_RUN we still proceed so the operator can see the plan.
if [ "$LOAD_RC" -ne 0 ] && [ "$MODE" = "submit" ] && [ "$DRY_RUN" != "true" ]; then
  echo "🚨 funder_load aborted (rc=$LOAD_RC). Use MODE=prepare or DRY_RUN=true to inspect."
  exit "$LOAD_RC"
fi

case "$MODE" in
  prepare)
    bash "$SKILL_DIR/scripts/prepare.sh" "$SPEC_FILE"
    ;;
  submit)
    bash "$SKILL_DIR/scripts/prepare.sh" "$SPEC_FILE"
    # Skip the actual submit step if loader vetoed (we only got here in DRY_RUN).
    if [ "$LOAD_RC" -eq 0 ]; then
      bash "$SKILL_DIR/scripts/submit.sh"  "$SPEC_FILE"
    else
      echo "  [LOAD_RC=$LOAD_RC] skipping submit.sh entirely (DRY_RUN inspection mode)"
    fi
    ;;
  *)
    echo "🚨 unknown MODE='$MODE'; expected prepare|submit"; exit 2;;
esac
