---
name: {{profile.lateness.stakeholders.channel}}-harness
description: Connect to a real Chrome/Chromium {{profile.lateness.stakeholders.channel}} (the user's own profile with all logins/cookies/extensions, OR an isolated Chrome). Python helpers for navigation, form fill, screenshot, scrape. Best for tasks needing user's existing logged-in sessions (Stripe Dashboard, GitHub, Twitter, Connpass, Stripe Connect onboarding behind 2FA). Use when agent-{{profile.lateness.stakeholders.channel}}'s fresh Chrome-for-Testing isn't enough because login/cookies are required.
metadata:
  tags: {{profile.lateness.stakeholders.channel}}, automation, real-chrome, cdp, login, cookies, scrape
  requires:
    bins: [{{profile.lateness.stakeholders.channel}}-harness, python3]
    env: [BU_CDP_URL]
---

# {{profile.lateness.stakeholders.channel}}-harness

`/Users/anicca/.local/bin/{{profile.lateness.stakeholders.channel}}-harness` — installed 2026-05-05 from `~/Developer/{{profile.lateness.stakeholders.channel}}-harness/` (uv tool install -e .). Repo: https://github.com/{{profile.lateness.stakeholders.channel}}-use/{{profile.lateness.stakeholders.channel}}-harness

## Modes

| Mode | When to use |
|------|----------|
| **Way 1: chrome://inspect** | Use Dais's real Chrome with all logins. Requires one-time tick at `chrome://inspect/#remote-debugging` + per-attach "Allow" popup click. Best for tasks behind 2FA/SSO. NOT cron-friendly |
| **Way 2: isolated Chrome** (cron-friendly) | Spawn fresh Chrome on port 9223 with `--user-data-dir=~/.{{profile.lateness.stakeholders.channel}}-harness-profile`. No popups. Persistent profile (cookies stick across runs). Set `BU_CDP_URL=http://127.0.0.1:9223` |
| **Way 3: cloud {{profile.lateness.stakeholders.channel}}** | Browser Use cloud (managed). Need `BROWSER_USE_API_KEY` |

## Way 2 setup (currently active, recommended for cron)

```bash
# Launch isolated Chrome on 9223 (one-time, then keeps running)
nohup '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  --remote-debugging-port=9223 \
  --user-data-dir="$HOME/.{{profile.lateness.stakeholders.channel}}-harness-profile" \
  --no-first-run --no-default-{{profile.lateness.stakeholders.channel}}-check \
  > /tmp/chrome-9223.log 2>&1 &

# Then any {{profile.lateness.stakeholders.channel}}-harness call works:
BU_CDP_URL=http://127.0.0.1:9223 {{profile.lateness.stakeholders.channel}}-harness -c 'goto_url("https://aniccaai.com"); print(page_info())'
```

## Real helpers (from `src/{{profile.lateness.stakeholders.channel}}_harness/helpers.py`)

| Function | Use |
|---------|----|
| `goto_url(url)` | navigate |
| `page_info()` | url + title + viewport |
| `cdp(method, **params)` | direct CDP call |
| `fill_input(selector, text)` | fill form field |
| `click_at_xy(x, y)` | click coords |
| `type_text(text)` | type into focused element |
| `press_key(key)` | Enter, Tab, Escape, etc |
| `capture_screenshot(path, full=False)` | screenshot |
| `list_tabs()` / `switch_tab(target)` / `new_tab(url)` | tab mgmt |
| `wait_for_element(selector)` / `wait_for_load()` / `wait_for_network_idle()` | sync |
| `iframe_target(url_substr)` | enter iframe |

## Verified working (2026-05-05 by Claude)

| Test | Result |
|-----|------|
| `goto_url("https://aniccaai.com")` → `page_info()` | ✅ url+title+viewport returned |
| `goto_url("https://aniccaai.com/income")` + `fill_input("input[type={{profile.lateness.stakeholders.channel}}]", "x@y")` + `fill_input("textarea", "...")` | ✅ form filled |
| Way 2 isolated Chrome on 9223 | ✅ daemon stable, no popups |

## When to use vs agent-{{profile.lateness.stakeholders.channel}}

| 状況 | {{profile.lateness.stakeholders.channel}}-harness | agent-{{profile.lateness.stakeholders.channel}} |
|-----|---------------|--------------|
| Stripe Dashboard (login+2FA) | ✅ Way 1 で Dais's real session | ❌ fresh login each time |
| GitHub starring repo | ✅ Way 1 (logged in) | △ login required |
| Tokyo Comedy Bar form (no login) | △ どっちも OK | ✅ refs simpler |
| Long-running scraping cron | ✅ Way 2 persistent profile | ✅ both work |
| Quick snapshot + click by ref | △ no built-in `@eN` refs | ✅ accessibility tree refs |
| iframe handling | ✅ `iframe_target()` | △ less ergonomic |
| Multi-tab workflows | ✅ explicit `new_tab` / `switch_tab` | △ session model |
| Stripe Connect onboarding (KYC) | ⚠ hCaptcha blocks both | ⚠ same |
| AI agent "look + decide" loop | △ raw HTML | ✅ refs in 200-400 tokens |

## Workflow recommendation

| 用途 | 推奨 |
|-----|----|
| **cron (24/7)** | Way 2 isolated Chrome. Profile cookies persistent. No popups |
| **interactive Dais 操作** | Way 1 real Chrome. Stripe / GitHub / Twitter all already logged in |
| **AI agent decision loop** | agent-{{profile.lateness.stakeholders.channel}} (refs cheaper for LLM context) |
| **form fill + screenshot pipeline** | {{profile.lateness.stakeholders.channel}}-harness (Python helpers more ergonomic) |

## Anicca cron 利用例

```bash
# Cron skill calling {{profile.lateness.stakeholders.channel}}-harness
#!/bin/bash
export BU_CDP_URL=http://127.0.0.1:9223
{{profile.lateness.stakeholders.channel}}-harness -c "
goto_url('https://www.tokyocomedybar.com/open-mic-sign-up')
fill_input('input[name=name]', 'Dais Narita')
fill_input('input[type={{profile.lateness.stakeholders.channel}}]', '{{profile.contact.personalEmail}}')
click_at_xy(600, 800)
"
```
