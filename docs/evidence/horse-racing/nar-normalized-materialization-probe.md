# NAR normalized-materialization probe

## Gate and scope

| Field | Observed value |
|---|---|
| evidence_class | `REAL_PUBLIC_WEB_RECORD` |
| source_authority | `official` |
| jurisdiction | `NAR` |
| probe_scope | Current monthly race and odds archives discovered from official navigation |
| gate_status | `BLOCKED_NO_CUTOFF_TIMESTAMP` |
| cutoff_safe_normalized_records | `0` safely constructible without invention |
| cash_authorized | `false` |
| model_ready | `false` |
| revenue | `0` (no cash activity) |
| raw_values_exported | `false` |

This is a bounded personal probe under `USER_ATTESTED_PERMISSION`. The permission
document was not supplied or independently verified (`permission_document_verified=false`).
The attestation does not imply general bot, redistribution, publication, or cash
execution permission.

## Retrieval trace

CRWL was run once for each official navigation page. Both navigation calls exited
`0`; the markdown was written to a private temporary directory and is not in Git.
The MonthlyConveneInfo page exposed the following current links (the month was not
remembered or substituted):

- `https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=monthly&k_year=2026&k_month=8`
- `https://www.keiba.go.jp/KeibaWeb/DataDownload/OddsDataDownload?type=monthly&k_year=2026&k_month=8`

CRWL was then invoked once for each discovered binary URL before curl. Both exited
`1` with the private diagnostic `Error: 'NoneType' object has no attribute 'raw_markdown'`.
This is the binary/download handling limitation recorded for the transport fallback,
not a fabricated success or a source failure.

Curl used `--fail --location --show-error --silent --verbose` with private response
headers and metadata. Both downloads returned HTTP/2 `200`, content type
`application/zip`, TLS 1.3, `ssl_verify_result=0`, and effective URLs equal to the
discovered URLs. The server date was `Mon, 10 Aug 2026 01:37:13 GMT`; retrieval
started at `2026-08-10T10:37:13+09:00`. The daily archive was not fetched because the
monthly race archive already contained the observed start-time and race fields needed
for this probe; no polling or loop was used.

## Private raw boundary

Raw ZIPs, response headers, curl metadata, and verbose TLS traces are outside the
repository at:

`/Users/anicca/Library/Application Support/Anicca/horse-racing/raw/nar/`

The directory mode is `700`; every private file created by this probe is mode `600`.
Nothing under that directory is staged or committed. The CRWL navigation captures are
also private temporary files. No raw CSV row, horse/person name, odds, payout, secret,
or credential is present in this evidence file.

## Monthly race archive manifest

Source URL: `https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=monthly&k_year=2026&k_month=8`

| Field | Observed value |
|---|---|
| content type / bytes | `application/zip` / `430295` |
| archive SHA-256 | `ca512328b477054738f0a926710c3c5c16b1e25d9f7e4ffaf7f9cfc9604c2149` |
| content-disposition | `202608_1786294843_race.zip` |
| encoding | UTF-8 with BOM for every CSV entry |
| date range | `2026-08-01` through `2026-08-14` |

| Entry | Columns / data rows | Distinct dates | Distinct key / duplicate rows | Entry SHA-256 |
|---|---:|---:|---:|---|
| `202608_racelist.csv` | 66 / 494 | 14 | 494 / 0 | `d12da81c52e0c98e49e9fab6944a830fc3f2656c0ef247de26153ad24c55a95c` |
| `202608_payback.csv` | 54 / 322 | 9 | 321 / 1 | `a59c605a084ba8ad896bbfdd966ee31f0a3b52939aa43c15ebfcd3573abdbd35` |
| `202608_horselist.csv` | 36 / 4805 | 14 | 4805 / 0 | `d2133de6156676685ee7454041451e50eb3a7ee4d3d721c782be1cfda75e95e8` |

Observed schema is CSV text fields (no unobserved type coercion). Header names are:

- `racelist`: `競馬場`, `競走年月日`, `レース番号`, `発走時刻`, `競走種類名称`, `レース名`, `副賞名1..15`, `芝ダート区分`, `回り`, `距離`, `天候`, `馬場`, `頭数`, `条件`, `1着賞金(円)..5着賞金(円)`, `上がり4F`, `上がり3F`, `ハロンタイム1..15`, `コーナー名称1..8`, `コーナー通過順1..8`.
- `payback`: `競馬場`, `競走年月日`, `レース番号`, `レース名`, `単勝組番`, `単勝払戻金（円）`, `単勝人気`, `複勝組番1`, `複勝払戻金1（円）`, `複勝人気1`, `複勝組番2`, `複勝払戻金2（円）`, `複勝人気2`, `複勝組番3`, `複勝払戻金3（円）`, `複勝人気3`, `枠複組番1`, `枠複組番2`, `枠複払戻金（円）`, `枠複人気`, `枠単組番1`, `枠単組番2`, `枠単払戻金（円）`, `枠単人気`, `馬複組番1`, `馬複組番2`, `馬複払戻金（円）`, `馬複人気1`, `馬単組番1`, `馬単組番2`, `馬単払戻金（円）`, `馬単人気1`, `ワイド組番1馬番1`, `ワイド組番1馬番2`, `ワイド払戻金1（円）`, `ワイド人気1`, `ワイド組番2馬番1`, `ワイド組番2馬番2`, `ワイド払戻金2（円）`, `ワイド人気2`, `ワイド組番3馬番1`, `ワイド組番3馬番2`, `ワイド払戻金3（円）`, `ワイド人気3`, `３連複組番馬番1`, `３連複組番馬番2`, `３連複組番馬番3`, `３連複払戻金（円）`, `３連複人気`, `３連単組番馬番1`, `３連単組番馬番2`, `３連単組番馬番3`, `３連単払戻金（円）`, `３連単人気`.
- `horselist`: `競馬場`, `競走年月日`, `レース番号`, `枠番`, `帽色`, `馬番`, `馬名`, `性`, `齢`, `毛色`, `生年月日`, `父馬名`, `母馬名`, `母父馬名`, `騎手名`, `騎手所属`, `負担重量`, `騎手成績`, `調教師`, `調教師所属`, `馬主氏名`, `生産牧場名`, `馬体重`, `馬体重増減`, `全成績`, `ダート左成績`, `ダート右成績`, `当競馬場成績`, `うち当距離成績`, `最高タイム`, `最高タイム良馬場`, `着順`, `タイム`, `着差`, `上がり3F`, `人気`.

Null/missing summary (blank CSV fields):

| Entry | Blank cells | Rows with any blank | Missing race-key fields |
|---|---:|---:|---|
| racelist | 21047 | 494 | 0 for each of `競馬場`/`競走年月日`/`レース番号` |
| payback | 1428 | 252 | 0 for each of the three race-key fields |
| horselist | 17114 | 3280 | 0 for race keys and `馬番` |

## Monthly odds archive manifest

Source URL: `https://www.keiba.go.jp/KeibaWeb/DataDownload/OddsDataDownload?type=monthly&k_year=2026&k_month=8`

| Field | Observed value |
|---|---|
| content type / bytes | `application/zip` / `2159847` |
| archive SHA-256 | `ad18c23b4648bef4113c8191cc78d084168a2aa37c9b49431742e64621f0397f` |
| content-disposition | `202608_1786294843_odds.zip` |
| encoding | UTF-8 with BOM for every CSV entry |
| date range | `2026-08-01` through `2026-08-09` |

| Entry | Columns / data rows | Distinct dates | Distinct full key / duplicate rows | Entry SHA-256 |
|---|---:|---:|---:|---|
| `202608_01_odds.csv` | 10 / 327274 | 9 | 255570 / 0 | `97398e8d2e7dced044115ec93d333dc6e79dbf7c09d74ab8d787ee682aa3a430` |
| `202608_02_odds.csv` | 10 / 0 | 0 | 0 / 0 | `aa77291058ed8abb897a79c7b2466d9635049d77f2ee6774dc3dc94b86b46a72` |
| `202608_03_odds.csv` | 10 / 0 | 0 | 0 / 0 | `aa77291058ed8abb897a79c7b2466d9635049d77f2ee6774dc3dc94b86b46a72` |

The observed odds headers are `競馬場`, `競走年月日`, `レース番号`, `賭式`,
`番号1`, `番号2`, `番号3`, `オッズ`, `オッズ（最大）`, and `人気`.
Missing-key counts are zero for the race identity and bet-type/`番号1` fields;
`番号2` is blank in 6134 rows and `番号3` in 71704 rows (the observed variable
combination shape). Total blank cells are 388517 and every non-empty-data row has at
least one blank combination field. No odds value is reproduced here.

## Join and settlement coverage

The race key is the observed tuple `(競馬場, 競走年月日, レース番号)`; runner keys
append `馬番`. Counts below are computed locally from the private archives and contain
no row values:

| Check | Count |
|---|---:|
| distinct race keys | 494 |
| distinct runner keys | 4805 |
| odds rows / rows joining a race key | 327274 / 327274 |
| odds rows whose numeric components join the observed runner sets | 327274 / 327274 |
| payback rows / rows joining a race key | 322 / 322 |
| settled payback fields observed | 13 |
| settled payback rows | 322 |
| settled race-id count | 321 |
| races with race + odds + settled payback | 321 |
| candidate single-runner keys with settled payback | 3067 |

The one duplicate payback key is retained in the aggregate count and is not silently
deduplicated into a normalized record.

## Pre-race cutoff audit and gate

`racelist` contains the observed `発走時刻` field, nonblank for 494/494 race rows.
The odds schema contains `競走年月日` (date) but no row-level start time, timestamp,
snapshot time, or effective-time field. The retrieval timestamp above is archive-level
only; it cannot prove that any individual odds row was available before its race start.

Therefore the exact number of cutoff-safe normalized records constructible without
inventing a timestamp is **0**. The 3067 candidate runner joins and 321 settled race
joins remain observed candidates, not normalized records; their cutoff eligibility is
`UNKNOWN`, not converted to zero. The selected outcome is:

`BLOCKED_NO_CUTOFF_TIMESTAMP`

This probe does not authorize model training, backtesting, SHADOW decisions, Telegram
recommendations, CFO revenue, or browser order/payment. `cash_authorized=false` remains
the hard boundary.

## Permission and source references

- [NAR robots.txt](https://www.keiba.go.jp/robots.txt): retain `Crawl-delay: 10` and `Disallow` for `TodayRaceInfo`, `DataRoom`, and `DataDownload`.
- [NAR TodayRaceInfo](https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop): CRWL exit 0; current daily links observed.
- [NAR MonthlyConveneInfo](https://www.keiba.go.jp/KeibaWeb/MonthlyConveneInfo/MonthlyConveneInfoTop): CRWL exit 0; current monthly links observed.
- [NAR terms](https://www.keiba.go.jp/terms.html): permission/redistribution terms remain unverified for this attestation.
- [NAR data manual](https://www.keiba.go.jp/pdf/manual/data_pdf_manual.pdf): cadence and field semantics are source context, not a replacement for row-level cutoff timestamps.

`permission_basis=USER_ATTESTED_PERMISSION`, `permission_document_verified=false`,
`allowed_scope=private_shadow`, `raw_values_exported=false`, and
`cash_authorized=false` are retained for this lane. No source authority is upgraded by
the existence of HTTP/ZIP/schema joins alone.
