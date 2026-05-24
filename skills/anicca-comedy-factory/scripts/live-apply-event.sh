#!/usr/bin/env bash
# comedy-live-apply-event — event-driven trigger
#
# Usage: live-apply-event.sh <city>
#
# Flow:
#   1. data/live-events/<city>-<YYYY-MM-DD>.json (next 35 days, not applied) を探す
#   2. 各 candidate の signup_method 別に応募:
#       - {{profile.lateness.stakeholders.channel}}_host / online_form_or_{{profile.lateness.stakeholders.channel}} → gog gmail で template send
#       - in_person_at_door → Slack 通知のみ (Dais 物理 signup)
#       - online_form → 将来 agent-{{profile.lateness.stakeholders.channel}} で form 入力 (今は Slack 通知)
#   3. applied=true + message_id 永続化
#   4. Slack #metrics 報告
#
# stdout last line: ✅ live-apply: <N> applications sent / <M> manual flag

set -euo pipefail

CITY="${1:-}"
[ -z "$CITY" ] && { echo "❌ live-apply: city required (e.g. sf, tokyo, la)"; exit 1; }

SKILL_DIR="$HOME/.openclaw/skills/anicca-comedy-factory"
DATA_DIR="$SKILL_DIR/data"
LIVE_DIR="$DATA_DIR/live-events"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
source "$HOME/.openclaw/skills/sao-content-factory/lib/slack.sh"

NOW_S=$(date +%s)
H35=$(( 35 * 86400 ))

sent=0
manual=0
files_changed=""

shopt -s nullglob
for f in "$LIVE_DIR/${CITY}-"*.json; do
  date=$(jq -r '.date' "$f")
  trip_s=$(date -j -f "%Y-%m-%d" "$date" +%s 2>/dev/null || date -d "$date" +%s)
  diff=$(( trip_s - NOW_S ))
  [ "$diff" -lt 0 ] && continue
  [ "$diff" -gt "$H35" ] && continue

  N=$(jq '.candidates | length' "$f")
  for i in $(seq 0 $((N - 1))); do
    applied=$(jq -r ".candidates[$i].applied // false" "$f")
    [ "$applied" = "true" ] && continue

    method=$(jq -r ".candidates[$i].signup_method // \"\"" "$f")
    name=$(jq -r ".candidates[$i].name" "$f")
    {{profile.lateness.stakeholders.channel}}=$(jq -r ".candidates[$i].host_{{profile.lateness.stakeholders.channel}} // \"\"" "$f")

    case "$method" in
      {{profile.lateness.stakeholders.channel}}_host|online_form_or_{{profile.lateness.stakeholders.channel}})
        if [ -z "${{profile.lateness.stakeholders.channel}}" ]; then
          # Email missing — flag for manual
          manual=$((manual + 1))
          continue
        fi
        body="Hi,

I'm Daisuke (\"Dais\") — Tokyo-based founder + open mic comedian. I'll be in $(echo "$CITY" | tr '[:lower:]' '[:upper:]') on $date and would love to do a 5-min set at $name.

Material: impermanence-themed monk persona stand-up (English, occasional JP). I run anicca.ai — a Buddhist AI agent project — and that lens is the spine of the act.

Three quick questions:
1. Is the open mic running on $date?
2. What time should I arrive for sign-up?
3. Anything I should know as a first-timer?

Thanks,
Dais
{{profile.contact.personalEmail}}
https://aniccaai.com/comedy"

        resp=$(/opt/homebrew/bin/gog send \
          --account {{profile.contact.personalEmail}} \
          --to "${{profile.lateness.stakeholders.channel}}" \
          --subject "${CITY^^} visit $date — Tokyo comedian asking about $name" \
          --body "$body" -j 2>/dev/null || echo '{}')
        mid=$(echo "$resp" | jq -r '.messageId // empty')
        if [ -n "$mid" ]; then
          tmp=$(mktemp)
          jq --argjson i "$i" --arg mid "$mid" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            '.candidates[$i] += {applied: true, applied_at: $ts, application_method: "gmail", message_id: $mid}' \
            "$f" > "$tmp" && mv "$tmp" "$f"
          sent=$((sent + 1))
          files_changed="${files_changed}${f}\n"
        fi
        ;;
      in_person_at_door|lottery|professional_only)
        # Dais 物理 signup or non-applicable → flag
        manual=$((manual + 1))
        ;;
      online_form|*)
        # 将来 agent-{{profile.lateness.stakeholders.channel}} で form 入力 → 今は manual flag
        manual=$((manual + 1))
        ;;
    esac
  done
done

slack_metrics "*comedy-live-apply-event ($CITY):* sent=$sent manual=$manual" >/dev/null || true

echo "✅ live-apply: $sent application(s) sent / $manual manual"
