# BROWSER-GEN-1 production evidence

## Verdict

Real external action succeeded. Life Manager received a natural-language Telegram
request, used Railway-private Steel Chromium, opened a live Luma event, filled the
agent-owned registration identity, submitted the form, passed a managed Cloudflare
browser check, and captured the provider-authored result **“You’re In”**.

This is not a dry run, fixture, fake CDP session, or navigation-only smoke.

## Successful production run

| Evidence | Value |
|---|---|
| Telegram user request (MTProto view) | `4945` |
| Browser job | `73d313c0-2574-49d2-8aad-e40665db0cdb` |
| Telegram Bot API inbound message | `347` |
| Telegram update | `200427711` |
| Prompt SHA-256 | `148bce90d333a0b22cedd0da8082627bd5fe2ce25aff2b87018f56674f07bb72` |
| Steel session | `ac1fabf6-eada-48d2-a0ee-e9145504a989` |
| Selected provider | `https://luma.com/livestream-agenticaisummit` |
| Provider | Luma |
| External action | Free Agentic AI Summit 2026 livestream registration |
| Provider readback status | `confirmed` |
| Provider-authored visual readback | `You’re In` |
| Telegram evidence photo (Bot API) | `350` |
| Telegram evidence photo (MTProto user view) | `4948` |
| PNG SHA-256 | `0a72dec21b1d831299a1c8760e5d2658013bd7a91deae26b0e2bc430447c1c1f` |
| Steel release | `true` |
| Execution host | Railway `life-call` → `steel-browser.railway.internal:8080` |
| Local Mac browser used by the executor | no |

The visual receipt also shows the event date, virtual venue, event countdown,
Add to Calendar control, and the note that email verification is needed only to
manage the already-created registration and view more details.

## Production trace

```text
claimed
discovery session=ac1fabf6-eada-48d2-a0ee-e9145504a989
selected url=https://luma.com/livestream-agenticaisummit origin=https://luma.com
action_started action=one delegated zero-cost browser action
action_observed action=Registering for the Agentic AI Summit 2026 | Free Livestream event.
provider_readback status=confirmed current_url=https://luma.com/livestream-agenticaisummit
telegram_sent message_id=349
evidence_sent message_id=350 sha256=0a72dec21b1d831299a1c8760e5d2658013bd7a91deae26b0e2bc430447c1c1f
steel_released released=true session=ac1fabf6-eada-48d2-a0ee-e9145504a989
```

## Readback correction and challenge evidence

The successful run's first boolean classifier returned `confirmed=false` despite
its own `status=confirmed`, because the page also contained the word `verify`.
Telegram photo `350` is the independent provider screen proving the action. The
classifier was corrected in production commit
`410decb5079c4e10a794abc502e2073b322521f2`: provider-authored “You’re In” now
counts as success while optional email verification to manage an existing
registration does not negate it.

Cloudflare is nondeterministic from the datacenter session:

| Class | Job | Result | Evidence |
|---|---|---|---|
| managed check passed | `73d313c0-2574-49d2-8aad-e40665db0cdb` | provider page says `You’re In` | Telegram photo `350` |
| managed check still running | `a560a351-b6b6-4e4d-a0b9-dc8ba4298ac1` | honest `pending_challenge`, no success claim | Telegram photo `354` |
| challenge detected | `a3f72829-2fbc-4e9c-897b-b3e0df0fbb46` | honest `handoff_required` | Telegram photo `346` |

Every run released its Steel session. Interactive CAPTCHA, login, 2FA, KYC, and
payment remain fail-closed; the implementation does not bypass them.

## Production release

| Item | Value |
|---|---|
| Success-readback fix commit | `410decb5079c4e10a794abc502e2073b322521f2` |
| Railway deployment | `4870fc7f-d3f8-4a6b-9671-9016e2e443f6` |
| Deployment state | `SUCCESS` |
| Focused browser verification | `27/27 PASS` |

Stagehand uses its documented remote-browser patterns: a DOM agent for discovery,
Computer Use mode for unconstrained remote interaction, and atomic `act` calls for
the live form. Primary references:

- Stagehand v3 quickstart: <https://docs.stagehand.dev/v3/first-steps/quickstart>
- Stagehand agent reference: <https://docs.stagehand.dev/v3/references/agent>

## Boundary of this evidence

BROWSER-GEN-1 is complete: one real provider action and receipt crossed the whole
Telegram → Life Manager → Railway Steel → provider → Telegram path. This does not
complete BROWSER-AUTH-1, the three-intent BROWSER-MATRIX-1, or recovery coverage
for every provider/challenge class.
