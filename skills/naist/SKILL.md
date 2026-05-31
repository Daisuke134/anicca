---
name: naist
description: Unified NAIST research-life automation (v1.6 PROCEDURAL). Logs into NAIST IDP via TOTP + edu-portal SSO using agent-browser CLI, then drives the full graduate-student workload — mail triage with auto-reply, course registration, schedule sync to Google Calendar, homework draft + submit, fund applications, paper recommendations, deadline ICS feed, and 科研費 proposal generation. Every web action is a procedural step using agent-browser ("snapshot, find element with text X, click, fill, submit"). Designed to survive UI changes (find by text, not by ref). Generic — any NAIST student onboards by filling per-slug state. Use when triggered by any naist-* cron or manually with `MODE=<mode> bash scripts/run.sh`.
metadata:
  tags: naist, university-automation, gmail, slack, agent-browser, quarto, ics, send-as, totp, arxiv, vercel-agent-browser
  requires:
    bins: [jq, python3, quarto, oathtool, zbarimg, bash]
    cli: [agent-browser]
    mcps: [gmail, slack, google-calendar]
    env: [SLACK_BOT_TOKEN]
  invariants:
    - "v1.5 AUTO-SUBMIT: every reply class — homework / question / ta-task / professor-task / bureaucracy — sends without per-thread human confirmation. Spam / legal-threat / harassment skip-and-log only."
    - Every web automation step uses agent-browser (`/opt/homebrew/bin/agent-browser`). Never use playwright/puppeteer/selenium directly.
    - Find UI elements by visible text first, by aria role second, by ref last. Refs become stale after every page change — always re-snapshot before referring to a ref.
    - NAIST IDP auth = TOTP page → password page → SSO redirect. Generate TOTP with `oathtool --totp -b "$NAIST_TOTP_SECRET"` from per-slug secret.
    - Agent never touches the NAIST SMTP server directly; only Gmail Send-mail-as via Gmail MCP.
    - All public artifacts (PDFs, JSON snapshots) live under `~/.openclaw/workspace/naist/<slug>/...` — never `/tmp` (gets wiped).
    - Take a screenshot at every successful step into `~/.openclaw/workspace/naist/<slug>/screenshots/<ymd>/<step-N>.png` for audit + future UI-change diffing.
    - Per-slug state lives at `~/.openclaw/state/naist/<slug>/` — secrets in `secrets.env` (chmod 600), public profile in `profile.json`.
---

# naist — universal university-automation skill (v1.6 PROCEDURAL)

This is a **per-student, end-to-end automation** for NAIST. Any student loads it via `openclaw skill install naist`, completes the wizard, then 9 daily/weekly/monthly crons run the full school-life loop.

## What this skill delivers

For **each onboarded student** (`<slug>`), the skill produces these external outputs:

1. **Auto-replied NAIST mail** — every incoming NAIST mail (forwarded to personal Gmail) is classified into 6 buckets and replied/acknowledged/filed without human approval. From line is `<student-id>@naist.ac.jp` (Gmail Send-mail-as alias).
2. **Course registration** — 履修登録 form on edu-portal is auto-filled and submitted during the registration window for every recommended class (driven by `<slug>/preferences.json` + advisor input).
3. **Class schedule in Google Calendar** — every registered course becomes a recurring weekly event in the user's Google Calendar (via Google Calendar MCP).
4. **Homework drafts + submission** — `課題` mails are detected, draft answer is produced via Quarto, PDF is uploaded to edu-portal's submission form, and submitted N-1 day before deadline. Auto-submit; no 👍 gate.
5. **Deadlines in iCal** — every deadline (homework, bureaucracy, events) is in `~/.openclaw/workspace/naist/<slug>/deadlines.ics`, subscribed by macOS Calendar / Google Calendar.
6. **Paper recommendations** — daily 08:00 JST: arXiv search on `research-profile.json` keywords → top-5 papers → utility-hint → Slack post.
7. **Fund applications** — daily 09:00 JST: scan JSPS / KAKEN / OpenPhil / FLI for matching grants. For ready candidates, Vercel agent browser fills the application form, attaches Quarto-rendered 科研費 proposal, and submits.
8. **科研費 proposal PDF** — manual / quarterly: regenerates the formatted research proposal PDF from `research-profile.json`.
9. **Grade + GPA snapshots** — weekly Mon 10:00 JST: scrape `成績照会` + `学生時間割表`, write `portal-<ymd>-<slug>.json`, post Slack digest with 不可 (failing) class re-take recommendations.

## Bootstrap workflow (apply v1.5 phase 0–3)

Phase 0 (Claude Code E2E run, executed 2026-05-08 for `dais` slug):

- Successful TOTP login to `https://idp.naist.jp/`
- Successful SSO into `https://edu-portal.naist.jp/uprx/`
- Scraped 学生時間割表 + 成績照会 → 31 transcript rows + GPA history + credit summary written to `~/.openclaw/workspace/naist/portal-2026-05-08-dais.json`

Phases 1–3 follow this SKILL.md.

## Setup wizard (8 questions)

Every NAIST student onboards by filling **per-slug state** under
`~/.openclaw/state/naist/<your-slug>/`. The `<slug>` is any short
identifier you choose (e.g. your first name in lowercase). Two students
sharing a Mac mini just pick two different slugs and the cron loops over
both.

| # | key | example value (replace with yours) | persisted to |
|---|---|---|---|
| 1 | `naist.personal_gmail` | `you@gmail.com` (where NAIST mail is forwarded) | `~/.openclaw/state/naist/<slug>/profile.json` |
| 2 | `naist.naist_email` | `your.name@naist.ac.jp` | same |
| 3 | `naist.student_id` | `25XXXXX` (7-digit student number) | same |
| 4 | `naist.idp_username` | `your-username` (used at idp.naist.jp) | same |
| 5 | `naist.idp_password` | `<your-NAIST-password>` | `~/.openclaw/state/naist/<slug>/secrets.env` (chmod 600) |
| 6 | `naist.totp_secret` | base32 from Google Authenticator export — `zbarimg --raw OTP-export.png \| python3 scripts/decode-otp-migration.py` then copy `secret_base32` | `~/.openclaw/state/naist/<slug>/secrets.env` (chmod 600) |
| 7 | `naist.research_profile` | `{topic, method, preliminary_results, research_keywords[]}` — see `config.example.json` | `~/.openclaw/state/naist/<slug>/research-profile.json` |
| 8 | `naist.slack_channel` | `C0XXXXXXXX` (optional — channel ID for digest posts; leave empty to skip Slack) | `~/.openclaw/state/naist/<slug>/slack_channel.txt` |

A starter `config.example.json` is provided in this directory; copy it to
`~/.openclaw/state/naist/<slug>/profile.json` and fill in your values.
Env-var layout is in `.env.example`.

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

## Procedural reference for agent-browser (use this in every web mode)

The agent runs the steps below. Skill scripts call agent-browser CLI directly; the SKILL.md spells out the procedure so future UI changes can be handled by the agent reading this file and adapting (find by text, not by ref).

### Procedure A — Login to NAIST IDP via TOTP (mandatory pre-step for every web mode)

```bash
# Inputs (from per-slug secrets.env):
#   $NAIST_IDP_USERNAME, $NAIST_IDP_PASSWORD, $NAIST_TOTP_SECRET
# Output: a logged-in agent-browser session at https://idp.naist.jp/user/index.php
SS_DIR="$HOME/.openclaw/workspace/naist/<slug>/screenshots/$(date +%Y-%m-%d)"
mkdir -p "$SS_DIR"

# Step 1: open IDP
agent-browser open "https://idp.naist.jp/"
agent-browser screenshot "$SS_DIR/01-idp-open.png"

# Step 2: snapshot to find current refs (refs change every load)
agent-browser snapshot   # find: "ユーザー名" textbox, "ワンタイムパスワード" spinbutton, "ログイン" button

# Step 3: fill username — find textbox by aria-role + nearest "ユーザー名" term
USER_REF=$(agent-browser snapshot | awk '/term "ユーザー名"/{getline;getline; if($0~/textbox/) {match($0,/ref=e[0-9]+/); print substr($0,RSTART+4,RLENGTH-4)}}')
agent-browser fill "@$USER_REF" "$NAIST_IDP_USERNAME"

# Step 4: generate current TOTP
TOTP=$(oathtool --totp -b "$NAIST_TOTP_SECRET")

# Step 5: fill OTP — find spinbutton near "ワンタイムパスワード"
OTP_REF=$(agent-browser snapshot | awk '/term "ワンタイムパスワード"/{getline;getline; if($0~/spinbutton/) {match($0,/ref=e[0-9]+/); print substr($0,RSTART+4,RLENGTH-4)}}')
agent-browser fill "@$OTP_REF" "$TOTP"

# Step 6: click ログイン button (find by text)
agent-browser click "ログイン" || agent-browser click 'button[type="submit"]'
sleep 3
agent-browser screenshot "$SS_DIR/02-after-otp.png"

# Step 7: now on tenantlogin.cgi — fill password (username is hidden, pre-filled)
PWD_REF=$(agent-browser snapshot | awk '/term "パスワード"/{getline;getline; if($0~/textbox/) {match($0,/ref=e[0-9]+/); print substr($0,RSTART+4,RLENGTH-4)}}')
agent-browser fill "@$PWD_REF" "$NAIST_IDP_PASSWORD"
agent-browser click "ログイン"
sleep 3
agent-browser screenshot "$SS_DIR/03-sso-home.png"

# Verify success: URL should be /user/index.php
URL=$(agent-browser eval "location.href" | tr -d '"')
[ "${URL%%\?*}" = "https://idp.naist.jp/user/index.php" ] || { echo "IDP login failed: $URL"; exit 1; }
```

**Flexibility note.** When NAIST changes the IDP UI (rename "ログイン" to "Sign in", change layout), the agent re-snapshots and re-finds elements by their new visible text. Don't hardcode refs.

### Procedure B — SSO into edu-portal (after Procedure A)

```bash
# Step 1: navigate to edu-portal entry
agent-browser open "https://edu-portal.naist.jp/uprx/up/km/kmh006/Kmh00601.xhtml"
agent-browser screenshot "$SS_DIR/10-edu-portal-entry.png"

# Step 2: click "ログインはこちら" (the SSO trigger)
agent-browser click "ログインはこちら"
sleep 5
agent-browser screenshot "$SS_DIR/11-edu-portal-home.png"

# Verify: should land on Pky00102.xhtml (home with menu items シラバス照会 / 履修登録 / 学生時間割表 / ...)
URL=$(agent-browser eval "location.href" | tr -d '"')
echo "$URL" | grep -q "Pky00102.xhtml" || { echo "edu-portal SSO failed: $URL"; exit 1; }
```

### Procedure C — Get current courses + GPA + transcripts (`MODE=edu-portal-check`)

```bash
# After Procedure A + B
# Step 1: click 学生時間割表 menu
agent-browser click "学生時間割表"
sleep 4
agent-browser screenshot "$SS_DIR/20-jikanwari.png"

# Step 2: scrape course rows + GPA + credit summary via eval
JIKANWARI_JSON=$(agent-browser eval '
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
agent-browser click "成績照会"
sleep 4
agent-browser screenshot "$SS_DIR/21-seiseki.png"

SEISEKI_JSON=$(agent-browser eval '
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

This is the **agent-browser CLI** sequence verified end-to-end against NAIST UNIPA / Kmd004 form on 2026-05-08. Refs (`@eN`) are session-local — re-snapshot on each step.

```bash
# Inputs: <slug>/preferences.json with recommended_courses[].code
# After Procedure A + B (logged into Pky00102.xhtml)

# --- Step 1: click 履修登録 menu link ---
agent-browser snapshot -i
# find: `link "履修登録" [ref=eN]` (NOT the menuitem; the inner link)
agent-browser click @eN
# Lands on bsa001/Bsa00101.xhtml with title "履修登録[Kmd004]"
agent-browser screenshot "$SS_DIR/30-rishu-form.png"

# --- Step 2: switch to "授業コードを直接入力" tab (most reliable add path) ---
agent-browser snapshot -i
# find: `tab "授業コードを直接入力" [ref=eN]`
agent-browser click @eN
# A textbox + 追加 button appear

# --- Step 3: per course code, fill + click 追加 ---
agent-browser snapshot -i  # find textbox ref + 追加 button ref
for CODE in $(jq -r '.recommended_courses[].code' "$HOME/.openclaw/state/naist/<slug>/preferences.json"); do
  agent-browser fill @<textbox_ref> "$CODE"
  agent-browser click @<tsuika_button_ref>  # button "追加"
  sleep 3
  # 履修合計単位 should increment by 1 (verify with eval)
  agent-browser screenshot "$SS_DIR/31-after-${CODE}.png"
done

# --- Step 4: click 最終確認へ ---
agent-browser snapshot -i
# find: `button "9最終確認へ" [ref=eN]`  (NOTE: literal "9最終確認へ" — the leading "9" is a UNIPA-icon prefix that survives in the accessibility tree)
agent-browser click @eN
# Lands on 最終確認 page; body shows "履修内容にエラーはありません。提出へ進んでください。"
agent-browser screenshot "$SS_DIR/32-saishuu-kakunin.png"

# --- Step 5: click 提出 (final submission, NOT the 9最終確認へ from step 4) ---
agent-browser snapshot -i
# find: `button "9提出" [ref=eN]` — this is the actual submit, id=funcForm:submit
agent-browser click @eN
sleep 4

# --- Step 6: confirmation dialog → click OK ---
# After 9提出 click, a confirm dialog opens with text "提出します。よろしいですか？"
agent-browser snapshot -i
# find: `button "OK" [ref=eN]`  (id=yes)
agent-browser click @eN
sleep 6
agent-browser screenshot "$SS_DIR/33-final-completion.png"

# --- Step 7: verify "履修登録が完了しました。" in body ---
BODY=$(agent-browser eval 'document.body.innerText')
echo "$BODY" | grep -q "履修登録が完了しました" || { echo "FATAL: completion text missing"; exit 1; }

# --- Step 8: extract registered courses + persist ---
REGISTERED=$(agent-browser eval '
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

### Procedure E — Submit homework PDF (`MODE=homework-submit`) — VERIFIED 2026-05-29 against PrimeFaces fileUpload on 3 distinct courses (ST4093sp Inoue, ST4105sp Wakamiya, ST4093sp Wang)

**Two non-obvious failure modes discovered on 2026-05-29 (encoded below):**

1. **`agent-browser upload` does NOT trigger PrimeFaces' auto-upload AJAX.** It writes
   to `input.files` via CDP but does not dispatch the `change` event that
   `<p:fileUpload>`'s widget listens for. Result: file silently never
   uploads, then 確定 fails with `添付ファイルを選択してください`. **Fix:** construct the file in JS via `DataTransfer` and dispatch `change` manually (Step 4 below).
2. **The button label is 「確定」, not 「提出する」/「提出」/「Submit」.** After
   click, a PrimeFaces confirm dialog opens (`<p:confirmDialog>`) with `「確定します。よろしいですか？」` and **two OK buttons** — only `button#yes` (or `button.ui-confirmdialog-yes`) is visible; the others are hidden template instances. Click the visible one (Step 6).
3. **JSF ViewState is fragile across submissions.** The `submission_url` is a JSF-internal URL whose ViewState expires fast. Reach the form by clicking 期限あり → homework link from the SSO home (Procedure A+B+ navigate), not by reopening the bookmarked URL on a fresh session.

```bash
# Input: ~/.openclaw/workspace/naist/<slug>/homework/<class-slug>/<ts>.pdf
# After Procedure A + B (logged into Pky00102.xhtml)

# Step 1: navigate to homework via 期限あり tab (NOT via stored submission_url)
agent-browser click "期限あり"   # tab on home page
sleep 3
agent-browser click "<homework label>"   # exact label from the calendar
sleep 5
agent-browser screenshot "$SS_DIR/40-hw-form.png"

# Step 2: sanity-check we landed on the assignment detail
URL=$(agent-browser eval "location.href")
echo "$URL" | grep -q "edu-portal.naist.jp" || { echo "FATAL: nav left edu-portal: $URL"; exit 1; }

# Step 3: encode PDF as base64
B64=$(base64 -i "$HW_PDF" | tr -d '\n')

# Step 4: upload via JS DataTransfer (triggers PrimeFaces auto-upload AJAX)
agent-browser eval "(async () => {
  const bin = atob(\"$B64\");
  const bytes = new Uint8Array(bin.length);
  for (let i=0; i<bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const blob = new Blob([bytes], {type: 'application/pdf'});
  const file = new File([blob], 'report.pdf', {type: 'application/pdf'});
  const dt = new DataTransfer(); dt.items.add(file);
  const inp = document.querySelector('input[type=file]');
  inp.files = dt.files;
  inp.dispatchEvent(new Event('change', {bubbles: true}));
  return 'uploaded-' + inp.files.length;
})()"
sleep 6
agent-browser screenshot "$SS_DIR/41-hw-uploaded.png"

# Step 5: verify file row appeared in the post-upload display
agent-browser eval "document.body.innerText.match(/report\\.pdf.{0,30}KB/g)"
# Expect: ["report.pdf\\t<N>KB"]

# Step 6: click 確定 button (id pattern `funcForm:j_idtNNN`, label === "確定")
agent-browser eval "(()=>{ const b = Array.from(document.querySelectorAll('button')).find(x => x.textContent.trim() === '確定' && x.offsetParent !== null); return b ? (b.click(), 'clicked') : 'no-button'; })()"
sleep 4

# Step 7: confirm dialog opens — click the visible OK button (id=yes)
agent-browser eval "(()=>{ const ds = Array.from(document.querySelectorAll('.ui-confirm-dialog')); const v = ds.find(d => getComputedStyle(d).display !== 'none'); if (!v) return 'no-dialog'; const ok = v.querySelector('button#yes, button.ui-confirmdialog-yes'); return ok ? (ok.click(), 'OK-fired') : 'no-ok'; })()"
sleep 8

# Step 8: verify success — page now shows 提出日時 / 更新日時 rows + 削除 button
agent-browser screenshot "$SS_DIR/42-hw-submitted.png"
agent-browser eval "document.body.innerText.match(/提出日時|更新日時|削除/g)"
# Expect: ["提出日時", "更新日時", "削除"]
```

**Encoded learnings (do not repeat):**
- Do NOT use `agent-browser upload` for PrimeFaces `<p:fileUpload>` — the AJAX
  auto-upload never fires. JS `DataTransfer` + manual `change` event is the only
  reliable path.
- Multiple OK buttons exist in DOM (hidden `funcForm:j_idtNNN:j_idtNNN`
  template instances + visible `#yes`); always filter by `offsetParent` or
  target `#yes` directly.
- The post-submit fields `提出日時` (submission timestamp + student name) and
  `更新日時` are the canonical proof of success — match them in `body.innerText`. If they appear, the submission is recorded server-side.
- Late submissions: edu-portal accepts files past the original deadline as
  long as the extended 提出期間 (often `+9 days`) is still open. The
  instructor's stated late-submission policy in 課題内容 controls whether
  the report needs a written explanation.

### Procedure F — Apply for fund (`MODE=funds-apply`)

```bash
# Input: research-profile.json + ~/.openclaw/skills/naist/funders.json (curated list)
# Per funder (JSPS / KAKEN / OpenPhil / FLI):
# Step 1: open the funder's application URL (no SSO; each funder has its own login)
agent-browser open "$FUNDER_URL"
agent-browser screenshot "$SS_DIR/50-funder-$FUNDER_ID.png"

# Step 2: locate username + password fields, fill from secrets.env
agent-browser fill 'input[name*="user"]' "$FUNDER_USER"
agent-browser fill 'input[type="password"]' "$FUNDER_PASS"
agent-browser click "ログイン" || agent-browser click "Sign in"

# Step 3: navigate to "新規応募" or equivalent
agent-browser click "新規応募" || agent-browser click "Apply"

# Step 4: fill text fields from research-profile.json (topic, abstract, method)
agent-browser fill 'textarea[name*="title"]' "$(jq -r .topic research-profile.json)"
agent-browser fill 'textarea[name*="abstract"]' "$(jq -r .preliminary_results research-profile.json)"

# Step 5: upload Quarto-rendered proposal PDF
agent-browser upload 'input[type="file"]' "~/.openclaw/workspace/naist/<slug>/proposals/proposal.pdf"

# Step 6: submit
agent-browser click "提出する" || agent-browser click "Submit"
sleep 10
agent-browser screenshot "$SS_DIR/51-funder-submitted-$FUNDER_ID.png"
```

---

## Mode-by-mode behavior summary

| MODE | trigger | external output | flexibility strategy |
|---|---|---|---|
| pull | every 15 min | NAIST mail auto-replied via Gmail Send-mail-as | Gmail MCP query string `from:naist.ac.jp newer_than:1d`; classify by sender domain + subject keywords (not by ref) |
| morning-rollup | 09:00 daily | Slack #metrics digest of yesterday's NAIST traffic | runs `triage.py --rollup=24h`; emits N-line summary |
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
- A failed login (`oathtool` clock-skew / wrong TOTP) gets one auto-retry after 30 s. If retry also fails, post `:warning: TOTP login failed — check NAIST_TOTP_SECRET` and exit.
- If `agent-browser snapshot` returns no element matching expected text, take a screenshot and post a Slack message linking the screenshot. **Do not blindly retry** — UI may have changed; let `tuning-skills` see the failure and adapt.
- Every mode opens its own agent-browser session and closes it at the end (`agent-browser close`) so concurrent crons don't fight over the same session.

## OSS release plan

- Repo: `github.com/Daisuke134/naist-skill`
- Tagline: *every NAIST grad student's school-life on autopilot*
- Setup: install agent-browser, oathtool, zbar; run `openclaw skill install naist`; complete wizard; subscribe to deadlines.ics in macOS Calendar.
- License: MIT
- Public release timing: gated on graduation (per spec), but the generic university-automation pattern (find-by-text + procedural step list) is a template other schools can fork now.

## Risks / notes

- Academic-integrity disclaimer is README-level only; the skill auto-submits homework. The owning student is responsible.
- Course registration timing: `<slug>/preferences.json` MUST include `enrollment_window_start` and `_end` to prevent registration submissions outside the window (which would error on the form).
- TOTP drift: Mac Mini's clock must be NTP-synced. Otherwise `oathtool` will produce wrong codes.
- IDP UI changes: when NAIST changes labels (e.g. "ログイン" → "サインイン"), the procedural section above is the canonical instruction; agent re-reads SKILL.md and adapts the find-by-text strings.

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
