# Horse-racing Reality Gate index

This index records the independent source lanes observed by the bounded
private-shadow probes. It is an index only; it performs no new fetch.

| source lane | evidence class | URL(s) | authority | jurisdiction | permission status | observed record counts | content SHA-256 | observed schema status | allowed scope | cash authorized | gate state | evidence link |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| JRA official | `REAL_PUBLIC_WEB_RECORD` | `https://www.jra.go.jp/JRADB/accessS.html?CNAME=pw01sde1004202602060720260809/DD` | official | JRA | `JRA_PRIVATE_USE_POLICY`; `permission_document_verified=false` | results=12 | HTML: `85ff5415dfdd66fc5dd0b59fedb14eb8b2dbbb8d28e7e28effa29165539bd012` | observed `result_runner_table`, 12x14 | `private_shadow` | false | `PASS_PRIVATE_SHADOW` | [JRA probe](jra-public-web-probe.md) |
| NAR official | `REAL_PUBLIC_WEB_RECORD` | daily: `https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily`<br>monthly odds: `https://www.keiba.go.jp/KeibaWeb/DataDownload/OddsDataDownload?type=monthly&k_year=2026&k_month=8` | official | NAR | `USER_ATTESTED_PERMISSION`; `permission_document_verified=false` | races=46; horses=456; monthly_odds=327274; paybacks_pre_settlement=0 | daily ZIP: `f245030f4608055c2fa24e2910d51edcd029f2292c9cfbe66d2911604e1e1c5b`<br>monthly odds ZIP: `ad18c23b4648bef4113c8191cc78d084168a2aa37c9b49431742e64621f0397f` | observed UTF-8 CSV fields | `private_shadow` | false | `PASS_PRIVATE_SHADOW`; raw archive recompute `CANNOT_RECOMPUTE_RAW_ARCHIVE_ABSENT` | [NAR probe](nar-official-data-probe.md) |
| JRA secondary candidate (`race.netkeiba.com`) | none observed; `PUBLIC_WEB_SECONDARY` required if later observed | `https://race.netkeiba.com/` | secondary | JRA | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `shadow_only` | false | `NOT_OBSERVED` | none |
| NAR secondary candidate (`nar.netkeiba.com`) | none observed; `PUBLIC_WEB_SECONDARY` required if later observed | `https://nar.netkeiba.com/` | secondary | NAR | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `shadow_only` | false | `NOT_OBSERVED` | none |

## Invariants

- Each lane is independent; a JRA `PASS` never changes NAR.
- A secondary lane can never upgrade to official or authorize cash/revenue.
- HTTP or DOM success alone is not a record.
- `NOT_OBSERVED` means unknown/not collected, not zero.
- This index performs no new fetch and does not authorize backtest, SHADOW,
  Telegram, CFO, order, or payment actions.
