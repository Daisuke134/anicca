# NAR official public-web data probe

## Status and scope

| Field | Observed value |
|---|---|
| evidence_class | REAL_PUBLIC_WEB_RECORD |
| source_authority | official |
| jurisdiction | NAR |
| gate_status | PASS_PRIVATE_SHADOW |
| raw_values_exported | false |
| raw boundary | Mac-local ephemeral archive now absent/CANNOT_RECOMPUTE_RAW_ARCHIVE_ABSENT; no raw file was committed |

This is a bounded personal probe performed under USER_ATTESTED_PERMISSION. On 2026-08-10 the user explicitly attested that personal crawling approval exists via the user/friend. The permission document was not provided or independently verified: permission_document_verified=false. The assertion authorizes this bounded personal probe only; it is not evidence that NAR generally permits bots, redistribution, public publication, or SaaS use.

## Permission and robots evidence

The robots source is https://www.keiba.go.jp/robots.txt. It still reports:

~~~text
Crawl-delay: 10
Disallow: /KeibaWeb/TodayRaceInfo/
Disallow: /KeibaWeb/DataRoom/
Disallow: /KeibaWeb/DataDownload/
~~~

The probe was performed on the basis of USER_ATTESTED_PERMISSION, and the disallow directives are retained here rather than hidden. No general crawler permission or redistribution permission is inferred. HRA-2F is GREEN at commits `ae56d3524` + `956d1b50d`, final focused 24/full 32; the exact-host/path/Mac-local/redacted boundary is accepted; cash remains false.

## Redacted YAML manifest

~~~yaml
evidence_class: REAL_PUBLIC_WEB_RECORD
source_url: https://www.keiba.go.jp/
source_authority: official
jurisdiction: NAR
permission_basis: USER_ATTESTED_PERMISSION
permission_document_verified: false
retrieved_at: 2026-08-10
page_or_effective_timestamp: 2026-08-10
fetch_exit_code: 0
http_status: 200
parsed_row_count: 46
runner_rows: 456
race_rows: 46
horse_rows: 456
odds_rows: 327274
payback_rows: 0
observed_schema_type: utf8_csv_field
observed_schema:
  racelist: venue/date/race_number/start_time/surface/distance/weather/track_condition/runner_count/prize
  horselist: gate/horse_number/horse_name/sex/age/pedigree/jockey/trainer/weight/result_fields
  payback: win/place/quinella/exacta/wide/trio/trifecta_fields
  monthly_odds: venue/date/race_number/bet_type/number1/number2/number3/odds/odds_max/popularity
content_sha256:
  daily_race_zip: f245030f4608055c2fa24e2910d51edcd029f2292c9cfbe66d2911604e1e1c5b
  monthly_odds_zip: ad18c23b4648bef4113c8191cc78d084168a2aa37c9b49431742e64621f0397f
  official_manual_pdf: 56009a444ffb61ddc99097ffdd2d2a84a864073c00052d9f691cfda1770236dd
artifact_source_urls:
  daily_race_zip: https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily
  monthly_odds_zip: https://www.keiba.go.jp/KeibaWeb/DataDownload/OddsDataDownload?type=monthly&k_year=2026&k_month=8
  official_manual_pdf: https://www.keiba.go.jp/pdf/manual/data_pdf_manual.pdf
robots_snapshot_url: https://www.keiba.go.jp/robots.txt
robots_status: "Crawl-delay: 10; TodayRaceInfo/DataRoom/DataDownload disallowed"
terms_url: https://www.keiba.go.jp/terms.html
terms_status: "observed no-unauthorized-reproduction/redistribution; USER_ATTESTED_PERMISSION_DOCUMENT_UNVERIFIED"
raw_values_exported: false
allowed_scope: private_shadow
cash_authorized: false
ingest_boundary_status: GREEN
ingest_boundary_commits:
  - ae56d3524
  - 956d1b50d
raw_archive_recompute_status: CANNOT_RECOMPUTE_RAW_ARCHIVE_ABSENT
gate_status: PASS_PRIVATE_SHADOW
~~~

In the manifest, fetch_exit_code=0 refers to the three public-page crwl observations; http_status=200 refers to the curl archive artifacts. The direct daily crwl download had the download-starting limitation recorded below.

## Public page observations

### TodayRaceInfo

- URL: https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop
- crwl exit: 0.
- The page exposed the 2026-08-10 venues 帯広ば、盛岡、浦和、金沢 and an official daily-data link.
- No runner values were copied.

### DataRoom

- URL: https://www.keiba.go.jp/KeibaWeb/DataRoom/DataRoomTop
- crwl exit: 0.
- The page showed official searchable historical years through 1998.

### MonthlyConveneInfo

- URL: https://www.keiba.go.jp/KeibaWeb/MonthlyConveneInfo/MonthlyConveneInfoTop
- crwl exit: 0.
- The page exposed exact monthly race-download and odds-download endpoints.

## Daily race archive observation

The direct crwl request to https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily failed with:

~~~text
Page.goto: Download is starting
~~~

This is a CRWL download-handling limitation, not a source failure. The curl fallback observed the following archive:

| Field | Observed value |
|---|---|
| URL | https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily |
| HTTP date | Sun, 09 Aug 2026 22:22:26 GMT |
| effective timestamp | 2026-08-10T07:22:26+09:00 |
| HTTP / content type | 200 / application/zip |
| content-disposition | filename 20260810_1786314133_race.zip |
| bytes | 38040 |
| sha256 | f245030f4608055c2fa24e2910d51edcd029f2292c9cfbe66d2911604e1e1c5b |
| entries | 20260810_racelist.csv, 20260810_payback.csv, 20260810_horselist.csv |
| CSV encoding | UTF-8 BOM |

Lines including header were 47 for racelist, 1 for payback, and 457 for horselist. Parsed data rows were races=46, paybacks=0 pre-settlement, and horses=456. No CSV row or person/runner value is reproduced here.

Observed schema type is utf8_csv_field. Compact header names only:

- racelist: venue, date, race_number, start_time, surface, distance, weather, track_condition, runner_count, prize
- horselist: gate, horse_number, horse_name, sex, age, pedigree, jockey, trainer, weight, result fields
- payback: win, place, quinella, exacta, wide, trio, trifecta fields

## Monthly odds archive observation

The monthly odds endpoint was:

https://www.keiba.go.jp/KeibaWeb/DataDownload/OddsDataDownload?type=monthly&k_year=2026&k_month=8

| Field | Observed value |
|---|---|
| HTTP date | Sun, 09 Aug 2026 22:23:47 GMT |
| effective timestamp | 2026-08-10T07:23:47+09:00 |
| HTTP / content type | 200 / application/zip |
| content-disposition | filename 202608_1786294843_odds.zip |
| bytes | 2159847 |
| sha256 | ad18c23b4648bef4113c8191cc78d084168a2aa37c9b49431742e64621f0397f |
| entries | 202608_01_odds.csv, 202608_02_odds.csv, 202608_03_odds.csv |
| lines including header | 327275, 1, 1 |
| parsed data rows | 327274 in the first interval |

Compact header names only: venue, date, race_number, bet_type, number1, number2, number3, odds, odds_max, popularity. No raw odds value is included.

## Official manual observation

Source: https://www.keiba.go.jp/pdf/manual/data_pdf_manual.pdf

- Observed 8 pages, 778383 bytes.
- sha256: 56009a444ffb61ddc99097ffdd2d2a84a864073c00052d9f691cfda1770236dd.
- The manual says daily data includes intermediate odds.
- Core quotes:
  - 「更新頻度: 約2分ごとに更新されます。」
  - 「1日1回、毎日夜間（午前2時頃）に更新されます。」
  - 「レース情報は1998年1月以降、オッズ情報は2026年3月以降」

## Limitations and gate judgment

The observed archive rows and hashes are real public-web observations accepted by the private-shadow manifest. HRA-2F is GREEN at commits `ae56d3524` + `956d1b50d` (final focused 24/full 32); the exact-host/path/Mac-local/redacted boundary is accepted and `cash_authorized` remains false. The ephemeral archive is now absent, so hashes, archive entries, line counts, UTF-8 BOM, and headers cannot be recomputed now; Task 4 performs the next bounded official acquisition instead of a synthetic refetch. This file does not claim completed schema adoption, historical backtest, prediction, Telegram delivery, CFO revenue, cash permission, or LIVE_CASH. The pre-settlement payback row count is 0 and must remain 0 until an official settled result is separately reconciled. All downstream/backtest/Telegram/CFO/revenue/cash values remain 0 or not completed.

The Mac-local ephemeral raw archive is now absent and was never committed (`raw_archive_recompute_status=CANNOT_RECOMPUTE_RAW_ARCHIVE_ABSENT`). Only headers, counts, timestamps, statuses, and hashes are recorded; raw_values_exported=false.

## Sources and core observations

1. User attestation (2026-08-10), USER_ATTESTED_PERMISSION — “personal crawling approval exists via user/friend”; permission document not provided or verified.
2. [NAR robots.txt](https://www.keiba.go.jp/robots.txt) — “Crawl-delay: 10” and the three disallowed paths listed above.
3. [NAR TodayRaceInfo](https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop) — crwl exit 0; 2026-08-10 daily venues and official daily-data link observed.
4. [NAR DataRoom](https://www.keiba.go.jp/KeibaWeb/DataRoom/DataRoomTop) — crwl exit 0; searchable historical years through 1998 observed.
5. [NAR MonthlyConveneInfo](https://www.keiba.go.jp/KeibaWeb/MonthlyConveneInfo/MonthlyConveneInfoTop) — crwl exit 0; monthly race and odds download endpoints observed.
6. [NAR daily download](https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily) — curl HTTP 200 application/zip; archive hash and counts recorded above.
7. [NAR monthly odds download](https://www.keiba.go.jp/KeibaWeb/DataDownload/OddsDataDownload?type=monthly&k_year=2026&k_month=8) — curl HTTP 200 application/zip; first interval contains 327274 parsed rows.
8. [NAR data manual](https://www.keiba.go.jp/pdf/manual/data_pdf_manual.pdf) — daily intermediate-odds behavior and historical coverage; exact quotes are recorded above.
9. [NAR terms](https://www.keiba.go.jp/terms.html) — observed “事前の許諾なく転載、複製することを禁じます。”; no-unauthorized-reproduction/redistribution boundary; permission document remains unverified.
