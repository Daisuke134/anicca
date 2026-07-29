# BROWSER-AUTH-1 — Luma agent-owned login production checkpoint

## Verdict

`BROWSER-AUTH-1` is not done. The implementation and production browser path are
green, but the current `@agentmail.to` identity does not receive Luma's sign-in
code. The provider-authenticated context, fresh-process restore, and production
queue proof therefore remain unproven.

## Shipped implementation

- PR `#1325` merged as `a9118f38d0e6cd6ce123b68b0ade6e1d16c907d9`.
- Railway production deployment
  `7597c832-cfde-4226-a51f-0c7bf3b22aa2` reached `SUCCESS` at that exact SHA.
- The bootstrap reports only an allowlisted failure stage. Provider errors,
  mailbox addresses, codes, links, cookies, and context material are never
  reflected in the diagnostic.
- A `SUBMIT_EMAIL` failure test proves the real Steel browser release still
  runs. Focused bootstrap tests are `8/8`; the Life Manager `npm test` chain
  passes.

## Production measurements

The production bootstrap ran in the deployed `life-call` image and exited:

```text
Luma authentication unavailable [POLL_EMAIL]
```

A separate safe probe used the same Railway-private Steel and deterministic CDP
driver. It returned only booleans and origin/path:

| Measurement | Before submit | Five seconds after submit |
|---|---:|---:|
| origin/path | `https://luma.com/signin` | `https://luma.com/signin` |
| email input visible | true | false |
| one-time-code input visible | false | true |
| `Enter Code` visible | false | true |
| provider error visible | false | false |
| CAPTCHA visible | false | false |

This proves Steel creation, CDP connection, navigation, email form submission,
and Luma's transition to the six-digit-code UI. It does not prove that Luma sent
an email.

The configured AgentMail inbox was independently read back without printing its
address or message bodies:

| Check | Result |
|---|---:|
| inbox API | HTTP success |
| supplied inbox ID equals canonical inbox address | true |
| verified custom domains in the organization | 0 |
| recent Luma-shaped messages | 0 |
| recent six-digit-code messages | 0 |
| recent direct Luma auth URLs | 0 |
| last-hour `message.received.spam` | 0 |
| last-hour `message.received.blocked` | 0 |
| last-hour `message.received.unauthenticated` | 0 |

The configured identity is on AgentMail's default domain. The alternate
`reply.aniccaai.com` path is not a usable fallback: its implementation comment
exists, but public DNS has no MX record for that subdomain.

## Production two-tenant isolation proof

The storage-isolation leg now passes in the deployed production image. The
first controlled run failed closed at `UPSERT` because `example.com` is a
reserved origin and the browser-auth boundary correctly rejects special-use
hostnames. A regression test reproduced that failure before the probe was
moved to the owned, non-reserved origin `https://auth.aniccaai.com`.

- PR `#1335` shipped the production two-tenant harness.
- PR `#1337` added fixed, non-secret failure stages.
- PR `#1341` replaced the reserved probe origin and added the production-deps
  regression test.
- Railway production deployment
  `4b02c31b-69d4-4162-9104-e11a5a1d406a` reached `SUCCESS` at exact merge SHA
  `f8db2d4da8321f78c8df197d09d136876154323c`.
- Focused browser-auth tests are `38/38`; the full Life Manager `npm test`
  chain and OSS self-contained boundary pass.

The production run returned:

| Measurement | Result |
|---|---:|
| isolated tenants written | 2 |
| origin | `https://auth.aniccaai.com` |
| distinct encrypted context hashes | true |
| fresh Node process reads | 2 |
| cross-tenant decrypt/read successes | 0 |
| plaintext marker hits in ciphertext fields | 0 |
| exact controlled rows deleted | 2 |
| controlled rows after cleanup | 0 |

The two context SHA-256 values were distinct:
`d6f250b4d82388f06863851f0a7d6b28bd7c88976f6f7e0366e6f1774e1e0e17`
and
`f8e9aa70e7cacef274e9f5881ef05a97e4744ee28723e3c8d3f5c7a197600d9e`.
No UID, cookie value, mailbox address, or raw browser context was emitted.
This proves tenant-bound encrypted persistence, fresh-process restoration, AAD
cross-tenant rejection, ciphertext non-plaintext, and cleanup. It does not
prove that a provider-authenticated Luma context can be obtained.

## External dependency already started

The agent-owned inbox sent one idempotent support request to the official Luma
support address. AgentMail returned HTTP `200` with both message and thread
identifiers present. The request asks whether default AgentMail addresses are
suppressed for sign-in codes and which programmatic mailbox domains are
supported. No Dais personal mailbox or credential was used.

The independent two-tenant isolation proof is complete. A support reply is an
input to the next Luma attempt, not a reason to stop unrelated implementable
work.

## Evidence limits

- Confirmed: the production browser no longer dies before provider interaction;
  Luma accepts the email form and shows the OTP UI; Steel is released; the
  mailbox API is healthy. Two production tenants persist distinct encrypted
  contexts, restore them from fresh processes, reject cross-tenant decrypts,
  expose no plaintext marker, and leave zero controlled rows after cleanup.
- Not confirmed: Luma email dispatch, receipt of a code, provider-authenticated
  Luma context save/restore, or authenticated production queue action.
- Do not claim `BROWSER-AUTH-1` done until all missing legs above pass in one
  traceable production proof.

## Primary sources

- [AgentMail: missing inbound emails](https://github.com/agentmail-to/agentmail-docs/blob/main/fern/pages/knowledge-base/inbound-emails-missing.mdx) —
  AgentMail drops messages when inbound SPF/DKIM/DMARC explicitly fail and
  exposes received/spam/blocked/unauthenticated event classes.
- [AgentMail: custom domains](https://github.com/agentmail-to/agentmail-docs/blob/main/fern/pages/guides/domains/custom-domains.mdx) —
  the default domain is for getting started; production applications should use
  a verified custom domain.
- [AgentMail support](https://github.com/agentmail-to/agentmail-docs/blob/main/fern/pages/resources/support.mdx) —
  the official email support address is documented there.
- [Luma Help](https://help.luma.com) — the official page exposes
  `support@luma.com`.
