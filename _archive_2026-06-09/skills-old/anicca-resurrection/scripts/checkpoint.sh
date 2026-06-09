#!/usr/bin/env bash
# checkpoint.sh — snapshot the live instance's self-model (spec 18 §3 RESURRECTION; P14 #337
# Wave 1). Writes ~/.hermes/state/checkpoints/<id>.json (chmod 600) + a ledger row. Gathering is
# best-effort: a missing field falls back rather than failing the whole checkpoint.
#
# Cron entry point (daily). No restart — that is a deliberate failover act (see restart.sh).
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
. "$DIR/_lib.sh"

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# --- model: last token of `hermes model` output, else "unknown".
MODEL="$(hermes model 2>/dev/null | tail -1 | awk '{print $NF}')"; MODEL="${MODEL:-unknown}"

# --- profile: best-effort (Hermes profile cmd may not exist), else env, else "genesis".
PROFILE="$(hermes profile current 2>/dev/null | tail -1 | awk '{print $NF}')"
PROFILE="${PROFILE:-${HERMES_PROFILE:-genesis}}"

# --- last_skill_run: newest ts across the live state jsonl logs, else "none".
LAST_SKILL_RUN="none"
if compgen -G "$HERMES_LIVE_HOME/state/"*.jsonl >/dev/null 2>&1; then
  LAST_SKILL_RUN="$(grep -rhoE '"ts":"[^"]+"' "$HERMES_LIVE_HOME/state/"*.jsonl 2>/dev/null \
    | sed -E 's/"ts":"([^"]+)"/\1/' | sort | tail -1)"
  LAST_SKILL_RUN="${LAST_SKILL_RUN:-none}"
fi

# --- last_decision: last line of self-manage decisions, else "none".
LAST_DECISION="none"
if [ -s "$HERMES_LIVE_HOME/state/self-manage-decisions.jsonl" ]; then
  LAST_DECISION="$(tail -1 "$HERMES_LIVE_HOME/state/self-manage-decisions.jsonl")"
fi

# --- config + oss sha.
CONFIG_SHA="$(rs_sha_file "$HERMES_LIVE_HOME/cron/jobs.json")"
OSS_SHA="$(git -C "$RS_REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "none")"

CKID="$(rs_id "$MODEL$PROFILE$OSS_SHA$TS")"
CKFILE="$CHECKPOINTS_DIR/$CKID.json"

"$JQ" -nc \
  --arg id "$CKID" --arg ts "$TS" --arg model "$MODEL" --arg profile "$PROFILE" \
  --arg lsr "$LAST_SKILL_RUN" --arg ld "$LAST_DECISION" \
  --arg csha "$CONFIG_SHA" --arg osha "$OSS_SHA" \
  '{checkpoint_id:$id, ts:$ts, model:$model, profile:$profile,
    last_skill_run:$lsr, last_decision:$ld,
    hermes_config_sha:$csha, anicca_oss_sha:$osha}' > "$CKFILE"
chmod 600 "$CKFILE"

rs_log "$("$JQ" -nc --arg ts "$TS" --arg id "$CKID" --arg osha "$OSS_SHA" \
  '{ts:$ts, op:"checkpoint", checkpoint_id:$id, anicca_oss_sha:$osha}')"

echo "checkpoint: wrote $CKID (model=$MODEL profile=$PROFILE oss=${OSS_SHA:0:8})"
