# OSS security baseline evidence

## Scope and result

| Gate | Before | Current local evidence |
|---|---:|---|
| gitleaks current tree | 16 findings | 0 |
| gitleaks full history | 852 findings / 851 unique fingerprints / 143 files | 0 after fingerprint adjudication baseline |
| PII shape gate | 63 broad-grep hits | 0; exact rule/path/value fingerprints allow only synthetic fixtures |
| TruffleHog filesystem | not independently measured | 4,441 chunks / 26,063,885 bytes / verified secrets 0 |
| TruffleHog full history | 7 verified Postgres hits pointing to one endpoint | same full-history Postgres detector: verified secrets 0 after remediation |
| Python security contract | missing packages and stale expectations | 12 tests pass with an explicit pure-stdlib security manifest |
| Shell syntax | pass | pending final exact-five rerun |

No raw secret or matched personal-data value is stored in this evidence.

## Gitleaks adjudication

| Class | Count | Disposition |
|---|---:|---|
| generic-api-key | 830 | generated-code fragments, public identifiers, placeholders, and historical inactive provider values; current-tree fixtures were changed to explicit placeholders |
| jwt | 10 | historical inactive fixture/token-shaped values |
| stripe-access-token | 4 | synthetic test values; current fixtures use explicit placeholders |
| gcp-api-key | 4 | historical credentials; provider verification returns invalid key |
| curl-auth-user | 2 | historical credential-shaped command material; no verified active secret |
| private-key | 1 | historical self-signed TLS key; paired certificate expired |
| slack-bot-token | 1 | provider verification returns `invalid_auth` |

The 851 unique historical fingerprints are recorded in `.gitleaksignore`.
The baseline is fingerprint-specific, so a value added at a new
commit/path/line is not suppressed. A mutation check with a new synthetic AWS
key was rejected by the configured detector.

Gitleaks documents that a long-history repository can use a baseline and that
each finding has a unique fingerprint:
[Gitleaks README](https://github.com/gitleaks/gitleaks#creating-a-baseline) —
“When scanning large repositories or repositories with a long history, it can
be convenient to use a baseline.”

## Active database finding and remediation

The first full-history TruffleHog run found seven verified Postgres occurrences
in old backup/docs commits. They all resolved to one Railway database endpoint.
Direct readback showed:

| Check | Before | After |
|---|---|---|
| `pg_hba_file_rules` | local/IPv4/IPv6 `trust` | local/IPv4/IPv6 `scram-sha-256` |
| wrong password | connection accepted | connection rejected |
| old password | connection accepted | connection rejected |
| new password | n/a | connection accepted before public endpoint removal |
| public TCP proxy | 1 | 0 |
| consumer database route | mixed public/internal | internal Railway hostname only |

The database password was rotated, seven consumer variables across
`life-call`, `API`, `nudge-cron`, `nudge-cronp`, and `x402-agents` were updated,
and those five services were redeployed. Production readback after cutover:

| Service | Deployment | State | Health |
|---|---|---|---:|
| `life-call` | `3356efa6-e565-4f21-967b-d03fe088d739` | SUCCESS | 200 |
| `API` | `243b35b8-6b02-4daa-b800-eb31de31183d` | SUCCESS | 200 |
| `nudge-cron` | `6431065a-cf6d-4614-a714-9c3f61f8838b` | SUCCESS | 200 |
| `nudge-cronp` | `88fbc733-4953-4025-b712-f1a683ee202d` | SUCCESS | private service |
| `x402-agents` | `5ee685de-b623-4b7a-8d57-b12c027837be` | SUCCESS | 200 |

GitHub’s remediation guidance says a committed secret must be treated as
compromised and rotated:
[GitHub secret scanning](https://docs.github.com/en/code-security/secret-scanning/managing-alerts-from-secret-scanning/resolving-alerts) —
“Once a secret has been committed to a repository, you should consider the
secret compromised.”

Railway documents that public networking exposes a service to the internet:
[Railway public networking](https://docs.railway.com/networking/public-networking) —
“Public networking allows you to expose your Railway services to the
internet.” The database no longer has a public TCP proxy.

## Evidence boundary

The local implementation gates are green except for the final all-shell parse,
which is run with the complete exact-five local verification immediately
before push. Completion still requires the fresh pull request to report
gitleaks, PII, TruffleHog, Python, and Shell all green. Until then,
`OSS-SECURITY-BASELINE-1` is not marked done.
