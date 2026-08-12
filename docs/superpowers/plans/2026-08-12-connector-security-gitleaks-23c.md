# Connector Item 23C — secret-shaped fixture cleanup

## Goal

Make both current-tree and full-history gitleaks gates pass without hiding a live secret or weakening repository-wide scanning.

## Scope

- Production files: 0.
- Test/fixture/history files: 13 existing files plus `.gitleaksignore`; mechanical substitutions only, estimated 30–45 changed lines.
- Replace synthetic API/idempotency values with low-entropy constructed fixtures while preserving minimum-length and identity contracts. Replace derived hashes with runtime construction or explicit redaction. Reword the one prose false positive.
- Add only the ten exact commit-prefixed fingerprints introduced by the Connector feature to `.gitleaksignore`; do not add path/rule allowlists.

## Verification

1. Run every changed focused test.
2. Run `gitleaks dir . --config .gitleaks.toml --no-banner --redact -v` and require zero current-tree findings.
3. Run `gitleaks git . --config .gitleaks.toml --no-banner --redact -v --log-opts=--all` and require zero unadjudicated history findings.
4. Run `git diff --check`; inspect the diff for raw credentials and unrelated changes.

