# Job Search Loop — Live Verification

## Outcome

The loop reaches its daily target with two real, employer-confirmed applications and
retains independent browser, ledger, email, and Telegram evidence. The launchd
deployment runs the daily pass at 08:30 JST and polls Gmail every 15 minutes without
starting a model on empty inbox passes.

| Role | Employer | Confirmation |
|---|---|---|
| AI/LLM Division Research Engineer (R&D) | LayerX | Talentio returned success and LayerX sent an entry receipt |
| 生成AIエンジニア | エクスチュア株式会社 | HRMOS displayed its completion page and sent an application receipt |

Private application IDs, contact data, form payloads, and screenshots stay under
`~/.local/state/anicca/job-search/` and are not committed.

## Grounded claims and role evidence

| Source | URL | Evidence used |
|---|---|---|
| Salesforce Japan / MUFG announcement | https://www.salesforce.com/jp/news/press-releases/2026/03/25/mufg-customer-news-3/ | “2025年8月に日本で初めて同ソリューションを選定” supports the institution-level first-deployment claim; the resume says Daisuke contributed and does not claim sole ownership |
| Daisuke Narita — ICLR 2026 report | https://www.youtube.com/watch?v=biHAQ6aSQuc | Public presentation link included in the resume |
| LayerX official opening | https://open.talentio.com/r/1/c/layerx/pages/112891 | Role scope, working arrangement, and compensation |
| Ex-ture official opening | https://hrmos.co/pages/ex-ture/jobs/2195115868180295680 | Role scope, Tokyo arrangement, and JPY 5.5M–11M compensation |

## Verification commands

```bash
cd /Users/anicca/anicca-job-search-loop/apps/job-search-loop
python3 -m unittest discover -s tests -v
zsh -n scripts/run-daily.sh scripts/run-inbox.sh scripts/healthcheck.sh
plutil -lint launchd/*.plist
zsh scripts/healthcheck.sh
```

The healthcheck verifies both installed schedulers, SQLite
`PRAGMA integrity_check`, private file permissions, application state counts, and
fresh daily/inbox evidence.
