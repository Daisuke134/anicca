---
name: naist
description: Unified {{profile.education.institution}} research-life automation (v1.6 PROCEDURAL). Logs into {{profile.education.institution}} IDP via TOTP + edu-portal SSO using agent-{{profile.lateness.stakeholders.channel}} CLI, then drives the full graduate-student workload — mail triage with auto-reply, course registration, schedule sync to Google Calendar, homework draft + submit, fund applications, paper recommendations, deadline ICS feed, and 科研費 proposal generation. Every web action is a procedural step using agent-{{profile.lateness.stakeholders.channel}} ("snapshot, find element with text X, click, fill, submit"). Designed to survive UI changes (find by text, not by ref). Generic — any {{profile.education.institution}} student onboards by filling per-slug state. Use when triggered by any naist-* cron or manually with `MODE=<mode> bash scripts/run.sh`.
metadata:
  tags: naist, university-automation, gmail, slack, agent-{{profile.lateness.stakeholders.channel}}, quarto, ics, send-as, totp, arxiv, vercel-agent-{{profile.lateness.stakeholders.channel}}
  requires:
    bins: [jq, python3, quarto, oathtool, zbarimg, bash]
    cli: [agent-{{profile.lateness.stakeholders.channel}}]
    mcps: [gmail, slack, google-calendar]
    env: [SLACK_BOT_TOKEN]
  invariants:
    - "v1.5 AUTO-SUBMIT: every reply class — homework / question / ta-task / professor-task / bureaucracy — sends without per-thread human confirmation. Spam / {{profile.lateness.stakeholders.senderType}}-threat / harassment skip-and-log only."
    - Every web automation step uses agent-{{profile.lateness.stakeholders.channel}} (`/opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}`). Never use playwright/puppeteer/selenium directly.
    - Find UI elements by visible text first, by aria role second, by ref last. Refs become stale after every page change — always re-snapshot before referring to a ref.
    - {{profile.education.institution}} IDP auth = TOTP page → password page → SSO redirect. Generate TOTP with `oathtool --totp -b "${{profile.education.institution}}_TOTP_SECRET"` from per-slug secret.
    - Agent never touches the {{profile.education.institution}} SMTP server directly; only Gmail Send-mail-as via Gmail MCP.
    - All public artifacts (PDFs, JSON snapshots) live under `~/.openclaw/workspace/naist/<slug>/...` — never `/tmp` (gets wiped).
    - Take a screenshot at every successful step into `~/.openclaw/workspace/naist/<slug>/screenshots/<ymd>/<step-N>.png` for audit + future UI-change diffing.
    - Per-slug state lives at `~/.openclaw/state/naist/<slug>/` — secrets in `secrets.env` (chmod 600), public profile in `profile.json`.
---

# naist — universal university-automation skill (v1.6 PROCEDURAL)

This is a **per-student, end-to-end automation** for {{profile.education.institution}}. Any student loads it via `openclaw skill install naist`, completes the wizard, then 9 daily/weekly/monthly crons run the full school-life loop.

## What this skill delivers

For **each onboarded student** (`<slug>`), the skill produces these external outputs:

1. **Auto-replied {{profile.education.institution}} mail** — every incoming {{profile.education.institution}} mail (forwarded to personal Gmail) is classified into 6 buckets and replied/acknowledged/filed without human approval. From line is `<student-id>@naist.ac.jp` (Gmail Send-mail-as alias).
2. **Course registration** — 履修登録 form on edu-portal is auto-filled and submitted during the registration window for every recommended class (driven by `<slug>/preferences.json` + advisor input).
3. **Class schedule in Google Calendar** — every registered course becomes a recurring weekly event in the user's Google Calendar (via Google Calendar MCP).
4. **Homework drafts + submission** — `課題` mails are detected, draft answer is produced via Quarto, PDF is uploaded to edu-portal's submission form, and submitted N-1 day before deadline. Auto-submit; no 👍 gate.
5. **Deadlines in iCal** — every deadline (homework, bureaucracy, events) is in `~/.openclaw/workspace/naist/<slug>/deadlines.ics`, subscribed by macOS Calendar / Google Calendar.
6. **Paper recommendations** — daily 08:00 JST: arXiv search on `research-profile.json` keywords → top-5 papers → utility-hint → Slack post.
7. **Fund applications** — daily 09:00 JST: scan JSPS / KAKEN / OpenPhil / FLI for matching grants. For ready candidates, Vercel agent {{profile.lateness.stakeholders.channel}} fills the application form, attaches Quarto-rendered 科研費 proposal, and submits.
8. **科研費 proposal PDF** — manual / quarterly: regenerates the formatted research proposal PDF from `research-profile.json`.
9. **Grade + GPA snapshots** — weekly Mon 10:00 JST: scrape `成績照会` + `学生時間割表`, write `portal-<ymd>-<slug>.json`, post Slack digest with 不可 (failing) class re-take recommendations.

## Bootstrap workflow (apply v1.5 phase 0–3)

Phase 0 (Claude Code E2E run, executed 2026-05-08 for `dais` slug):

- Successful TOTP login to `https://idp.naist.jp/`
- Successful SSO into `https://edu-portal.naist.jp/uprx/`
- Scraped 学生時間割表 + 成績照会 → 31 transcript rows + GPA history + credit summary written to `~/.openclaw/workspace/naist/portal-2026-05-08-dais.json`

Phases 1–3 follow this SKILL.md.

## Setup wizard (8 questions)

| # | key | example | persisted to |
|---|---|---|---|
| 1 | `naist.personal_gmail` | `{{profile.contact.personalEmail}}` | `~/.openclaw/state/naist/<slug>/profile.json` |
| 2 | `naist.naist_{{profile.lateness.stakeholders.channel}}` | `yamada.taro.xy0@naist.ac.jp` | same |
| 3 | `naist.student_id` | `2511444` | same |
| 4 | `naist.idp_username` | `daisuke-na` | same (the username used at idp.naist.jp) |
| 5 | `naist.idp_password` | `<secret>` | `~/.openclaw/state/naist/<slug>/secrets.env` (chmod 600) |
| 6 | `naist.totp_secret` | base32 from Google Authenticator migration QR (decode with `zbarimg --raw OTP.png`, then `python3 ~/.openclaw/skills/naist/scripts/decode-otp-migration.py`) | `~/.openclaw/state/naist/<slug>/secrets.env` (chmod 600) |
| 7 | `naist.research_profile` | `{topic, method, preliminary_results, research_keywords[]}` | `~/.openclaw/state/naist/<slug>/research-profile.json` |
| 8 | `naist.slack_channel` | `{{profile.channels.reportChannel}}` | `~/.openclaw/state/naist/<slug>/slack_channel.txt` |

## Modes (11)

```bash
# 15-min Gmail pull + triage + auto-reply (cron: naist-pull */15 * * * *)
MODE=pull bash scripts/run.sh

# 09:00 JST daily digest of last 24h (cron: naist-morning-rollup)
MODE=morning-rollup bash scripts/run.sh

# Fri 18:00 JST week summary + missing deadlines (cron: naist-friday-rollup)
MODE=friday-rollup bash scripts/run.sh

# 07:00 JST regenerate deadlines.ics (cron: naist-deadline-ical)
MODE=deadline-ical bash scripts/run.sh

# 08:00 JST arXiv search + Slack post (cron: naist-papers-suggest)
MODE=papers-suggest bash scripts/run.sh

# 09:00 JST scan JSPS/KAKEN/OpenPhil/FLI + auto-submit (cron: naist-funds-apply)
MODE=funds-apply bash scripts/run.sh

# Mon 10:00 JST scrape edu-portal grades + schedule (cron: naist-edu-portal-check)
MODE=edu-portal-check bash scripts/run.sh

# 履修期間中 11:00 JST register recommended courses (cron: naist-course-register)
MODE=course-register bash scripts/run.sh

# 期日 -1日 14:00 JST upload + submit homework PDFs (cron: naist-homework-submit)
MODE=homework-submit bash scripts/run.sh

# 履修確定後 Mon 12:00 JST sync schedule to Google Calendar (cron: naist-gcal-sync)
MODE=gcal-sync bash scripts/run.sh

# Manual / quarterly research proposal regen
MODE=research-proposal-gen bash scripts/run.sh
```

---

## Procedural reference for agent-{{profile.lateness.stakeholders.channel}} (use this in every web mode)

The agent runs the steps below. Skill scripts call agent-{{profile.lateness.stakeholders.channel}} CLI directly; the SKILL.md spells out the procedure so future UI changes can be handled by the agent reading this file and adapting (find by text, not by ref).

### Procedure A — Login to {{profile.education.institution}} IDP via TOTP (mandatory pre-step for every web mode)

```bash
# Inputs (from per-slug secrets.env):
#   ${{profile.education.institution}}_IDP_USERNAME, ${{profile.education.institution}}_IDP_PASSWORD, ${{profile.education.institution}}_TOTP_SECRET
# Output: a logged-in agent-{{profile.lateness.stakeholders.channel}} session at https://idp.naist.jp/user/index.php
SS_DIR="$HOME/.openclaw/workspace/naist/<slug>/screenshots/$(date +%Y-%m-%d)"
mkdir -p "$SS_DIR"

# Step 1: open IDP
agent-{{profile.lateness.stakeholders.channel}} open "https://idp.naist.jp/"
agent-{{profile.lateness.stakeholders.channel}} screenshot "$SS_DIR/01-idp-open.png"

# Step 2: snapshot to find current refs (refs change every load)
agent-{{profile.lateness.stakeholders.channel}} snapshot   # find: "ユーザー名" textbox, "ワンタイムパスワード" spinbutton, "ログイン" button

# Step 3: fill username — find textbox by aria-role + nearest "ユーザー名" term
USER_REF=$(agent-{{profile.lateness.stakeholders.channel}} snapshot | awk '/term "ユーザー名"/{getline;getline; if($0~/textbox/) {match($0,/ref=e[0-9]+/); print substr($0,RSTART+4,RLENGTH-4)}}')
agent-{{profile.lateness.stakeholders.channel}} fill "@$USER_REF" "${{profile.education.institution}}_IDP_USERNAME"

# Step 4: generate current TOTP
TOTP=$(oathtool --totp -b "${{profile.education.institution}}_TOTP_SECRET")

# Step 5: fill OTP — find spinbutton near "ワンタイムパスワード"
OTP_REF=$(agent-{{profile.lateness.stakeholders.channel}} snapshot | awk '/term "ワンタイムパスワード"/{getline;getline; if($0~/spinbutton/) {match($0,/ref=e[0-9]+/); print substr($0,RSTART+4,RLENGTH-4)}}')
agent-{{profile.lateness.stakeholders.channel}} fill "@$OTP_REF" "$TOTP"

# Step 6: click ログイン button (find by text)
agent-{{profile.lateness.stakeholders.channel}} click "ログイン" || agent-{{profile.lateness.stakeholders.channel}} click 'button[type="submit"]'
sleep 3
agent-{{profile.lateness.stakeholders.channel}} screenshot "$SS_DIR/02-after-otp.png"

# Step 7: now on tenantlogin.cgi — fill password (username is hidden, pre-filled)
PWD_REF=$(agent-{{profile.lateness.stakeholders.channel}} snapshot | awk '/term "パスワード"/{getline;getline; if($0~/textbox/) {match($0,/ref=e[0-9]+/); print substr($0,RSTART+4,RLENGTH-4)}}')
agent-{{profile.lateness.stakeholders.channel}} fill "@$PWD_REF" "${{profile.education.institution}}_IDP_PASSWORD"
agent-{{profile.lateness.stakeholders.channel}} click "ログイン"
sleep 3
agent-{{profile.lateness.stakeholders.channel}} screenshot "$SS_DIR/03-sso-home.png"

# Verify success: URL should be /user/index.php
URL=$(agent-{{profile.lateness.stakeholders.channel}} eval "location.href" | tr -d '"')
[ "${URL%%\?*}" = "https://idp.naist.jp/user/index.php" ] || { echo "IDP login failed: $URL"; exit 1; }
```

**Flexibility note.** When {{profile.education.institution}} changes the IDP UI (rename "ログイン" to "Sign in", change layout), the agent re-snapshots and re-finds elements by their new visible text. Don't hardcode refs.

### Procedure B — SSO into edu-portal (after Procedure A)

```bash
# Step 1: navigate to edu-portal entry
agent-{{profile.lateness.stakeholders.channel}} open "https://edu-portal.naist.jp/uprx/up/km/kmh006/Kmh00601.xhtml"
agent-{{profile.lateness.stakeholders.channel}} screenshot "$SS_DIR/10-edu-portal-entry.png"

# Step 2: click "ログインはこちら" (the SSO trigger)
agent-{{profile.lateness.stakeholders.channel}} click "ログインはこちら"
sleep 5
agent-{{profile.lateness.stakeholders.channel}} screenshot "$SS_DIR/11-edu-portal-home.png"

# Verify: should land on Pky00102.xhtml (home with menu items シラバス照会 / 履修登録 / 学生時間割表 / ...)
URL=$(agent-{{profile.lateness.stakeholders.channel}} eval "location.href" | tr -d '"')
echo "$URL" | grep -q "Pky00102.xhtml" || { echo "edu-portal SSO failed: $URL"; exit 1; }
```

### Procedure C — Get current courses + GPA + transcripts (`MODE=edu-portal-check`)

```bash
# After Procedure A + B
# Step 1: click 学生時間割表 menu
agent-{{profile.lateness.stakeholders.channel}} click "学生時間割表"
sleep 4
agent-{{profile.lateness.stakeholders.channel}} screenshot "$SS_DIR/20-jikanwari.png"

# Step 2: scrape course rows + GPA + credit summary via eval
JIKANWARI_JSON=$(agent-{{profile.lateness.stakeholders.channel}} eval '
const text = document.body.innerText;
// Course rows under "授業科目 / 教員氏名 / 教室 / 単位数"
const courses = [];
document.querySelectorAll("tr").forEach(tr => {
  const tds = Array.from(tr.querySelectorAll("td")).map(td => td.innerText.trim());
  if (tds.length >= 4 && /^[A-Z]{2}\d{4}/.test(tds[0])) {
    courses.push({code: tds[0].split(/\s+/)[0], name: tds[0].replace(/^\S+\s+/, "").replace(/ui-button.*/,""), instructor: tds[1], credits: parseInt(tds[3])||1});
  }
});
const gpa = {};
text.match(/(\d{4})年度\s+(春|秋)学期\s*([\d.]+)/g)?.forEach(m => {
  const [, y, t, v] = m.match(/(\d{4})年度\s+(春|秋)学期\s*([\d.]+)/);
  gpa[`${y}_${t==="春"?"spring":"fall"}`] = parseFloat(v);
});
const cum = text.match(/通算\s*([\d.]+)/);
if (cum) gpa.cumulative = parseFloat(cum[1]);
JSON.stringify({courses, gpa})
')

# Step 3: click 成績照会
agent-{{profile.lateness.stakeholders.channel}} click "成績照会"
sleep 4
agent-{{profile.lateness.stakeholders.channel}} screenshot "$SS_DIR/21-seiseki.png"

SEISEKI_JSON=$(agent-{{profile.lateness.stakeholders.channel}} eval '
const rows = [];
document.querySelectorAll("tr").forEach(tr => {
  const c = Array.from(tr.querySelectorAll("td")).map(t => t.innerText.trim());
  // [empty?, name, credits, grade, gpaCount, year, term, instructor]
  if (c.length >= 7 && /^[一-龥぀-ヿ]/.test(c[1] || "")) {
    rows.push({name: c[1], credits: parseInt(c[2])||null, grade: c[3], gpa_count: c[4]==="○", year: parseInt(c[5])||null, term: c[6], instructor: c[7]||""});
  }
});
JSON.stringify(rows)
')

# Step 4: persist
OUT="$HOME/.openclaw/workspace/naist/<slug>/portal-$(date +%Y-%m-%d).json"
mkdir -p "$(dirname "$OUT")"
jq -n --argjson j "$JIKANWARI_JSON" --argjson s "$SEISEKI_JSON" \
  '{scraped_at: now|todate, jikanwari: $j, transcripts: $s}' > "$OUT"

# Step 5: identify 不可 (failing) classes that need retake → Slack post
RETAKES=$(echo "$SEISEKI_JSON" | jq -r '[.[] | select(.grade == "不可") | .name] | unique | .[]')
[ -n "$RETAKES" ] && slack_post ":warning: 不可科目あり (再履修推奨): $RETAKES"
```

### Procedure D — Register a course (`MODE=course-register`) — VERIFIED 2026-05-08 with ST1002sp 科学哲学 added to dais's spring-term registration

This is the **agent-{{profile.lateness.stakeholders.channel}} CLI** sequence verified end-to-end against {{profile.education.institution}} UNIPA / Kmd004 form on 2026-05-08. Refs (`@eN`) are session-local — re-snapshot on each step.

```bash
# Inputs: <slug>/preferences.json with recommended_courses[].code
# After Procedure A + B (logged into Pky00102.xhtml)

# --- Step 1: click 履修登録 menu link ---
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
# find: `link "履修登録" [ref=eN]` (NOT the menuitem; the inner link)
agent-{{profile.lateness.stakeholders.channel}} click @eN
# Lands on bsa001/Bsa00101.xhtml with title "履修登録[Kmd004]"
agent-{{profile.lateness.stakeholders.channel}} screenshot "$SS_DIR/30-rishu-form.png"

# --- Step 2: switch to "授業コードを直接入力" tab (most reliable add path) ---
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
# find: `tab "授業コードを直接入力" [ref=eN]`
agent-{{profile.lateness.stakeholders.channel}} click @eN
# A textbox + 追加 button appear

# --- Step 3: per course code, fill + click 追加 ---
agent-{{profile.lateness.stakeholders.channel}} snapshot -i  # find textbox ref + 追加 button ref
for CODE in $(jq -r '.recommended_courses[].code' "$HOME/.openclaw/state/naist/<slug>/preferences.json"); do
  agent-{{profile.lateness.stakeholders.channel}} fill @<textbox_ref> "$CODE"
  agent-{{profile.lateness.stakeholders.channel}} click @<tsuika_button_ref>  # button "追加"
  sleep 3
  # 履修合計単位 should increment by 1 (verify with eval)
  agent-{{profile.lateness.stakeholders.channel}} screenshot "$SS_DIR/31-after-${CODE}.png"
done

# --- Step 4: click 最終確認へ ---
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
# find: `button "9最終確認へ" [ref=eN]`  (NOTE: literal "9最終確認へ" — the leading "9" is a UNIPA-icon prefix that survives in the accessibility tree)
agent-{{profile.lateness.stakeholders.channel}} click @eN
# Lands on 最終確認 page; body shows "履修内容にエラーはありません。提出へ進んでください。"
agent-{{profile.lateness.stakeholders.channel}} screenshot "$SS_DIR/32-saishuu-kakunin.png"

# --- Step 5: click 提出 (final submission, NOT the 9最終確認へ from step 4) ---
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
# find: `button "9提出" [ref=eN]` — this is the actual submit, id=funcForm:submit
agent-{{profile.lateness.stakeholders.channel}} click @eN
sleep 4

# --- Step 6: confirmation dialog → click OK ---
# After 9提出 click, a confirm dialog opens with text "提出します。よろしいですか？"
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
# find: `button "OK" [ref=eN]`  (id=yes)
agent-{{profile.lateness.stakeholders.channel}} click @eN
sleep 6
agent-{{profile.lateness.stakeholders.channel}} screenshot "$SS_DIR/33-final-completion.png"

# --- Step 7: verify "履修登録が完了しました。" in body ---
BODY=$(agent-{{profile.lateness.stakeholders.channel}} eval 'document.body.innerText')
echo "$BODY" | grep -q "履修登録が完了しました" || { echo "FATAL: completion text missing"; exit 1; }

# --- Step 8: extract registered courses + persist ---
REGISTERED=$(agent-{{profile.lateness.stakeholders.channel}} eval '
Array.from(document.body.innerText.matchAll(/(ST\d{4}\w*)\s+(\S+?)\n/g)).map(m => m[1] + " " + m[2])
')
echo "$REGISTERED" > "$HOME/.openclaw/workspace/naist/<slug>/course-register-confirm-$(date +%Y-%m-%d).txt"
```

**Key learnings encoded above (don't repeat the mistakes):**
- The `ui-button` next to a course code in the catalog grid is a **syllabus-view button**, NOT a "select to register" button. Don't click it expecting it to add to registration. Title attribute is `"シラバス照会画面を表示します。"` to distinguish.
- The reliable add path is **「授業コードを直接入力」 tab → textbox → 追加 button** — this avoids needing to scroll to find each course in the long catalog grid.
- Button labels in the accessibility tree carry icon prefixes like `"9提出"`, `"9最終確認へ"`, `"6削除"` — find by `re.search(r'button "9?提出"', snap)` etc.
- Final OK confirm dialog is a separate accessibility element, not a `.ui-dialog` (so `document.querySelectorAll('.ui-dialog')` returns nothing) — find the OK button by `id=yes` or `button "OK"` in the snapshot.
- Browser session can become stale after multiple login attempts; if any step fails, close and re-do Procedure A from scratch with a fresh TOTP code.

### Procedure E — Submit homework PDF (`MODE=homework-submit`)

```bash
# Input: ~/.openclaw/workspace/naist/<slug>/homework/<class-slug>/<ts>.pdf (already rendered by Quarto)
# After Procedure A + B
# Step 1: click 掲示板 (where assignment links are posted) OR directly navigate to the LMS submission URL stored in the homework draft
HW_PDF="$1"
HW_META=$(jq -r ".submission_url" "$HOME/.openclaw/workspace/naist/<slug>/drafts/<class-slug>/<ts>.json")

agent-{{profile.lateness.stakeholders.channel}} open "$HW_META"
agent-{{profile.lateness.stakeholders.channel}} screenshot "$SS_DIR/40-hw-form.png"

# Step 2: locate file input + upload
agent-{{profile.lateness.stakeholders.channel}} upload 'input[type="file"]' "$HW_PDF"
sleep 2

# Step 3: click submit (UI varies — try common submit button labels)
agent-{{profile.lateness.stakeholders.channel}} click "提出する" || agent-{{profile.lateness.stakeholders.channel}} click "提出" || agent-{{profile.lateness.stakeholders.channel}} click "Submit"
sleep 5
agent-{{profile.lateness.stakeholders.channel}} screenshot "$SS_DIR/41-hw-submitted.png"

# Step 4: capture confirmation page → log
agent-{{profile.lateness.stakeholders.channel}} eval 'document.body.innerText.substring(0, 500)' >> "$HOME/.openclaw/workspace/naist/<slug>/homework-submitted.log"
```

### Procedure F — Apply for fund (`MODE=funds-apply`)

```bash
# Input: research-profile.json + ~/.openclaw/skills/naist/funders.json (curated list)
# Per funder (JSPS / KAKEN / OpenPhil / FLI):
# Step 1: open the funder's application URL (no SSO; each funder has its own login)
agent-{{profile.lateness.stakeholders.channel}} open "$FUNDER_URL"
agent-{{profile.lateness.stakeholders.channel}} screenshot "$SS_DIR/50-funder-$FUNDER_ID.png"

# Step 2: locate username + password fields, fill from secrets.env
agent-{{profile.lateness.stakeholders.channel}} fill 'input[name*="user"]' "$FUNDER_USER"
agent-{{profile.lateness.stakeholders.channel}} fill 'input[type="password"]' "$FUNDER_PASS"
agent-{{profile.lateness.stakeholders.channel}} click "ログイン" || agent-{{profile.lateness.stakeholders.channel}} click "Sign in"

# Step 3: navigate to "新規応募" or equivalent
agent-{{profile.lateness.stakeholders.channel}} click "新規応募" || agent-{{profile.lateness.stakeholders.channel}} click "Apply"

# Step 4: fill text fields from research-profile.json (topic, abstract, method)
agent-{{profile.lateness.stakeholders.channel}} fill 'textarea[name*="title"]' "$(jq -r .topic research-profile.json)"
agent-{{profile.lateness.stakeholders.channel}} fill 'textarea[name*="abstract"]' "$(jq -r .preliminary_results research-profile.json)"

# Step 5: upload Quarto-rendered proposal PDF
agent-{{profile.lateness.stakeholders.channel}} upload 'input[type="file"]' "~/.openclaw/workspace/naist/<slug>/proposals/proposal.pdf"

# Step 6: submit
agent-{{profile.lateness.stakeholders.channel}} click "提出する" || agent-{{profile.lateness.stakeholders.channel}} click "Submit"
sleep 10
agent-{{profile.lateness.stakeholders.channel}} screenshot "$SS_DIR/51-funder-submitted-$FUNDER_ID.png"
```

---

## Mode-by-mode behavior summary

| MODE | trigger | external output | flexibility strategy |
|---|---|---|---|
| pull | every 15 min | {{profile.education.institution}} mail auto-replied via Gmail Send-mail-as | Gmail MCP query string `from:naist.ac.jp newer_than:1d`; classify by sender domain + subject keywords (not by ref) |
| morning-rollup | 09:00 daily | Slack #metrics digest of yesterday's {{profile.education.institution}} traffic | runs `triage.py --rollup=24h`; emits N-line summary |
| friday-rollup | Fri 18:00 | Slack week rollup + missing deadlines audit | `triage.py --rollup=7d --audit-deadlines` |
| deadline-ical | 07:00 daily | `~/.openclaw/workspace/naist/<slug>/deadlines.ics` (subscribed by macOS Calendar / Google Calendar) | extract deadlines from triaged + portal-scraped sources |
| papers-suggest | 08:00 daily | Slack post: top-5 arXiv papers + utility hint | arXiv API (no UI scraping); keywords from research-profile.json |
| funds-apply | 09:00 daily | Funder portal submission ID(s) | Procedure F per funder; `funders.json` is per-funder URL + selectors; UI changes → re-snapshot + find by visible text |
| edu-portal-check | Mon 10:00 | `portal-<ymd>.json` (jikanwari + transcripts + GPA) + Slack 不可 retake recommendations | Procedure A + B + C |
| course-register | 履修期間 11:00 | edu-portal 履修登録 form submitted; confirmation page screenshot | Procedure A + B + D; recommended_courses[] from preferences.json |
| homework-submit | 期日-1日 14:00 | edu-portal 課題提出 form submitted with rendered PDF | Procedure A + B + E |
| gcal-sync | Mon 12:00 | Recurring weekly events in user's Google Calendar | Google Calendar MCP; one event per course in jikanwari |
| research-proposal-gen | manual / quarterly | `proposal.pdf` (Quarto-rendered 科研費 form) | Quarto render of `research-profile.json` into 科研費 template |

---

## Cron registration

11 cron entries are pre-defined in `cron-template.json`. After `openclaw skill install naist` + wizard, each entry is merged into `~/.openclaw/cron/jobs.json` with `enabled: true` (unless the wizard answers say otherwise). Restart the gateway: `openclaw gateway restart`.

| cron name | schedule | mode |
|---|---|---|
| naist-pull | `*/15 * * * *` Asia/Tokyo | pull |
| naist-morning-rollup | `0 9 * * *` Asia/Tokyo | morning-rollup |
| naist-friday-rollup | `0 18 * * 5` Asia/Tokyo | friday-rollup |
| naist-deadline-ical | `0 7 * * *` Asia/Tokyo | deadline-ical |
| naist-papers-suggest | `0 8 * * *` Asia/Tokyo | papers-suggest |
| naist-funds-apply | `0 9 * * *` Asia/Tokyo | funds-apply |
| naist-edu-portal-check | `0 10 * * 1` Asia/Tokyo | edu-portal-check |
| naist-course-register | `0 11 * * *` Asia/Tokyo | course-register (script self-skips outside the 履修期間 window listed in `<slug>/preferences.json`) |
| naist-homework-submit | `0 14 * * *` Asia/Tokyo | homework-submit (self-skips if no draft is past its `submit_at`) |
| naist-gcal-sync | `0 12 * * 1` Asia/Tokyo | gcal-sync |
| naist-research-proposal-gen | manual | research-proposal-gen |

## Failure handling (every mode)

- Each mode wraps each step with `if [ $? -ne 0 ]; then post_slack ":warning: naist:<mode> step <N> failed — see $SS_DIR/<step>-error.png"; exit 1; fi`
- A failed login (`oathtool` clock-skew / wrong TOTP) gets one auto-retry after 30 s. If retry also fails, post `:warning: TOTP login failed — check {{profile.education.institution}}_TOTP_SECRET` and exit.
- If `agent-{{profile.lateness.stakeholders.channel}} snapshot` returns no element matching expected text, take a screenshot and post a Slack message linking the screenshot. **Do not blindly retry** — UI may have changed; let `tuning-skills` see the failure and adapt.
- Every mode opens its own agent-{{profile.lateness.stakeholders.channel}} session and closes it at the end (`agent-{{profile.lateness.stakeholders.channel}} close`) so concurrent crons don't fight over the same session.

## OSS release plan

- Repo: `github.com/Daisuke134/naist-skill`
- Tagline: *every {{profile.education.institution}} grad student's school-life on autopilot*
- Setup: install agent-{{profile.lateness.stakeholders.channel}}, oathtool, zbar; run `openclaw skill install naist`; complete wizard; subscribe to deadlines.ics in macOS Calendar.
- License: MIT
- Public release timing: gated on graduation (per spec), but the generic university-automation pattern (find-by-text + procedural step list) is a template other schools can fork now.

## Risks / notes

- Academic-integrity disclaimer is README-level only; the skill auto-submits homework. The owning student is responsible.
- Course registration timing: `<slug>/preferences.json` MUST include `enrollment_window_start` and `_end` to prevent registration submissions outside the window (which would error on the form).
- TOTP drift: Mac Mini's clock must be NTP-synced. Otherwise `oathtool` will produce wrong codes.
- IDP UI changes: when {{profile.education.institution}} changes labels (e.g. "ログイン" → "サインイン"), the procedural section above is the canonical instruction; agent re-reads SKILL.md and adapts the find-by-text strings.

## See also

- `cron-template.json` — exact cron entries to merge
- `scripts/run.sh` — top-level dispatcher (one entry per MODE)
- `scripts/triage.py` — Gmail-side triage rules
- `scripts/draft-homework.py` — homework reply skeleton
- `scripts/quarto-render.sh` — Quarto PDF render
- `scripts/send-as.py` — Gmail Send-mail-as wrapper
- `scripts/papers-suggest.py` — arXiv search + utility-hint
- `scripts/funds-apply.py` — funder candidate scan + Procedure F driver
- `scripts/edu-portal-check.py` — Procedure A + B + C driver
- `scripts/course-register.py` — Procedure A + B + D driver
- `scripts/homework-submit.py` — Procedure A + B + E driver
- `scripts/gcal-sync.py` — Google Calendar MCP driver
- `scripts/research-proposal-gen.py` — Quarto driver
- `scripts/decode-otp-migration.py` — wizard helper that takes Google Authenticator migration QR PNG and emits `naist.totp_secret`
