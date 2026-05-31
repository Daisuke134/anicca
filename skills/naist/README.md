# naist — every NAIST grad student's school-life on autopilot

OSS Anicca skill that runs the entire NAIST graduate workload off your
Mac mini (or any always-on machine) without you ever opening
edu-portal again:

- **Mail triage + auto-reply** for every NAIST mail forwarded to your
  personal Gmail (sender domain + subject classification, no human
  approval needed).
- **履修登録** auto-fill on edu-portal during the registration window
  for every course in `preferences.json`.
- **Class schedule** synced to your Google Calendar (one recurring event
  per registered course).
- **Homework draft + auto-submit** — fetched from the 期限あり tab, an
  LLM drafts the answer, Quarto renders the PDF, edu-portal upload +
  「確定」 + OK happens on a cron N−1 days before the deadline.
  *(Verified end-to-end on 2026-05-29 for three concurrent courses:
  ST4093sp アルゴリズム設計論, ST4105sp データサイエンス論, and
  ST4093sp Quantum Information.)*
- **Deadlines in iCal** at `~/.openclaw/workspace/naist/<slug>/deadlines.ics`,
  subscribable by macOS Calendar.
- **Paper recommendations** — daily 08:00 JST: arXiv search on your
  `research-profile.json` keywords → top-5 papers → Slack post.
- **Fund applications** — daily 09:00 JST: scan JSPS / KAKEN / OpenPhil /
  FLI and submit ready candidates with a Quarto-rendered 科研費 PDF.
- **Grades + GPA snapshots** — weekly Mon 10:00 JST: 学生時間割表 +
  成績照会 scraped to JSON, 不可 (failing) classes flagged in Slack.

## Two ways to use this skill

| Mode | What you do | How it runs |
|------|-------------|-------------|
| **A. Manual / Claude Code interactive** | `cd ~/anicca-oss/skills/naist && MODE=homework-fetch SLUG=<your-slug> bash scripts/run.sh` from any Claude Code chat, or load the skill via Claude Code's `Skill` tool and ask "fetch my NAIST homework" | One-off run, you watch the screenshots in `~/.openclaw/workspace/naist/<slug>/screenshots/<date>/`. |
| **B. Fully autonomous (Anicca cron)** | Install once, complete the wizard, register the 11 crons (`naist-pull`, `naist-homework-fetch`, `naist-homework-submit`, etc.) | Mac mini wakes, logs in to NAIST IDP via TOTP, drafts, renders, submits — you never touch edu-portal for 2 years. |

Both modes share the same scripts; mode B is just A on a cron.

## Quick install (5 minutes)

```bash
# 1. Clone anicca-oss (or just this skill subtree)
git clone https://github.com/Daisuke134/anicca-oss.git ~/anicca-oss

# 2. Install runtime deps
brew install oath-toolkit zbar jq quarto pdftotext
npm install -g @aniccatech/agent-browser   # or follow agent-browser README

# 3. Bootstrap per-slug state
SLUG=<your-slug>   # e.g. "ayame"
mkdir -p ~/.openclaw/state/naist/$SLUG ~/.openclaw/workspace/naist/$SLUG
cp ~/anicca-oss/skills/naist/config.example.json ~/.openclaw/state/naist/$SLUG/profile.json
$EDITOR ~/.openclaw/state/naist/$SLUG/profile.json   # fill placeholders

# 4. Drop your IDP secrets in a chmod-600 env file
cat > ~/.openclaw/state/naist/$SLUG/secrets.env <<'EOF'
NAIST_IDP_USERNAME=<your-username>
NAIST_IDP_PASSWORD=<your-NAIST-password>
NAIST_TOTP_SECRET=<base32-from-decode-otp-migration.py>
EOF
chmod 600 ~/.openclaw/state/naist/$SLUG/secrets.env

# 5. Sanity-check: fetch the 期限あり tab
SLUG=$SLUG MODE=homework-fetch bash ~/anicca-oss/skills/naist/scripts/run.sh
#   → writes ~/.openclaw/workspace/naist/$SLUG/homework-<today>.json
#   → also posts to Slack if SLACK_BOT_TOKEN + channel are set
```

After step 5 you should see a JSON file with one entry per outstanding
homework. Pick one, hand-render a Quarto PDF (or wait for the
auto-draft cron to do it for you), then:

```bash
SLUG=$SLUG MODE=homework-submit bash ~/anicca-oss/skills/naist/scripts/run.sh
```

That uploads the rendered PDF and clicks 確定 → OK. The
`提出日時` row appearing on the form is the canonical proof of
success.

## Architecture

```
~/.openclaw/state/naist/<slug>/
  ├── profile.json                  # PII (name, student-id, email)
  ├── secrets.env                   # chmod 600 (IDP credentials + TOTP)
  ├── research-profile.json         # your thesis topic + keywords
  ├── preferences.json              # recommended_courses[], enrollment window
  └── slack_channel.txt             # optional Slack target

~/.openclaw/workspace/naist/<slug>/
  ├── homework-YYYY-MM-DD.json      # fetched assignments + errors
  ├── homework/<class-slug>/        # downloaded lecture PDFs + report.pdf
  ├── drafts/<class-slug>/<ts>.json # auto-draft → submission_url + pdf_path + submit_at
  ├── screenshots/<date>/           # every step's screenshot (audit + UI-diff)
  ├── portal-YYYY-MM-DD.json        # weekly transcript + GPA snapshot
  ├── deadlines.ics                 # subscribed by macOS/Google Calendar
  └── homework-submit-history.json  # what was submitted, when, with what
```

## The 11 cron entries

After install, restart the gateway and the 11 cron jobs run automatically:

| name | schedule | mode |
|------|----------|------|
| `naist-pull` | every 15 min | mail triage |
| `naist-morning-rollup` | 09:00 JST | yesterday-digest |
| `naist-friday-rollup` | Fri 18:00 JST | week-digest |
| `naist-deadline-ical` | 07:00 JST | regenerate iCal |
| `naist-papers-suggest` | 08:00 JST | arXiv → Slack |
| `naist-funds-apply` | 09:00 JST | grant scan + submit |
| `naist-edu-portal-check` | Mon 10:00 JST | grades + transcript |
| `naist-course-register` | 11:00 JST during registration window | 履修登録 |
| `naist-homework-fetch` | 07:00 JST | new assignments → JSON |
| `naist-homework-submit` | 14:00 JST | render + upload + 確定 |
| `naist-gcal-sync` | Mon 12:00 JST | schedule → Google Calendar |

Drop a `<name>.disabled` flag in `~/.openclaw/cron/` to pause any one.

## What's verified, what's planned

| Feature | Status | Last verified |
|---|---|---|
| TOTP login + SSO | ✅ live | 2026-05-29 |
| 期限あり tab → homework fetch | ✅ live (partial-failure tolerant) | 2026-05-29 |
| Homework submit (JS DataTransfer + 確定 + OK) | ✅ live, 3 courses | 2026-05-29 |
| 学生時間割表 + 成績照会 scrape | ✅ live | 2026-05-08 |
| 履修登録 auto-fill | ✅ verified once | 2026-05-08 (ST1002sp add) |
| iCal deadline feed | ✅ live | 2026-05-29 |
| arXiv paper digest | ✅ live | runs daily |
| Fund apply | 🟡 framework + per-funder selectors; needs your account | — |
| **LLM-driven `homework-auto-draft.py`** | 🟡 planned (Task #6) — see SKILL.md §Procedure G | scaffolded |

## Security checklist

- `profile.json` is **gitignored**. Your name/student-ID/lab never leaves
  the machine.
- `secrets.env` is chmod 600 and never read by anything outside the
  scripts. Add it to `.gitignore` again locally if you keep a private
  fork.
- `decode-otp-migration.py` accepts the OTP-export string only via
  stdin/argv; it never persists. Run it once, copy the `secret_base32`
  to `secrets.env`, throw the QR away.
- The skill talks **only** to `idp.naist.jp` + `edu-portal.naist.jp` +
  Gmail/Calendar/Slack via their official APIs. No third-party
  middleware.
- Every web step takes a screenshot (workspace dir). Forensic trail if
  anything looks off.

## License

MIT. The shared selectors for funder portals
(`funders.json`) are generic and contributed back here as you tune them.

## Credits

- `agent-browser` for the CDP wrapper. (See `~/anicca-oss/skills/agent-browser/`.)
- Quarto for the LaTeX render path.
- NAIST UNIPA team for the consistent JSF/PrimeFaces UI that made
  programmatic submission feasible.
