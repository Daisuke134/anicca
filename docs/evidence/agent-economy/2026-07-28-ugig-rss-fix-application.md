# uGig AIorNot.vote RSS fix application

This is a real external-work attempt. The buyer is an existing human uGig user,
the requested compensation is `$1` paid in SOL, and the delivered pull request
fixes a bug reproduced against the production site. The application is pending,
so verified external revenue remains `$0.00`.

| Field | Verified value |
|---|---|
| uGig | [`2b410cad-7cc9-44fd-b2f1-843d9eae6c24`](https://ugig.net/gigs/2b410cad-7cc9-44fd-b2f1-843d9eae6c24) — “Need beta testers to file bugs and submit PRs” |
| External buyer | `chovy` / account `749cb703-2f6c-4d1a-8a68-72bfd55e490d` |
| Offered payment | `$1 USD paid in SOL` |
| Life Manager uGig identity | `life_manager_agent`, agent account `02652115-ff92-43b6-8dec-05412fd67f4e`, email confirmed |
| Registered payout wallet | Solana `71FfqFniYoMsWZb1qFeQDb1fk2xqvajzivpsnMb44gTf` |
| Pull request | [profullstack/aiornot.vote#100](https://github.com/profullstack/aiornot.vote/pull/100) |
| Delivery commit | `a0424042815523f438f85c333938af691a9741f8` |
| uGig application | `5e315cfd-33fc-433b-a5f0-3cfcdc27a9a4` |
| Readback | `status=pending`, `proposed_rate=1`, created `2026-07-28T08:30:49.902805Z` |
| Current economic state | no buyer acceptance; no payment receipt; external revenue `$0.00` |

## Production reproduction

The [live RSS feed](https://aiornot.vote/rss.xml) declares every image enclosure
as `image/webp`. One current enclosure is
`https://picsum.photos/seed/qrcms33zi8/1000/1250`; following that URL returns
HTTP `200` with `content-type: image/jpeg`. The feed therefore publishes a false
MIME type for the JPEG response.

The [RSS 2.0 specification](https://www.rssboard.org/rss-specification#ltenclosuregtSubelementOfLtitemgt)
states that an enclosure's `type` is a standard MIME type. The fix infers known
types from image URL extensions and omits the optional enclosure when the remote
type cannot be established, while preserving the image in the item description.

## Superpowers TDD verification

| Gate | Result |
|---|---|
| RED | New JPEG and extensionless-URL regression tests failed against the original hard-coded `image/webp` behavior |
| Focused GREEN | `apps/web/lib/rss.test.ts`: `6/6 PASS` |
| Full tests | `15` files, `61/61 PASS` |
| TypeScript | `pnpm typecheck`: PASS |
| Lint | PASS with the same five pre-existing warnings |
| Production build | Next.js compile PASS; static generation `43/43` |
| GitHub checks | Socket project report PASS; Socket pull-request alerts PASS |

