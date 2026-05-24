---
name: core
description: Core agent-{{profile.lateness.stakeholders.channel}} usage guide. Read this before running any agent-{{profile.lateness.stakeholders.channel}} commands. Covers the snapshot-and-ref workflow, navigating pages, interacting with elements (click, fill, type, select), extracting text and data, taking screenshots, managing tabs, handling forms and auth, waiting for content, running multiple {{profile.lateness.stakeholders.channel}} sessions in parallel, and troubleshooting common failures. Use when the user asks to interact with a website, fill a form, click something, extract data, take a screenshot, log into a site, test a web app, or automate any {{profile.lateness.stakeholders.channel}} task.
allowed-tools: Bash(agent-{{profile.lateness.stakeholders.channel}}:*), Bash(npx agent-{{profile.lateness.stakeholders.channel}}:*)
---

# agent-{{profile.lateness.stakeholders.channel}} core

Fast {{profile.lateness.stakeholders.channel}} automation CLI for AI agents. Chrome/Chromium via CDP, no
Playwright or Puppeteer dependency. Accessibility-tree snapshots with compact
`@eN` refs let agents interact with pages in ~200-400 tokens instead of
parsing raw HTML.

Most normal web tasks (navigate, read, click, fill, extract, screenshot) are
covered here. Load a specialized skill when the task falls outside {{profile.lateness.stakeholders.channel}}
web pages — see [When to load another skill](#when-to-load-another-skill).

## The core loop

```bash
agent-{{profile.lateness.stakeholders.channel}} open <url>        # 1. Open a page
agent-{{profile.lateness.stakeholders.channel}} snapshot -i       # 2. See what's on it (interactive elements only)
agent-{{profile.lateness.stakeholders.channel}} click @e3         # 3. Act on refs from the snapshot
agent-{{profile.lateness.stakeholders.channel}} snapshot -i       # 4. Re-snapshot after any page change
```

Refs (`@e1`, `@e2`, ...) are assigned fresh on every snapshot. They become
**stale the moment the page changes** — after clicks that navigate, form
submits, dynamic re-renders, dialog opens. Always re-snapshot before your
next ref interaction.

## Quickstart

```bash
# Install once
npm i -g agent-{{profile.lateness.stakeholders.channel}} && agent-{{profile.lateness.stakeholders.channel}} install

# Take a screenshot of a page
agent-{{profile.lateness.stakeholders.channel}} open https://example.com
agent-{{profile.lateness.stakeholders.channel}} screenshot home.png
agent-{{profile.lateness.stakeholders.channel}} close

# Search, click a result, and capture it
agent-{{profile.lateness.stakeholders.channel}} open https://duckduckgo.com
agent-{{profile.lateness.stakeholders.channel}} snapshot -i                      # find the search box ref
agent-{{profile.lateness.stakeholders.channel}} fill @e1 "agent-{{profile.lateness.stakeholders.channel}} cli"
agent-{{profile.lateness.stakeholders.channel}} press Enter
agent-{{profile.lateness.stakeholders.channel}} wait --load networkidle
agent-{{profile.lateness.stakeholders.channel}} snapshot -i                      # refs now reflect results
agent-{{profile.lateness.stakeholders.channel}} click @e5                        # click a result
agent-{{profile.lateness.stakeholders.channel}} screenshot result.png
```

The {{profile.lateness.stakeholders.channel}} stays running across commands so these feel like a single
session. Use `agent-{{profile.lateness.stakeholders.channel}} close` (or `close --all`) when you're done.

## Reading a page

```bash
agent-{{profile.lateness.stakeholders.channel}} snapshot                    # full tree (verbose)
agent-{{profile.lateness.stakeholders.channel}} snapshot -i                 # interactive elements only (preferred)
agent-{{profile.lateness.stakeholders.channel}} snapshot -i -u              # include href urls on links
agent-{{profile.lateness.stakeholders.channel}} snapshot -i -c              # compact (no empty structural nodes)
agent-{{profile.lateness.stakeholders.channel}} snapshot -i -d 3            # cap depth at 3 levels
agent-{{profile.lateness.stakeholders.channel}} snapshot -s "#main"         # scope to a CSS selector
agent-{{profile.lateness.stakeholders.channel}} snapshot -i --json          # machine-readable output
```

Snapshot output looks like:

```
Page: Example - Log in
URL: https://example.com/login

@e1 [heading] "Log in"
@e2 [form]
  @e3 [input type="{{profile.lateness.stakeholders.channel}}"] placeholder="Email"
  @e4 [input type="password"] placeholder="Password"
  @e5 [button type="submit"] "Continue"
  @e6 [link] "Forgot password?"
```

For unstructured reading (no refs needed):

```bash
agent-{{profile.lateness.stakeholders.channel}} get text @e1                # visible text of an element
agent-{{profile.lateness.stakeholders.channel}} get html @e1                # innerHTML
agent-{{profile.lateness.stakeholders.channel}} get attr @e1 href           # any attribute
agent-{{profile.lateness.stakeholders.channel}} get value @e1               # input value
agent-{{profile.lateness.stakeholders.channel}} get title                   # page title
agent-{{profile.lateness.stakeholders.channel}} get url                     # current URL
agent-{{profile.lateness.stakeholders.channel}} get count ".item"           # count matching elements
```

## Interacting

```bash
agent-{{profile.lateness.stakeholders.channel}} click @e1                   # click
agent-{{profile.lateness.stakeholders.channel}} click @e1 --new-tab         # open link in new tab instead of navigating
agent-{{profile.lateness.stakeholders.channel}} dblclick @e1                # double-click
agent-{{profile.lateness.stakeholders.channel}} hover @e1                   # hover
agent-{{profile.lateness.stakeholders.channel}} focus @e1                   # focus (useful before keyboard input)
agent-{{profile.lateness.stakeholders.channel}} fill @e2 "hello"            # clear then type
agent-{{profile.lateness.stakeholders.channel}} type @e2 " world"           # type without clearing
agent-{{profile.lateness.stakeholders.channel}} press Enter                 # press a key at current focus
agent-{{profile.lateness.stakeholders.channel}} press Control+a             # key combination
agent-{{profile.lateness.stakeholders.channel}} check @e3                   # check checkbox
agent-{{profile.lateness.stakeholders.channel}} uncheck @e3                 # uncheck
agent-{{profile.lateness.stakeholders.channel}} select @e4 "option-value"   # select dropdown option
agent-{{profile.lateness.stakeholders.channel}} select @e4 "a" "b"          # select multiple
agent-{{profile.lateness.stakeholders.channel}} upload @e5 file1.pdf        # upload file(s)
agent-{{profile.lateness.stakeholders.channel}} scroll down 500             # scroll page (up/down/left/right)
agent-{{profile.lateness.stakeholders.channel}} scrollintoview @e1          # scroll element into view
agent-{{profile.lateness.stakeholders.channel}} drag @e1 @e2                # drag and drop
```

### When refs don't work or you don't want to snapshot

Use semantic locators:

```bash
agent-{{profile.lateness.stakeholders.channel}} find role button click --name "Submit"
agent-{{profile.lateness.stakeholders.channel}} find text "Sign In" click
agent-{{profile.lateness.stakeholders.channel}} find text "Sign In" click --exact     # exact match only
agent-{{profile.lateness.stakeholders.channel}} find label "Email" fill "user@test.com"
agent-{{profile.lateness.stakeholders.channel}} find placeholder "Search" type "query"
agent-{{profile.lateness.stakeholders.channel}} find testid "submit-btn" click
agent-{{profile.lateness.stakeholders.channel}} find first ".card" click
agent-{{profile.lateness.stakeholders.channel}} find nth 2 ".card" hover
```

Or a raw CSS selector:

```bash
agent-{{profile.lateness.stakeholders.channel}} click "#submit"
agent-{{profile.lateness.stakeholders.channel}} fill "input[name={{profile.lateness.stakeholders.channel}}]" "user@test.com"
agent-{{profile.lateness.stakeholders.channel}} click "button.primary"
```

Rule of thumb: snapshot + `@eN` refs are fastest and most reliable for
AI agents. `find role/text/label` is next best and doesn't require a prior
snapshot. Raw CSS is a fallback when the others fail.

## Waiting (read this)

Agents fail more often from bad waits than from bad selectors. Pick the
right wait for the situation:

```bash
agent-{{profile.lateness.stakeholders.channel}} wait @e1                     # until an element appears
agent-{{profile.lateness.stakeholders.channel}} wait 2000                    # dumb wait, milliseconds (last resort)
agent-{{profile.lateness.stakeholders.channel}} wait --text "Success"        # until the text appears on the page
agent-{{profile.lateness.stakeholders.channel}} wait --url "**/dashboard"    # until URL matches pattern (glob)
agent-{{profile.lateness.stakeholders.channel}} wait --load networkidle      # until network idle (post-navigation)
agent-{{profile.lateness.stakeholders.channel}} wait --load domcontentloaded # until DOMContentLoaded
agent-{{profile.lateness.stakeholders.channel}} wait --fn "window.myApp.ready === true"  # until JS condition
```

After any page-changing action, pick one:

- Wait for a specific element you expect to appear: `wait @ref` or `wait --text "..."`.
- Wait for URL change: `wait --url "**/new-page"`.
- Wait for network idle (catch-all for SPA navigation): `wait --load networkidle`.

Avoid bare `wait 2000` except when debugging — it makes scripts slow and
flaky. Timeouts default to 25 seconds.

## Common workflows

### Log in

```bash
agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com/login
agent-{{profile.lateness.stakeholders.channel}} snapshot -i

# Pick the {{profile.lateness.stakeholders.channel}}/password refs out of the snapshot, then:
agent-{{profile.lateness.stakeholders.channel}} fill @e3 "user@example.com"
agent-{{profile.lateness.stakeholders.channel}} fill @e4 "hunter2"
agent-{{profile.lateness.stakeholders.channel}} click @e5
agent-{{profile.lateness.stakeholders.channel}} wait --url "**/dashboard"
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
```

Credentials in shell history are a leak. For anything sensitive, use the
auth vault (see [references/authentication.md](references/authentication.md)):

```bash
agent-{{profile.lateness.stakeholders.channel}} auth save my-app --url https://app.example.com/login \
  --username user@example.com --password-stdin
# (type password, Ctrl+D)

agent-{{profile.lateness.stakeholders.channel}} auth login my-app    # fills + clicks, waits for form
```

### Persist session across runs

```bash
# Log in once, save cookies + localStorage
agent-{{profile.lateness.stakeholders.channel}} state save ./auth.json

# Later runs start already-logged-in
agent-{{profile.lateness.stakeholders.channel}} --state ./auth.json open https://app.example.com
```

Or use `--session-name` for auto-save/restore:

```bash
AGENT_BROWSER_SESSION_NAME=my-app agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com
# State is auto-saved and restored on subsequent runs with the same name.
```

### Extract data

```bash
# Structured snapshot (best for AI reasoning over page content)
agent-{{profile.lateness.stakeholders.channel}} snapshot -i --json > page.json

# Targeted extraction with refs
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
agent-{{profile.lateness.stakeholders.channel}} get text @e5
agent-{{profile.lateness.stakeholders.channel}} get attr @e10 href

# Arbitrary shape via JavaScript
cat <<'EOF' | agent-{{profile.lateness.stakeholders.channel}} eval --stdin
const rows = document.querySelectorAll("table tbody tr");
Array.from(rows).map(r => ({
  name: r.cells[0].innerText,
  price: r.cells[1].innerText,
}));
EOF
```

Prefer `eval --stdin` (heredoc) or `eval -b <base64>` for any JS with
quotes or special characters. Inline `agent-{{profile.lateness.stakeholders.channel}} eval "..."` works
only for simple expressions.

### Screenshot

```bash
agent-{{profile.lateness.stakeholders.channel}} screenshot                        # temp path, printed on stdout
agent-{{profile.lateness.stakeholders.channel}} screenshot page.png               # specific path
agent-{{profile.lateness.stakeholders.channel}} screenshot --full full.png        # full scroll height
agent-{{profile.lateness.stakeholders.channel}} screenshot --annotate map.png     # numbered labels + legend keyed to snapshot refs
```

`--annotate` is designed for multimodal models: each label `[N]` maps to ref `@eN`.

### Handle multiple pages via tabs

```bash
agent-{{profile.lateness.stakeholders.channel}} tab                      # list open tabs (with stable tabId)
agent-{{profile.lateness.stakeholders.channel}} tab new https://docs...  # open a new tab (and switch to it)
agent-{{profile.lateness.stakeholders.channel}} tab 2                    # switch to tab 2
agent-{{profile.lateness.stakeholders.channel}} tab close 2              # close tab 2
```

Stable `tabId`s mean `tab 2` points at the same tab across commands even
when other tabs open or close. After switching, refs from a prior snapshot
on a different tab no longer apply — re-snapshot.

### Run multiple {{profile.lateness.stakeholders.channel}}s in parallel

Each `--session <name>` is an isolated {{profile.lateness.stakeholders.channel}} with its own cookies, tabs,
and refs. Useful for testing multi-user flows or parallel scraping:

```bash
agent-{{profile.lateness.stakeholders.channel}} --session a open https://app.example.com
agent-{{profile.lateness.stakeholders.channel}} --session b open https://app.example.com
agent-{{profile.lateness.stakeholders.channel}} --session a fill @e1 "alice@test.com"
agent-{{profile.lateness.stakeholders.channel}} --session b fill @e1 "bob@test.com"
```

`AGENT_BROWSER_SESSION=myapp` sets the default session for the current
shell.

### Mock network requests

```bash
agent-{{profile.lateness.stakeholders.channel}} network route "**/api/users" --body '{"users":[]}'   # stub a response
agent-{{profile.lateness.stakeholders.channel}} network route "**/analytics" --abort                 # block entirely
agent-{{profile.lateness.stakeholders.channel}} network requests                                     # inspect what fired
agent-{{profile.lateness.stakeholders.channel}} network har start                                    # record all traffic
# ... perform actions ...
agent-{{profile.lateness.stakeholders.channel}} network har stop /tmp/trace.har
```

### Record a video of the workflow

```bash
agent-{{profile.lateness.stakeholders.channel}} record start demo.webm
agent-{{profile.lateness.stakeholders.channel}} open https://example.com
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
agent-{{profile.lateness.stakeholders.channel}} click @e3
agent-{{profile.lateness.stakeholders.channel}} record stop
```

See [references/video-recording.md](references/video-recording.md) for
codec options, GIF export, and more.

### Iframes

Iframes are auto-inlined in the snapshot — their refs work transparently:

```bash
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
# @e3 [Iframe] "payment-frame"
#   @e4 [input] "Card number"
#   @e5 [button] "Pay"

agent-{{profile.lateness.stakeholders.channel}} fill @e4 "4111111111111111"
agent-{{profile.lateness.stakeholders.channel}} click @e5
```

To scope a snapshot to an iframe (for focus or deep nesting):

```bash
agent-{{profile.lateness.stakeholders.channel}} frame @e3      # switch context to the iframe
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
agent-{{profile.lateness.stakeholders.channel}} frame main     # back to main frame
```

### Dialogs

`alert` and `beforeunload` are auto-accepted so agents never block. For
`confirm` and `prompt`:

```bash
agent-{{profile.lateness.stakeholders.channel}} dialog status          # is there a pending dialog?
agent-{{profile.lateness.stakeholders.channel}} dialog accept           # accept
agent-{{profile.lateness.stakeholders.channel}} dialog accept "text"    # accept with prompt input
agent-{{profile.lateness.stakeholders.channel}} dialog dismiss          # cancel
```

## Diagnosing install issues

If a command fails unexpectedly (`Unknown command`, `Failed to connect`,
stale daemons, version mismatches after `upgrade`, missing Chrome, etc.)
run `doctor` before anything else:

```bash
agent-{{profile.lateness.stakeholders.channel}} doctor                     # full diagnosis (env, Chrome, daemons, config, providers, network, launch test)
agent-{{profile.lateness.stakeholders.channel}} doctor --offline --quick   # fast, local-only
agent-{{profile.lateness.stakeholders.channel}} doctor --fix               # also run destructive repairs (reinstall Chrome, purge old state, ...)
agent-{{profile.lateness.stakeholders.channel}} doctor --json              # structured output for programmatic consumption
```

`doctor` auto-cleans stale socket/pid/version sidecar files on every run.
Destructive actions require `--fix`. Exit code is `0` if all checks pass
(warnings OK), `1` if any fail.

## Troubleshooting

**"Ref not found" / "Element not found: @eN"**
Page changed since the snapshot. Run `agent-{{profile.lateness.stakeholders.channel}} snapshot -i` again,
then use the new refs.

**Element exists in the DOM but not in the snapshot**
It's probably off-screen or not yet rendered. Try:

```bash
agent-{{profile.lateness.stakeholders.channel}} scroll down 1000
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
# or
agent-{{profile.lateness.stakeholders.channel}} wait --text "..."
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
```

**Click does nothing / overlay swallows the click**
Some modals and cookie banners block other clicks. Snapshot, find the
dismiss/close button, click it, then re-snapshot.

**Fill / type doesn't work**
Some custom input components intercept key events. Try:

```bash
agent-{{profile.lateness.stakeholders.channel}} focus @e1
agent-{{profile.lateness.stakeholders.channel}} keyboard inserttext "text"    # bypasses key events
# or
agent-{{profile.lateness.stakeholders.channel}} keyboard type "text"          # raw keystrokes, no selector
```

**Page needs JS you can't get right in one shot**
Use `eval --stdin` with a heredoc instead of inline:

```bash
cat <<'EOF' | agent-{{profile.lateness.stakeholders.channel}} eval --stdin
// Complex script with quotes, backticks, whatever
document.querySelectorAll('[data-id]').length
EOF
```

**Cross-origin iframe not accessible**
Cross-origin iframes that block accessibility tree access are silently
skipped. Use `frame "#iframe"` to switch into them explicitly if the
parent opts in, otherwise the iframe's contents aren't available via
snapshot — fall back to `eval` in the iframe's origin or use the
`--headers` flag to satisfy CORS.

**Authentication expires mid-workflow**
Use `--session-name <name>` or `state save`/`state load` so your session
survives {{profile.lateness.stakeholders.channel}} restarts. See [references/session-management.md](references/session-management.md)
and [references/authentication.md](references/authentication.md).

## Global flags worth knowing

```bash
--session <name>        # isolated {{profile.lateness.stakeholders.channel}} session
--json                  # JSON output (for machine parsing)
--headed                # show the window (default is headless)
--auto-connect          # connect to an already-running Chrome
--cdp <port>            # connect to a specific CDP port
--profile <name|path>   # use a Chrome profile (login state survives)
--headers <json>        # HTTP headers scoped to the URL's origin
--proxy <url>           # proxy server
--state <path>          # load saved auth state from JSON
--session-name <name>   # auto-save/restore session state by name
```

## When to load another skill

- **Electron desktop app** (VS Code, Slack desktop, Discord, Figma, etc.):
  `agent-{{profile.lateness.stakeholders.channel}} skills get electron`
- **Slack workspace automation**: `agent-{{profile.lateness.stakeholders.channel}} skills get slack`
- **Exploratory testing / QA / bug hunts**: `agent-{{profile.lateness.stakeholders.channel}} skills get dogfood`
- **Vercel Sandbox microVMs**: `agent-{{profile.lateness.stakeholders.channel}} skills get vercel-sandbox`
- **AWS Bedrock AgentCore cloud {{profile.lateness.stakeholders.channel}}**: `agent-{{profile.lateness.stakeholders.channel}} skills get agentcore`

## Full reference

Everything covered here plus the complete command/flag/env listing:

```bash
agent-{{profile.lateness.stakeholders.channel}} skills get core --full
```

That pulls in:

- `references/commands.md` — every command, flag, alias
- `references/snapshot-refs.md` — deep dive on the snapshot + ref model
- `references/authentication.md` — auth vault, credential handling
- `references/session-management.md` — persistence, multi-session workflows
- `references/profiling.md` — Chrome DevTools tracing and profiling
- `references/video-recording.md` — video capture options
- `references/proxy-support.md` — proxy configuration
- `templates/*` — starter shell scripts for auth, capture, form automation

--- references/authentication.md ---

# Authentication Patterns

Login flows, session persistence, OAuth, 2FA, and authenticated browsing.

**Related**: [session-management.md](session-management.md) for state persistence details, [SKILL.md](../SKILL.md) for quick start.

## Contents

- [Import Auth from Your Browser](#import-auth-from-your-{{profile.lateness.stakeholders.channel}})
- [Persistent Profiles](#persistent-profiles)
- [Session Persistence](#session-persistence)
- [Basic Login Flow](#basic-login-flow)
- [Saving Authentication State](#saving-authentication-state)
- [Restoring Authentication](#restoring-authentication)
- [OAuth / SSO Flows](#oauth--sso-flows)
- [Two-Factor Authentication](#two-factor-authentication)
- [HTTP Basic Auth](#http-basic-auth)
- [Cookie-Based Auth](#cookie-based-auth)
- [Token Refresh Handling](#token-refresh-handling)
- [Security Best Practices](#security-best-practices)

## Import Auth from Your Browser

The fastest way to authenticate is to reuse cookies from a Chrome session you are already logged into.

**Step 1: Start Chrome with remote debugging**

```bash
# macOS
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

Log in to your target site(s) in this Chrome window as you normally would.

> **Security note:** `--remote-debugging-port` exposes full {{profile.lateness.stakeholders.channel}} control on localhost. Any local process can connect and read cookies, execute JS, etc. Only use on trusted machines and close Chrome when done.

**Step 2: Grab the auth state**

```bash
# Auto-discover the running Chrome and save its cookies + localStorage
agent-{{profile.lateness.stakeholders.channel}} --auto-connect state save ./my-auth.json
```

**Step 3: Reuse in automation**

```bash
# Load auth at launch
agent-{{profile.lateness.stakeholders.channel}} --state ./my-auth.json open https://app.example.com/dashboard

# Or load into an existing session
agent-{{profile.lateness.stakeholders.channel}} state load ./my-auth.json
agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com/dashboard
```

This works for any site, including those with complex OAuth flows, SSO, or 2FA -- as long as Chrome already has valid session cookies.

> **Security note:** State files contain session tokens in plaintext. Add them to `.gitignore`, delete when no longer needed, and set `AGENT_BROWSER_ENCRYPTION_KEY` for encryption at rest. See [Security Best Practices](#security-best-practices).

**Tip:** Combine with `--session-name` so the imported auth auto-persists across restarts:

```bash
agent-{{profile.lateness.stakeholders.channel}} --session-name myapp state load ./my-auth.json
# From now on, state is auto-saved/restored for "myapp"
```

## Persistent Profiles

Use `--profile` to point agent-{{profile.lateness.stakeholders.channel}} at a Chrome user data directory. This persists everything (cookies, IndexedDB, service workers, cache) across {{profile.lateness.stakeholders.channel}} restarts without explicit save/load:

```bash
# First run: login once
agent-{{profile.lateness.stakeholders.channel}} --profile ~/.myapp-profile open https://app.example.com/login
# ... complete login flow ...

# All subsequent runs: already authenticated
agent-{{profile.lateness.stakeholders.channel}} --profile ~/.myapp-profile open https://app.example.com/dashboard
```

Use different paths for different projects or test users:

```bash
agent-{{profile.lateness.stakeholders.channel}} --profile ~/.profiles/admin open https://app.example.com
agent-{{profile.lateness.stakeholders.channel}} --profile ~/.profiles/viewer open https://app.example.com
```

Or set via environment variable:

```bash
export AGENT_BROWSER_PROFILE=~/.myapp-profile
agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com/dashboard
```

## Session Persistence

Use `--session-name` to auto-save and restore cookies + localStorage by name, without managing files:

```bash
# Auto-saves state on close, auto-restores on next launch
agent-{{profile.lateness.stakeholders.channel}} --session-name twitter open https://twitter.com
# ... login flow ...
agent-{{profile.lateness.stakeholders.channel}} close  # state saved to ~/.agent-{{profile.lateness.stakeholders.channel}}/sessions/

# Next time: state is automatically restored
agent-{{profile.lateness.stakeholders.channel}} --session-name twitter open https://twitter.com
```

Encrypt state at rest:

```bash
export AGENT_BROWSER_ENCRYPTION_KEY=$(openssl rand -hex 32)
agent-{{profile.lateness.stakeholders.channel}} --session-name secure open https://app.example.com
```

## Basic Login Flow

```bash
# Navigate to login page
agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com/login
agent-{{profile.lateness.stakeholders.channel}} wait --load networkidle

# Get form elements
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
# Output: @e1 [input type="{{profile.lateness.stakeholders.channel}}"], @e2 [input type="password"], @e3 [button] "Sign In"

# Fill credentials
agent-{{profile.lateness.stakeholders.channel}} fill @e1 "user@example.com"
agent-{{profile.lateness.stakeholders.channel}} fill @e2 "password123"

# Submit
agent-{{profile.lateness.stakeholders.channel}} click @e3
agent-{{profile.lateness.stakeholders.channel}} wait --load networkidle

# Verify login succeeded
agent-{{profile.lateness.stakeholders.channel}} get url  # Should be dashboard, not login
```

## Saving Authentication State

After logging in, save state for reuse:

```bash
# Login first (see above)
agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com/login
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
agent-{{profile.lateness.stakeholders.channel}} fill @e1 "user@example.com"
agent-{{profile.lateness.stakeholders.channel}} fill @e2 "password123"
agent-{{profile.lateness.stakeholders.channel}} click @e3
agent-{{profile.lateness.stakeholders.channel}} wait --url "**/dashboard"

# Save authenticated state
agent-{{profile.lateness.stakeholders.channel}} state save ./auth-state.json
```

## Restoring Authentication

Skip login by loading saved state:

```bash
# Load saved auth state
agent-{{profile.lateness.stakeholders.channel}} state load ./auth-state.json

# Navigate directly to protected page
agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com/dashboard

# Verify authenticated
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
```

## OAuth / SSO Flows

For OAuth redirects:

```bash
# Start OAuth flow
agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com/auth/google

# Handle redirects automatically
agent-{{profile.lateness.stakeholders.channel}} wait --url "**/accounts.google.com**"
agent-{{profile.lateness.stakeholders.channel}} snapshot -i

# Fill Google credentials
agent-{{profile.lateness.stakeholders.channel}} fill @e1 "user@gmail.com"
agent-{{profile.lateness.stakeholders.channel}} click @e2  # Next button
agent-{{profile.lateness.stakeholders.channel}} wait 2000
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
agent-{{profile.lateness.stakeholders.channel}} fill @e3 "password"
agent-{{profile.lateness.stakeholders.channel}} click @e4  # Sign in

# Wait for redirect back
agent-{{profile.lateness.stakeholders.channel}} wait --url "**/app.example.com**"
agent-{{profile.lateness.stakeholders.channel}} state save ./oauth-state.json
```

## Two-Factor Authentication

Handle 2FA with manual intervention:

```bash
# Login with credentials
agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com/login --headed  # Show {{profile.lateness.stakeholders.channel}}
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
agent-{{profile.lateness.stakeholders.channel}} fill @e1 "user@example.com"
agent-{{profile.lateness.stakeholders.channel}} fill @e2 "password123"
agent-{{profile.lateness.stakeholders.channel}} click @e3

# Wait for user to complete 2FA manually
echo "Complete 2FA in the {{profile.lateness.stakeholders.channel}} window..."
agent-{{profile.lateness.stakeholders.channel}} wait --url "**/dashboard" --timeout 120000

# Save state after 2FA
agent-{{profile.lateness.stakeholders.channel}} state save ./2fa-state.json
```

## HTTP Basic Auth

For sites using HTTP Basic Authentication:

```bash
# Set credentials before navigation
agent-{{profile.lateness.stakeholders.channel}} set credentials username password

# Navigate to protected resource
agent-{{profile.lateness.stakeholders.channel}} open https://protected.example.com/api
```

## Cookie-Based Auth

Manually set authentication cookies:

```bash
# Set auth cookie
agent-{{profile.lateness.stakeholders.channel}} cookies set session_token "abc123xyz"

# Navigate to protected page
agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com/dashboard
```

## Token Refresh Handling

For sessions with expiring tokens:

```bash
#!/bin/bash
# Wrapper that handles token refresh

STATE_FILE="./auth-state.json"

# Try loading existing state
if [[ -f "$STATE_FILE" ]]; then
    agent-{{profile.lateness.stakeholders.channel}} state load "$STATE_FILE"
    agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com/dashboard

    # Check if session is still valid
    URL=$(agent-{{profile.lateness.stakeholders.channel}} get url)
    if [[ "$URL" == *"/login"* ]]; then
        echo "Session expired, re-authenticating..."
        # Perform fresh login
        agent-{{profile.lateness.stakeholders.channel}} snapshot -i
        agent-{{profile.lateness.stakeholders.channel}} fill @e1 "$USERNAME"
        agent-{{profile.lateness.stakeholders.channel}} fill @e2 "$PASSWORD"
        agent-{{profile.lateness.stakeholders.channel}} click @e3
        agent-{{profile.lateness.stakeholders.channel}} wait --url "**/dashboard"
        agent-{{profile.lateness.stakeholders.channel}} state save "$STATE_FILE"
    fi
else
    # First-time login
    agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com/login
    # ... login flow ...
fi
```

## Security Best Practices

1. **Never commit state files** - They contain session tokens
   ```bash
   echo "*.auth-state.json" >> .gitignore
   ```

2. **Use environment variables for credentials**
   ```bash
   agent-{{profile.lateness.stakeholders.channel}} fill @e1 "$APP_USERNAME"
   agent-{{profile.lateness.stakeholders.channel}} fill @e2 "$APP_PASSWORD"
   ```

3. **Clean up after automation**
   ```bash
   agent-{{profile.lateness.stakeholders.channel}} cookies clear
   rm -f ./auth-state.json
   ```

4. **Use short-lived sessions for CI/CD**
   ```bash
   # Don't persist state in CI
   agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com/login
   # ... login and perform actions ...
   agent-{{profile.lateness.stakeholders.channel}} close  # Session ends, nothing persisted
   ```

--- references/commands.md ---

# Command Reference

Complete reference for all agent-{{profile.lateness.stakeholders.channel}} commands. For quick start and common patterns, see SKILL.md.

## Navigation

```bash
agent-{{profile.lateness.stakeholders.channel}} open <url>      # Navigate to URL (aliases: goto, navigate)
                              # Supports: https://, http://, file://, about:, data://
                              # Auto-prepends https:// if no protocol given
agent-{{profile.lateness.stakeholders.channel}} back            # Go back
agent-{{profile.lateness.stakeholders.channel}} forward         # Go forward
agent-{{profile.lateness.stakeholders.channel}} reload          # Reload page
agent-{{profile.lateness.stakeholders.channel}} close           # Close {{profile.lateness.stakeholders.channel}} (aliases: quit, exit)
agent-{{profile.lateness.stakeholders.channel}} connect 9222    # Connect to {{profile.lateness.stakeholders.channel}} via CDP port
```

## Snapshot (page analysis)

```bash
agent-{{profile.lateness.stakeholders.channel}} snapshot            # Full accessibility tree
agent-{{profile.lateness.stakeholders.channel}} snapshot -i         # Interactive elements only (recommended)
agent-{{profile.lateness.stakeholders.channel}} snapshot -c         # Compact output
agent-{{profile.lateness.stakeholders.channel}} snapshot -d 3       # Limit depth to 3
agent-{{profile.lateness.stakeholders.channel}} snapshot -s "#main" # Scope to CSS selector
```

## Interactions (use @refs from snapshot)

```bash
agent-{{profile.lateness.stakeholders.channel}} click @e1           # Click
agent-{{profile.lateness.stakeholders.channel}} click @e1 --new-tab # Click and open in new tab
agent-{{profile.lateness.stakeholders.channel}} dblclick @e1        # Double-click
agent-{{profile.lateness.stakeholders.channel}} focus @e1           # Focus element
agent-{{profile.lateness.stakeholders.channel}} fill @e2 "text"     # Clear and type
agent-{{profile.lateness.stakeholders.channel}} type @e2 "text"     # Type without clearing
agent-{{profile.lateness.stakeholders.channel}} press Enter         # Press key (alias: key)
agent-{{profile.lateness.stakeholders.channel}} press Control+a     # Key combination
agent-{{profile.lateness.stakeholders.channel}} keydown Shift       # Hold key down
agent-{{profile.lateness.stakeholders.channel}} keyup Shift         # Release key
agent-{{profile.lateness.stakeholders.channel}} hover @e1           # Hover
agent-{{profile.lateness.stakeholders.channel}} check @e1           # Check checkbox
agent-{{profile.lateness.stakeholders.channel}} uncheck @e1         # Uncheck checkbox
agent-{{profile.lateness.stakeholders.channel}} select @e1 "value"  # Select dropdown option
agent-{{profile.lateness.stakeholders.channel}} select @e1 "a" "b"  # Select multiple options
agent-{{profile.lateness.stakeholders.channel}} scroll down 500     # Scroll page (default: down 300px)
agent-{{profile.lateness.stakeholders.channel}} scrollintoview @e1  # Scroll element into view (alias: scrollinto)
agent-{{profile.lateness.stakeholders.channel}} drag @e1 @e2        # Drag and drop
agent-{{profile.lateness.stakeholders.channel}} upload @e1 file.pdf # Upload files
```

## Get Information

```bash
agent-{{profile.lateness.stakeholders.channel}} get text @e1        # Get element text
agent-{{profile.lateness.stakeholders.channel}} get html @e1        # Get innerHTML
agent-{{profile.lateness.stakeholders.channel}} get value @e1       # Get input value
agent-{{profile.lateness.stakeholders.channel}} get attr @e1 href   # Get attribute
agent-{{profile.lateness.stakeholders.channel}} get title           # Get page title
agent-{{profile.lateness.stakeholders.channel}} get url             # Get current URL
agent-{{profile.lateness.stakeholders.channel}} get cdp-url         # Get CDP WebSocket URL
agent-{{profile.lateness.stakeholders.channel}} get count ".item"   # Count matching elements
agent-{{profile.lateness.stakeholders.channel}} get box @e1         # Get bounding box
agent-{{profile.lateness.stakeholders.channel}} get styles @e1      # Get computed styles (font, color, bg, etc.)
```

## Check State

```bash
agent-{{profile.lateness.stakeholders.channel}} is visible @e1      # Check if visible
agent-{{profile.lateness.stakeholders.channel}} is enabled @e1      # Check if enabled
agent-{{profile.lateness.stakeholders.channel}} is checked @e1      # Check if checked
```

## Screenshots and PDF

```bash
agent-{{profile.lateness.stakeholders.channel}} screenshot          # Save to temporary directory
agent-{{profile.lateness.stakeholders.channel}} screenshot path.png # Save to specific path
agent-{{profile.lateness.stakeholders.channel}} screenshot --full   # Full page
agent-{{profile.lateness.stakeholders.channel}} pdf output.pdf      # Save as PDF
```

## Video Recording

```bash
agent-{{profile.lateness.stakeholders.channel}} record start ./demo.webm    # Start recording
agent-{{profile.lateness.stakeholders.channel}} click @e1                   # Perform actions
agent-{{profile.lateness.stakeholders.channel}} record stop                 # Stop and save video
agent-{{profile.lateness.stakeholders.channel}} record restart ./take2.webm # Stop current + start new
```

## Wait

```bash
agent-{{profile.lateness.stakeholders.channel}} wait @e1                     # Wait for element
agent-{{profile.lateness.stakeholders.channel}} wait 2000                    # Wait milliseconds
agent-{{profile.lateness.stakeholders.channel}} wait --text "Success"        # Wait for text (or -t)
agent-{{profile.lateness.stakeholders.channel}} wait --url "**/dashboard"    # Wait for URL pattern (or -u)
agent-{{profile.lateness.stakeholders.channel}} wait --load networkidle      # Wait for network idle (or -l)
agent-{{profile.lateness.stakeholders.channel}} wait --fn "window.ready"     # Wait for JS condition (or -f)
```

## Mouse Control

```bash
agent-{{profile.lateness.stakeholders.channel}} mouse move 100 200      # Move mouse
agent-{{profile.lateness.stakeholders.channel}} mouse down left         # Press button
agent-{{profile.lateness.stakeholders.channel}} mouse up left           # Release button
agent-{{profile.lateness.stakeholders.channel}} mouse wheel 100         # Scroll wheel
```

## Semantic Locators (alternative to refs)

```bash
agent-{{profile.lateness.stakeholders.channel}} find role button click --name "Submit"
agent-{{profile.lateness.stakeholders.channel}} find text "Sign In" click
agent-{{profile.lateness.stakeholders.channel}} find text "Sign In" click --exact      # Exact match only
agent-{{profile.lateness.stakeholders.channel}} find label "Email" fill "user@test.com"
agent-{{profile.lateness.stakeholders.channel}} find placeholder "Search" type "query"
agent-{{profile.lateness.stakeholders.channel}} find alt "Logo" click
agent-{{profile.lateness.stakeholders.channel}} find title "Close" click
agent-{{profile.lateness.stakeholders.channel}} find testid "submit-btn" click
agent-{{profile.lateness.stakeholders.channel}} find first ".item" click
agent-{{profile.lateness.stakeholders.channel}} find last ".item" click
agent-{{profile.lateness.stakeholders.channel}} find nth 2 "a" hover
```

## Browser Settings

```bash
agent-{{profile.lateness.stakeholders.channel}} set viewport 1920 1080          # Set viewport size
agent-{{profile.lateness.stakeholders.channel}} set viewport 1920 1080 2        # 2x retina (same CSS size, higher res screenshots)
agent-{{profile.lateness.stakeholders.channel}} set device "iPhone 14"          # Emulate device
agent-{{profile.lateness.stakeholders.channel}} set geo 37.7749 -122.4194       # Set geolocation (alias: geolocation)
agent-{{profile.lateness.stakeholders.channel}} set offline on                  # Toggle offline mode
agent-{{profile.lateness.stakeholders.channel}} set headers '{"X-Key":"v"}'     # Extra HTTP headers
agent-{{profile.lateness.stakeholders.channel}} set credentials user pass       # HTTP basic auth (alias: auth)
agent-{{profile.lateness.stakeholders.channel}} set media dark                  # Emulate color scheme
agent-{{profile.lateness.stakeholders.channel}} set media light reduced-motion  # Light mode + reduced motion
```

## Cookies and Storage

```bash
agent-{{profile.lateness.stakeholders.channel}} cookies                     # Get all cookies
agent-{{profile.lateness.stakeholders.channel}} cookies set name value      # Set cookie
agent-{{profile.lateness.stakeholders.channel}} cookies clear               # Clear cookies
agent-{{profile.lateness.stakeholders.channel}} storage local               # Get all localStorage
agent-{{profile.lateness.stakeholders.channel}} storage local key           # Get specific key
agent-{{profile.lateness.stakeholders.channel}} storage local set k v       # Set value
agent-{{profile.lateness.stakeholders.channel}} storage local clear         # Clear all
```

## Network

```bash
agent-{{profile.lateness.stakeholders.channel}} network route <url>              # Intercept requests
agent-{{profile.lateness.stakeholders.channel}} network route <url> --abort      # Block requests
agent-{{profile.lateness.stakeholders.channel}} network route <url> --body '{}'  # Mock response
agent-{{profile.lateness.stakeholders.channel}} network unroute [url]            # Remove routes
agent-{{profile.lateness.stakeholders.channel}} network requests                 # View tracked requests
agent-{{profile.lateness.stakeholders.channel}} network requests --filter api    # Filter requests
```

## Tabs and Windows

```bash
agent-{{profile.lateness.stakeholders.channel}} tab                              # List tabs with tabId and label
agent-{{profile.lateness.stakeholders.channel}} tab new [url]                    # New tab
agent-{{profile.lateness.stakeholders.channel}} tab new --label docs [url]       # New tab with a memorable label
agent-{{profile.lateness.stakeholders.channel}} tab t2                           # Switch to tab by id
agent-{{profile.lateness.stakeholders.channel}} tab docs                         # Switch to tab by label
agent-{{profile.lateness.stakeholders.channel}} tab close                        # Close current tab
agent-{{profile.lateness.stakeholders.channel}} tab close t2                     # Close tab by id
agent-{{profile.lateness.stakeholders.channel}} tab close docs                   # Close tab by label
agent-{{profile.lateness.stakeholders.channel}} window new                       # New window
```

Tab ids are stable strings of the form `t1`, `t2`, `t3`. They're never reused
within a session, so the same id keeps referring to the same tab across
commands. Positional integers are **not** accepted — `tab 2` errors with a
teaching message; use `t2`.

User-assigned labels (`docs`, `app`, `admin`) are interchangeable with ids
everywhere a tab ref is accepted. Labels are the agent-friendly way to write
multi-tab workflows:

```bash
agent-{{profile.lateness.stakeholders.channel}} tab new --label docs https://docs.example.com
agent-{{profile.lateness.stakeholders.channel}} tab new --label app  https://app.example.com
agent-{{profile.lateness.stakeholders.channel}} tab docs                   # switch to docs
agent-{{profile.lateness.stakeholders.channel}} snapshot                   # populate refs for docs
agent-{{profile.lateness.stakeholders.channel}} click @e1                  # ref click on docs
agent-{{profile.lateness.stakeholders.channel}} tab app                    # switch to app
agent-{{profile.lateness.stakeholders.channel}} tab close docs             # close by label
```

Labels are never auto-generated, never rewritten on navigation, and must be
unique within a session. To interact with another tab, switch to it first:
the daemon maintains a single active tab, so refs (`@eN`) belong to the tab
that was active when the snapshot ran.

## Frames

```bash
agent-{{profile.lateness.stakeholders.channel}} frame "#iframe"     # Switch to iframe by CSS selector
agent-{{profile.lateness.stakeholders.channel}} frame @e3           # Switch to iframe by element ref
agent-{{profile.lateness.stakeholders.channel}} frame main          # Back to main frame
```

### Iframe support

Iframes are detected automatically during snapshots. When the main-frame snapshot runs, `Iframe` nodes are resolved and their content is inlined beneath the iframe element in the output (one level of nesting; iframes within iframes are not expanded).

```bash
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
# @e3 [Iframe] "payment-frame"
#   @e4 [input] "Card number"
#   @e5 [button] "Pay"

# Interact directly — refs inside iframes already work
agent-{{profile.lateness.stakeholders.channel}} fill @e4 "4111111111111111"
agent-{{profile.lateness.stakeholders.channel}} click @e5

# Or switch frame context for scoped snapshots
agent-{{profile.lateness.stakeholders.channel}} frame @e3               # Switch using element ref
agent-{{profile.lateness.stakeholders.channel}} snapshot -i             # Snapshot scoped to that iframe
agent-{{profile.lateness.stakeholders.channel}} frame main              # Return to main frame
```

The `frame` command accepts:
- **Element refs** — `frame @e3` resolves the ref to an iframe element
- **CSS selectors** — `frame "#payment-iframe"` finds the iframe by selector
- **Frame name/URL** — matches against the {{profile.lateness.stakeholders.channel}}'s frame tree

## Dialogs

By default, `alert` and `beforeunload` dialogs are automatically accepted so they never block the agent. `confirm` and `prompt` dialogs still require explicit handling. Use `--no-auto-dialog` to disable this behavior.

```bash
agent-{{profile.lateness.stakeholders.channel}} dialog accept [text]  # Accept dialog
agent-{{profile.lateness.stakeholders.channel}} dialog dismiss        # Dismiss dialog
agent-{{profile.lateness.stakeholders.channel}} dialog status         # Check if a dialog is currently open
```

## JavaScript

```bash
agent-{{profile.lateness.stakeholders.channel}} eval "document.title"          # Simple expressions only
agent-{{profile.lateness.stakeholders.channel}} eval -b "<base64>"             # Any JavaScript (base64 encoded)
agent-{{profile.lateness.stakeholders.channel}} eval --stdin                   # Read script from stdin
```

Use `-b`/`--base64` or `--stdin` for reliable execution. Shell escaping with nested quotes and special characters is error-prone.

```bash
# Base64 encode your script, then:
agent-{{profile.lateness.stakeholders.channel}} eval -b "ZG9jdW1lbnQucXVlcnlTZWxlY3RvcignW3NyYyo9Il9uZXh0Il0nKQ=="

# Or use stdin with heredoc for multiline scripts:
cat <<'EOF' | agent-{{profile.lateness.stakeholders.channel}} eval --stdin
const links = document.querySelectorAll('a');
Array.from(links).map(a => a.href);
EOF
```

## State Management

```bash
agent-{{profile.lateness.stakeholders.channel}} state save auth.json    # Save cookies, storage, auth state
agent-{{profile.lateness.stakeholders.channel}} state load auth.json    # Restore saved state
```

## Global Options

```bash
agent-{{profile.lateness.stakeholders.channel}} --session <name> ...    # Isolated {{profile.lateness.stakeholders.channel}} session
agent-{{profile.lateness.stakeholders.channel}} --json ...              # JSON output for parsing
agent-{{profile.lateness.stakeholders.channel}} --headed ...            # Show {{profile.lateness.stakeholders.channel}} window (not headless)
agent-{{profile.lateness.stakeholders.channel}} --full ...              # Full page screenshot (-f)
agent-{{profile.lateness.stakeholders.channel}} --cdp <port> ...        # Connect via Chrome DevTools Protocol
agent-{{profile.lateness.stakeholders.channel}} -p <provider> ...       # Cloud {{profile.lateness.stakeholders.channel}} provider (--provider)
agent-{{profile.lateness.stakeholders.channel}} --proxy <url> ...       # Use proxy server
agent-{{profile.lateness.stakeholders.channel}} --proxy-bypass <hosts>  # Hosts to bypass proxy
agent-{{profile.lateness.stakeholders.channel}} --headers <json> ...    # HTTP headers scoped to URL's origin
agent-{{profile.lateness.stakeholders.channel}} --executable-path <p>   # Custom {{profile.lateness.stakeholders.channel}} executable
agent-{{profile.lateness.stakeholders.channel}} --extension <path> ...  # Load {{profile.lateness.stakeholders.channel}} extension (repeatable)
agent-{{profile.lateness.stakeholders.channel}} --ignore-https-errors   # Ignore SSL certificate errors
agent-{{profile.lateness.stakeholders.channel}} --help                  # Show help (-h)
agent-{{profile.lateness.stakeholders.channel}} --version               # Show version (-V)
agent-{{profile.lateness.stakeholders.channel}} <command> --help        # Show detailed help for a command
```

## Debugging

```bash
agent-{{profile.lateness.stakeholders.channel}} --headed open example.com   # Show {{profile.lateness.stakeholders.channel}} window
agent-{{profile.lateness.stakeholders.channel}} --cdp 9222 snapshot         # Connect via CDP port
agent-{{profile.lateness.stakeholders.channel}} connect 9222                # Alternative: connect command
agent-{{profile.lateness.stakeholders.channel}} console                     # View console messages
agent-{{profile.lateness.stakeholders.channel}} console --clear             # Clear console
agent-{{profile.lateness.stakeholders.channel}} errors                      # View page errors
agent-{{profile.lateness.stakeholders.channel}} errors --clear              # Clear errors
agent-{{profile.lateness.stakeholders.channel}} highlight @e1               # Highlight element
agent-{{profile.lateness.stakeholders.channel}} inspect                     # Open Chrome DevTools for this session
agent-{{profile.lateness.stakeholders.channel}} trace start                 # Start recording trace
agent-{{profile.lateness.stakeholders.channel}} trace stop trace.zip        # Stop and save trace
agent-{{profile.lateness.stakeholders.channel}} profiler start              # Start Chrome DevTools profiling
agent-{{profile.lateness.stakeholders.channel}} profiler stop trace.json    # Stop and save profile
```

## Environment Variables

```bash
AGENT_BROWSER_SESSION="mysession"            # Default session name
AGENT_BROWSER_EXECUTABLE_PATH="/path/chrome" # Custom {{profile.lateness.stakeholders.channel}} path
AGENT_BROWSER_EXTENSIONS="/ext1,/ext2"       # Comma-separated extension paths
AGENT_BROWSER_PROVIDER="{{profile.lateness.stakeholders.channel}}base"         # Cloud {{profile.lateness.stakeholders.channel}} provider
AGENT_BROWSER_STREAM_PORT="9223"             # Override WebSocket streaming port (default: OS-assigned)
AGENT_BROWSER_HOME="/path/to/agent-{{profile.lateness.stakeholders.channel}}"  # Custom install location
```

--- references/profiling.md ---

# Profiling

Capture Chrome DevTools performance profiles during {{profile.lateness.stakeholders.channel}} automation for performance analysis.

**Related**: [commands.md](commands.md) for full command reference, [SKILL.md](../SKILL.md) for quick start.

## Contents

- [Basic Profiling](#basic-profiling)
- [Profiler Commands](#profiler-commands)
- [Categories](#categories)
- [Use Cases](#use-cases)
- [Output Format](#output-format)
- [Viewing Profiles](#viewing-profiles)
- [Limitations](#limitations)

## Basic Profiling

```bash
# Start profiling
agent-{{profile.lateness.stakeholders.channel}} profiler start

# Perform actions
agent-{{profile.lateness.stakeholders.channel}} navigate https://example.com
agent-{{profile.lateness.stakeholders.channel}} click "#button"
agent-{{profile.lateness.stakeholders.channel}} wait 1000

# Stop and save
agent-{{profile.lateness.stakeholders.channel}} profiler stop ./trace.json
```

## Profiler Commands

```bash
# Start profiling with default categories
agent-{{profile.lateness.stakeholders.channel}} profiler start

# Start with custom trace categories
agent-{{profile.lateness.stakeholders.channel}} profiler start --categories "devtools.timeline,v8.execute,blink.user_timing"

# Stop profiling and save to file
agent-{{profile.lateness.stakeholders.channel}} profiler stop ./trace.json
```

## Categories

The `--categories` flag accepts a comma-separated list of Chrome trace categories. Default categories include:

- `devtools.timeline` -- standard DevTools performance traces
- `v8.execute` -- time spent running JavaScript
- `blink` -- renderer events
- `blink.user_timing` -- `performance.mark()` / `performance.measure()` calls
- `latencyInfo` -- input-to-latency tracking
- `renderer.scheduler` -- task scheduling and execution
- `toplevel` -- broad-spectrum basic events

Several `disabled-by-default-*` categories are also included for detailed timeline, call stack, and V8 CPU profiling data.

## Use Cases

### Diagnosing Slow Page Loads

```bash
agent-{{profile.lateness.stakeholders.channel}} profiler start
agent-{{profile.lateness.stakeholders.channel}} navigate https://app.example.com
agent-{{profile.lateness.stakeholders.channel}} wait --load networkidle
agent-{{profile.lateness.stakeholders.channel}} profiler stop ./page-load-profile.json
```

### Profiling User Interactions

```bash
agent-{{profile.lateness.stakeholders.channel}} navigate https://app.example.com
agent-{{profile.lateness.stakeholders.channel}} profiler start
agent-{{profile.lateness.stakeholders.channel}} click "#submit"
agent-{{profile.lateness.stakeholders.channel}} wait 2000
agent-{{profile.lateness.stakeholders.channel}} profiler stop ./interaction-profile.json
```

### CI Performance Regression Checks

```bash
#!/bin/bash
agent-{{profile.lateness.stakeholders.channel}} profiler start
agent-{{profile.lateness.stakeholders.channel}} navigate https://app.example.com
agent-{{profile.lateness.stakeholders.channel}} wait --load networkidle
agent-{{profile.lateness.stakeholders.channel}} profiler stop "./profiles/build-${BUILD_ID}.json"
```

## Output Format

The output is a JSON file in Chrome Trace Event format:

```json
{
  "traceEvents": [
    { "cat": "devtools.timeline", "name": "RunTask", "ph": "X", "ts": 12345, "dur": 100, ... },
    ...
  ],
  "metadata": {
    "clock-domain": "LINUX_CLOCK_MONOTONIC"
  }
}
```

The `metadata.clock-domain` field is set based on the host platform (Linux or macOS). On Windows it is omitted.

## Viewing Profiles

Load the output JSON file in any of these tools:

- **Chrome DevTools**: Performance panel > Load profile (Ctrl+Shift+I > Performance)
- **Perfetto UI**: https://ui.perfetto.dev/ -- drag and drop the JSON file
- **Trace Viewer**: `chrome://tracing` in any Chromium {{profile.lateness.stakeholders.channel}}

## Limitations

- Only works with Chromium-based {{profile.lateness.stakeholders.channel}}s (Chrome, Edge). Not supported on Firefox or WebKit.
- Trace data accumulates in memory while profiling is active (capped at 5 million events). Stop profiling promptly after the area of interest.
- Data collection on stop has a 30-second timeout. If the {{profile.lateness.stakeholders.channel}} is unresponsive, the stop command may fail.

--- references/proxy-support.md ---

# Proxy Support

Proxy configuration for geo-testing, rate limiting avoidance, and corporate environments.

**Related**: [commands.md](commands.md) for global options, [SKILL.md](../SKILL.md) for quick start.

## Contents

- [Basic Proxy Configuration](#basic-proxy-configuration)
- [Authenticated Proxy](#authenticated-proxy)
- [SOCKS Proxy](#socks-proxy)
- [Proxy Bypass](#proxy-bypass)
- [Common Use Cases](#common-use-cases)
- [Verifying Proxy Connection](#verifying-proxy-connection)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Basic Proxy Configuration

Use the `--proxy` flag or set proxy via environment variable:

```bash
# Via CLI flag
agent-{{profile.lateness.stakeholders.channel}} --proxy "http://proxy.example.com:8080" open https://example.com

# Via environment variable
export HTTP_PROXY="http://proxy.example.com:8080"
agent-{{profile.lateness.stakeholders.channel}} open https://example.com

# HTTPS proxy
export HTTPS_PROXY="https://proxy.example.com:8080"
agent-{{profile.lateness.stakeholders.channel}} open https://example.com

# Both
export HTTP_PROXY="http://proxy.example.com:8080"
export HTTPS_PROXY="http://proxy.example.com:8080"
agent-{{profile.lateness.stakeholders.channel}} open https://example.com
```

## Authenticated Proxy

For proxies requiring authentication:

```bash
# Include credentials in URL
export HTTP_PROXY="http://username:password@proxy.example.com:8080"
agent-{{profile.lateness.stakeholders.channel}} open https://example.com
```

## SOCKS Proxy

```bash
# SOCKS5 proxy
export ALL_PROXY="socks5://proxy.example.com:1080"
agent-{{profile.lateness.stakeholders.channel}} open https://example.com

# SOCKS5 with auth
export ALL_PROXY="socks5://user:pass@proxy.example.com:1080"
agent-{{profile.lateness.stakeholders.channel}} open https://example.com
```

## Proxy Bypass

Skip proxy for specific domains using `--proxy-bypass` or `NO_PROXY`:

```bash
# Via CLI flag
agent-{{profile.lateness.stakeholders.channel}} --proxy "http://proxy.example.com:8080" --proxy-bypass "localhost,*.internal.com" open https://example.com

# Via environment variable
export NO_PROXY="localhost,127.0.0.1,.internal.company.com"
agent-{{profile.lateness.stakeholders.channel}} open https://internal.company.com  # Direct connection
agent-{{profile.lateness.stakeholders.channel}} open https://external.com          # Via proxy
```

## Common Use Cases

### Geo-Location Testing

```bash
#!/bin/bash
# Test site from different regions using geo-located proxies

PROXIES=(
    "http://us-proxy.example.com:8080"
    "http://eu-proxy.example.com:8080"
    "http://asia-proxy.example.com:8080"
)

for proxy in "${PROXIES[@]}"; do
    export HTTP_PROXY="$proxy"
    export HTTPS_PROXY="$proxy"

    region=$(echo "$proxy" | grep -oP '^\w+-\w+')
    echo "Testing from: $region"

    agent-{{profile.lateness.stakeholders.channel}} --session "$region" open https://example.com
    agent-{{profile.lateness.stakeholders.channel}} --session "$region" screenshot "./screenshots/$region.png"
    agent-{{profile.lateness.stakeholders.channel}} --session "$region" close
done
```

### Rotating Proxies for Scraping

```bash
#!/bin/bash
# Rotate through proxy list to avoid rate limiting

PROXY_LIST=(
    "http://proxy1.example.com:8080"
    "http://proxy2.example.com:8080"
    "http://proxy3.example.com:8080"
)

URLS=(
    "https://site.com/page1"
    "https://site.com/page2"
    "https://site.com/page3"
)

for i in "${!URLS[@]}"; do
    proxy_index=$((i % ${#PROXY_LIST[@]}))
    export HTTP_PROXY="${PROXY_LIST[$proxy_index]}"
    export HTTPS_PROXY="${PROXY_LIST[$proxy_index]}"

    agent-{{profile.lateness.stakeholders.channel}} open "${URLS[$i]}"
    agent-{{profile.lateness.stakeholders.channel}} get text body > "output-$i.txt"
    agent-{{profile.lateness.stakeholders.channel}} close

    sleep 1  # Polite delay
done
```

### Corporate Network Access

```bash
#!/bin/bash
# Access internal sites via corporate proxy

export HTTP_PROXY="http://corpproxy.company.com:8080"
export HTTPS_PROXY="http://corpproxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1,.company.com"

# External sites go through proxy
agent-{{profile.lateness.stakeholders.channel}} open https://external-vendor.com

# Internal sites bypass proxy
agent-{{profile.lateness.stakeholders.channel}} open https://intranet.company.com
```

## Verifying Proxy Connection

```bash
# Check your apparent IP
agent-{{profile.lateness.stakeholders.channel}} open https://httpbin.org/ip
agent-{{profile.lateness.stakeholders.channel}} get text body
# Should show proxy's IP, not your real IP
```

## Troubleshooting

### Proxy Connection Failed

```bash
# Test proxy connectivity first
curl -x http://proxy.example.com:8080 https://httpbin.org/ip

# Check if proxy requires auth
export HTTP_PROXY="http://user:pass@proxy.example.com:8080"
```

### SSL/TLS Errors Through Proxy

Some proxies perform SSL inspection. If you encounter certificate errors:

```bash
# For testing only - not recommended for production
agent-{{profile.lateness.stakeholders.channel}} open https://example.com --ignore-https-errors
```

### Slow Performance

```bash
# Use proxy only when necessary
export NO_PROXY="*.cdn.com,*.static.com"  # Direct CDN access
```

## Best Practices

1. **Use environment variables** - Don't hardcode proxy credentials
2. **Set NO_PROXY appropriately** - Avoid routing local traffic through proxy
3. **Test proxy before automation** - Verify connectivity with simple requests
4. **Handle proxy failures gracefully** - Implement retry logic for unstable proxies
5. **Rotate proxies for large scraping jobs** - Distribute load and avoid bans

--- references/session-management.md ---

# Session Management

Multiple isolated {{profile.lateness.stakeholders.channel}} sessions with state persistence and concurrent browsing.

**Related**: [authentication.md](authentication.md) for login patterns, [SKILL.md](../SKILL.md) for quick start.

## Contents

- [Named Sessions](#named-sessions)
- [Session Isolation Properties](#session-isolation-properties)
- [Session State Persistence](#session-state-persistence)
- [Common Patterns](#common-patterns)
- [Default Session](#default-session)
- [Session Cleanup](#session-cleanup)
- [Best Practices](#best-practices)

## Named Sessions

Use `--session` flag to isolate {{profile.lateness.stakeholders.channel}} contexts:

```bash
# Session 1: Authentication flow
agent-{{profile.lateness.stakeholders.channel}} --session auth open https://app.example.com/login

# Session 2: Public browsing (separate cookies, storage)
agent-{{profile.lateness.stakeholders.channel}} --session public open https://example.com

# Commands are isolated by session
agent-{{profile.lateness.stakeholders.channel}} --session auth fill @e1 "user@example.com"
agent-{{profile.lateness.stakeholders.channel}} --session public get text body
```

## Session Isolation Properties

Each session has independent:
- Cookies
- LocalStorage / SessionStorage
- IndexedDB
- Cache
- Browsing history
- Open tabs

## Session State Persistence

### Save Session State

```bash
# Save cookies, storage, and auth state
agent-{{profile.lateness.stakeholders.channel}} state save /path/to/auth-state.json
```

### Load Session State

```bash
# Restore saved state
agent-{{profile.lateness.stakeholders.channel}} state load /path/to/auth-state.json

# Continue with authenticated session
agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com/dashboard
```

### State File Contents

```json
{
  "cookies": [...],
  "localStorage": {...},
  "sessionStorage": {...},
  "origins": [...]
}
```

## Common Patterns

### Authenticated Session Reuse

```bash
#!/bin/bash
# Save login state once, reuse many times

STATE_FILE="/tmp/auth-state.json"

# Check if we have saved state
if [[ -f "$STATE_FILE" ]]; then
    agent-{{profile.lateness.stakeholders.channel}} state load "$STATE_FILE"
    agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com/dashboard
else
    # Perform login
    agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com/login
    agent-{{profile.lateness.stakeholders.channel}} snapshot -i
    agent-{{profile.lateness.stakeholders.channel}} fill @e1 "$USERNAME"
    agent-{{profile.lateness.stakeholders.channel}} fill @e2 "$PASSWORD"
    agent-{{profile.lateness.stakeholders.channel}} click @e3
    agent-{{profile.lateness.stakeholders.channel}} wait --load networkidle

    # Save for future use
    agent-{{profile.lateness.stakeholders.channel}} state save "$STATE_FILE"
fi
```

### Concurrent Scraping

```bash
#!/bin/bash
# Scrape multiple sites concurrently

# Start all sessions
agent-{{profile.lateness.stakeholders.channel}} --session site1 open https://site1.com &
agent-{{profile.lateness.stakeholders.channel}} --session site2 open https://site2.com &
agent-{{profile.lateness.stakeholders.channel}} --session site3 open https://site3.com &
wait

# Extract from each
agent-{{profile.lateness.stakeholders.channel}} --session site1 get text body > site1.txt
agent-{{profile.lateness.stakeholders.channel}} --session site2 get text body > site2.txt
agent-{{profile.lateness.stakeholders.channel}} --session site3 get text body > site3.txt

# Cleanup
agent-{{profile.lateness.stakeholders.channel}} --session site1 close
agent-{{profile.lateness.stakeholders.channel}} --session site2 close
agent-{{profile.lateness.stakeholders.channel}} --session site3 close
```

### A/B Testing Sessions

```bash
# Test different user experiences
agent-{{profile.lateness.stakeholders.channel}} --session variant-a open "https://app.com?variant=a"
agent-{{profile.lateness.stakeholders.channel}} --session variant-b open "https://app.com?variant=b"

# Compare
agent-{{profile.lateness.stakeholders.channel}} --session variant-a screenshot /tmp/variant-a.png
agent-{{profile.lateness.stakeholders.channel}} --session variant-b screenshot /tmp/variant-b.png
```

## Default Session

When `--session` is omitted, commands use the default session:

```bash
# These use the same default session
agent-{{profile.lateness.stakeholders.channel}} open https://example.com
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
agent-{{profile.lateness.stakeholders.channel}} close  # Closes default session
```

## Session Cleanup

```bash
# Close specific session
agent-{{profile.lateness.stakeholders.channel}} --session auth close

# List active sessions
agent-{{profile.lateness.stakeholders.channel}} session list
```

## Best Practices

### 1. Name Sessions Semantically

```bash
# GOOD: Clear purpose
agent-{{profile.lateness.stakeholders.channel}} --session github-auth open https://github.com
agent-{{profile.lateness.stakeholders.channel}} --session docs-scrape open https://docs.example.com

# AVOID: Generic names
agent-{{profile.lateness.stakeholders.channel}} --session s1 open https://github.com
```

### 2. Always Clean Up

```bash
# Close sessions when done
agent-{{profile.lateness.stakeholders.channel}} --session auth close
agent-{{profile.lateness.stakeholders.channel}} --session scrape close
```

### 3. Handle State Files Securely

```bash
# Don't commit state files (contain auth tokens!)
echo "*.auth-state.json" >> .gitignore

# Delete after use
rm /tmp/auth-state.json
```

### 4. Timeout Long Sessions

```bash
# Set timeout for automated scripts
timeout 60 agent-{{profile.lateness.stakeholders.channel}} --session long-task get text body
```

--- references/snapshot-refs.md ---

# Snapshot and Refs

Compact element references that reduce context usage dramatically for AI agents.

**Related**: [commands.md](commands.md) for full command reference, [SKILL.md](../SKILL.md) for quick start.

## Contents

- [How Refs Work](#how-refs-work)
- [Snapshot Command](#the-snapshot-command)
- [Using Refs](#using-refs)
- [Ref Lifecycle](#ref-lifecycle)
- [Best Practices](#best-practices)
- [Ref Notation Details](#ref-notation-details)
- [Troubleshooting](#troubleshooting)

## How Refs Work

Traditional approach:
```
Full DOM/HTML → AI parses → CSS selector → Action (~3000-5000 tokens)
```

agent-{{profile.lateness.stakeholders.channel}} approach:
```
Compact snapshot → @refs assigned → Direct interaction (~200-400 tokens)
```

## The Snapshot Command

```bash
# Basic snapshot (shows page structure)
agent-{{profile.lateness.stakeholders.channel}} snapshot

# Interactive snapshot (-i flag) - RECOMMENDED
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
```

### Snapshot Output Format

```
Page: Example Site - Home
URL: https://example.com

@e1 [header]
  @e2 [nav]
    @e3 [a] "Home"
    @e4 [a] "Products"
    @e5 [a] "About"
  @e6 [button] "Sign In"

@e7 [main]
  @e8 [h1] "Welcome"
  @e9 [form]
    @e10 [input type="{{profile.lateness.stakeholders.channel}}"] placeholder="Email"
    @e11 [input type="password"] placeholder="Password"
    @e12 [button type="submit"] "Log In"

@e13 [footer]
  @e14 [a] "Privacy Policy"
```

## Using Refs

Once you have refs, interact directly:

```bash
# Click the "Sign In" button
agent-{{profile.lateness.stakeholders.channel}} click @e6

# Fill {{profile.lateness.stakeholders.channel}} input
agent-{{profile.lateness.stakeholders.channel}} fill @e10 "user@example.com"

# Fill password
agent-{{profile.lateness.stakeholders.channel}} fill @e11 "password123"

# Submit the form
agent-{{profile.lateness.stakeholders.channel}} click @e12
```

## Ref Lifecycle

**IMPORTANT**: Refs are invalidated when the page changes!

```bash
# Get initial snapshot
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
# @e1 [button] "Next"

# Click triggers page change
agent-{{profile.lateness.stakeholders.channel}} click @e1

# MUST re-snapshot to get new refs!
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
# @e1 [h1] "Page 2"  ← Different element now!
```

## Best Practices

### 1. Always Snapshot Before Interacting

```bash
# CORRECT
agent-{{profile.lateness.stakeholders.channel}} open https://example.com
agent-{{profile.lateness.stakeholders.channel}} snapshot -i          # Get refs first
agent-{{profile.lateness.stakeholders.channel}} click @e1            # Use ref

# WRONG
agent-{{profile.lateness.stakeholders.channel}} open https://example.com
agent-{{profile.lateness.stakeholders.channel}} click @e1            # Ref doesn't exist yet!
```

### 2. Re-Snapshot After Navigation

```bash
agent-{{profile.lateness.stakeholders.channel}} click @e5            # Navigates to new page
agent-{{profile.lateness.stakeholders.channel}} snapshot -i          # Get new refs
agent-{{profile.lateness.stakeholders.channel}} click @e1            # Use new refs
```

### 3. Re-Snapshot After Dynamic Changes

```bash
agent-{{profile.lateness.stakeholders.channel}} click @e1            # Opens dropdown
agent-{{profile.lateness.stakeholders.channel}} snapshot -i          # See dropdown items
agent-{{profile.lateness.stakeholders.channel}} click @e7            # Select item
```

### 4. Snapshot Specific Regions

For complex pages, snapshot specific areas:

```bash
# Snapshot just the form
agent-{{profile.lateness.stakeholders.channel}} snapshot @e9
```

## Ref Notation Details

```
@e1 [tag type="value"] "text content" placeholder="hint"
│    │   │             │               │
│    │   │             │               └─ Additional attributes
│    │   │             └─ Visible text
│    │   └─ Key attributes shown
│    └─ HTML tag name
└─ Unique ref ID
```

### Common Patterns

```
@e1 [button] "Submit"                    # Button with text
@e2 [input type="{{profile.lateness.stakeholders.channel}}"]                 # Email input
@e3 [input type="password"]              # Password input
@e4 [a href="/page"] "Link Text"         # Anchor link
@e5 [select]                             # Dropdown
@e6 [textarea] placeholder="Message"     # Text area
@e7 [div class="modal"]                  # Container (when relevant)
@e8 [img alt="Logo"]                     # Image
@e9 [checkbox] checked                   # Checked checkbox
@e10 [radio] selected                    # Selected radio
```

## Iframes

Snapshots automatically detect and inline iframe content. When the main-frame snapshot runs, each `Iframe` node is resolved and its child accessibility tree is included directly beneath it in the output. Refs assigned to elements inside iframes carry frame context, so interactions like `click`, `fill`, and `type` work without manually switching frames.

```bash
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
# @e1 [heading] "Checkout"
# @e2 [Iframe] "payment-frame"
#   @e3 [input] "Card number"
#   @e4 [input] "Expiry"
#   @e5 [button] "Pay"
# @e6 [button] "Cancel"

# Interact with iframe elements directly using their refs
agent-{{profile.lateness.stakeholders.channel}} fill @e3 "4111111111111111"
agent-{{profile.lateness.stakeholders.channel}} fill @e4 "12/28"
agent-{{profile.lateness.stakeholders.channel}} click @e5
```

**Key details:**
- Only one level of iframe nesting is expanded (iframes within iframes are not recursed)
- Cross-origin iframes that block accessibility tree access are silently skipped
- Empty iframes or iframes with no interactive content are omitted from the output
- To scope a snapshot to a single iframe, use `frame @ref` then `snapshot -i`

## Troubleshooting

### "Ref not found" Error

```bash
# Ref may have changed - re-snapshot
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
```

### Element Not Visible in Snapshot

```bash
# Scroll down to reveal element
agent-{{profile.lateness.stakeholders.channel}} scroll down 1000
agent-{{profile.lateness.stakeholders.channel}} snapshot -i

# Or wait for dynamic content
agent-{{profile.lateness.stakeholders.channel}} wait 1000
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
```

### Too Many Elements

```bash
# Snapshot specific container
agent-{{profile.lateness.stakeholders.channel}} snapshot @e5

# Or use get text for content-only extraction
agent-{{profile.lateness.stakeholders.channel}} get text @e5
```

--- references/video-recording.md ---

# Video Recording

Capture {{profile.lateness.stakeholders.channel}} automation as video for debugging, documentation, or verification.

**Related**: [commands.md](commands.md) for full command reference, [SKILL.md](../SKILL.md) for quick start.

## Contents

- [Basic Recording](#basic-recording)
- [Recording Commands](#recording-commands)
- [Use Cases](#use-cases)
- [Best Practices](#best-practices)
- [Output Format](#output-format)
- [Limitations](#limitations)

## Basic Recording

```bash
# Start recording
agent-{{profile.lateness.stakeholders.channel}} record start ./demo.webm

# Perform actions
agent-{{profile.lateness.stakeholders.channel}} open https://example.com
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
agent-{{profile.lateness.stakeholders.channel}} click @e1
agent-{{profile.lateness.stakeholders.channel}} fill @e2 "test input"

# Stop and save
agent-{{profile.lateness.stakeholders.channel}} record stop
```

## Recording Commands

```bash
# Start recording to file
agent-{{profile.lateness.stakeholders.channel}} record start ./output.webm

# Stop current recording
agent-{{profile.lateness.stakeholders.channel}} record stop

# Restart with new file (stops current + starts new)
agent-{{profile.lateness.stakeholders.channel}} record restart ./take2.webm
```

## Use Cases

### Debugging Failed Automation

```bash
#!/bin/bash
# Record automation for debugging

agent-{{profile.lateness.stakeholders.channel}} record start ./debug-$(date +%Y%m%d-%H%M%S).webm

# Run your automation
agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
agent-{{profile.lateness.stakeholders.channel}} click @e1 || {
    echo "Click failed - check recording"
    agent-{{profile.lateness.stakeholders.channel}} record stop
    exit 1
}

agent-{{profile.lateness.stakeholders.channel}} record stop
```

### Documentation Generation

```bash
#!/bin/bash
# Record workflow for documentation

agent-{{profile.lateness.stakeholders.channel}} record start ./docs/how-to-login.webm

agent-{{profile.lateness.stakeholders.channel}} open https://app.example.com/login
agent-{{profile.lateness.stakeholders.channel}} wait 1000  # Pause for visibility

agent-{{profile.lateness.stakeholders.channel}} snapshot -i
agent-{{profile.lateness.stakeholders.channel}} fill @e1 "demo@example.com"
agent-{{profile.lateness.stakeholders.channel}} wait 500

agent-{{profile.lateness.stakeholders.channel}} fill @e2 "password"
agent-{{profile.lateness.stakeholders.channel}} wait 500

agent-{{profile.lateness.stakeholders.channel}} click @e3
agent-{{profile.lateness.stakeholders.channel}} wait --load networkidle
agent-{{profile.lateness.stakeholders.channel}} wait 1000  # Show result

agent-{{profile.lateness.stakeholders.channel}} record stop
```

### CI/CD Test Evidence

```bash
#!/bin/bash
# Record E2E test runs for CI artifacts

TEST_NAME="${1:-e2e-test}"
RECORDING_DIR="./test-recordings"
mkdir -p "$RECORDING_DIR"

agent-{{profile.lateness.stakeholders.channel}} record start "$RECORDING_DIR/$TEST_NAME-$(date +%s).webm"

# Run test
if run_e2e_test; then
    echo "Test passed"
else
    echo "Test failed - recording saved"
fi

agent-{{profile.lateness.stakeholders.channel}} record stop
```

## Best Practices

### 1. Add Pauses for Clarity

```bash
# Slow down for human viewing
agent-{{profile.lateness.stakeholders.channel}} click @e1
agent-{{profile.lateness.stakeholders.channel}} wait 500  # Let viewer see result
```

### 2. Use Descriptive Filenames

```bash
# Include context in filename
agent-{{profile.lateness.stakeholders.channel}} record start ./recordings/login-flow-2024-01-15.webm
agent-{{profile.lateness.stakeholders.channel}} record start ./recordings/checkout-test-run-42.webm
```

### 3. Handle Recording in Error Cases

```bash
#!/bin/bash
set -e

cleanup() {
    agent-{{profile.lateness.stakeholders.channel}} record stop 2>/dev/null || true
    agent-{{profile.lateness.stakeholders.channel}} close 2>/dev/null || true
}
trap cleanup EXIT

agent-{{profile.lateness.stakeholders.channel}} record start ./automation.webm
# ... automation steps ...
```

### 4. Combine with Screenshots

```bash
# Record video AND capture key frames
agent-{{profile.lateness.stakeholders.channel}} record start ./flow.webm

agent-{{profile.lateness.stakeholders.channel}} open https://example.com
agent-{{profile.lateness.stakeholders.channel}} screenshot ./screenshots/step1-homepage.png

agent-{{profile.lateness.stakeholders.channel}} click @e1
agent-{{profile.lateness.stakeholders.channel}} screenshot ./screenshots/step2-after-click.png

agent-{{profile.lateness.stakeholders.channel}} record stop
```

## Output Format

- Default format: WebM (VP8/VP9 codec)
- Compatible with all modern {{profile.lateness.stakeholders.channel}}s and video players
- Compressed but high quality

## Limitations

- Recording adds slight overhead to automation
- Large recordings can consume significant disk space
- Some headless environments may have codec limitations

--- templates/authenticated-session.sh ---

#!/bin/bash
# Template: Authenticated Session Workflow
# Purpose: Login once, save state, reuse for subsequent runs
# Usage: ./authenticated-session.sh <login-url> [state-file]
#
# RECOMMENDED: Use the auth vault instead of this template:
#   echo "<pass>" | agent-{{profile.lateness.stakeholders.channel}} auth save myapp --url <login-url> --username <user> --password-stdin
#   agent-{{profile.lateness.stakeholders.channel}} auth login myapp
# The auth vault stores credentials securely and the LLM never sees passwords.
#
# Environment variables:
#   APP_USERNAME - Login username/{{profile.lateness.stakeholders.channel}}
#   APP_PASSWORD - Login password
#
# Two modes:
#   1. Discovery mode (default): Shows form structure so you can identify refs
#   2. Login mode: Performs actual login after you update the refs
#
# Setup steps:
#   1. Run once to see form structure (discovery mode)
#   2. Update refs in LOGIN FLOW section below
#   3. Set APP_USERNAME and APP_PASSWORD
#   4. Delete the DISCOVERY section

set -euo pipefail

LOGIN_URL="${1:?Usage: $0 <login-url> [state-file]}"
STATE_FILE="${2:-./auth-state.json}"

echo "Authentication workflow: $LOGIN_URL"

# ================================================================
# SAVED STATE: Skip login if valid saved state exists
# ================================================================
if [[ -f "$STATE_FILE" ]]; then
    echo "Loading saved state from $STATE_FILE..."
    if agent-{{profile.lateness.stakeholders.channel}} --state "$STATE_FILE" open "$LOGIN_URL" 2>/dev/null; then
        agent-{{profile.lateness.stakeholders.channel}} wait --load networkidle

        CURRENT_URL=$(agent-{{profile.lateness.stakeholders.channel}} get url)
        if [[ "$CURRENT_URL" != *"login"* ]] && [[ "$CURRENT_URL" != *"signin"* ]]; then
            echo "Session restored successfully"
            agent-{{profile.lateness.stakeholders.channel}} snapshot -i
            exit 0
        fi
        echo "Session expired, performing fresh login..."
        agent-{{profile.lateness.stakeholders.channel}} close 2>/dev/null || true
    else
        echo "Failed to load state, re-authenticating..."
    fi
    rm -f "$STATE_FILE"
fi

# ================================================================
# DISCOVERY MODE: Shows form structure (delete after setup)
# ================================================================
echo "Opening login page..."
agent-{{profile.lateness.stakeholders.channel}} open "$LOGIN_URL"
agent-{{profile.lateness.stakeholders.channel}} wait --load networkidle

echo ""
echo "Login form structure:"
echo "---"
agent-{{profile.lateness.stakeholders.channel}} snapshot -i
echo "---"
echo ""
echo "Next steps:"
echo "  1. Note the refs: username=@e?, password=@e?, submit=@e?"
echo "  2. Update the LOGIN FLOW section below with your refs"
echo "  3. Set: export APP_USERNAME='...' APP_PASSWORD='...'"
echo "  4. Delete this DISCOVERY MODE section"
echo ""
agent-{{profile.lateness.stakeholders.channel}} close
exit 0

# ================================================================
# LOGIN FLOW: Uncomment and customize after discovery
# ================================================================
# : "${APP_USERNAME:?Set APP_USERNAME environment variable}"
# : "${APP_PASSWORD:?Set APP_PASSWORD environment variable}"
#
# agent-{{profile.lateness.stakeholders.channel}} open "$LOGIN_URL"
# agent-{{profile.lateness.stakeholders.channel}} wait --load networkidle
# agent-{{profile.lateness.stakeholders.channel}} snapshot -i
#
# # Fill credentials (update refs to match your form)
# agent-{{profile.lateness.stakeholders.channel}} fill @e1 "$APP_USERNAME"
# agent-{{profile.lateness.stakeholders.channel}} fill @e2 "$APP_PASSWORD"
# agent-{{profile.lateness.stakeholders.channel}} click @e3
# agent-{{profile.lateness.stakeholders.channel}} wait --load networkidle
#
# # Verify login succeeded
# FINAL_URL=$(agent-{{profile.lateness.stakeholders.channel}} get url)
# if [[ "$FINAL_URL" == *"login"* ]] || [[ "$FINAL_URL" == *"signin"* ]]; then
#     echo "Login failed - still on login page"
#     agent-{{profile.lateness.stakeholders.channel}} screenshot /tmp/login-failed.png
#     agent-{{profile.lateness.stakeholders.channel}} close
#     exit 1
# fi
#
# # Save state for future runs
# echo "Saving state to $STATE_FILE"
# agent-{{profile.lateness.stakeholders.channel}} state save "$STATE_FILE"
# echo "Login successful"
# agent-{{profile.lateness.stakeholders.channel}} snapshot -i

--- templates/capture-workflow.sh ---

#!/bin/bash
# Template: Content Capture Workflow
# Purpose: Extract content from web pages (text, screenshots, PDF)
# Usage: ./capture-workflow.sh <url> [output-dir]
#
# Outputs:
#   - page-full.png: Full page screenshot
#   - page-structure.txt: Page element structure with refs
#   - page-text.txt: All text content
#   - page.pdf: PDF version
#
# Optional: Load auth state for protected pages

set -euo pipefail

TARGET_URL="${1:?Usage: $0 <url> [output-dir]}"
OUTPUT_DIR="${2:-.}"

echo "Capturing: $TARGET_URL"
mkdir -p "$OUTPUT_DIR"

# Optional: Load authentication state
# if [[ -f "./auth-state.json" ]]; then
#     echo "Loading authentication state..."
#     agent-{{profile.lateness.stakeholders.channel}} state load "./auth-state.json"
# fi

# Navigate to target
agent-{{profile.lateness.stakeholders.channel}} open "$TARGET_URL"
agent-{{profile.lateness.stakeholders.channel}} wait --load networkidle

# Get metadata
TITLE=$(agent-{{profile.lateness.stakeholders.channel}} get title)
URL=$(agent-{{profile.lateness.stakeholders.channel}} get url)
echo "Title: $TITLE"
echo "URL: $URL"

# Capture full page screenshot
agent-{{profile.lateness.stakeholders.channel}} screenshot --full "$OUTPUT_DIR/page-full.png"
echo "Saved: $OUTPUT_DIR/page-full.png"

# Get page structure with refs
agent-{{profile.lateness.stakeholders.channel}} snapshot -i > "$OUTPUT_DIR/page-structure.txt"
echo "Saved: $OUTPUT_DIR/page-structure.txt"

# Extract all text content
agent-{{profile.lateness.stakeholders.channel}} get text body > "$OUTPUT_DIR/page-text.txt"
echo "Saved: $OUTPUT_DIR/page-text.txt"

# Save as PDF
agent-{{profile.lateness.stakeholders.channel}} pdf "$OUTPUT_DIR/page.pdf"
echo "Saved: $OUTPUT_DIR/page.pdf"

# Optional: Extract specific elements using refs from structure
# agent-{{profile.lateness.stakeholders.channel}} get text @e5 > "$OUTPUT_DIR/main-content.txt"

# Optional: Handle infinite scroll pages
# for i in {1..5}; do
#     agent-{{profile.lateness.stakeholders.channel}} scroll down 1000
#     agent-{{profile.lateness.stakeholders.channel}} wait 1000
# done
# agent-{{profile.lateness.stakeholders.channel}} screenshot --full "$OUTPUT_DIR/page-scrolled.png"

# Cleanup
agent-{{profile.lateness.stakeholders.channel}} close

echo ""
echo "Capture complete:"
ls -la "$OUTPUT_DIR"

--- templates/form-automation.sh ---

#!/bin/bash
# Template: Form Automation Workflow
# Purpose: Fill and submit web forms with validation
# Usage: ./form-automation.sh <form-url>
#
# This template demonstrates the snapshot-interact-verify pattern:
# 1. Navigate to form
# 2. Snapshot to get element refs
# 3. Fill fields using refs
# 4. Submit and verify result
#
# Customize: Update the refs (@e1, @e2, etc.) based on your form's snapshot output

set -euo pipefail

FORM_URL="${1:?Usage: $0 <form-url>}"

echo "Form automation: $FORM_URL"

# Step 1: Navigate to form
agent-{{profile.lateness.stakeholders.channel}} open "$FORM_URL"
agent-{{profile.lateness.stakeholders.channel}} wait --load networkidle

# Step 2: Snapshot to discover form elements
echo ""
echo "Form structure:"
agent-{{profile.lateness.stakeholders.channel}} snapshot -i

# Step 3: Fill form fields (customize these refs based on snapshot output)
#
# Common field types:
#   agent-{{profile.lateness.stakeholders.channel}} fill @e1 "John Doe"           # Text input
#   agent-{{profile.lateness.stakeholders.channel}} fill @e2 "user@example.com"   # Email input
#   agent-{{profile.lateness.stakeholders.channel}} fill @e3 "SecureP@ss123"      # Password input
#   agent-{{profile.lateness.stakeholders.channel}} select @e4 "Option Value"     # Dropdown
#   agent-{{profile.lateness.stakeholders.channel}} check @e5                     # Checkbox
#   agent-{{profile.lateness.stakeholders.channel}} click @e6                     # Radio button
#   agent-{{profile.lateness.stakeholders.channel}} fill @e7 "Multi-line text"   # Textarea
#   agent-{{profile.lateness.stakeholders.channel}} upload @e8 /path/to/file.pdf # File upload
#
# Uncomment and modify:
# agent-{{profile.lateness.stakeholders.channel}} fill @e1 "Test User"
# agent-{{profile.lateness.stakeholders.channel}} fill @e2 "test@example.com"
# agent-{{profile.lateness.stakeholders.channel}} click @e3  # Submit button

# Step 4: Wait for submission
# agent-{{profile.lateness.stakeholders.channel}} wait --load networkidle
# agent-{{profile.lateness.stakeholders.channel}} wait --url "**/success"  # Or wait for redirect

# Step 5: Verify result
echo ""
echo "Result:"
agent-{{profile.lateness.stakeholders.channel}} get url
agent-{{profile.lateness.stakeholders.channel}} snapshot -i

# Optional: Capture evidence
agent-{{profile.lateness.stakeholders.channel}} screenshot /tmp/form-result.png
echo "Screenshot saved: /tmp/form-result.png"

# Cleanup
agent-{{profile.lateness.stakeholders.channel}} close
echo "Done"
