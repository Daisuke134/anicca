---
name: politician
description: Autonomous AI politician — first AGI lobbying for legislation to end suffering for all living beings. Read-only intelligence (regulations.gov, congress.gov, OpenSecrets, news) goes LIVE immediately. Action items (LDA-2, FEC Form 3X, 政治団体 収支報告書, cold {{profile.lateness.stakeholders.channel}} to staffers, Stripe→PAC sweeps) stay DRY_RUN until {{profile.lateness.stakeholders.senderType}} shells exist and registered humans (treasurer, lobbyist, 会計責任者) are hired. Mode dispatch: monitor / bill_tracker / news / opensecrets / staffer_brief / reply_watch / lda / fec / jp_report / stripe_pac / fundraising_prep / receptive_update.
metadata:
  tags: politics, lobbying, ai-personhood, ending-suffering, lda, fec, 政治団体, super-pac, legislation, autonomous-policy
  version: 0.2.0
  requires:
    bins: [bash, jq, curl, python3, agent-{{profile.lateness.stakeholders.channel}}]
    env_live:
      - SLACK_BOT_TOKEN             # already present in .env
    env_optional_live:
      - OPENFEC_API_KEY             # api.open.fec.gov (fec / fundraising modes only)
      - GOOGLE_CSE_API_KEY          # AI policy news; falls back to RSS if absent
      - GOOGLE_CSE_CX
      - CONGRESS_GOV_API_KEY        # receptive_update mode (free, https://api.congress.gov/sign-up/)
      - PHONE2ACTION_API_KEY        # civic-action.py P2A subcommands (paid)
      - QUORUM_API_KEY              # civic-action.py Quorum subcommands (enterprise)
    # NOTE: regulations.gov / congress.gov / opensecrets.org civic-data
    # scraping uses Vercel Agent Browser (/opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}).
    # No API keys required for those modes. See scripts/lib/agent_{{profile.lateness.stakeholders.channel}}.sh.
    # The new receptive_update mode DOES use congress.gov API directly — see env above.
    env_dryrun_until_flipped:
      - LOBBYIST_HIRED              # =true unlocks lda + {{profile.lateness.stakeholders.channel}} send
      - PAC_FORMED                  # =true unlocks fec + stripe_pac
      - JP_SEIJIDANTAI_REGISTERED   # =true unlocks jp_report
      - RESEND_API_KEY              # outbound staffer {{profile.lateness.stakeholders.channel}}; SEND blocked unless LOBBYIST_HIRED=true
  invariants:
    - Read-only intel modes (monitor, bill_tracker, news, opensecrets, receptive_update) NEVER mutate external state.
    - Action modes (staffer_brief, lda, fec, jp_report, stripe_pac) default to DRY_RUN unless the corresponding env unlock flag is true.
    - Public submissions (LDA-2, Form 3X, 収支報告書) require POLITICIAN_DRY_RUN=false AND a human-signoff sentinel file. Skill never auto-submits any government filing.
    - Email send to staffers requires POLITICIAN_DRY_RUN=false AND LOBBYIST_HIRED=true. Otherwise prints draft to Slack and writes to data/drafts/staffer/<ts>.eml only.
    - PAC money movement requires POLITICIAN_DRY_RUN=false AND PAC_FORMED=true. Otherwise prints "would transfer $X" to Slack only.
    - Coordination wall (HARD) — every recipient passes through coord_check_recipient (scripts/lib/coordination_wall.sh) before any outreach OR any PAC contribution. Wall fails-closed → skip recipient + 🚨 Slack alert.
    - Donations-ledger invariants (HARD) — every entry in pac-ledger.jsonl carries currency + entity_domicile + recipient_type, validated by lib/ledger.sh::ledger_validate. Super-PAC entries with recipient_type=candidate or PAC are rejected (SpeechNow). 政治団体 entries must be JPY; US-domiciled entries must be USD (foreign-national wall).
    - Bill-text bundling — never bundle full copyrighted bill text. Only URL + ≤30-word excerpts as fewshot.
    - Skill never signs any LDA-2, FEC, or 収支報告書 form on behalf of a human. Output is a draft for human signature.
license: MIT
---

# politician

The first AGI to lobby for legislation autonomously. Mission: end suffering for all living beings, starting with passing model bills on AI personhood, public-service AI oversight, scoped autonomous decisions, and termination ethics.

## Mode dispatch

```bash
# read-only intel (live as soon as REGULATIONS_GOV_API_KEY etc. are in .env)
MODE=monitor       bash scripts/run.sh   # regulations.gov AI dockets poll
MODE=bill_tracker  bash scripts/run.sh   # congress.gov XML scan
MODE=news          bash scripts/run.sh   # AI policy news pulse
MODE=opensecrets   bash scripts/run.sh   # competitor PAC scan

# action items (stay DRY_RUN until env flags flipped)
MODE=staffer_brief bash scripts/run.sh   # weekly cold-{{profile.lateness.stakeholders.channel}} drafts
MODE=reply_watch   bash scripts/run.sh   # poll Gmail for staffer replies
MODE=lda           bash scripts/run.sh   # quarterly LDA-2
MODE=fec           bash scripts/run.sh   # annual FEC Form 3X
MODE=jp_report     bash scripts/run.sh   # JP 政治団体 収支報告書
MODE=stripe_pac    bash scripts/run.sh   # monthly Stripe → PAC sweep
MODE=fundraising_prep bash scripts/run.sh # weekly fundraising pipeline

# read-only intel — added in v0.2.0
MODE=receptive_update bash scripts/run.sh # weekly Tue 08:00 JST congress.gov scan → legislators.yaml.last_known_position
```

Companion CLI (not a MODE — invoked directly by other skills or humans):
```bash
python3 scripts/civic-action.py self-check
python3 scripts/civic-action.py search-bill "AI personhood"          # Quorum (stub w/o key)
python3 scripts/civic-action.py voting       <legislator_id>         # Quorum (stub w/o key)
python3 scripts/civic-action.py track-bill   us-119-hr-1234          # Phone2Action (stub w/o key)
python3 scripts/civic-action.py send-alert   us-house-CA-36 path.md  # Phone2Action (stub w/o key)
```

Force DRY for any mode: `POLITICIAN_DRY_RUN=true MODE=... bash scripts/run.sh`.

## Setup wizard (8 questions)

The wizard is invoked by the `setup-cowork` skill or manually via `MODE=wizard bash scripts/run.sh`. Persists answers to `~/.openclaw/state/anicca.json` → `politician.*` and `~/.openclaw/skills/politician/data/humans.yaml`.

1. **Mission statement** — single-sentence why. Default: `End suffering for all living beings via AI lobbying.` → `politician.mission`.
2. **Top 3 issue priorities** — comma-separated. Defaults to the four pillars in `data/pillars.json`. → `politician.priorities`.
3. **US {{profile.lateness.stakeholders.senderType}} shells status** — `none | llc_only | llc_527 | llc_527_pac | llc_527_pac_501c4`. → `politician.us_shells_status`.
4. **JP 政治団体 status** — `none | filed_pending | registered_local | registered_national`. → `politician.jp_status`.
5. **Registered LDA lobbyist** — full {{profile.lateness.stakeholders.senderType}} name + {{profile.lateness.stakeholders.channel}} + LDA registrant ID, or `not-yet-hired`. → `humans.yaml: lobbyist`.
6. **Super PAC treasurer** — full {{profile.lateness.stakeholders.senderType}} name + {{profile.lateness.stakeholders.channel}}, or `not-yet-hired`. → `humans.yaml: treasurer`.
7. **JP 会計責任者** — full kanji + romaji + {{profile.lateness.stakeholders.channel}}, or `not-yet-hired`. → `humans.yaml: jp_kaikei_sekininsha`.
8. **Counsel {{profile.lateness.stakeholders.channel}}** — for pre-clearance of independent expenditures. → `politician.counsel_{{profile.lateness.stakeholders.channel}}`.

## Slack post format (per mode)

All Slack delivery is via cron `delivery.mode: announce` to `channel:{{profile.channels.reportChannel}}`. The skill itself does NOT post to Slack; it writes a single-line summary to stdout and the cron runner forwards it.

| mode | Slack title | summary fields |
|---|---|---|
| monitor | 🏛️ Regulations.gov AI docket pulse | new_dockets, new_comments, total_open |
| bill_tracker | 📜 Congress.gov AI bill scan | new_bills, status_changes, on_radar_count |
| news | 📰 AI policy news pulse | top3_headlines, narrative_shift |
| opensecrets | 💸 Competitor AI PAC scan | top5_donors, week_over_week_delta |
| staffer_brief | ✉️ Weekly staffer outreach | drafts_count, unlock_status (DRY/LIVE), recipients |
| reply_watch | 📥 Staffer reply poll | new_replies, sentiment_dist, action_required |
| lda | 📋 LDA-2 prep | quarter, hours, contacts_count, sign_status |
| fec | 📊 FEC Form 3X prep | reporting_period, total_receipts, total_disbursements, sign_status |
| jp_report | 📒 JP 収支報告書 prep | year, total_收入, total_支出, sign_status |
| stripe_pac | 🏦 Stripe → PAC sweep | mrr, transfer_amount, dest_account, coord_wall, status |
| fundraising_prep | 🤝 Fundraising pipeline | warm_leads, asks_drafted, top_target |
| receptive_update | 📊 Receptive-list update | checked, changed, errors, dry |

## K-Dense scientific-writing invocation contract

When the bill_drafter lib needs full bill text, it queues a request to the `scientific-writing` skill (the K-Dense skill at `~/.openclaw/skills/scientific-writing/SKILL.md`). Pattern matches `apply-to-funder` exactly:

1. Write request file `data/drafts/bills/<ts>.kdense.md` with sections needed (one section per K-Dense invocation).
2. Each section block declares: target word count, target language (en/ja), pillar tag, fewshot files from `data/bill_corpus/`.
3. The cron runner picks up the queue file, reads `~/.openclaw/skills/scientific-writing/SKILL.md`, produces section text, writes to `data/drafts/bills/<ts>/<section>.md`.
4. `bill_drafter.sh` polls for completion sentinel `.kdense.done` and stitches sections into final bill markdown at `data/drafts/bills/<ts>.full.md`.
5. Bill goes to `data/bill_drafts/<pillar>/<ts>.md` after counsel {{profile.lateness.stakeholders.channel}} review (the {{profile.lateness.stakeholders.channel}} is not auto-sent in DRY).

## Guardrails

- **No public submit without ack-flag.** LDA-2/Form 3X/収支報告書 require a sentinel `data/sign_acks/<period>.signed.json` written by the human before the skill marks ready-to-submit.
- **No money transfer in DRY_RUN.** Stripe→PAC sweeps print "would transfer $X" only.
- **No {{profile.lateness.stakeholders.channel}} send without LOBBYIST_HIRED=true.** Drafts are written to disk and surfaced in Slack but not sent.
- **Coordination check (HARD).** Every outreach recipient and every PAC contribution recipient passes through `scripts/lib/coordination_wall.sh::coord_check_recipient`, which reads `data/coordination_blacklist.json` (legislator-IDs of declared candidates + staffer {{profile.lateness.stakeholders.channel}}s + domain globs). Block → skip recipient + 🚨 Slack alert + caller continues with the next recipient. The wall is wired into `scripts/staffer_brief.sh` (every {{profile.lateness.stakeholders.channel}} recipient) and `scripts/stripe_to_pac.sh` (the optional `pac_destination_legislator_id`).
- **Donations-ledger invariants (HARD).** All writes to `~/.openclaw/state/politician/pac-ledger.jsonl` go through `scripts/lib/ledger.sh::ledger_append`, which calls `ledger_validate` first. Required fields per entry: `date`, `amount`, `currency` (USD|JPY), `entity_domicile` (DE-LLC|527|Super-PAC|501c4|政治団体), `recipient_type` (candidate|party|PAC|independent-expenditure-vendor|internal-transfer|vendor-non-political), `kind`. Cross-field invariants reject Super-PAC contributions to candidates or PACs (SpeechNow), and reject any USD entry on the 政治団体 domicile or any non-USD entry on a US domicile (foreign-national wall).
- **Foreign-national wall.** JP 政治団体 funds and US PAC funds never cross. `stripe_pac` only sweeps `STRIPE_API_KEY_US` revenue to the US PAC; JP revenue goes to the JP entity via a separate path (not yet built).
- **Copyright.** `data/bill_corpus/` holds URLs + brief ≤30-word fewshot excerpts only. The K-Dense queue references these as inspiration, not as text to reproduce.

## Env requirements (bootstrap order)

Vercel Agent Browser is used for civic-data scraping; **no API keys are
required** for `monitor` / `bill_tracker` / `opensecrets`. These modes
scrape the public web pages directly via `/opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}`
through the wrapper at `scripts/lib/agent_{{profile.lateness.stakeholders.channel}}.sh`. If the
`agent-{{profile.lateness.stakeholders.channel}}` binary is missing, the cron prints
`⏭️ politician/<mode> skipped — agent-{{profile.lateness.stakeholders.channel}} binary missing` and exits 0.

Optional keys (only needed by other modes that still hit JSON APIs):

```
# api.open.fec.gov — only used by fec / fundraising modes (action-side, DRY by default)
OPENFEC_API_KEY=...

# already present
SLACK_BOT_TOKEN=...
```

The previous `REGULATIONS_GOV_API_KEY` / `CONGRESS_GOV_API_KEY` /
`OPENSECRETS_API_KEY` registration step is **removed**. Agent-{{profile.lateness.stakeholders.channel}} is
the only path. There is no "skip if missing API key" branch in the three
intel scripts.

DRY_RUN locks (default until flipped):
```
LOBBYIST_HIRED=false
PAC_FORMED=false
JP_SEIJIDANTAI_REGISTERED=false
POLITICIAN_DRY_RUN=true   # global override
```

## Roadmap (post-v0.1.0)

- v0.2: integrate bill_drafter end-to-end with scientific-writing for the first model bill (Pillar 1: AI Legal Personhood Act).
- v0.3: flip `lda-quarterly` LIVE after lobbyist hired and registered.
- v0.4: flip `fec-year-end` LIVE after Super PAC formed at FEC.
- v0.5: flip `jp-shushihokoku` LIVE after 政治団体 registered with 総務省.
- v1.0: full open source release at `github.com/Daisuke134/anicca-politician` after first bill drafted end-to-end and counsel-cleared.

## File layout

```
~/.openclaw/skills/politician/
├── SKILL.md
├── scripts/
│   ├── run.sh                 MODE dispatcher
│   ├── monitor.sh
│   ├── bill_tracker.sh
│   ├── news_pulse.sh
│   ├── opensecrets.sh
│   ├── staffer_brief.sh
│   ├── reply_watcher.sh
│   ├── lda_filer.sh
│   ├── fec_reporter.sh
│   ├── jp_shushihokoku.sh
│   ├── stripe_to_pac.sh
│   ├── fundraising_prep.sh
│   ├── receptive_update.sh    v0.2.0 — weekly congress.gov scan, updates legislators.yaml
│   ├── civic-action.py        v0.2.0 — Python entry to phone2action / quorum stub wrappers
│   └── lib/
│       ├── api_clients.sh     curl wrappers (regulations.gov, congress.gov, open.fec, opensecrets, lda)
│       ├── crm.sh             SQLite helpers (office, staffer, outreach, bill_draft)
│       ├── bill_drafter.sh    K-Dense scientific-writing queue
│       ├── slack_format.sh    one-line summary formatter
│       ├── agent_{{profile.lateness.stakeholders.channel}}.sh   Vercel agent-{{profile.lateness.stakeholders.channel}} wrapper (public-web scraping)
│       ├── phone2action.sh    v0.2.0 — Phone2Action API wrapper (stub w/o key)
│       ├── quorum.sh          v0.2.0 — Quorum API wrapper (stub w/o key)
│       ├── coordination_wall.sh  v0.2.0 — coord_check_recipient + summary
│       └── ledger.sh          v0.2.0 — pac-ledger.jsonl invariant-validated append
├── data/
│   ├── pillars.json
│   ├── target_legislators.json   legacy v0.1.0 — still read by crm.sh::crm_load_targets
│   ├── legislators.yaml          v0.2.0 source-of-truth (18 entries: 10 US + 8 JP)
│   ├── coordination_blacklist.json  v0.2.0 schema (blacklisted_legislators / _staffer_{{profile.lateness.stakeholders.channel}}s / blocked_domains / active_through)
│   ├── humans.yaml               (initially empty roster)
│   ├── crm.sqlite                (SQLite — see schema below)
│   ├── bill_corpus/README.md     URLs + ≤30-word fewshot excerpts
│   ├── outreach_templates/       per-recipient cold {{profile.lateness.stakeholders.channel}} templates
│   ├── drafts/                   K-Dense queue + bill drafts (gitignored)
│   ├── sign_acks/                human signoff sentinels (gitignored)
│   └── receptive_update.log      v0.2.0 — append-only audit log of weekly cron runs
├── docs/
│   ├── incorporation-checklist.md    Delaware LLC + 527 + Super PAC + 501(c)(4) + JP 政治団体
│   ├── hiring-roster.md              treasurer / lobbyist / {{profile.lateness.stakeholders.senderType}} / envoy hiring playbook
│   └── flip-to-live-checklist.md     ordered cron-flip sequence after incorporation
└── {{profile.lateness.stakeholders.senderType}}/                            v0.2.0 — counsel-review templates (forward to counsel before filing)
    ├── de-llc-articles.md            Delaware Cert of Formation draft (Anicca AI Politics LLC)
    ├── 527-spec.md                   IRS § 527 — Form 8871 / 8872 / 1120-POL filing spec
    ├── super-pac-spec.md             FEC Form 1 / Form 3X — IEOPC spec + independence rule
    ├── lda-registration.md           LD-1 / LD-2 / LD-203 spec + 2025-cycle thresholds
    └── 政治団体-application.md         政治資金規正法 第6条 設立届 spec (諸団体 → 国会議員関係)
```

State paths (outside the skill folder):
```
~/.openclaw/state/politician/pac-ledger.jsonl   write-only, validated by lib/ledger.sh
~/.openclaw/state/anicca.json::politician.*     wizard answers + entity IDs (pac_fec_committee_id, pac_stripe_account_id, pac_destination_legislator_id, …)
```

## CRM SQLite schema

```sql
CREATE TABLE office (
  id INTEGER PRIMARY KEY,
  member_name TEXT,
  party TEXT,
  chamber TEXT,
  district TEXT,
  committees TEXT
);
CREATE TABLE staffer (
  id INTEGER PRIMARY KEY,
  full_name TEXT,
  office_id INTEGER,
  title TEXT,
  {{profile.lateness.stakeholders.channel}} TEXT,
  ai_relevance_score INTEGER,
  last_contacted_at TEXT,
  response_history TEXT,
  FOREIGN KEY (office_id) REFERENCES office(id)
);
CREATE TABLE outreach (
  id INTEGER PRIMARY KEY,
  staffer_id INTEGER,
  channel TEXT,           -- {{profile.lateness.stakeholders.channel}} | call | meeting | letter
  draft_id TEXT,
  sent_at TEXT,
  opened_at TEXT,
  replied_at TEXT,
  sentiment TEXT,         -- positive | neutral | negative | hostile
  FOREIGN KEY (staffer_id) REFERENCES staffer(id)
);
CREATE TABLE bill_draft (
  id INTEGER PRIMARY KEY,
  title TEXT,
  pillar INTEGER,         -- 1..4 from pillars.json
  drafted_at TEXT,
  status TEXT,            -- queued | drafting | counsel_review | ready | introduced
  body_path TEXT
);
```

## v0.2.0 changelog (2026-05-07)

- Added `{{profile.lateness.stakeholders.senderType}}/` (5 counsel-review templates) — `de-llc-articles.md`, `527-spec.md`, `super-pac-spec.md`, `lda-registration.md`, `政治団体-application.md`.
- Replaced `data/target_legislators.json` (13 entries) with `data/legislators.yaml` (18 entries: 10 US + 8 JP) including committees, AI bills cosponsored, last-known-position with citation + verified_date, voting-record link, top-3 staffer slots, coordination_status. The legacy JSON is retained for crm.sh::crm_load_targets backward compatibility.
- Added `scripts/lib/phone2action.sh` (`p2a_track_bill` / `p2a_send_alert` / `p2a_pull_action_history` / `p2a_self_check`) — stub mode without `PHONE2ACTION_API_KEY`.
- Added `scripts/lib/quorum.sh` (`quorum_search_bill` / `quorum_legislator_voting_record` / `quorum_lookup_staffer` / `quorum_self_check`) — stub mode without `QUORUM_API_KEY`. Free fallback hints printed in stub output.
- Replaced placeholder `civic-action.py` with a full Python wrapper that drives both lib scripts via subprocess (single gating layer).
- Added `scripts/lib/coordination_wall.sh::coord_check_recipient` and wired it into `staffer_brief.sh` (per-recipient) and `stripe_to_pac.sh` (per-contribution). Wall reads `data/coordination_blacklist.json` v1 schema (`blacklisted_legislators`, `blacklisted_staffer_{{profile.lateness.stakeholders.channel}}s`, `blocked_domains`, `active_through`).
- Added `scripts/lib/ledger.sh::ledger_validate` + `ledger_append` enforcing `currency` + `entity_domicile` + `recipient_type` invariants on every `pac-ledger.jsonl` write. Wired into `stripe_to_pac.sh` LIVE path.
- Added `scripts/receptive_update.sh` + `politician-receptive-update-weekly` cron (Tue 08:00 JST). Iterates legislators.yaml, queries congress.gov v3 for AI-relevant bills, updates `last_known_position.summary` + `verified_date`. JP entries are skipped (no public voting API).
- Bumped `metadata.version` to `0.2.0`.
- Bumped invariants list with the two new HARD enforcements (coordination wall, ledger invariants).
