#!/usr/bin/env bash

render_ig_provision_prompt() {
  local state_file="${IG_PROVISION_ACCOUNT_STATE_FILE:?IG_PROVISION_ACCOUNT_STATE_FILE is required}"
  local handle_prefix="${IG_PROVISION_HANDLE_PREFIX:?IG_PROVISION_HANDLE_PREFIX is required}"
  local instance="${IG_PROVISION_INSTANCE:?IG_PROVISION_INSTANCE is required}"
  local gmail_plus_tag_prefix="${IG_PROVISION_GMAIL_PLUS_TAG_PREFIX:?IG_PROVISION_GMAIL_PLUS_TAG_PREFIX is required}"
  local bio_text="${IG_PROVISION_BIO_TEXT:?IG_PROVISION_BIO_TEXT is required}"
  local browser_instructions="${IG_PROVISION_BROWSER_INSTRUCTIONS:?IG_PROVISION_BROWSER_INSTRUCTIONS is required}"
  local profile_prefix="${IG_PROVISION_PROFILE_PREFIX:-${instance}-mkt}"
  local success_status="${IG_PROVISION_SUCCESS_STATUS:-warming}"
  local started_warming="${IG_PROVISION_STARTED_WARMING:-no}"
  local cooked_marker="${IG_PROVISION_COOKED_MARKER:-}"
  local provision_reason="${IG_PROVISION_REASON:-none}"
  local reach_marker="${IG_PROVISION_REACH_MARKER:-}"
  local last_pass_marker="${IG_PROVISION_LAST_PASS_MARKER:-}"
  local telegram_target="${IG_PROVISION_TELEGRAM_TARGET:-}"
  local started_warming_field=""

  if [ "$started_warming" = "yes" ]; then
    started_warming_field=',"started_warming":"<today YYYY-MM-DD>"'
  fi

  cat <<EOF
STEP PROVISION (1-loop-1-account, replace-on-cold, ZERO human): ${state_file} has no usable ready/warming account. Read ~/.claude/skills/ig-account-create/SKILL.md and follow its proven email-only flow. Create one brand-new ${instance} IG account on residential home IP with NO proxy. Use a unique handle beginning with ${handle_prefix}. Use a fresh Gmail plus-address keiodaisuke+${gmail_plus_tag_prefix}<random-tag>@gmail.com. Read the 6-digit OTP with: gog gmail search --account keiodaisuke@gmail.com "instagram in:anywhere newer_than:1h" --max 3 --plain. The in:anywhere term is mandatory because OTP can land in spam. Do not use phone flow unless Instagram forces it; if phone or text-CAPTCHA is forced, stop and report provision-blocked:<reason>. BROWSER ISOLATION: ${browser_instructions} Fill fields with trusted CDP typing, set DOB with trusted clicks, create the unique handle, and run setup_profile.py with a \$0 PIL monogram avatar plus this one-line bio containing NO link: "${bio_text}". Save signup credentials to ~/.cloak/ig-<handle>.json as JSON with username, name, email, pw, dob, and created.

DURABLE GOLDEN SESSION — mandatory make-or-break step: browser sessionid is ephemeral and dies when the isolated context closes. NEVER save browser sessionid as the durable session and NEVER call login_by_sessionid. Instead use ~/.cache/instagrapi-venv/bin/python and the fresh password from ~/.cloak/ig-<handle>.json: from instagrapi import Client; cl=Client(); cl.login(<username>, <pw>) exactly once as the first fresh-account login; feed=cl.get_timeline_feed(); require real returned data; cl.dump_settings("~/.cloak/instagrapi-<handle>.json"). Read the settings file back. Feed verification, not file existence, proves the session alive. If Client().login, get_timeline_feed(), or dump_settings fails, the account is not usable.

STATE WRITE: use ${state_file} only and preserve every existing row. Choose a free dedicated port that is neither 9222 nor 9223 after checking lsof, and a unique profile beginning with ${profile_prefix}. Only after get_timeline_feed() confirms a live session, atomically append {"handle":"<handle>","profile":"<profile>","port":<free-port>,"lang":"en","status":"${success_status}","session_owner":"instagrapi","instance":"${instance}","created":"<today YYYY-MM-DD>"${started_warming_field}}. Parse the full JSON after writing, confirm row count increased by one and the final row matches the new handle. Never write ${success_status} unless feed_verified_alive=yes.
EOF

  if [ -n "$cooked_marker" ]; then
    cat <<EOF
If provision reason is ${provision_reason} and equals cooked-marker, first mark prior ready/warming rows poisoned_manual_backup with poisoned_reason and poisoned_at so only the new appended row is active. On success remove ${cooked_marker}${reach_marker:+ and remove ${reach_marker}} so replacement account restarts clean validation.
EOF
  fi

  cat <<EOF
FAILURE: if signup, Client().login, get_timeline_feed(), dump_settings, or state verification fails, append a best-effort row with status=provision_failed and failure reason. Never label it ready/warming.
EOF

  if [ -n "$cooked_marker" ]; then
    printf 'Ensure %s remains present on failure.\n' "$cooked_marker"
  fi
  if [ -n "$telegram_target" ]; then
    cat <<EOF
Send Telegram chat ${telegram_target} a success message containing handle, port, feed_verified_alive=yes, status_written=${success_status}, and that this pass posted nothing. On failure send exactly one provision-blocked:<reason> report.
EOF
  else
    printf '%s\n' 'Report handle + port + feed_verified_alive(yes/no) + status_written, or provision-blocked:<reason>.'
  fi
  if [ -n "$last_pass_marker" ]; then
    printf 'Touch %s and stop this pass after the provision success/failure report.\n' "$last_pass_marker"
  fi
}
