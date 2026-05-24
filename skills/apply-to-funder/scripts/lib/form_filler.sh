#!/usr/bin/env bash
# form_filler.sh — generic CDP form filler driven by funder JSON spec.
# Invoked by submit.sh in live mode only. In DRY_RUN, submit.sh exits before this.
#
# Inputs:  $1 = path to funders/<id>.json
#          $2 = path to resolved payload JSON
# Env:     BU_CDP_URL (default http://127.0.0.1:9223)
# Requires: {{profile.lateness.stakeholders.channel}}-harness, jq, curl, Chrome 9223 with {{profile.lateness.stakeholders.channel}}-harness profile.

set -uo pipefail

SPEC="$1"
PAYLOAD="$2"
SKILL_DIR="${SKILL_DIR:-$HOME/.openclaw/skills/apply-to-funder}"
CDP_URL="${BU_CDP_URL:-http://127.0.0.1:9223}"
export BU_CDP_URL="$CDP_URL"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

FUNDER_ID=$(jq -r '.id' "$SPEC")
FUNDER_URL=$(jq -r '.url' "$SPEC")
AUTH_KIND=$(jq -r '.auth.kind // "none"' "$SPEC")

# 1. Ensure Chrome up
if ! curl -sS -o /dev/null -w '%{http_code}' "$CDP_URL/json/version" | grep -q 200; then
  echo "  starting Chrome 9223…"
  nohup '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
    --remote-debugging-port=9223 \
    --user-data-dir="$HOME/.{{profile.lateness.stakeholders.channel}}-harness-profile" \
    --no-first-run --no-default-{{profile.lateness.stakeholders.channel}}-check \
    > /tmp/chrome-9223.log 2>&1 &
  for i in 1 2 3 4 5 6 7 8; do sleep 1
    curl -sS -o /dev/null -w '%{http_code}' "$CDP_URL/json/version" | grep -q 200 && break
  done
fi

# 2. Auth
if [ "$AUTH_KIND" = "session_cookie" ]; then
  LOGIN_URL=$(jq -r '.auth.login_url' "$SPEC")
  EMAIL_VAR=$(jq -r '.auth.{{profile.lateness.stakeholders.channel}}_env'    "$SPEC")
  PW_VAR=$(jq    -r '.auth.password_env' "$SPEC")
  EMAIL="${!EMAIL_VAR:-}"
  PW="${!PW_VAR:-}"
  [ -z "$EMAIL" ] || [ -z "$PW" ] && { echo "🚨 missing creds env $EMAIL_VAR / $PW_VAR"; exit 7; }
  {{profile.lateness.stakeholders.channel}}-harness -c "
goto_url('$LOGIN_URL')
wait_for_load()
import time; time.sleep(2)
info = page_info()
print('LOGIN_URL_NOW', info.get('url',''))
if 'sign_in' in info.get('url','').lower() or info.get('url','').rstrip('/') == '$LOGIN_URL'.rstrip('/'):
    try:
        fill_input('{{profile.lateness.stakeholders.channel}}', '$EMAIL')
        fill_input('password', '$PW')
        click_button('Sign In')
        time.sleep(3)
    except Exception as e:
        print('LOGIN_SKIP', e)
" 2>&1 | head -10
fi

# 3. Draft resolution (per spec)
DRAFT_STRATEGY=$(jq -r '.draft_resolution.strategy // "none"' "$SPEC")
DRAFT_ID=""
if [ "$DRAFT_STRATEGY" = "continue_or_start" ]; then
  HOME_URL=$(jq -r '.draft_resolution.home_url' "$SPEC")
  CONT_BTN=$(jq -r '.draft_resolution.continue_button' "$SPEC")
  START_BTN=$(jq -r '.draft_resolution.start_button' "$SPEC")
  REGEX=$(jq    -r '.draft_resolution.draft_id_regex' "$SPEC")
  {{profile.lateness.stakeholders.channel}}-harness -c "
goto_url('$HOME_URL')
wait_for_load()
import time; time.sleep(2)
for label in ('$CONT_BTN', '$START_BTN'):
    try:
        click_button(label); time.sleep(3); break
    except Exception: continue
print('AFTER_HOME', page_info().get('url',''))
" 2>&1 | tail -5
  DRAFT_ID=$({{profile.lateness.stakeholders.channel}}-harness -c "
import re
u = page_info().get('url','')
m = re.search(r'$REGEX', u)
print('DRAFT_ID', m.group(1) if m else '')
" 2>&1 | grep DRAFT_ID | awk '{print $2}')
  [ -z "$DRAFT_ID" ] && { echo "🚨 could not resolve draft_id"; exit 8; }
  echo "  draft=$DRAFT_ID"
fi

EDIT_TPL=$(jq -r '.edit_url_template // ""' "$SPEC")
build_url() {
  local suffix="$1"
  if [ -n "$DRAFT_ID" ] && [ -n "$EDIT_TPL" ]; then
    local base="${EDIT_TPL/\{draft_id\}/$DRAFT_ID}"
    base="${base%/edit}"
    [ -z "$suffix" ] && echo "$base/edit" || echo "$base/$suffix"
  else
    echo "$FUNDER_URL"
  fi
}

# 4. For each page, fill all fields, click save
PAGES_COUNT=$(jq '.pages | length' "$SPEC")
for ((p=0; p<PAGES_COUNT; p++)); do
  PAGE_NAME=$(jq -r ".pages[$p].name" "$SPEC")
  PATH_SUF=$(jq  -r ".pages[$p].path_suffix" "$SPEC")
  SAVE_BTN=$(jq  -r ".pages[$p].save_button // empty" "$SPEC")
  PAGE_URL=$(build_url "$PATH_SUF")
  echo "  ── page=$PAGE_NAME url=$PAGE_URL ──"

  FCOUNT=$(jq ".pages[$p].fields | length" "$SPEC")
  for ((f=0; f<FCOUNT; f++)); do
    FLD=$(jq -c ".pages[$p].fields[$f]" "$SPEC")
    FNAME=$(echo "$FLD" | jq -r '.name')
    FTYPE=$(echo "$FLD" | jq -r '.type')
    FSEL=$(echo  "$FLD" | jq -r '.selector // ""')
    KEY="$PAGE_NAME.$FNAME"
    VAL=$(jq -r --arg k "$KEY" '.[$k] // ""' "$PAYLOAD")

    case "$FTYPE" in
      text|textarea)
        # JS native value setter
        ESC_VAL=$(printf '%s' "$VAL" | jq -Rs .)
        {{profile.lateness.stakeholders.channel}}-harness -c "
goto_url('$PAGE_URL')
wait_for_load()
import time; time.sleep(2)
js = '''(function(){var el=document.querySelector('$FSEL'); if(!el) return 'MISSING'; var p=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype; var s=Object.getOwnPropertyDescriptor(p,'value').set; s.call(el, $ESC_VAL); el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); el.dispatchEvent(new Event('blur',{bubbles:true})); return 'FILLED:$FNAME';})()'''
print(run_js(js))
" 2>&1 | tail -2
        ;;
      file)
        SRC=$(echo "$FLD" | jq -r '.value_source')
        if [[ "$SRC" == config.* ]]; then
          PATH_VAL=$(jq -r ".config[\"${SRC#config.}\"]" "$SPEC")
          EXPANDED="${PATH_VAL/#\~/$HOME}"
          [ ! -f "$EXPANDED" ] && { echo "    🚨 file missing: $EXPANDED — skip"; continue; }
          {{profile.lateness.stakeholders.channel}}-harness -c "
goto_url('$PAGE_URL')
wait_for_load()
import time; time.sleep(2)
try:
    set_file_input('$FSEL', '$EXPANDED'); time.sleep(8); print('UPLOADED:$FNAME')
except Exception as e:
    try: set_file_input('input[type=file]', '$EXPANDED'); time.sleep(8); print('UPLOADED_FB:$FNAME')
    except Exception as e2: print('UPLOAD_FAIL:$FNAME', e2)
" 2>&1 | tail -2
        fi
        ;;
      indexed_inputs)
        # Array of values into input[i] in document order
        COUNT=$(echo "$FLD" | jq -r '.count')
        ARR_JSON="$VAL"  # already JSON array string e.g. "[0,0,0,0,0,68]"
        {{profile.lateness.stakeholders.channel}}-harness -c "
goto_url('$PAGE_URL')
wait_for_load()
import time; time.sleep(2)
js = '''(function(){var arr=$ARR_JSON; var els=document.querySelectorAll('$FSEL'); var p=HTMLInputElement.prototype; var s=Object.getOwnPropertyDescriptor(p,'value').set; for(var i=0;i<Math.min(arr.length,els.length,$COUNT);i++){s.call(els[i], String(arr[i])); els[i].dispatchEvent(new Event('input',{bubbles:true})); els[i].dispatchEvent(new Event('change',{bubbles:true})); els[i].dispatchEvent(new Event('blur',{bubbles:true}));} return 'FILLED_INDEXED:'+Math.min(arr.length,els.length);})()'''
print(run_js(js))
" 2>&1 | tail -2
        ;;
      fake_radio_div)
        FILTER=$(echo "$FLD" | jq -r '.selector_filter')
        {{profile.lateness.stakeholders.channel}}-harness -c "
goto_url('$PAGE_URL')
wait_for_load()
import time; time.sleep(2)
js = '''(function(){var divs=Array.from(document.querySelectorAll('div.cursor-pointer, div[role=\"radio\"]')); var hits=divs.filter(function(d){var t=d.textContent.trim(); return /\\\\b$FILTER\\\\b/i.test(t) && t.length<10;}); hits.forEach(function(d){d.click();}); return 'CLICKED:'+hits.length;})()'''
print(run_js(js))
" 2>&1 | tail -2
        ;;
      select)
        ESC_VAL=$(printf '%s' "$VAL" | jq -Rs .)
        {{profile.lateness.stakeholders.channel}}-harness -c "
goto_url('$PAGE_URL')
wait_for_load()
import time; time.sleep(2)
js = '''(function(){var el=document.querySelector('$FSEL'); if(!el) return 'MISSING'; el.value=$ESC_VAL; el.dispatchEvent(new Event('change',{bubbles:true})); return 'SELECTED:'+el.value;})()'''
print(run_js(js))
" 2>&1 | tail -2
        ;;
      *)
        echo "    [skip: unknown field type=$FTYPE name=$FNAME]"
        ;;
    esac
  done

  # save
  if [ -n "$SAVE_BTN" ] && [ "$SAVE_BTN" != "null" ]; then
    {{profile.lateness.stakeholders.channel}}-harness -c "
import time; time.sleep(1)
try: click_button('$SAVE_BTN'); time.sleep(3); print('SAVED:$PAGE_NAME')
except Exception as e: print('SAVE_SKIP:$PAGE_NAME', e)
" 2>&1 | tail -2
  fi
done

# 5. Submit
SUBMIT_PAGE=$(jq -r '.submit.page' "$SPEC")
SUBMIT_BTN=$(jq  -r '.submit.button_text' "$SPEC")
SUBMIT_URL=$(build_url "edit")
echo "  ── submit on page=$SUBMIT_PAGE  btn='$SUBMIT_BTN' ──"
{{profile.lateness.stakeholders.channel}}-harness -c "
goto_url('$SUBMIT_URL')
wait_for_load()
import time; time.sleep(2)
try:
    click_button('$SUBMIT_BTN'); time.sleep(5)
    try: click_button('Submit'); time.sleep(2)
    except Exception: pass
    print('SUBMITTED', page_info().get('url',''))
except Exception as e:
    print('SUBMIT_FAIL', e)
" 2>&1 | tail -10

# 6. Persist state
STATE_FILE="$SKILL_DIR/data/applications/$FUNDER_ID-latest.json"
TS=$(date -u +%FT%TZ)
mkdir -p "$(dirname "$STATE_FILE")"
jq -n --arg id "$FUNDER_ID" --arg draft "$DRAFT_ID" --arg payload "$PAYLOAD" --arg ts "$TS" \
  '{funder_id:$id, draft_id:$draft, payload:$payload, status:"submitted", submitted_at:$ts}' \
  > "$STATE_FILE"
cp "$STATE_FILE" "$SKILL_DIR/data/applications/$FUNDER_ID-$(date +%Y%m%d-%H%M).json"
echo "  state → $STATE_FILE"
