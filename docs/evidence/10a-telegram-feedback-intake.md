# 10a Telegram feedback intake — real L3

## Outcome

An explicit Telegram `feedback:` / `フィードバック:` message is classified at the user-facing
webhook edge, scrubbed before persistence, stored as a closed summary/labels/HMAC source reference,
and acknowledged without echoing its content.

The database table has no raw text or identity columns. It contains only `id`, `source_ref`,
`summary`, `labels`, `status`, `issue_url`, and timestamps. PUBLIC table/sequence privileges are
revoked.

## Real provider and database evidence

- Real user Telegram message id: `3922`.
- Real bot acknowledgement id: `3923`.
- Acknowledgement: `Thanks — your privacy-safe feedback was recorded.`
- Railway Postgres row id: `1`, status `queued`.
- Stored summary: `Calendar panel button label is confusing; please say Connect Calendar.`
- Labels: `feedback,calendar,panel`.
- Source reference: `tg:sha256:5d078e81db0e8eb547caf6f7d3daae62`.
- Forbidden raw/identity columns (`raw_text`, chat/user/actor ids, email, phone): `0`.
- Telegram webhook is restored to
  `https://life-call-production.up.railway.app/telegram`, pending updates `0`, last error `null`.

The real message intentionally contains no PII. Contract tests separately prove that email, phone,
postal address, URL/query, Telegram handle, explicit name, and secret-shaped values are replaced
before the parameterized insert. The HMAC provenance input contains the internal user/chat/message
tuple, but only its 128-bit hexadecimal reference is stored.

## Release evidence

- Code commit: `62057f6b`.
- PR: <https://github.com/Daisuke134/life-manager/pull/1084>.
- Staging method 1 deployment `08e55b43-1164-4f1e-9046-10d465b54fc9` fails before build because an
  app-only archive cannot satisfy the service source root.
- Staging method 2 deployment `d90b92f9-67eb-429a-92ba-661b14900b4b` fails before build because the
  stale staging metadata still expects `apps/life-call`.
- Method 3 byte-copies the current app into that expected path only inside a temporary upload
  archive. Deployment `ac0f6b9a-2a15-4762-88fc-52b7fe92caa4` is `SUCCESS`; `/health` is HTTP 200.
- Production's feedback DB reference is staged secret-to-secret for the next production deploy and
  SHA-equals the existing Railway Postgres internal URL.
- Temporary staging Telegram/DB/provenance variables are deleted after the controlled run.

## Verification

- Focused module, migration, production HTTP webhook, and existing callback contracts: `8/8` PASS.
- Full Life Manager `npm test`: exit `0`, fail `0`.
- Every eval: `21/21 + 12/12 + 12/12 + 27/27 + 18/18 + 15/15 + 12/12`, all 100%.
- Panel privacy eval: PASS.
- Migration preflight: table count `1` inside a transaction and `0` after rollback; applied
  production table count `1`, columns `8`.
- Changed-path gitleaks and PII-shape scans: `0`.

## Upstream basis

- node-postgres warns against concatenating parameters into SQL and documents passing unaltered
  query text plus separate parameters. Source:
  [node-postgres queries](https://github.com/brianc/node-postgres/blob/master/docs/pages/features/queries.mdx).
- PostgreSQL defines `ON CONFLICT DO NOTHING` as avoiding the conflicting insert rather than raising
  a unique violation. Source:
  [PostgreSQL INSERT reference](https://github.com/postgres/postgres/blob/master/doc/src/sgml/ref/insert.sgml).
