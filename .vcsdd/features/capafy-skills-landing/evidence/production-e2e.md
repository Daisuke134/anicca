# Production E2E Evidence — capafy-skills-landing

## Live data and generator

| Check | Observed |
|---|---|
| `GET /agent/agents` | HTTP command exit 0; 26 total; 21 `agentStatus=online` |
| generator stdout | `{"ok": true, "online_skills": 21, ...}` |
| generated cards | 21 |
| generated `capafy.ai/agent` links | 21 |
| generated scripts | 0 |
| idempotence | MD5 `011a3615ea20d91532cffdb137f116dc` on both consecutive builds |
| unit tests | 6 PASS |
| shell syntax | `bash -n capafy-ig-marketing-daily.sh` PASS |

## Netlify

| Check | Observed |
|---|---|
| CLI | `netlify-cli/24.0.1` |
| auth | Daisuke Narita / Daisuke134’s team |
| dedicated site ID | `41c8e52e-b163-442a-84ff-fd866269bf6c` |
| production URL | `https://capafy-skills-daily.netlify.app` |
| redeploy ID | `6a5b9adaefb7a9c5200a38dc` |
| curl | HTTP 200; 21 `capafy.ai/agent` links; title present |

Netlify CLI inherited an unrelated linked project on the first create attempt and sent one deploy to `anicca-invoice-gen-1781219208`. That project had zero previous deploys. `deleteSiteDeploy` returned 405 and rollback had no prior deploy. Recovery used a 404-only production deploy; root now returns HTTP 404. Dedicated site creation then used `--account-slug daisuke134 --disable-linking`; every landing deploy now pins `--site 41c8e52e-b163-442a-84ff-fd866269bf6c`.

## Real browser

| View | Observed |
|---|---|
| mobile light 390x844 | title/header/tagline present; 21 cards; 21 links; footer `21 skills available`; scrollWidth=clientWidth=390 |
| mobile dark 390x844 | `prefers-color-scheme: dark` true; body `rgb(16, 18, 15)`; card `rgba(27, 30, 25, 0.82)`; 21 cards; no horizontal overflow |
| desktop light 1440x900 | 21 cards; 21 links; two-column card internals; no horizontal overflow |

Screenshots: `mobile-light.png`, `mobile-dark.png`, `desktop-light.png` in this evidence directory. Visual inspection confirms readable hierarchy, consistent card spacing, visible CTA contrast, and footer completion.
