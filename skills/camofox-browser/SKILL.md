---
name: camofox-browser
description: Stealth Firefox browser server for agent-driven Google OAuth and bot-protected sites. REST API on :9377. Use whenever a target site rejects agent-browser/playwright due to fingerprint detection (Google login, reCAPTCHA, Cloudflare). Wraps Camoufox (Firefox fork with C++-level fingerprint spoofing). Required for Anicca to login to Printful, Stripe Connect, Slack admin, Shopify, etc. via Google OAuth without human input after first 2FA. Cookie/storage persistence per (userId, sessionKey).
metadata:
  tags: browser, automation, stealth, google-oauth, bot-bypass, camoufox, firefox
  requires:
    bins: [bash, curl, jq, node, npm, python3]
    env: []
---

# camofox-browser

Stealth browser server. **Use this for any login/OAuth flow that fails on agent-browser** (Chrome for Testing fingerprint detected by Google).

Repo: https://github.com/jo-inc/camofox-browser
Source: `~/Developer/camofox-browser/`
Server: `:9377`
Profile dir: `~/.camofox/profiles/<userId>/<sessionKey>/`
Logs: `/tmp/camofox.log`

## Start (lazy, idempotent)

```bash
bash $LIFE_MANAGER_REPO/skills/camofox-browser/scripts/start.sh
# starts only if not running, prints health, exits
```

## Stop

```bash
bash $LIFE_MANAGER_REPO/skills/camofox-browser/scripts/stop.sh
```

## Standard call pattern

Every call needs `userId` + `sessionKey` (cookie/storage isolation per logical user).

```bash
# Default: userId=anicca, sessionKey=default. Override per skill if needed.
USER_ID="anicca"
SESSION_KEY="default"

# 1. Open tab (creates camofox tab, navigates URL)
TAB_ID=$(curl -sS -X POST http://localhost:9377/tabs \
  -H 'Content-Type: application/json' \
  -d "{\"url\":\"https://example.com\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" \
  | jq -r .tabId)

# 2. Snapshot (accessibility tree with @e1..@eN refs)
curl -sS "http://localhost:9377/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY"

# 3. Click element by ref
curl -sS -X POST "http://localhost:9377/tabs/$TAB_ID/click" \
  -H 'Content-Type: application/json' \
  -d "{\"ref\":\"e2\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}"

# 4. Type into element
curl -sS -X POST "http://localhost:9377/tabs/$TAB_ID/type" \
  -H 'Content-Type: application/json' \
  -d "{\"ref\":\"e1\",\"text\":\"$BROWSER_LOGIN_EMAIL\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}"

# 5. Press key (Enter, Tab, etc.)
curl -sS -X POST "http://localhost:9377/tabs/$TAB_ID/press" \
  -H 'Content-Type: application/json' \
  -d "{\"key\":\"Enter\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}"

# 6. Screenshot
curl -sS "http://localhost:9377/tabs/$TAB_ID/screenshot?userId=$USER_ID&sessionKey=$SESSION_KEY" \
  -o /tmp/snap.png

# 7. Close tab
curl -sS -X DELETE "http://localhost:9377/tabs/$TAB_ID?userId=$USER_ID&sessionKey=$SESSION_KEY"
```

Use `bash $LIFE_MANAGER_REPO/skills/camofox-browser/scripts/cf.sh` as a thin wrapper (loads `userId`/`sessionKey`, sets `TAB_ID` env).

## Google OAuth login pattern (verified 2026-05-08)

```
1. Navigate https://accounts.google.com/signin/v2/identifier?... → email field
2. Type email → click Next → Google may ask for passkey
3. Click "Try another way" → "Enter your password"
4. Type the password from the user's secret store (never from this repository)
5. Google asks 2-step verification → click "Tap Yes on your phone or tablet"
6. The user completes any provider-required trusted-device prompt
7. Session lands at target site, cookie persists in ~/.camofox/profiles/<userId>/<sessionKey>/
8. Future runs reuse cookie — no human re-auth needed
```

## When to NOT use camofox

- Site has API + token: use API (Stripe, Printful, Resend, GitHub, Postiz, Slack via Composio MCP)
- Site has no bot detection: use agent-browser (Tokyo Comedy Bar, Uber Eats Manager scrape, kashispace)
- Need Google services (Gmail/Calendar/Drive): use `gog` CLI

## Endpoints

| Endpoint | Use |
|----|----|
| `POST /tabs` | open new tab + navigate (returns tabId) |
| `GET /tabs/{id}/snapshot` | accessibility tree with refs |
| `POST /tabs/{id}/navigate` | navigate same tab to new URL |
| `POST /tabs/{id}/click` | click ref |
| `POST /tabs/{id}/type` | type into ref |
| `POST /tabs/{id}/press` | press key (Enter/Tab/...) |
| `GET /tabs/{id}/screenshot` | PNG bytes |
| `POST /tabs/{id}/scroll` | scroll |
| `GET /tabs/{id}/extract` | structured JSON via JSON Schema + x-ref |
| `GET /sessions/{userId}/cookies` | export Netscape cookies for session |
| `POST /sessions/{userId}/cookies` | import cookies |
| `GET /tabs?userId&sessionKey` | list tabs |
| `DELETE /tabs/{id}?userId&sessionKey` | close tab |

Full OpenAPI: http://localhost:9377/openapi.json
Interactive: http://localhost:9377/docs

## Reporting

Report final external output (Stripe charge id / Printful order id / etc.), not "I navigated to X". Internal Slack reports OK as secondary, but never primary.
