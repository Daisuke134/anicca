# Connector Item 23D — personal-data shape cleanup

## Goal

Remove all sixteen PII-shape findings without admitting personal data to the synthetic-fixture allowlist.

## Scope

- Production files: 0.
- Tests: 7 files / 9 findings; replace Gmail and E.164 literals with explicit non-PII placeholders that retain each parser/validation contract.
- Historical evidence/plans/spec: 5 files / 7 findings; replace personal values with `<REDACTED_EMAIL>` or `<REDACTED_PHONE>` while retaining the evidentiary meaning.
- `.pii-shape-allowlist`: 0 additions.

## Verification

1. Run every changed focused test.
2. Run `python3 scripts/security/pii_shape_scan.py --allowlist .pii-shape-allowlist .` and require clean output.
3. Run security scanner contract tests and `git diff --check`.

