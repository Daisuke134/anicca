---
name: browser-foundation
description: Shared browser foundation every loop that drives the logged-in daily-driver Chromium (CDP :9222) must call FIRST — gig, clip, IG posting, Life Manager marketing, promote, warmup. Heals a dead browser, restores logins from the cookie vault so no human ever re-authenticates, and closes the tabs that pile up and kill Chromium. Read this before writing any new browser loop.
disable-model-invocation: true
---

# Browser foundation — open your eyes before you work

Every autonomous loop here drives one shared, logged-in Chromium over CDP `:9222`
(profile `~/.cloak/profiles/daily-driver`). That browser is the single point of failure for the
whole business: when it dies, every loop goes blind and keeps "running" while doing nothing.

This actually happened (2026-07-13): Chromium died from memory pressure, the gig loop kept waking up
hourly for twelve hours and accomplished nothing, and the only recovery lived *outside* the loop in a
guard that fired once and gave up.

**Self-healing belongs inside the loop.** Call this at the top of every pass, before any browser step.

## Call this first, every pass

```bash
bash $LIFE_MANAGER_REPO/skills/browser/ensure_browser.sh          # ALIVE | RECOVERED | FAILED
python3 $LIFE_MANAGER_REPO/skills/browser/scripts/cdp_tab_gc.py   # close the tabs the last pass left behind
```

If `ensure_browser.sh` prints `FAILED`, do **not** hang or retry forever — skip the browser steps,
run whatever file-only work the pass can still do, and report the failure honestly.

## What each piece is for

| Piece | Problem it solves |
|---|---|
| `ensure_browser.sh` | Chromium is dead → the loop is blind. Relaunches it with capped caches and restores the logins. Idempotent: prints `ALIVE` when it is already up. |
| `scripts/session_vault.py` | A hard kill takes the newest cookies with it → re-login → 2FA → **a human**, which breaks autonomy. Snapshots every cookie **and localStorage** (some SPAs keep the session token there) to `~/.cloak/vault/daily-driver/auth-state.json` (launchd `ai.anicca.session-vault`, every 30 min) and pushes it back in when the browser returns. Also does `keepalive` (extend the server-side session + detect logout) and `totp` (generate a 2FA code so re-login needs no human). |
| `scripts/cdp_tab_gc.py` | Each task opens a tab and nothing closes it. Fifteen-plus live tabs starved memory (load average past 21) and killed Chromium. Keeps one working tab, closes the rest. |
| `scripts/scout.py` | Articles teach theory; the deepest signal is on the actual winning pages. Every improve cycle should LOOK at who is already winning (top sellers, viral clips, best-selling apps) and copy what they do. Fetches winner pages (public via `crwl`, or logged-in via CDP) and returns their content for the loop's model to learn from. `python3 scripts/scout.py '{"urls":[...],"mode":"public\|browser"}'` |

```bash
python3 $LIFE_MANAGER_REPO/skills/browser/scripts/session_vault.py dump      # snapshot logins (cookies + localStorage)
python3 $LIFE_MANAGER_REPO/skills/browser/scripts/session_vault.py restore   # push them back into the browser
python3 $LIFE_MANAGER_REPO/skills/browser/scripts/session_vault.py status    # how many cookies, which origins, how old
python3 $LIFE_MANAGER_REPO/skills/browser/scripts/session_vault.py keepalive https://coconala.com/mypage/dashboard  # warm + detect logout
python3 $LIFE_MANAGER_REPO/skills/browser/scripts/session_vault.py totp @coconala   # fresh 2FA code from stored secret
```

Run `dump` right after any fresh login, so that login is banked forever.

## Staying logged in with ZERO human — the re-login ladder every loop follows

"Logged out" must never reach a human (a Telegram asking Dais to log in does not scale to hundreds of
accounts). When a page redirects to `/login`, the loop climbs this ladder itself, in order, and only
records a report — it never waits for a person:

```
1. session_vault.py restore            # push the banked cookies + localStorage back
2. session_vault.py keepalive <authed-url>   # still logged out?
3. still out → self-login with the account's OWN credentials:
     email + password (from env)  →  if 2FA asked: session_vault.py totp @<service>
   ★ Every earn account is created with an AI-owned email + app-based 2FA (TOTP secret stored in
     ~/.cloak/vault/daily-driver/totp-secrets.json, chmod 600). NEVER Dais's Google/passkey account —
     passkey and SMS-2FA cannot be finished by a machine. ★
4. only if all of the above fail: append a one-line report and run the file-only path. Do NOT block on a human.
```

The profile itself (`--user-data-dir`, never deleted, caches capped) is what keeps you logged in 99%
of the time; the ladder is for the rare server-side expiry. To cut expiry frequency: keep the profile,
keep a stable fingerprint, and (at scale) pin a sticky proxy per account.

## Rules for browser loops

- **Never launch your own Chromium** and never point at your own `--user-data-dir`. One browser, one
  profile. A second profile means a second set of logins, which means a human logging in twice.
- **Never close a tab you did not open**, and never kill the browser to "reset" it — that throws away
  everyone else's work. Use the tab GC.
- **Close what you open.** Tabs are the leak that kills the browser.
- Caches are capped at launch (`--disk-cache-size`, cache dir under `/tmp`). An uncapped profile grew
  to 1.0GB, 97% of it disposable cache, and filled the disk the loops write their ledgers to.

## Lease your own space — never share a tab with another loop

Loops used to share one tab space, so a `navigate` from clip would destroy the form gig was halfway
through filling, and neither could tell. Take a context instead: CDP `Target.createBrowserContext` is
"Similar to an incognito profile but you can have more than one", and nothing outside your context can
reach into it.

For an agent subprocess, the parent/controller acquires and releases the lease. The agent receives
only a stable handle and must never copy or transcribe the opaque page websocket:

```bash
python3 "$GIG_DIR/scripts/cdp_nav_snapshot.py" observe \
  --lease "$ANICCA_BROWSER_LEASE" --url "$URL" \
  --screenshot "$SCREENSHOT" --dom "$DOM"
```

Controller code that owns a driver without `--lease` support may resolve `ws` internally from the
atomic lease ledger. Do not expose that value to an LLM command-building step.

A fresh context starts logged out, so `acquire` seeds it from the vault's cookies — verified live:
a leased context reaches `coconala.com/mypage/dashboard` already authenticated. A loop killed with -9
never releases, so run `cdp_context_lease.py gc --idle-min 45` from the healthcheck to reap what it
left holding.

Rules: one context per task, the owning controller always releases it, and no worker touches another
task's context.
