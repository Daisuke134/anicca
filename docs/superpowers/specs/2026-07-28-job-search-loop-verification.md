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
cd /path/to/life-manager/apps/job-search-loop
python3 -m unittest discover -s tests -v
zsh -n scripts/run-daily.sh scripts/run-inbox.sh scripts/healthcheck.sh
plutil -lint launchd/*.plist
zsh scripts/healthcheck.sh
```

The healthcheck verifies both installed schedulers, SQLite
`PRAGMA integrity_check`, private file permissions, application state counts, and
fresh daily/inbox evidence.

## `JOB-CANONICAL-MERGE-1` verification

| Check | Current evidence |
|---|---|
| Legacy behavior baseline | 107 tests pass in 4.916 seconds from legacy commit `d86adf4d5f1422b28f6675ac7ffa08f3b9c7e987` |
| Canonical job runtime | 112 tests pass in 3.273 seconds |
| Canonical model runner | 7 tests pass in 0.465 seconds |
| Path behavior | Temporary XDG roots and launchd destination resolve only inside the Life Manager checkout |
| Private env behavior | The loader reads only the requested key and does not execute unrelated dotenv lines |
| Runner configuration | Four job-loop task classes; no personal account, absolute user path, candidate profile, or gig route |
| Legacy source scan | No legacy checkout or private Gmail path in `apps/job-search-loop` or `runtime/agent-runner` |
| Live cutover | Pending canonical commit and shadow healthcheck |
