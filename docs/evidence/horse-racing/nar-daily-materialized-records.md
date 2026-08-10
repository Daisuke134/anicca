# NAR daily materialized win records

## Redacted execution evidence

| Field | Observed value |
|---|---|
| evidence_class | `REAL_PUBLIC_WEB_RECORD` |
| source_authority | `official` |
| jurisdiction | `NAR` |
| market | `win` (`賭式=単勝` only) |
| source_url | `https://www.keiba.go.jp/KeibaWeb/DataDownload/OddsDataDownload?type=daily` |
| snapshot_at | `2026-08-10T10:46:23+09:00` |
| race archive SHA-256 | `60c8fb659d6b31369453bf6121576d1af082ddc274e3380dd19e3135403d0135` |
| odds archive SHA-256 | `feaa43d6bdaa019aa748a7ce05f527235647531bc90bfcc38fb0eadb5dc8c515` |
| materialized record count | `7` |
| materialized runner count | `76` |
| official odds manifest parsed rows | `25008` |
| coverage start (JST) | `2026-08-10T11:40:00+09:00` |
| coverage end (JST) | `2026-08-10T18:10:00+09:00` |
| permission_document_verified | `false` |
| allowed_scope | `private_shadow` |
| raw_values_exported | `false` |
| cash_authorized | `false` |
| model_ready | `false` |
| settled_payback_rows | `0` |
| gate blocker | `NO_SETTLED_PAYBACK` |

The parser accepted only complete races where every official horselist runner had
one unique positive `単勝` row, with no extra runner key, and where the odds archive
snapshot was no later than the scheduled start minus ten minutes. Incomplete races,
zero odds, non-win bet types, and post-cutoff candidates were excluded without
inventing zero values.

Private Mac-local normalized records contain deterministic opaque identifiers,
normalized numeric `odds`, and may contain numeric `body_weight_kg` for parser/audit
input. These values remain inside the private process. The committed redacted
evidence and `AuditReport` export no numeric odds or weights, no horse/person names,
result or payout fields, raw CSV rows, credentials, or archive members. The private
ZIPs remain outside Git at:

`/Users/anicca/Library/Application Support/Anicca/horse-racing/raw/nar/`

`audit_records` was run against the exact official daily odds manifest above. It
returned `record_count=7`, `race_count=7`, `model_ready=false`,
`settled_payback_rows=0`, and `cash_authorized=false`. This is a materialized
private-shadow data result, not a model or purchase authorization.
