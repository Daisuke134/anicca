#!/usr/bin/env bash
# watch-sweep.sh — run the bash-script watch/poll skills in ONE heartbeat pass, so 15+
# standalone watch crons collapse into the single heartbeat entity (shared context via
# interaction-ledger → no double-reply / out-of-context reply). #34.
#
# Two kinds of watchers:
#   • bash-script (handled HERE): detection/triage scripts that run deterministically.
#   • agent-driven (handled in HEARTBEAT §2 by the LLM): Gmail/gog reply-judgement that
#     needs the model (meetup-accept, opening-cafe-watch-replies, skill-scout, hot-hooks).
#
# Reply-emitting watchers MUST read state/interaction-ledger.jsonl before replying (who /
# thread / last-reply / pending) so the one-entity beat never double-replies or replies
# out of context. New/changed items are surfaced to §3 for the beat to act on.
#
# NOT folded (stay as wall-clock crons): dais-morning-leave-check (7:50 leave), posting peaks,
# heavy pipelines. See ANICCA_AUTONOMY_SPEC.md W6.
set -uo pipefail
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
LEDGER="$ANICCA_HOME/state/interaction-ledger.jsonl"
mkdir -p "$(dirname "$LEDGER")"; [ -f "$LEDGER" ] || : > "$LEDGER"
ev() { python3 "$ANICCA_HOME/skills/_shared/event_log.py" "$@" >/dev/null 2>&1 || true; }

# fold-set: bash-script watchers (name → command). Each runs with a per-watcher timeout.
run_watcher() {
  local name="$1"; shift
  echo "── watch-sweep: $name ──"
  if timeout 120 bash -c "$*" 2>&1 | tail -6; then ev watch.swept watcher="$name" ok=1
  else echo "  ($name returned nonzero)"; ev watch.swept watcher="$name" ok=0; fi
}

echo "════ watch-sweep ($(date '+%H:%M')) — folded watchers, shared ledger=$LEDGER ════"
run_watcher comedy-watch-replies     "bash $ANICCA_HOME/skills/anicca-comedy-factory/scripts/watch-replies-6h.sh"
run_watcher comedy-recruit-poll      "bash $ANICCA_HOME/skills/anicca-comedy-factory/scripts/recruit-poll-daily.sh"
run_watcher opening-cafe-uber-poll   "bash $ANICCA_HOME/skills/opening-cafe-tokyo-skills/scripts/lib/uber-status-check.sh"
run_watcher retreat-phase1-reply     "bash $ANICCA_HOME/skills/anicca-retreat-factory/scripts/phase1-reply-watch.sh"
run_watcher retreat-phase2-triage    "bash $ANICCA_HOME/skills/anicca-retreat-factory/scripts/phase2-reply-triage.sh"
run_watcher retreat-phase4-followup  "bash $ANICCA_HOME/skills/anicca-retreat-factory/scripts/phase4-followup-scanner.sh"
run_watcher politician-reply-watch   "MODE=reply_watch bash $ANICCA_HOME/skills/politician/scripts/run.sh"
run_watcher naist-edu-portal-check   "MODE=edu-portal-check bash $ANICCA_HOME/skills/naist/scripts/run.sh"
run_watcher tt-draft-graduator       "bash $ANICCA_HOME/skills/tt-draft-graduator/scripts/check.sh"
run_watcher account-burn-detector    "bash $ANICCA_HOME/skills/account-burn-detector/scripts/run.sh"
run_watcher skill-cull-analyzer      "bash $ANICCA_HOME/skills/skill-cull-analyzer/scripts/run_weekly.sh"
echo "════ watch-sweep done — surface any new/changed items to §3 (reply via ledger) ════"
echo "NOTE: agent-driven watchers (meetup-accept / opening-cafe-watch-replies / skill-scout /"
echo "      hot-hooks-refresh) are handled by the LLM in HEARTBEAT §2 (Gmail/gog), not here."
