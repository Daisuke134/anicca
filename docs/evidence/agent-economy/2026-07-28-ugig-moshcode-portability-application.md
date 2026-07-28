# uGig moshcode portability fix application

| Field | Verified value |
|---|---|
| external buyer gig | `d9778d45-f0fc-46c7-a85f-710e20d928e2` |
| promised bug-fix rate | `$0.25`, paid in SOL |
| reproduced failure | `test/skills.test.mjs`: uppercase checkout parent expected `Projects`, normalized implementation returned `projects` |
| external pull request | <https://github.com/moshcoder/moshcode/pull/61> |
| delivery commit | `36098cf` |
| focused verification | 9/9 |
| full verification | 172 pass / 25 skip / 0 fail |
| uGig application | `f8960763-2d63-4a49-b004-65d9f2c61f2c` |
| live application readback | `pending`, proposed rate `0.25` |

The fix changes only the test expectation to match `skillName`'s documented
lowercase normalization. It does not pretend the existing product behavior is a
new feature.

The delivered application is included in Life Manager's production uGig
observer. The observer will not create an invoice until the external buyer
accepts the application and PR #61 is merged. An invoice or application status
alone does not count as revenue; 13c advances only after independently verified
external wallet/chain receipt and exactly-once ledger entry.
