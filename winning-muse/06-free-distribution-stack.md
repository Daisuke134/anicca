# Free Distribution Stack

How to post at volume for $0: stack free scheduler tiers, fill the gaps
with the platforms' own native schedulers, and never let one tool's cap
become the whole operation's cap.

Every route below is labeled by how far it was actually verified:

- **Proven** — an agent completed it end-to-end (for registrations:
  sign-up → email verification → sign-out → sign-in again, all three).
- **Terms read** — free-tier terms verified on the vendor's official
  pricing page (November 2026), but the route has not been run end-to-end.
- **Unverified** — designed, not yet run. Do not quote it as capability.

## Rule zero: prove the replacement before cancelling the paid tool

The standing order for dropping any paid tool is: first run the free
replacement end-to-end (sign in → post → public URL lands), *then* cancel.
Cancelling first converts a cost saving into a distribution outage with a
deadline attached.

## Proven: agent-owned registrations on free scheduler tiers

These three were registered with an agent-owned email and an
agent-generated password typed directly into the form (no human identity,
no SSO) and email-verified. BulkPublish and Social Champ are also
re-login-verified, and both list TikTok and LinkedIn as connectable on
the free tier *inside the product*. Fedica's re-login check is still
open (its UI exposes no sign-out until a social account is connected),
and its in-product check corrected its own pricing page: LinkedIn is
connectable on Free, TikTok is classified paid-only. Connecting accounts
and posting through them is the next stage and is **Unverified**.

| Service | Free tier (as measured in-product) | Notes |
|---|---|---|
| BulkPublish | 3 channels (one per platform), 1 post/day (30/month, X excluded), 3 queued reservations, free API (10 requests/day), 100 MB media | YouTube uploads showed "paused" on Free |
| Social Champ | 3 social accounts, 15 scheduled posts, 1 user | MCP access present in settings at no extra charge (OAuth; not yet connected) |
| Fedica | 12 accounts (one per platform), up to 10 scheduled posts, unlimited drafts | Measured in-product (2026-11-06): LinkedIn connectable on Free; TikTok is paid-only despite the pricing page. Re-login verification still open (no sign-out UI before connecting an account) |

The registration method itself is the reusable asset: agent-owned email,
agent-generated password entered directly, vault storage with re-login
verification. It succeeded on services where earlier attempts that stopped
at the password step had failed — the difference was the instruction, not
the service.

## Terms read (official pricing pages, November 2026)

- **Buffer** — 3 channels total; 10 scheduled posts per channel in queue
  (refillable, so monthly volume per connected channel is uncapped);
  TikTok automatic publishing and LinkedIn pages+profiles included; free
  API (1 key). Reported watch-out (secondary): a lifetime cap of 8 unique
  channel connections per network on Free.
- **Publer** — 3 social accounts (X excluded), 10 scheduled posts per
  account, refillable; no API on free. **Proven negative**: at sign-up it
  rejected two different agent-mail domains as "invalid or not allowed"
  (reCAPTCHA passed both times) — some vendors filter email domains; test
  your agent domain early.
- **Fedica / Social Champ / BulkPublish / Post Planner / Ampli** — genuine
  free plans with TikTok and/or LinkedIn scheduling, per the census table
  in the research notes. Post Planner's sign-up is via Facebook (per its
  own privacy policy). **Ampli is sign-in-with-Google only** — excluded
  under the agent-owned-credential rule, however good its free tier looks.
- **No free plan at all** (trial only or none), confirmed on official
  pages: RecurPost, Vista Social, SocialPilot, Planly, Postly,
  ContentStudio, RADAAR, Kontentino, NapoleonCat, Sendible, Hootsuite,
  Sprout Social, Agorapulse (free tier ended 2026-07-06), Later (no free
  plan on the public pricing page), SocialBee, OneUp, Planable (first 50
  posts ever, not monthly). Crowdfire's scheduler product has ended.
  Metricool Free is 1 brand with a hard 20 posts/month and no LinkedIn.
  Zoho Social Free has no TikTok and no scheduling.

## Native schedulers (the $0 filler)

Per the platforms' official documentation as read in November 2026:

- **TikTok Studio** — schedule 15 minutes to 10 days ahead; desktop
  scheduling requires a Business account; no edits after scheduling
  (delete and re-upload).
- **LinkedIn** — profiles 10 minutes to 3 months ahead; Pages 1 hour to
  3 months (admins only); scheduled posts remain editable.
- **YouTube Studio** — no official advance-scheduling cap found; one Google
  account can manage up to 100 channels via Brand Accounts.

Native routes are one account at a time: batch weekly, per account, in
series. They are the fallback that makes the whole stack independent of
any scheduler vendor.

## Stacking arithmetic (calculation, not documented practice)

Summing the usable free tiers above yields roughly 13–15 TikTok channel
slots and more than enough LinkedIn slots for a 13+2 channel operation.
That is arithmetic on plan terms. Two honest caveats: (1) a census of
operator write-ups found **no first-person account** of running a large
operation by stacking free tiers — the documented methods of operators at
10+ channels are native posting, their own labor, their own automation,
or device farms; (2) queue-capped tiers convert a channel cap into a labor
cap — volume holds only if queues are refilled continuously, ideally by
automation. Treat the stack as capacity on paper until stage-2
(connect → post → public URL) is proven per service.

## Operating rules

- One scheduler per social channel — never connect the same channel to two
  schedulers (duplicate posting, token conflicts).
- Post directly (browser, connector, API, CLI) wherever you can; schedulers
  are for the surfaces you cannot reach directly, not a default.
- Record each route's verification stage in your ledger and upgrade the
  label only when the public URL lands.
