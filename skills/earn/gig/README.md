# The Coconala loop

Four background jobs that run a [Coconala](https://coconala.com) seller account
around the clock: they read the job board and apply, keep the storefront honest,
answer buyers who ask questions before they buy, and work the orders that get
paid for. They run on one Mac, as launchd user agents, driving one logged-in
browser. There is no server and no API key.

Everything the loop needs is in this folder. `scripts/` is the code, `schemas/`
the shapes it makes a model answer in, `config/` the catalogue and the job
definitions, `agent-runner/` the engine that talks to the model, `evals/` the
replays, `tests/` the tests.

| lane | job label | every | what it does |
|---|---|---|---|
| apply | `ai.anicca.hf-gig-apply-direct` | 60s | Reads the public job board, judges which postings this seller can actually do, and submits an application with a proposal. |
| storefront | `ai.anicca.hf-gig-storefront-direct` | 60s | Reads the seller's own listings and their view/inquiry counts, and edits the ones people look at and never contact. |
| negotiate | `ai.anicca.hf-gig-reply-detector` | 180s | Watches talkrooms opened *before* purchase and answers the buyer's questions and estimate requests. |
| paid | `ai.anicca.hf-gig-paid-direct` | 300s | Works orders that have been paid for: reads the requirement, builds or reviews the deliverable, and decides whether it is good enough to hand over. |

Two more jobs support them:

| job label | what it does |
|---|---|
| `ai.anicca.hf-gig-browser` | Keeps one Chromium alive on a debugging port. All four lanes share it, because the login lives in its profile. |
| `ai.anicca.hf-gig-release-watch` | Fast-forwards this checkout to `origin/main` and moves idle lanes onto the new code. |

---

## What you need before you start

| | why |
|---|---|
| A Mac, Apple Silicon, macOS 14 or newer | The jobs are launchd user agents and the browser build is a macOS app bundle. |
| A **Codex subscription** and the `codex` CLI signed in | This is the only thing you pay for. Every judgement the loop makes goes through it. `codex login`, then check `~/.codex/auth.json` exists. |
| A **Coconala seller account** with at least one listing | This is the only account you create. You do not need to finish identity verification or add a bank account to start — those matter when you withdraw, not when you sell. |
| Python 3.13 or newer | `brew install python@3.14`. Then `pip3 install websockets beautifulsoup4 jsonschema`. |
| A CloakBrowser Chromium build under `~/.cloakbrowser/chromium-*/` | An ordinary Chrome will not do: the lanes attach over CDP, and the launcher passes `--fingerprint`, a flag only this build has. See [the browser](#the-browser) below — the version matters. |

Optional: the `openclaw` CLI, if you want the loop to narrate itself to your
Telegram. Without it the loop runs the same and simply does not report.

---

## Install

### 1. Get the code

```bash
git clone https://github.com/Daisuke134/life-manager.git ~/life-manager
cd ~/life-manager
```

### 2. Tell it about your machine

Everything machine-specific lives in one file. Create it, and put in it only the
things that differ from the defaults:

```bash
mkdir -p ~/.config/anicca/gig
cat > ~/.config/anicca/gig/install.json <<'JSON'
{
  "GIG_REPORT_CHAT": "",
  "GIG_BROWSER_FINGERPRINT": "80136"
}
JSON
```

Every key and its default is listed under [Configuration](#configuration). If
you are happy with all of them, an empty `{}` is a valid file, and so is no file
at all.

### 3. The browser

The lanes drive [CloakBrowser](https://github.com/CloakHQ/CloakBrowser), a Chromium
whose fingerprint is patched at the C++ source level. `pip install cloakbrowser`
installs the wrapper; the ~200 MB browser binary downloads on first use and caches
itself under `~/.cloakbrowser/chromium-<version>/`. The free tier needs a GitHub
sign-in at [cloakbrowser.dev/free](https://cloakbrowser.dev/free) to pick which
binary you get.

```bash
pip3 install cloakbrowser
python3 -c "from cloakbrowser import launch; b = launch(headless=True); b.close()"
ls ~/.cloakbrowser/          # chromium-<version>/ should now exist
```

**The version matters, and today you will get a newer one than is qualified here.**
CloakBrowser currently ships Chromium 150/151; the loop was qualified on 145.
`scripts/launch_gig_browser.sh` carries a TLS compatibility switch bounded to 145 and
146, because newer Chromium offers ML-KEM by default and on at least one real network
path the larger ClientHello is dropped — the browser completes TCP and then returns
`ERR_TIMED_OUT` while `curl` on the same machine is fine.

Outside that range the switch is not applied and the launcher says so on stderr. It
still starts, because plenty of networks never drop that ClientHello and there is no
reason to block those. **If the site loads under `curl` but not in this browser**, that
warning is your answer:

```bash
# after qualifying it on your own network
GIG_BROWSER_TLS_COMPAT=force  # set it in ~/.config/anicca/gig/install.json
```

Do not widen the `145|146` case on faith. Qualify the major you actually have, against
the real site, and record what you measured.

### 4. Start the browser and log in — the one manual step

```bash
python3 skills/earn/gig/scripts/gig_release.py activate --jobs ai.anicca.hf-gig-browser
```

That launches Chromium with a debugging port on `127.0.0.1:9223` and a profile
at `~/.cloak/profiles/gig-daily-driver`. Open it, go to coconala.com, and **log
in once, by hand**. Solve whatever it asks you — that is the point of doing it
yourself.

The session then lives in that profile directory. The lanes never see your
password; they attach to the browser that is already logged in. Cookies are
snapshotted to `~/.cloak/vault/gig-daily-driver/` so a browser restart can
restore the session instead of asking you again.

Leave this browser running. It is the only thing standing between the loop and
a login prompt.

### 5. Describe what you sell

`config/storefront-catalog-scorecard.json` is the loop's model of the seller:
one entry per listing, what it promises, what evidence backs the promise, and
which listings are worth improving first. The one in this repository describes
its author's catalogue. **Replace it with yours** — the apply lane uses it to
decide what it is allowed to claim, and the storefront lane uses it to decide
what to edit.

Two more directories are seller-specific in the same way, and ship filled in as
worked examples rather than as templates:

| | |
|---|---|
| `contracts/` | What each listing offers, in the shape the lanes reason over. |
| `assets/storefront/<service_id>/` | The gallery images the storefront lane uploads to a listing, keyed by that listing's id. The ids here are its author's. |

Yours will not have those ids. Nothing breaks if you leave them — no listing of
yours matches — but the storefront lane has nothing to publish for your listings
until you put your own contracts and images beside them.

### 6. Start the lanes

```bash
python3 skills/earn/gig/scripts/gig_release.py activate
```

This cuts an immutable release of the current commit under
`~/gig/releases/life-manager/<sha>/`, writes the four launchd jobs, loads them,
and then reads the arguments back out of `launchctl` to prove that the jobs
launchd is holding really are the ones it just installed.

To also keep them following `main` by themselves:

```bash
python3 skills/earn/gig/scripts/gig_release.py activate --jobs ai.anicca.hf-gig-release-watch
```

### 7. Watch it work

```bash
python3 skills/earn/gig/scripts/gig_release.py status
launchctl kickstart gui/$(id -u)/ai.anicca.hf-gig-storefront-direct
```

Then look at what it actually did, not at whether the process exited:

```bash
tail -1 ~/gig/apply-direct/wakes.jsonl      | python3 -m json.tool | head -20
tail -1 ~/gig/storefront-direct/wakes.jsonl | python3 -m json.tool | head -20
cat ~/gig/evidence/paid-direct-live/latest.json | python3 -m json.tool | head -20
ls -t ~/gig/evidence | head
```

A lane that exits 0 and observed nothing is not working. `observed`,
`official_services_read` and `replied` are the numbers that mean something.

---

## Configuration

`~/.config/anicca/gig/install.json` overrides these. Nothing here is a secret;
no lane reads a credential from its environment.

| key | default | what it is |
|---|---|---|
| `PYTHON` | `/opt/homebrew/bin/python3` | The interpreter the jobs run. Must have `websockets`. |
| `GIG_STATE_DIR` | `~/gig` | Everything the loop remembers: ledgers, evidence, order workspaces, locks. |
| `GIG_LOG_DIR` | `~/gig/logs` | launchd stdout/stderr for each job. |
| `GIG_BRAKE_DIR` | `~/gig/state` | Where an operator brake file stops a lane. See below. |
| `LIFE_MANAGER_HOME` | `~/.local/state/life-manager` | Shared state directory for this repo's loops. |
| `CDP_PORT` | `9223` | The debugging port the shared browser listens on. |
| `CDP_DAILY_DRIVER_PROFILE` | `~/.cloak/profiles/gig-daily-driver` | The Chromium profile that holds your login. |
| `SESSION_VAULT_DIR` | `~/.cloak/vault/gig-daily-driver` | Cookie snapshots used to restore the session after a restart. |
| `GIG_BROWSER_FINGERPRINT` | *(empty)* | Fingerprint seed passed to the browser build. |
| `GIG_REPORT_CHAT` | *(empty)* | Telegram chat id for reports. Empty means the loop does not report. |
| `GIG_SANDBOX_DENY` | *(empty)* | Colon-separated absolute paths the sandboxed paid builder must not read — other checkouts, other loops' state. Must be absolute; a relative entry is refused rather than silently ignored. |

The job definitions themselves are `config/launchd-jobs.json`. Editing that file
and re-running `gig_release.py activate` is how you change a schedule, an
argument, or an environment variable — not by editing the plists in
`~/Library/LaunchAgents`, which are generated and will be overwritten.

---

## What it will not do

These are enforced in code, not by convention.

- **Formal delivery needs the buyer's own words as evidence.** Ticking 正式な納品
  is the irreversible step, so `validate_queue_contract()` in
  `scripts/coconala_formal_delivery_browser.py` refuses to drive toward it unless
  the queue carries an approval whose identity equals the newest message in the
  room, whose side is `buyer`, with a real message id and a 64-character content
  hash. No approval, no delivery — `formal_buyer_approval_evidence_required`.
  A pass also cannot escalate to formal at send time if it was not prepared as
  formal (`presend_action_escalation`), and a subscription room, which has no such
  checkbox at all, is refused outright.
- **It leaves hand-worked orders alone.** `OWNER_WORKED_TALKROOMS` in
  `scripts/paid_direct.py` lists orders that a person is handling. The lane still
  observes them so the backlog stays honest, and stops before any effect.
- **An operator brake stops a lane cold.** `scripts/gig_brake.sh raise --owner
  NAME --reason TEXT` writes a brake file; each lane refuses to start while it is
  held, and refuses to start if the brake file exists but cannot be read.
- **The paid builder runs sandboxed.** When it inspects or produces files it runs
  under `sandbox-exec` with a profile that denies it the release it runs from,
  the other orders' workspaces, and whatever else `GIG_SANDBOX_DENY` names. A
  profile that fails to compile stops the step; it never falls back to running
  unsandboxed.

---

## Known limits

Honest list. These are measured, not suspected.

- **The negotiate lane is slower than its own freshness rule.** It revalidates
  one talkroom per wake, every 180 seconds. With ~115 rooms a full sweep takes
  about 5.8 hours, while a room is considered stale after 30 minutes. The fast
  path exists — a change detector that would revalidate only rooms that moved —
  but it reports zero changes and no alarm fires when it does. In practice a
  buyer question can wait hours rather than minutes.
- **The paid lane's feedback digest is not stable.** The window that assembles
  the latest buyer feedback has been observed regressing to older concatenated
  text within the same day, which means the digest a builder would act on cannot
  currently be trusted to be the newest one.
- **The feedback cycle patch only fires once per project.** `_feedback_cycle_patch()`
  in `scripts/delivery_project.py` is wired, but the caller guards it on the
  project's `state.json` not existing yet, so it runs at bootstrap and never
  again. Do not loosen that guard before the digest above is stable: an unstable
  digest plus a live cycle is how a builder would act on stale instructions
  against a real customer's site.

---

## Keeping it running

`gig_release.py watch` is what the release watcher runs. It fetches, fast-forwards
`main`, and for every lane that is not already on the release for that commit it
builds one and switches it — skipping any lane that is mid-pass, because booting
a lane out in the middle drops its browser lease and strands its locks. The lane
gets picked up on the next tick instead.

Old releases accumulate under `~/gig/releases/`. They are ~50 MB each and safe to
delete once no loaded job points at one; `gig_release.py status` prints exactly
which ones are in use.
