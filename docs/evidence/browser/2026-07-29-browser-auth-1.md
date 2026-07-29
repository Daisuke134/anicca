# BROWSER-AUTH-1 — production completion evidence

## Verdict

`BROWSER-AUTH-1` is done.

The deployed Life Manager authenticated to the real Luma provider from Railway
private Steel, stored the resulting browser context encrypted and tenant-bound,
restored it into fresh Steel sessions and fresh application instances, executed
authenticated production queue jobs, read back a protected provider action, and
reported receipts to Telegram. The same boundary fails closed to
`handoff_required` when the context is expired. No Mac browser was used and no
loaded Mac loop was stopped.

## Exact production artifact

| Artifact | Verified value |
|---|---|
| final code | PR `#1344`, merge `e075fb305295559dc2f9c7c4b99efddf55bcce4a` |
| Railway deployment | `173c819d-8e34-4f2e-a942-9d87c8d1144d`, `SUCCESS`, exact merge SHA |
| final application instance | `253cd9d2188f` |
| browser runtime | Railway-private `steel-browser`; no public Browserbase account |
| focused verification | Stagehand/Steel driver `53/53`; Luma bootstrap + production E2E `23/23` |

The final fix does not treat a generic page title as authentication. Its
deterministic continuity fallback is available only when all of these are true:
an encrypted context was loaded for that tenant and origin, the restored page
shows a protected action, and no login, OTP, CAPTCHA, challenge, or risk UI is
visible. A fresh unauthenticated session therefore still fails closed.

## Real login and encrypted persistence

The real provider flow completed its six-field OTP form, profile completion,
passkey deferral, and landed at `https://luma.com/home`. The authenticated
provider marker was `Create Event`; authentication inputs and `Sign In` were
absent.

| Measurement | Result |
|---|---:|
| provider | real `luma.com` |
| authenticated URL | `https://luma.com/home` |
| protected action readback | `Create Event` |
| initial Steel session | `1aa1b667-8acb-4bcc-b1a5-8e3fd8c5906c` |
| encrypted-context SHA-256 | `a8466944f874d254220d431a4668e3bf7b43500f6a98d87d1a2a0cda861af3ca` |
| encryption key version | `1` |
| plaintext context emitted | `0` |
| Steel session released | `true` |

The mailbox address, OTP, cookies, and raw browser context are intentionally
excluded from this evidence.

## Production queue and restart continuity

An authenticated job first passed through the normal durable production queue.
The running service was then restarted from the exact same image, producing a
different application instance and a different Steel session. A second queued
job restored the saved context and independently read the protected provider
action.

| Measurement | Before restart | After exact-image restart |
|---|---|---|
| deployment | existing production image | `0f47d5ad-5b6a-4057-b73f-de32a5990b55` |
| commit | `b8158447a6f8b3801c32a510bc898667984f7f18` | same exact commit |
| application instance | `ecd0dab4c3e9` | `527642faa7f2` |
| durable job | `cbe092e6-df46-49e0-a1fb-aeda3d16bde2` | `5577abec-57fc-4393-b4ab-158372cd84fd` |
| Steel session | `896a584e-9107-410b-9050-034d68b080b4` | `a0582f4a-9957-40eb-9365-877dc1cc0300` |
| Telegram evidence | `461` | `464` |
| authenticated provider readback | pass | pass |
| Steel session released | `true` | `true` |

The final deployed guard was then verified once more from instance
`253cd9d2188f`:

| Measurement | Result |
|---|---|
| durable job | `84d9df6e-4ac4-4477-a9bd-f9b542948c63` |
| restored context SHA-256 before run | `40d3d44ad803ed9a7eeda22f6d372b1109bc65e25be56c67004c4bff58fb6aad` |
| fresh Steel session | `f0d5ae91-2a6f-4299-97fb-178b09888029` |
| provider marker hash | `76af8ca1f15a464152a82cd348639b1005e60b5bad777fa7cb1ce3bf7503c3f6` |
| Telegram evidence | `474` |
| Steel session released | `true` |

## Expired-session handoff

The exact active context row was temporarily marked expired while the valid
context remained preserved out of band. The production durable queue did not
pretend to be authenticated:

| Measurement | Result |
|---|---|
| durable job | `e071f4c1-ed5d-4bc8-84db-efee4437a629` |
| status | `handoff_required` |
| handoff reason | `login` |
| invalidation trace | `auth_context_invalidated=true` |
| Steel session | `3cb2763c-e006-48a3-a0d5-94fab5ffd95a` |
| Telegram evidence | `468` |
| Steel session released | `true` |

The preserved valid context was restored afterward and the final authenticated
readback above passed. The production row remains active.

## Two-tenant and principal isolation

Two independent production proofs cover both the persistence boundary and real
Steel export/restore behavior.

The owned-origin harness at `https://auth.aniccaai.com` wrote two tenant-bound
encrypted contexts and restored them from a fresh Node process:

| Measurement | Result |
|---|---:|
| isolated tenants written | 2 |
| distinct encrypted context hashes | true |
| fresh-process reads | 2 |
| cross-tenant decrypt/read successes | 0 |
| plaintext marker hits in ciphertext | 0 |
| controlled rows deleted | 2 |
| controlled rows remaining | 0 |

PRs `#1335`, `#1337`, and `#1341` shipped that harness. Deployment
`4b02c31b-69d4-4162-9104-e11a5a1d406a` reached `SUCCESS` at exact SHA
`f8db2d4da8321f78c8df197d09d136876154323c`.

A second proof used real Steel sessions on `https://www.wikipedia.org` and
round-tripped two opaque contexts through encrypted database persistence:

| Measurement | Result |
|---|---:|
| seed Steel sessions | 2 distinct |
| restore Steel sessions | 2 distinct and different from seed |
| distinct encrypted context hashes | true |
| wrong-tenant marker reads | 0 |
| wrong-origin marker reads | 0 |
| wrong-principal marker reads | 0 |
| released Steel sessions | 4/4 |
| controlled rows after cleanup | 0 |

## Secret and cleanup checks

The final deployment's bounded production log was scanned without printing
matching lines or secret values:

| Pattern class | Matches |
|---|---:|
| six-digit OTP near login/Luma/verification text | 0 |
| cookie or `Set-Cookie` value | 0 |
| Authorization value | 0 |
| browser-session encryption-key name | 0 |
| raw browser context field | 0 |

Every Steel session named in this proof was explicitly released. One-off
diagnostic sessions were also released and never used a local Mac browser.

## What this proves and what it does not

This proves a general tenant-bound browser-auth substrate: an allowed provider
login can be acquired, encrypted, restored across processes and browser
sessions, verified against protected DOM state, and invalidated honestly.

It does not prove every website, challenge system, booking flow, inquiry form,
or application flow. That separate generality requirement is
`BROWSER-MATRIX-1`; recovery and duplicate-side-effect behavior is
`BROWSER-RECOVERY-1`.

## Primary implementation references

- [Steel session schema](https://github.com/steel-dev/steel-browser/blob/5880b48c1af107219ff3d904edbb8f6b76bea9b6f/api/src/modules/sessions/sessions.schema.ts)
  defines the self-hosted session API used by the Railway-private service.
- [Stagehand locator reference](https://github.com/browserbase/stagehand/blob/0cce9dbfd4bdb0cc1a51b1b83151efbea6649b6f/packages/docs/v3/references/locator.mdx)
  documents the locator behavior used by the generic browser driver.
