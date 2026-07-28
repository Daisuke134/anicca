# BROWSER-AUTH-1 Design

**Status:** approved by the user's “Yes, let’s do it one by one” after the ordered
Life Manager browser roadmap was presented.

**Goal:** Life Manager restores an authorized browser session in Railway-private
Steel after a `life-call` restart without mixing tenants or persisting raw
passwords, and fails closed to an honest re-authentication handoff when that
session is absent, corrupt, expired, or rejected by the provider.

## Scope

BROWSER-AUTH-1 owns session continuity and isolation. It does not claim that one
cookie works on every provider, bypass CAPTCHA/2FA/KYC, build the later
three-intent provider matrix, or stop any currently loaded Mac loop.

The accepted credential contract is session-first:

1. an agent-owned or user-authorized login happens once in a live cloud browser;
2. raw username/password/OTP values are never written to the repository, job,
   trace, receipt, or session table;
3. Steel exports the resulting browser `sessionContext`;
4. Life Manager encrypts that context under a Railway runtime key and binds it
   to one `uid + origin + principal_kind`;
5. a later cloud job decrypts and injects only the exact matching context into a
   fresh Steel session.

`principal_kind` is closed to `agent_owned` and `user_provided`. A browser job
that does not depend on an authenticated account keeps `principal_kind = none`
and never reads the auth-session table.

## Chosen architecture

### Rejected: Steel `persist: true`

Steel's current OSS `SessionService` resolves `persist: true` to one fixed
`user-data-dir`. That is convenient for a single actor but is not a tenant
boundary. Sharing it would allow cookies and local storage from one Life Manager
tenant to enter another tenant's browser.

### Selected: encrypted `sessionContext` round-trip

Steel already exposes both halves needed by Life Manager:

- `GET /v1/sessions/:sessionId/context` exports cookies, localStorage,
  sessionStorage, and IndexedDB;
- `POST /v1/sessions` accepts the same `sessionContext` object.

Life Manager therefore remains the tenant-aware owner of encrypted state while
Steel remains an ephemeral Chromium worker.

## Components

### `browser-auth-session-store.js`

Owns origin normalization, AES-256-GCM sealing/opening, closed context
validation, tenant-bound database reads/upserts, and invalidation.

- Runtime key: `LM_BROWSER_SESSION_KEY`, exactly 64 hexadecimal characters.
- AAD: `uid + "\n" + origin + "\n" + principal_kind + "\n1`.
- Unique key: `(uid, origin, principal_kind)`.
- Plaintext: only the bounded Steel `sessionContext` JSON.
- Database columns expose ciphertext, IV, tag, key version, context hash,
  timestamps, and state; no cookie name/value or local-storage value is
  queryable in plaintext.
- Tables and functions are service-role-only with RLS enabled.

### `steel-cdp-client.js`

Adds the verified Steel context endpoint. It accepts only the existing
Railway-private Steel base URL, validates the returned closed context shape, and
rejects oversized or malformed data before it reaches encryption.

### `stagehand-steel-driver.js`

`openSession({ uid, goal, requiresLogin, principalKind })` extracts only an
explicit public HTTPS origin. For a login-dependent job it reads the exact
tenant/origin/principal context and passes it to `createRawSession`. Discovery
jobs without an explicit origin do not spray stored contexts across candidate
sites.

Before release, the driver exports and saves the context only for a
login-dependent job whose provider did not report a login/challenge handoff.
An explicit login handoff invalidates the stale row rather than overwriting it
with a logged-out context.

### Queue/runtime trace

The classifier adds `principal_kind`; the durable job stores only that enum.
Trace stages add:

- `auth_context_loaded`
- `auth_context_saved`
- `auth_context_invalidated`

Metadata is bounded to public origin, principal kind, boolean outcome, context
hash, and key version. Raw browser context and encryption material are forbidden.

## Data flow

```text
Telegram request
    ↓ strict classifier (requires_login + principal_kind)
tenant-bound PostgreSQL browser job
    ↓ claim
auth store: uid + origin + principal_kind
    ↓ decrypt exact row or return none
POST Steel /v1/sessions { sessionContext? }
    ↓ Stagehand over private CDP
provider authenticated readback
    ↓
GET Steel /v1/sessions/:id/context
    ↓ validate → AES-256-GCM → tenant row
release Steel → Telegram receipt
```

After a Railway redeploy, the process-local Stagehand map is empty, but the
encrypted PostgreSQL row remains. The next job creates a new Steel session and
restores the same provider state.

### Read-only authentication receipt

`browser_auth_continuity_readback` is a zero-action path: it creates no
Stagehand agent and calls none of `agent`, `execute`, or `act`. The model's
typed extract is auxiliary evidence, never the authentication oracle.

Before a positive receipt, the driver independently revalidates that the final
page is public HTTPS and has the exact origin of the explicit requested URL. It
then evaluates only bounded booleans in the live DOM: visible password,
one-time-code/authentication, challenge/CAPTCHA, KYC, and payment UI, plus
whether the model's bounded, secret-safe protected-content marker is actually
visible. A positive receipt requires all of these simultaneously:

- the typed extract reports authenticated continuity and supplies a marker;
- the final origin is the requested origin;
- no URL, model, or DOM handoff/risk signal exists;
- the safe marker is independently present in the DOM; and
- `handoffReason === null`.

Every other read-only outcome fails closed as a structured handoff. Its durable
status is one closed value (`authenticated` or `<reason>_required`) and its
confirmation identifier is always `null`; model-supplied status, identifiers,
tokens, cookies, email addresses, URLs, and control characters never enter the
receipt, result, or trace. The normal browser-action receipt contract is
unchanged.

## Failure behavior

| Failure | Required behavior |
|---|---|
| Missing key | Auth-dependent job fails closed before browser action |
| No stored context | Open unauthenticated provider page and return honest login handoff |
| Wrong tenant/origin/principal | No row is returned; never fall back to another row |
| Ciphertext/AAD mismatch | Reject and invalidate only the exact row |
| Provider rejects restored state | `handoff_required(login)` and invalidate exact row |
| Context export fails | Preserve the prior valid row, report save failure, release Steel |
| Steel release fails | Existing release-by-id then single-slot release-all fallback remains |
| CAPTCHA/2FA/KYC/payment | No bypass and no completion claim |
| Read-only model claims success on login/risk UI | Independent URL/DOM guard overrides it and returns handoff |
| Read-only final page is unsafe or cross-origin | Reject as unverified; never emit a positive receipt |
| Protected marker is absent from the live DOM | Reject as unverified; never trust the model alone |

## Deferred minor / final review

- Filter cookies whose finite `expires` timestamp is already in the past before
  sealing or comparing an exported context. Chromium already discards those
  cookies on import; filtering them earlier removes a harmless context-count
  mismatch. This does not block auth continuity because provider authentication
  is verified independently and the observed dropped item is not the
  HttpOnly session cookie.

## Verification contract

BROWSER-AUTH-1 is done only when all of the following are fresh evidence:

1. two tenant IDs at the same origin restore different opaque session markers;
2. the wrong tenant, origin, or principal returns no context;
3. repository, logs, trace, Telegram, and receipt contain zero raw cookie,
   password, token, IV, tag, key, or decrypted context values;
4. an authenticated provider readback succeeds before a `life-call` restart;
5. the same authenticated readback succeeds after an exact Railway redeploy from
   a new process and new Steel session;
6. an invalidated/expired session produces an honest re-authentication handoff;
7. every Steel session is released and no local Mac browser is used;
8. migration readback, focused tests, full suite, deployment SHA, job IDs,
   Steel IDs, provider URLs, Telegram evidence IDs, and secret-free hashes are
   recorded under `docs/evidence/browser/`.

## Primary evidence

| Source | URL | Core evidence |
|---|---|---|
| Steel `sessions.routes.ts` | https://github.com/steel-dev/steel-browser/blob/main/api/src/modules/sessions/sessions.routes.ts | Defines `GET /sessions/:sessionId/context` and `POST /sessions` |
| Steel `sessions.schema.ts` | https://github.com/steel-dev/steel-browser/blob/main/api/src/modules/sessions/sessions.schema.ts | `CreateSession` accepts `sessionContext`, `persist`, and `userDataDir` |
| Steel `session.service.ts` | https://github.com/steel-dev/steel-browser/blob/main/api/src/services/session.service.ts | `persist === true` resolves to the service's fixed `user-data-dir` |
| Steel context types | https://github.com/steel-dev/steel-browser/blob/main/api/src/services/context/types.ts | `SessionContextSchema` contains cookies and origin-scoped browser storage |
