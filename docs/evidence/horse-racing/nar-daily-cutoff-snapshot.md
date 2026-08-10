# NAR daily cutoff snapshot

## Gate and scope

| Field | Observed value |
|---|---|
| evidence_class | `REAL_PUBLIC_WEB_RECORD` |
| source_authority | `official` |
| jurisdiction | `NAR` |
| snapshot date | `2026-08-10` |
| gate_status | `PASS_DAILY_CUTOFF_SNAPSHOT` |
| safely materializable races (fixed win market v1) | `7` |
| safely materializable runners (fixed win market v1) | `76` |
| cross-bet-type positive single-runner candidate races | `12` |
| cross-bet-type positive single-runner candidate runners | `126` |
| cash_authorized | `false` |
| model_ready | `false` |
| revenue | `0` (no cash activity) |
| raw_values_exported | `false` |

This is one bounded daily snapshot, before parser/model/cash work. It is not a live
bet authorization. The probe is under `USER_ATTESTED_PERMISSION`; the permission
document was not supplied or independently verified (`permission_document_verified=false`).

## Navigation and publication state

CRWL ran once on the official [TodayRaceInfo page](https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop) and exited `0`. The page's current data-download section exposed an active Markdown link for both:

- Daily race: `https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily`
- Daily odds: `https://www.keiba.go.jp/KeibaWeb/DataDownload/OddsDataDownload?type=daily`

The daily odds control was an ordinary active link, not `disabled`, `NOT_PUBLISHED`, or
`javascript:void(0)`. No monthly archive was substituted. CRWL was then invoked once
on each binary link; both exited `1` with the private diagnostic
`Error: 'NoneType' object has no attribute 'raw_markdown'`. This is recorded as the
CRWL binary/download limitation before the curl fallback.

## Transport and private raw boundary

Curl used `--fail --location --show-error --silent --verbose` exactly once per daily
archive. The HTTP completion timestamp below is the snapshot timestamp for that
archive, in Asia/Tokyo; it is not reused from the monthly probe.

| Archive | Started (JST) | HTTP completed (JST) | HTTP/content type | Bytes | Content-disposition | Archive SHA-256 |
|---|---|---|---|---:|---|---|
| daily race | 2026-08-10T10:46:22+09:00 | 2026-08-10T10:46:22+09:00 | 200 / `application/zip` | 38255 | `20260810_1786326374_race.zip` | `60c8fb659d6b31369453bf6121576d1af082ddc274e3380dd19e3135403d0135` |
| daily odds | 2026-08-10T10:46:22+09:00 | 2026-08-10T10:46:23+09:00 | 200 / `application/zip` | 83079 | `20260810_1786326374_odds.zip` | `feaa43d6bdaa019aa748a7ce05f527235647531bc90bfcc38fb0eadb5dc8c515` |

Both responses used verified TLS (`ssl_verify_result=0`, TLS 1.3, HTTP/2). ZIPs,
headers, curl metadata, and verbose traces are outside Git at:

`/Users/anicca/Library/Application Support/Anicca/horse-racing/raw/nar/`

The directory is mode `700`; every daily artifact created here is mode `600`. No raw
CSV row, horse/person name, odds, payout, secret, or credential is committed or sent
to chat.

## Redacted archive manifests

All CSV entries are UTF-8 with BOM, parsed as text fields without invented type
coercion. Data dates are `2026-08-10` only; no post-race payout rows were present.

| Entry | Columns / data rows | Distinct dates | Distinct race/runner key | Duplicate rows | Blank cells / rows with any blank | Entry SHA-256 |
|---|---:|---:|---:|---:|---:|---|
| `20260810_racelist.csv` | 66 / 46 | 1 | 46 race keys | 0 | 2271 / 46 | `ae82b332656bd8a440c4d849d98f66df56d492062e4cc397d872d78a9a29b2e2` |
| `20260810_payback.csv` | 54 / 0 | 0 | 0 | 0 | 0 / 0 | `a85a5950b9e608dcfe6118540d68c68ef5bc84a7ae74ddf001de757df4db0f5f` |
| `20260810_horselist.csv` | 36 / 456 | 1 | 456 runner keys | 0 | 3138 / 456 | `41eb6664ce8f2aed710e8ea715c48f1cbaa1c16ae15eee902dd1a073bb04975b` |
| `20260810_odds.csv` | 10 / 25008 | 1 | 25008 full odds keys | 0 | 29578 / 25008 | `e4b0251ccd2c041ebe18915c4639d620709b1a5d5682e4b8e935316197c2f570` |

Race-key fields are `競馬場`, `競走年月日`, and `レース番号`; runner keys append
`馬番`. The race list observed `発走時刻` in all 46 rows as four-digit HHMM text.
The daily odds headers are `競馬場`, `競走年月日`, `レース番号`, `賭式`, `番号1`,
`番号2`, `番号3`, `オッズ`, `オッズ（最大）`, and `人気`. Missing-field counts
for daily odds are zero for race identity, bet type, `番号1`, `オッズ`, and `人気`;
`番号2` is blank in 432 rows, `番号3` in 5345 rows, and `オッズ（最大）` in
23801 rows. These are schema/combination observations; no odds value is reproduced.

The race-list headers include the official race/date/start-time, venue, surface,
distance, weather, track-condition, runner-count, prize, split-time, and corner-field
names (including the observed repeated ranges `副賞名1..15`, `ハロンタイム1..15`,
`コーナー名称1..8`, and `コーナー通過順1..8`). The horse-list headers include
official runner identity, `馬番`, name/pedigree/jockey/trainer/owner/breeder fields,
weight, result, time, finish, and popularity fields. The payback header set is present
but has zero data rows at this pre-settlement snapshot.

## Cutoff and join computation

For each race, the scheduled timestamp is constructed only from the observed official
date plus `発走時刻`, interpreted in Asia/Tokyo. The operational cutoff is the fixed
conservative rule `scheduled_start - 10 minutes`. A race is safe only when the daily
odds HTTP completion (`2026-08-10T10:46:23+09:00`) is no later than its cutoff and a
positive single-runner odds row joins its observed runner key.

| Check | Count |
|---|---:|
| race rows / distinct race keys | 46 / 46 |
| runner rows / distinct runner keys | 456 / 456 |
| payback rows | 0 |
| odds rows / race-key-joined rows | 25008 / 25008 |
| future races at snapshot | 46 |
| pre-cutoff races | 46 |
| past or current races excluded | 0 |
| missing start-time races excluded | 0 |
| late/after-cutoff races excluded | 0 |
| distinct race keys represented in odds | 22 |
| single-runner odds rows | 432 |
| positive cross-bet-type single-runner rows joined to runner keys | 238 |
| distinct cross-bet-type positive single-runner race keys | 12 |
| distinct cross-bet-type positive single-runner runner keys | 126 |
| future races without a positive cross-bet-type single-runner candidate | 34 |
| multi-runner or empty-component odds rows | 24576 |
| blank odds rows | 0 |
| non-positive odds rows excluded | 194 |
| safely materializable races (fixed win market v1) | 7 |
| safely materializable runners (fixed win market v1) | 76 |

### Fixed win market v1 (`賭式=単勝`)

The v1 market is fixed to exact `単勝`. It requires one positive odds row for every
official horselist runner in a race, with a unique race+runner key. The aggregate is:

| Win aggregate | Count |
|---|---:|
| all `単勝` rows | 216 |
| positive unique `単勝` rows | 125 |
| positive `単勝` race keys | 12 |
| positive `単勝` runner keys | 125 |
| duplicate positive `単勝` runner keys | 0 |
| complete races (every horselist runner covered) | 7 |
| runners in complete races | 76 |
| incomplete races excluded | 5 |
| missing positive win-runner rows | 6 |
| extra odds keys | 0 |

Coverage ratio (`positive unique 単勝 runners / official horselist runners`) is
distributed as `1.0: 7 races`, `0.916667: 1`, `0.909091: 2`, `0.888889: 1`, and
`0.833333: 1`. The count-gap distribution (official runners minus positive unique
win runners) is `0: 7 races`, `1: 4`, and `2: 1`. Incomplete races are excluded from
the materialized v1 set; cross-bet-type 12-race/126-runner counts remain candidates
only and are not materialized records.

“Single-runner odds” is a schema-only classification: exactly one of `番号1`,
`番号2`, and `番号3` is nonblank. No bet-type label or odds/payout value is used as
evidence in the cross-bet-type candidate count. The fixed win market v1 requires a
unique positive `単勝` row for every official horselist runner, so only the 7 complete
races and 76 runners are safely materializable. The remaining 5 win races are
incomplete and excluded; no odds value, name, ID, or raw row is reproduced.

## Gate and safety state

The selected gate is `PASS_DAILY_CUTOFF_SNAPSHOT`. This unlocks only later parser
implementation and SHADOW data collection. It does not unlock model training,
backtesting, Telegram recommendations, CFO revenue, or browser order/payment. Daily
payback rows are zero, so no settled outcome or return is inferred. The hard state is:

`cash_authorized=false`, `model_ready=false`, `revenue=0`, `raw_values_exported=false`.

## Permission and source references

- [NAR robots.txt](https://www.keiba.go.jp/robots.txt): retain `Crawl-delay: 10` and the `TodayRaceInfo`, `DataRoom`, and `DataDownload` disallow directives.
- [NAR TodayRaceInfo](https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop): navigation and active daily controls observed by CRWL.
- [NAR daily race archive](https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily): exact curl target and archive evidence.
- [NAR daily odds archive](https://www.keiba.go.jp/KeibaWeb/DataDownload/OddsDataDownload?type=daily): exact curl target and snapshot timestamp.
- [NAR terms](https://www.keiba.go.jp/terms.html): permission/redistribution terms remain unverified for the user attestation.

`permission_basis=USER_ATTESTED_PERMISSION`, `permission_document_verified=false`,
`allowed_scope=private_shadow`, and `cash_authorized=false` remain unchanged. Official
source authority is not upgraded into cash authority by this successful transport or
cutoff snapshot.
