#!/usr/bin/env bash
# DistroKid auto-upload via camofox-{{profile.lateness.stakeholders.channel}} (memory rule: camofox is DEFAULT).
#
# Submits ONE single track. Apple Music + iTunes ALWAYS unchecked
# (Anicca policy — no Apple credits).
#
# Why camofox instead of playwright-cli:
#   - DistroKid login is a Google OAuth popup; playwright-cli CLI can't follow popups
#     and Chrome for Testing trips Google bot detection. Camofox (Firefox stealth)
#     passes the bot check, and storage-state.json in the camofox profile persists.
#   - This script also handles auto-login: if /new/ redirects to /signin/, it does
#     the full Google OAuth flow with creds from ~/.openclaw/.env and grabs the
#     2-Step code from Gmail via gogcli.
#
# Usage:
#   04-upload-distrokid-cf.sh <audio_path> <cover_path> <title> <genre_jp> <release_yyyy_mm_dd> <output_dir>
#
# Output:
#   $output_dir/upload-receipt.json with { albumuuid, hyperfollow_url, release_date }

set -uo pipefail

AUDIO="$1"
COVER="$2"
TITLE="$3"
GENRE_JP="$4"
RELEASE_DATE="$5"
OUTDIR="$6"

mkdir -p "$OUTDIR"

# ──────── env + helpers ────────
[ -f "$HOME/.openclaw/.env" ] && { set -a; source "$HOME/.openclaw/.env"; set +a; }
source "$HOME/.openclaw/skills/camofox-{{profile.lateness.stakeholders.channel}}/scripts/cf.sh"

export CF_USER="${CF_USER:-anicca}"
export CF_SESSION="${CF_SESSION:-distrokid}"
export CF_HOST="${CF_HOST:-http://localhost:9377}"

TAB=""

snap_text() { cf_snapshot "$TAB" | jq -r .snapshot; }

# find_ref ROLE NAME → e<num>. Looks for `- ROLE "NAME" [eN]` patterns.
# camofox snapshot format. Falls back to substring match if exact fails.
find_ref_cf() {
  local role="$1" name="$2"
  snap_text | grep -F " \"$name\"" | grep -E "$role" | grep -oE '\[e[0-9]+\]' | head -1 | tr -d '[]'
}

# evaluate JS expression in current tab
cf_eval() {
  local expr="$1"
  curl -sS -X POST "$CF_HOST/tabs/$TAB/evaluate" \
    -H 'Content-Type: application/json' \
    -d "$(jq -n --arg u "$CF_USER" --arg s "$CF_SESSION" --arg e "$expr" '{userId:$u, sessionKey:$s, expression:$e}')"
}

fail() {
  local step="$1" msg="$2"
  echo "❌ FAILED at $step: $msg" >&2
  [ -n "$TAB" ] && cf_screenshot "$TAB" "$OUTDIR/.fail-$step.png" >/dev/null 2>&1 || true
  exit 1
}

# ──────── auto-login (Google OAuth + gogcli 2FA) ────────
do_auto_login() {
  echo "  → auto-login: Google OAuth + 2FA via gogcli"
  [ -z "${DISTROKID_EMAIL:-}" ] && fail "auto-login" "DISTROKID_EMAIL not set"
  [ -z "${DISTROKID_PASSWORD:-}" ] && fail "auto-login" "DISTROKID_PASSWORD not set"

  cf_navigate "$TAB" "https://distrokid.com/signin/" >/dev/null
  sleep 4

  local GOOGLE_REF
  GOOGLE_REF=$(snap_text | grep -F "Sign in with Google" | grep -oE '\[e[0-9]+\]' | head -1 | tr -d '[]')
  [ -z "$GOOGLE_REF" ] && GOOGLE_REF=$(snap_text | grep -F "Googleでログイン" | grep -oE '\[e[0-9]+\]' | head -1 | tr -d '[]')
  [ -z "$GOOGLE_REF" ] && fail "auto-login" "no Google sign-in button"

  cf_click "$TAB" "$GOOGLE_REF" >/dev/null
  sleep 6

  # After Google OAuth, may land on:
  #   (a) /mymusic/ (logged in directly, no 2FA needed — trusted device)
  #   (b) /newComputer/?forward=... (2FA required — code {{profile.lateness.stakeholders.channel}}ed)
  #   (c) accounts.google.com (Google login UI — fill {{profile.lateness.stakeholders.channel}}/password, then back to DistroKid)
  local URL
  URL=$(cf_url "$TAB")

  if [[ "$URL" == *"accounts.google.com"* ]]; then
    # Google login UI
    local GE_REF GP_REF GN_REF
    GE_REF=$(snap_text | grep -E 'input.*{{profile.lateness.stakeholders.channel}}|textbox.*[Ee]mail' | grep -oE '\[e[0-9]+\]' | head -1 | tr -d '[]')
    if [ -n "$GE_REF" ]; then
      cf_type "$TAB" "$GE_REF" "$DISTROKID_EMAIL" >/dev/null; sleep 1
      GN_REF=$(snap_text | grep -F "次へ" | head -1 | grep -oE '\[e[0-9]+\]' | tr -d '[]')
      [ -z "$GN_REF" ] && GN_REF=$(snap_text | grep -F "Next" | head -1 | grep -oE '\[e[0-9]+\]' | tr -d '[]')
      [ -n "$GN_REF" ] && cf_click "$TAB" "$GN_REF" >/dev/null
      sleep 4
      GP_REF=$(snap_text | grep -E '(password|パスワード)' | grep -oE '\[e[0-9]+\]' | head -1 | tr -d '[]')
      [ -n "$GP_REF" ] && cf_type "$TAB" "$GP_REF" "$DISTROKID_PASSWORD" >/dev/null; sleep 1
      GN_REF=$(snap_text | grep -F "次へ" | head -1 | grep -oE '\[e[0-9]+\]' | tr -d '[]')
      [ -z "$GN_REF" ] && GN_REF=$(snap_text | grep -F "Next" | head -1 | grep -oE '\[e[0-9]+\]' | tr -d '[]')
      [ -n "$GN_REF" ] && cf_click "$TAB" "$GN_REF" >/dev/null
      sleep 6
    fi
    URL=$(cf_url "$TAB")
  fi

  if [[ "$URL" == *"/newComputer/"* ]]; then
    # 2FA — wait a moment for the {{profile.lateness.stakeholders.channel}} to arrive, fetch the latest code from Gmail
    sleep 6
    local MSG_ID CODE
    for tries in 1 2 3 4 5; do
      MSG_ID=$(/opt/homebrew/bin/gog gmail messages search "from:distrokid newer_than:5m" -a "$DISTROKID_EMAIL" --max 1 --json 2>/dev/null | jq -r '.messages[0].id // empty')
      [ -n "$MSG_ID" ] && break
      sleep 4
    done
    [ -z "$MSG_ID" ] && fail "auto-login" "could not find DistroKid 2FA {{profile.lateness.stakeholders.channel}} within 30s"
    CODE=$(/opt/homebrew/bin/gog gmail get "$MSG_ID" -a "$DISTROKID_EMAIL" 2>/dev/null | grep -oE '確認コード：<b>[0-9]+|verification code[^0-9]*[0-9]{4,8}|[Cc]ode[: ]+[0-9]{4,8}' | head -1 | grep -oE '[0-9]{4,8}')
    [ -z "$CODE" ] && fail "auto-login" "could not extract 2FA code from {{profile.lateness.stakeholders.channel}} $MSG_ID"
    echo "  → 2FA code: $CODE"

    local CODE_REF
    CODE_REF=$(snap_text | grep -E 'spinbutton|textbox.*code' | grep -oE '\[e[0-9]+\]' | head -1 | tr -d '[]')
    [ -z "$CODE_REF" ] && fail "auto-login" "no 2FA code input field"
    cf_type "$TAB" "$CODE_REF" "$CODE" >/dev/null
    sleep 5
    URL=$(cf_url "$TAB")
  fi

  [[ "$URL" == *"/signin/"* || "$URL" == *"/newComputer/"* ]] && fail "auto-login" "login flow stuck at $URL"
  echo "  ✓ logged in (URL: $URL)"
}

# ──────── 0. open camofox tab + navigate ────────
echo "[0] open camofox tab"
TAB=$(cf_open_tab "https://distrokid.com/new/")
[ -z "$TAB" ] && fail "tab" "could not open camofox tab"
sleep 4
echo "  TAB=$TAB URL=$(cf_url "$TAB")"

# Switch UI to 日本語 (forms use Japanese labels in scripts below)
cf_eval "(()=>{const s=document.querySelector('#sitetran_select'); if(!s) return 'no-switcher'; const o=[...s.options].find(o=>o.text==='日本語'); if(!o) return 'no-ja-option'; s.value=o.value; s.dispatchEvent(new Event('change',{bubbles:true})); return s.value;})()" >/dev/null
sleep 5

# Verify we're on /new/
URL=$(cf_url "$TAB")
if [[ "$URL" == *"signin"* || "$URL" == *"newComputer"* ]]; then
  echo "  → login expired, running auto-login"
  do_auto_login
  cf_navigate "$TAB" "https://distrokid.com/new/" >/dev/null
  sleep 4
  cf_eval "(()=>{const s=document.querySelector('#sitetran_select'); if(!s) return null; const o=[...s.options].find(o=>o.text==='日本語'); s.value=o.value; s.dispatchEvent(new Event('change',{bubbles:true})); return s.value;})()" >/dev/null
  sleep 4
fi

# ──────── 1. confirm /new/ ────────
echo "[1] on /new/"
URL=$(cf_url "$TAB")
[[ "$URL" == *"/new/"* ]] || fail "navigate" "expected /new/ — got $URL"

# ──────── 2. uncheck Apple Music + iTunes ────────
echo "[2] uncheck Apple Music + iTunes"
cf_eval "(()=>{const want=['Apple Music','iTunes']; const out=[]; for(const lbl of want){const cb=[...document.querySelectorAll('input[type=checkbox]')].find(c=>{const id=c.id||''; const text=(c.closest('label')||c.parentElement||{}).innerText||''; return text.includes(lbl);}); if(cb && cb.checked){cb.click(); out.push(lbl+':unchecked');} else if(cb){out.push(lbl+':already-unchecked');} else out.push(lbl+':not-found');} return out.join(' | ');})()" 2>&1 | head -3
sleep 2

# ──────── 3. release date ────────
echo "[3] release date $RELEASE_DATE"
cf_eval "(()=>{const el=document.querySelector('#release-date-dp'); if(!el) return 'no-date-input'; el.value='$RELEASE_DATE'; el.dispatchEvent(new Event('change',{bubbles:true})); el.dispatchEvent(new Event('input',{bubbles:true})); return el.value;})()" >/dev/null
sleep 1

# ──────── 4. primary genre ────────
echo "[4] primary genre = $GENRE_JP"
cf_eval "(()=>{const sel=document.querySelector('#genrePrimary'); if(!sel) return 'no-genre-select'; const opt=[...sel.options].find(o=>o.text==='$GENRE_JP'); if(!opt) return 'no-option-'+'$GENRE_JP'; sel.value=opt.value; sel.dispatchEvent(new Event('change',{bubbles:true})); return opt.text;})()" 2>&1 | head -3
sleep 2

# ──────── 5. cover ────────
echo "[5] cover $COVER"
# DistroKid cover input: <input id="artwork" name="artwork" accept="image/*">.
cf_upload "$TAB" "input#artwork" "$COVER" 2>&1 | head -1
sleep 3

# ──────── 6. track title ────────
echo "[6] title \"$TITLE\""
# Escape title for embedding in single-quoted JS literal.
TITLE_JS=$(printf '%s' "$TITLE" | sed -e "s/\\\\/\\\\\\\\/g" -e "s/'/\\\\'/g")
TITLE_RES=$(cf_eval "(()=>{const inp=[...document.querySelectorAll('input[type=text]')].find(i=>(i.placeholder||'').match(/トラック1の曲名|Song name of track 1/)); if(!inp) return 'no-title-input'; inp.focus(); inp.value='${TITLE_JS}'; inp.dispatchEvent(new Event('input',{bubbles:true})); inp.dispatchEvent(new Event('change',{bubbles:true})); return 'set:'+inp.value;})()" 2>&1 | head -1)
echo "  title: $TITLE_RES"
echo "$TITLE_RES" | grep -q '"set:' || fail "title" "could not set title: $TITLE_RES"
sleep 1

# ──────── 7. audio ────────
echo "[7] audio $AUDIO"
# DistroKid audio input for track 1: <input id="js-track-upload-1" name="file" accept="audio/*,...">.
cf_upload "$TAB" "input#js-track-upload-1" "$AUDIO" 2>&1 | head -1
sleep 3

# ──────── 8. songwriter ────────
echo "[8] songwriter <your-name>"
# Use the stable name attributes; React state needs both input + change events.
SW_RES=$(cf_eval "(()=>{const set=(name,val)=>{const inp=document.querySelector('input[name=\"'+name+'\"]'); if(!inp) return name+':no-input'; inp.focus(); inp.value=val; inp.dispatchEvent(new Event('input',{bubbles:true})); inp.dispatchEvent(new Event('change',{bubbles:true})); return name+':'+inp.value;}; return [set('songwriter_real_name_first1','Daisuke'), set('songwriter_real_name_last1','Narita')].join(' | ');})()" 2>&1 | head -1)
echo "  songwriter: $SW_RES"
echo "$SW_RES" | grep -q 'first1:Daisuke' || fail "songwriter" "could not set first name: $SW_RES"
echo "$SW_RES" | grep -q 'last1:Narita' || fail "songwriter" "could not set last name: $SW_RES"
sleep 1

# ──────── 9. instrumental ────────
echo "[9] instrumental"
INST_REF=$(find_ref_cf "radio" "インスト")
[ -z "$INST_REF" ] && INST_REF=$(find_ref_cf "radio" "Instrumental")
[ -n "$INST_REF" ] && cf_click "$TAB" "$INST_REF" >/dev/null
sleep 1

# ──────── 10. AI = はい ────────
echo "[10] AI = はい (Yes)"
# Click the Yes radio directly in the DOM, anchored by the AI disclosure heading.
# This avoids snapshot-ref ambiguity when other Yes radios exist on the page.
AI_CLICK_RESULT=$(cf_eval "$(cat <<'JS'
(() => {
  const headings = [...document.querySelectorAll('h1,h2,h3,h4,label,legend,div,span,p')]
    .filter(e => /AIによって生成|generated by AI|include AI/i.test(e.textContent || ''));
  if (!headings.length) return 'no-ai-heading';
  // Find the nearest section/form container then look for radios within
  const heading = headings.find(h => (h.textContent || '').length < 200) || headings[0];
  let scope = heading.closest('section,fieldset,form,div') || heading.parentElement;
  // walk up if no radios in scope yet
  for (let i = 0; i < 5 && scope; i++) {
    const radios = [...scope.querySelectorAll('input[type=radio]')];
    if (radios.length >= 2) {
      // Yes is typically the 2nd radio (No is first by DistroKid convention)
      const yes = radios.find(r => {
        const lbl = (r.closest('label')||{}).innerText || r.value || '';
        return /^はい|^Yes/i.test(lbl.trim());
      }) || radios[1];
      yes.click();
      return 'clicked:' + ((yes.closest('label')||{}).innerText || yes.value || '?').slice(0,40);
    }
    scope = scope.parentElement;
  }
  return 'no-radios-in-scope';
})()
JS
)" 2>&1 | head -1)
echo "  AI Yes click: $AI_CLICK_RESULT"
echo "$AI_CLICK_RESULT" | grep -q '"result":"clicked' || fail "ai-yes" "could not click AI Yes radio: $AI_CLICK_RESULT"
sleep 4

# ──────── 11. AI modal: 作曲 + 音声すべて + 保存 ────────
# Click checkboxes by label text via evaluate (refs shift between clicks; label-based click is stable).
echo "[11] AI modal: composed + all audio + save"
# Wait up to 10s for modal to render
for retry in 1 2 3 4 5 6 7 8 9 10; do
  HAS_MODAL=$(cf_eval "(()=>{const cb=[...document.querySelectorAll('input[type=checkbox]')].find(c=>{const lbl=(c.closest('label')||c.parentElement||{}).innerText||''; return /作曲.*AIによって作曲|composed by AI/i.test(lbl);}); return cb?'yes':'no';})()" 2>&1 | jq -r .result 2>/dev/null)
  [ "$HAS_MODAL" = "yes" ] && break
  sleep 1
done
[ "$HAS_MODAL" != "yes" ] && { snap_text > "$OUTDIR/.ai-modal-debug.snap"; fail "ai-composed" "AI modal didn't render in 10s"; }

AI_MODAL_RESULT=$(cf_eval "$(cat <<'JS'
(() => {
  const out = [];
  const findCheckbox = (regex) => [...document.querySelectorAll('input[type=checkbox]')]
    .find(c => regex.test((c.closest('label')||c.parentElement||{}).innerText || ''));
  const composed = findCheckbox(/作曲.*AIによって作曲|composed by AI/i);
  const allAudio = findCheckbox(/音声すべて.*AIによる演奏|All of the audio.*AI/i);
  if (!composed) return 'no-composed';
  if (!allAudio) return 'no-all-audio';
  if (!composed.checked) { composed.click(); out.push('composed:clicked'); } else out.push('composed:already');
  if (!allAudio.checked) { allAudio.click(); out.push('allaudio:clicked'); } else out.push('allaudio:already');
  // Find Save button: button with text "保存する" or "Save"
  const saveBtn = [...document.querySelectorAll('button')]
    .find(b => /保存する|^Save$/.test((b.textContent || '').trim()));
  if (!saveBtn) return out.join(',') + ',no-save-btn';
  saveBtn.click();
  out.push('saved');
  return out.join(',');
})()
JS
)" 2>&1 | head -1)
echo "  AI modal result: $AI_MODAL_RESULT"
echo "$AI_MODAL_RESULT" | grep -q 'saved' || fail "ai-save" "could not save AI modal: $AI_MODAL_RESULT"
sleep 4

# ──────── 12. Apple persona = haven't released ────────
echo "[12] Apple persona = haven't released (defensive)"
APPLE_NEVER=$(snap_text | grep -B1 -F "Anicca名義でiTunes・Apple Musicに配信したことはない" | grep -oE '\[e[0-9]+\]' | head -1 | tr -d '[]')
[ -n "$APPLE_NEVER" ] && { cf_click "$TAB" "$APPLE_NEVER" >/dev/null; sleep 1; }

# ──────── 13. final mandatory checkboxes ────────
echo "[13] final mandatory checkboxes"
for label in \
    "配信先として「YouTube Music」を選択しました" \
    "特殊な大文字／小文字表記が使われています" \
    "再生回数を増やすサービスを使用しません" \
    "この音源は私自身がレコーディングしたものです" \
    "アーティスト名、曲名、アルバム名に、承認を得ていない他のアーティスト" \
    "以下の利用規約を読み、同意しました"; do
  REF=$(snap_text | grep -F "$label" | grep "checkbox" | grep -oE '\[e[0-9]+\]' | head -1 | tr -d '[]')
  if [ -n "$REF" ]; then
    cf_click "$TAB" "$REF" >/dev/null
    echo "  ✓ checked: ${label:0:30}..."
  fi
done
sleep 1

# ──────── 14. submit (続ける) ────────
echo "[14] submit"
SUBMIT_REF=$(find_ref_cf "button" "続ける")
[ -z "$SUBMIT_REF" ] && SUBMIT_REF=$(find_ref_cf "button" "Continue")
[ -z "$SUBMIT_REF" ] && fail "submit" "no 続ける button"
cf_click "$TAB" "$SUBMIT_REF" >/dev/null
sleep 8

# ──────── 15. Mixea upsell skip ────────
URL=$(cf_url "$TAB")
if [[ "$URL" == *"/new/mixea"* ]]; then
  echo "[15] skip Mixea mastering"
  USE_UPLOADED=$(find_ref_cf "button" "アップロードしたバージョンを使用")
  [ -z "$USE_UPLOADED" ] && USE_UPLOADED=$(find_ref_cf "button" "Use uploaded version")
  [ -n "$USE_UPLOADED" ] && { cf_click "$TAB" "$USE_UPLOADED" >/dev/null; sleep 8; }
fi

# ──────── 16. verify success ────────
URL=$(cf_url "$TAB")
[[ "$URL" == *"/new/done"* ]] || fail "post-submit" "did not reach /new/done — current URL: $URL"

ALBUM_UUID=$(echo "$URL" | grep -oE 'albumuuid=[A-F0-9-]+' | sed 's/albumuuid=//')
HF_URL=$(snap_text | grep -oE 'https://distrokid\.com/hyperfollow/[^ )]+' | head -1)

# ──────── 17. receipt ────────
echo "[17] receipt → $OUTDIR/upload-receipt.json"
jq -nc \
  --arg uuid "$ALBUM_UUID" \
  --arg hf "$HF_URL" \
  --arg title "$TITLE" \
  --arg rd "$RELEASE_DATE" \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{albumuuid:$uuid, hyperfollow_url:$hf, title:$title, release_date:$rd, uploaded_at:$ts, status:"submitted"}' \
  > "$OUTDIR/upload-receipt.json"

echo "✓ DistroKid upload complete: \"$TITLE\" (albumuuid=$ALBUM_UUID)"
