# HRA-2R1 JRA official public-web probe

This is a bounded, read-only JRA public-web observation. The raw result
snapshot is retained only under the private, mode-700 directory
`/Users/anicca/Library/Application Support/Anicca/horse-racing/raw/jra/` and
is outside Git. No horse, person, odds, or other raw row value is exported.

## Discovery and bounded navigation

1. `crwl crawl https://www.jra.go.jp/ -o markdown` exited `0` (39,895 bytes).
   The current official home source exposed the official result action
   `/JRADB/accessS.html` with its form CNAME; no race identifier was selected
   from memory.
2. A direct CRWL GET of the form endpoint exited `0` but returned the official
   error page because the endpoint requires the form CNAME. Submitting the
   CNAME from the home action with curl exited `0`, HTTP `200`, and returned
   the official `レース結果 開催選択` index.
3. The result index exposed completed-result links through 2026-08-09. No
   2026-08-10 result link was observed, so the most recent official result
   link was used. The bounded detail URL is recorded in the manifest below.
4. CRWL of that exact official detail URL exited `0`; curl of the same URL
   exited `0`, HTTP `200`, and was saved privately as the bounded HTML
   snapshot. The result date in the navigation/detail material is
   2026-08-09.

## Why the parsed count is a real result record

The private HTML snapshot was parsed as HTML, selecting the result-runner
table by its result headers and data cells. It contained 13 table rows
(one header plus 12 data rows), 14 header fields, and 168 data cells. Every
data row had 14 cells, therefore `parsed_row_count: 12` is the count of
actual result rows rather than a DOM-success or page-length signal.

## Redacted canonical manifest

```yaml
evidence_class: REAL_PUBLIC_WEB_RECORD
source_url: https://www.jra.go.jp/JRADB/accessS.html?CNAME=pw01sde1004202602060720260809/DD
source_authority: official
jurisdiction: JRA
permission_basis: JRA_PRIVATE_USE_POLICY
permission_document_verified: false
retrieved_at: "2026-08-10T08:55:43+09:00"
page_or_effective_timestamp: "2026-08-09"
effective_timestamp_basis: official JRA result date
fetch_exit_code: 0
crwl_exit_code: 0
http_status: 200
parsed_row_count: 12
observed_schema:
  table: result_runner_table
  field_names:
    - finish_position
    - frame_number
    - horse_number
    - horse_name
    - sex_age
    - assigned_weight
    - jockey
    - finish_time
    - margin
    - passing_order
    - estimated_closing_time
    - body_weight
    - trainer
    - win_popularity
  raw_field_types:
    - string
    - string
    - string
    - string
    - string
    - string
    - string
    - string
    - string
    - string
    - string
    - string
    - string
    - string
  row_basis: HTML table tr with result headers and td cells; 12 rows x 14 fields
content_sha256: 85ff5415dfdd66fc5dd0b59fedb14eb8b2dbbb8d28e7e28effa29165539bd012
crwl_markdown_sha256: 394ea4e74eaa5ca7c6afc3299de959d07daae4fe4e0d292afb69297c8961078b
robots_snapshot_url: https://www.jra.go.jp/robots.txt
robots_status: "HTTP 200; User-agent: *; Disallow: (empty); CRWL exit 0"
terms_url: https://www.jra.go.jp/use/
terms_status: "HTTP 200; CRWL exit 0; JRA states its managed media are copyrighted and secondary use beyond private use or quotation requires prior application and permission; page states applications are limited to corporations"
raw_values_exported: false
allowed_scope: private_shadow
cash_authorized: false
raw_local_private_non_git_status: "mode 700; bounded HTML/CRWL snapshot outside Git; no raw artifact staged"
gate_status: PASS_PRIVATE_SHADOW
```

## Verification boundary

The robots observation matches `User-agent: *` with an empty `Disallow`.
The official use page was read for the permission boundary; it does not
constitute a verified permission document for this probe, hence
`permission_document_verified: false`. No login, account, purchase, betting,
Telegram, CFO, model, or cash action occurred.
Fresh Sol review approved spec compliance and evidence quality with no
Critical/Important/Minor findings; acceptance is private-shadow only and does
not change `permission_document_verified: false` or `cash_authorized: false`.
