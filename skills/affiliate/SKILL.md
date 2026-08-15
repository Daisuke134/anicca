---
name: affiliate
description: Builds, runs, and migrates the Life Manager Affiliate Agent across macOS devices.
---

# Life Manager Affiliate Skill

status: `LOCAL_RUNTIME_READY`
legacy_migration: `MIGRATION_ONLY`
execution: `MACOS_LOCAL_ONLY`

The canonical source is this `skills/affiliate` directory in the Life Manager
repository. `legacy/` contains byte-preserved evidence only; archived files are
never executed by this skill.

Mutable state lives at
`${LIFE_MANAGER_STATE_HOME:-$HOME/.local/state/life-manager}/affiliate`.
Installed data lives at
`${LIFE_MANAGER_DATA_HOME:-$HOME/.local/share/life-manager}/affiliate`.

The runtime follows the proven Coconala boundary: an immutable release, mutable
append-only receipts outside Git, an isolated browser profile, and launchd-owned
local wakes. It does not use Railway or an Anicca API redirect. Public content
uses an authenticated provider tracking link directly; clicks are not revenue.

F0 provides four deterministic, non-publishing primitives:

- `bootstrap/install.sh` verifies a reviewed pinned manifest and writes an
  atomic machine-capability receipt;
- `scripts/authority_inventory.py` binds a Keychain reference to one explicit
  intent and records human-only external challenges;
- `scripts/profile_provisioner.py` creates isolated EN/JA browser roots without
  launching or copying a browser session.
- `scripts/machine_capability_inventory.py` receipts an explicitly requested
  macOS browser app from held no-follow file descriptors without launching it;
  generic executable admission remains fail-closed.

The first provider CLI slice is live:

```bash
skills/affiliate/affiliate provider inspect \
  --provider hubspot-impact --cdp-port 9327 --receipt "$RECEIPT"
```

It attaches read-only to the dedicated `impact-en:9327` browser, selects exactly one
origin/title/path-bound tab, maps rendered text through the versioned provider
playbook, and writes an atomic sanitized receipt. Unknown UI never becomes an
approval. The current slice observes status only; it cannot submit or publish.

Use `provider poll` with the same arguments in a loop. The first observation or
a real state change returns `changed=true` and a deterministic `transition_id`;
an unchanged retry returns `next_action=NO_STATE_CHANGE`. Downstream actions
must deduplicate on `transition_id`.

Use credential-first resume only on a supported semantic playbook:

```bash
skills/affiliate/affiliate provider resume \
  --provider elevenlabs --cdp-port 9324 --receipt "$RECEIPT"
```

It reads the mode-0600 Git-external Markdown, clears and fills the named controls
through CDP, submits at most once per invocation, and requires rendered readback.
Credentials never enter stdout, receipts, Git, selectors, or command arguments.

Install the local release and its four launchd owners:

```bash
skills/affiliate/scripts/install-release.sh
skills/affiliate/affiliate loop wake
skills/affiliate/affiliate loop placement --placement article-1 --locale en
```

`ai.anicca.affiliate-browser` owns the isolated provider profile on CDP `9324`;
`ai.anicca.affiliate-x-browser` owns the English X profile on CDP `9326`.
`ai.anicca.affiliate-loop` wakes every 10 minutes. Receipts live under
`~/.local/state/life-manager/affiliate`; provider passwords and the executable
ElevenLabs link remain only in the mode-0600 private Markdown. The current wake
polls the rendered ElevenLabs login state, records only a deterministic provider
transition ID, and requires `AUTHENTICATED` before publication readiness. It
still proves readiness only: publication, provider click readback, commission,
and payout stay separate later gates.

Publish an already approved English X artifact only through the dedicated
Affiliate browser:

```bash
skills/affiliate/affiliate x post publish \
  --content "$ARTIFACT" --placement elevenlabs-en-1
```

The command verifies `@selawmqt` on CDP `9326`, requires an explicit affiliate
disclosure and one owned `aniccaai.com/blog/` CTA, persists an effect-possible
fence before clicking, reconciles an identical timeline post on retry, and only
returns `LIVE` after an exact post-page readback. It never prints the post body
or a provider tracking link. A content policy decision and live owned article
remain prerequisites; the command does not generate or approve copy.

Refresh the versioned ElevenLabs evidence plan without an LLM-dependent parser:

```bash
skills/affiliate/affiliate sources capture --plan elevenlabs-en
```

The admitted routes are installed CRWL for official web pages and `gh api` for
the official SDK. Raw artifacts and deduplicated receipts stay under the
Git-external Affiliate state root. Each receipt binds locale, evidence class,
license, parser version, body hash, observation time, and expiry; adapter failure
is fail-closed rather than converted into an empty source.

Build the first source-bound English article into private runtime state:

```bash
skills/affiliate/affiliate content build
```

The builder requires fresh official support markers and the executable private
ElevenLabs link, places disclosure before the first CTA, and prints only the
artifact identity and hash. The article body and tracking link remain mode-0600
Git-external state until the later policy and owned-publication boundary.

Before publication, issue the deterministic policy receipt and exact-once
placement intent:

```bash
skills/affiliate/affiliate content policy
skills/affiliate/affiliate loop placement \
  --placement elevenlabs-plans-for-solo-creators --locale en
```

The policy command fails closed unless the artifact hash and fresh source hashes
match, the disclosure precedes the first CTA, exactly one owned HTTPS
`try.elevenlabs.io` link exists, and forbidden income guarantees are absent. It
stores no tracking URL in its receipt. `owned publish` independently requires the
matching `PASS` receipt and later reads both disclosure markers and the exact link
back from production HTML.

After the owned article has a `LIVE` receipt, build and publish its disclosed X
artifact:

```bash
skills/affiliate/affiliate content build-x
skills/affiliate/affiliate x post publish \
  --content ~/.local/state/life-manager/affiliate/x-content/elevenlabs-en-1.txt \
  --placement elevenlabs-en-1
```

Both commands require the exact owned publication receipt to be `LIVE`; the X
publisher rechecks it before opening the composer.

Capture the official PartnerStack overview after its one-time account,
email-verification, partnership, and program-terms bootstrap:

```bash
skills/affiliate/affiliate revenue observe
skills/affiliate/affiliate revenue capture
skills/affiliate/affiliate revenue reconcile
```

The observer extracts rendered bilingual metric cards, preserves the immutable
initial `BASELINE_ONLY` values and timestamp, reports later deltas, keeps
unavailable approved/reversed amounts as `null`, and returns the browser to
ElevenLabs home so the existing provider wake continues to work. The initial
total is never retroactively assigned to a placement.

`revenue capture` reads the rendered PartnerStack Commission Report and Payouts
surfaces, verifies their real field schemas, and writes a mode-0600 raw rendered
artifact plus a sanitized hash receipt under Git-external state. An empty report
is recorded as `EMPTY`; it is never replaced by fixtures or counted as money.
The authenticated report JSON is the row-count authority. Its provider-native
`reward_key`, raw status, amount, and attribution fields are normalized inside
the private artifact; customer name and email never enter the normalized ledger.
`revenue reconcile` verifies the source artifact hash and appends one stable
transition per provider key, raw status, amount, and source hash. Replaying the
same report is a no-op; a later provider status creates a new append-only event.
It joins a row to one LIVE owned placement by sub-ID/shared-ID or tracking-link
fingerprint. Zero or multiple candidates remain explicit `UNMATCHED` or
`AMBIGUOUS`; raw tracking links and customer PII never enter the ledger.

The 10-minute local wake invokes `observe → capture → reconcile` only when the
provider is authenticated and its independent one-hour revenue cooldown is due.
The cooldown receipt is written after all three commands succeed; a partial
failure is retried by the next wake rather than hidden for an hour.

Each wake also derives at most one owner-readable semantic transition. It first
appends that transition to `telegram-outbox.jsonl`, then sends it through the
existing `openclaw message send` Telegram transport. A successful delivery is
recorded in `telegram-sent.jsonl` with the provider `messageId`. Stable event
UUIDs suppress repeated empty-report/status notifications across later wakes;
tracking links and customer PII are never included.

Every supported external mutation is wrapped by `scripts/job_journal.py`.
Immediately before provider login submit, X profile save, X post publish, owned
Git push, or Telegram send, the adapter persists a mode-0600 job containing
`run_id`, `job_id`, `state`, `attempt`, `action_fingerprint`, `cooldown`, and the
last verified external object. Only a semantic readback changes it from
`EFFECT_STARTED` to `VERIFIED`; an unresolved effect refuses a blind retry.
On a later process, a fresh provider/profile/post/publication/Telegram readback
may reconcile exactly one unresolved target. It keeps the original `run_id` and
`job_id`, increments `attempt`, and records `resumed=true`; zero or multiple
unresolved effects cannot be silently retried.

Build and deliver the non-affiliate English foundation article through the same
installed skill:

```bash
skills/affiliate/affiliate content build-foundation
skills/affiliate/affiliate owned publish \
  --slug how-to-test-ai-voice-tools-before-you-pay \
  --landing-root "$CLEAN_PRODUCTION_WORKTREE"
```

`owned publish` accepts only a hash-valid `READY_FOR_PUBLICATION` artifact,
writes one deterministic blog JSON target, refuses unrelated worktree/index
changes, commits and pushes only that target, then records `DELIVERED` until a
later tick reads the title and three immutable markers from the public page.

Use the versioned English program research before any application:

```bash
skills/affiliate/affiliate programs list
skills/affiliate/affiliate programs next --decision READY_NO_REVIEW
skills/affiliate/affiliate programs credential --id hubspot-impact
python3 -c 'import secrets; print("A!" + secrets.token_hex(24))' | \
  skills/affiliate/affiliate programs store-credential \
  --id elevenlabs --label ElevenLabs
```

The registry stores only official-source eligibility and the latest receipted
application decision. Execute its `next_action`, then require authenticated
rendered readback before changing application or tracking-link state. Never
bulk-apply past an audience, content, fit, or traffic gate.

Provider passwords are never committed. The mode-0600 Git-external local
`~/.config/anicca/affiliate-credentials.md` is the recovery SSOT and is written
before any signup/reset submit. Each program may also bind to a fixed
`keychain://service/account` mirror. `programs credential` checks that mirror:
only a non-empty value is `VERIFIED_NONEMPTY`; a present but empty item is
`MISSING_OR_EMPTY` and login stays disabled. Impact uses
`keychain://ai.anicca.affiliate.provider.impact/primary`. After official recovery,
write the new value there and prove a fresh-tab login before resuming Grammarly.
`store-credential` reads the secret only from stdin, writes the Git-external
mode-0600 private Markdown first, then mirrors it to the fixed program Keychain
reference, and returns status only. Run it before every signup/reset submission;
after fresh login repeat with `--verification VERIFIED_LOGIN`. Never pass a
password on the affiliate CLI command line.

When an approved program delegates reporting to a separate network dashboard,
bootstrap a separate login section without reusing the program password:

```bash
PASSWORD_GENERATOR | skills/affiliate/affiliate programs store-credential \
  --id elevenlabs --label PartnerStack --source-label ElevenLabs \
  --credential-ref keychain://ai.anicca.affiliate.provider.partnerstack/elevenlabs
```

The source label contributes only the existing login identifier. The new password
is read from stdin and saved to the new private Markdown section before Keychain.

The committed bootstrap manifest pins PBS CPython `3.14.7+20260814` for macOS
arm64 by immutable URL and SHA-256. The installer verifies and extracts the same
held artifact, validates the full runtime tree, and atomically activates it
without changing PATH or the system Python. The current Mac also has a receipted
CloakBrowser app. Affiliate-only Keychain readback is live-proven; an unverified
reference is never `AUTHORIZED`. Authenticated X account-handle verification,
publication, provider commission readback, and revenue remain gated; launchd and
the isolated local browser are owned by this installed skill.
