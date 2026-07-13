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
bash ~/anicca/skills/browser/ensure_browser.sh          # ALIVE | RECOVERED | FAILED
python3 ~/anicca/skills/browser/scripts/cdp_tab_gc.py   # close the tabs the last pass left behind
```

If `ensure_browser.sh` prints `FAILED`, do **not** hang or retry forever — skip the browser steps,
run whatever file-only work the pass can still do, and report the failure honestly.

## What each piece is for

| Piece | Problem it solves |
|---|---|
| `ensure_browser.sh` | Chromium is dead → the loop is blind. Relaunches it with capped caches and restores the logins. Idempotent: prints `ALIVE` when it is already up. |
| `scripts/session_vault.py` | A hard kill takes the newest cookies with it → re-login → 2FA → **a human**, which breaks autonomy. Snapshots every cookie to `~/.cloak/vault/daily-driver/auth-state.json` (launchd `ai.anicca.session-vault`, every 30 min) and pushes it back in when the browser returns. |
| `scripts/cdp_tab_gc.py` | Each task opens a tab and nothing closes it. Fifteen-plus live tabs starved memory (load average past 21) and killed Chromium. Keeps one working tab, closes the rest. |

```bash
python3 ~/anicca/skills/browser/scripts/session_vault.py dump      # snapshot the current logins
python3 ~/anicca/skills/browser/scripts/session_vault.py restore   # push them back into the browser
python3 ~/anicca/skills/browser/scripts/session_vault.py status    # how many cookies, which origins, how old
```

Run `dump` right after any fresh human login, so that login is banked forever.

## Rules for browser loops

- **Never launch your own Chromium** and never point at your own `--user-data-dir`. One browser, one
  profile. A second profile means a second set of logins, which means a human logging in twice.
- **Never close a tab you did not open**, and never kill the browser to "reset" it — that throws away
  everyone else's work. Use the tab GC.
- **Close what you open.** Tabs are the leak that kills the browser.
- Caches are capped at launch (`--disk-cache-size`, cache dir under `/tmp`). An uncapped profile grew
  to 1.0GB, 97% of it disposable cache, and filled the disk the loops write their ledgers to.

## Known gap (see task #28)

Loops still share one tab space, so a `navigate` from one loop can destroy another's half-filled form.
The fix is one browser with **one BrowserContext per task** (CDP `Target.createBrowserContext`:
"Similar to an incognito profile but you can have more than one"), seeded from the vault's
`auth-state.json` because contexts do not share cookies, and disposed when the task ends.
