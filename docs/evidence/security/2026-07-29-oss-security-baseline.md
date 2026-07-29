# OSS-SECURITY-BASELINE-1 evidence

Raw credentials and personal values are intentionally absent from this file,
the CI output, and both allowlists.

## Root-cause reproduction

| Gate | Reproduced cause | Correction |
|---|---|---|
| gitleaks current tree | `gitleaks detect` was labeled as a working-tree scan, but in gitleaks 8.30.1 it is the deprecated alias of `git` history scanning | use `gitleaks dir .` for the merge result |
| gitleaks history | the repo has a large pre-baseline history; failing every run on already-adjudicated immutable findings does not distinguish a new leak | scan every ref with `gitleaks git ... --log-opts=--all` and ignore only exact finding fingerprints |
| PII | broad path exclusions hid both fixtures and genuine personal values and printed only aggregate counts | redact values, fingerprint `rule + repo-relative path + value`, and permit only 14 exact synthetic phone fixtures |
| Python | the security workflow called every `test_*.py` directly and mislabeled all of them pure-stdlib | retain AST parsing for every Python file and execute only the explicit security-test manifest |
| X launch gate | the test still expected `9c` to be open after the canonical spec recorded `9c` done | update the live-spec expectation; `9d` remains the only blocker |

The original Python command produced 50 failures: 49 were import/package/CWD
contract violations caused by the indiscriminate runner, and one was the stale
`9c` expectation. Installing arbitrary dependencies would not repair the wrong
test-discovery contract.

## Historical secret adjudication

Fresh `gitleaks 8.30.1` without the fingerprint baseline scans 10,447 commits,
about 469.73 MB, and reports 848 findings / 847 unique fingerprints:

| Rule | Findings | Adjudication |
|---|---:|---|
| generic API key | 826 | 670 generated vendored PlantUML identifiers; 20 test fixtures; 39 docs/evidence strings; 10 public app identifiers; 87 remaining source/config strings reviewed by path and runtime equality |
| JWT | 10 | package metadata and documented/sample tokens; no current runtime equality |
| curl auth user | 2 | research-document examples; no current runtime equality |
| GCP API key | 4 | two unique historical values; provider readback returns HTTP 400 for both |
| Stripe access token | 4 | one synthetic test value across history; provider readback returns HTTP 401 |
| Slack bot token | 1 | provider `auth.test` returns `invalid_auth` |
| private key | 1 | key belongs to a self-signed `CN=localhost` certificate, absent from current tree; certificate expired at `2026-06-21T13:40:11Z` |

An in-memory comparison against the agent-owned runtime environment finds two
exact matches, both non-secret identifiers: an App Store Connect issuer UUID
and a Mixpanel client project token. No provider credential from history equals
the current runtime credential values.

The remaining generic historical credentials that could be provider keys were
checked separately without printing values:

| Historical location | Provider readback |
|---|---|
| old proxy environment, EXA key | HTTP 401 |
| old dotfiles mirror, Firecrawl key | HTTP 401 |
| old desktop deployment client key | obsolete internal example; current code reference 0 and runtime equality 0 |

`.gitleaksignore` contains 851 exact fingerprints: all 847 findings produced by
the current config plus four exact findings produced before the public
on-chain-contract allowlist was tightened. It contains no wildcard, path-wide,
rule-wide, or raw-secret entry.

This follows GitHub's incident priority: “rotate the affected credential
immediately.” GitHub also notes that history removal is often unnecessary
after revocation. Source:
[GitHub secret scanning](https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning).
The fingerprint mechanism follows gitleaks' documented `.gitleaksignore`
contract. Source:
[gitleaks README](https://github.com/gitleaks/gitleaks/blob/master/README.md).

## Personal-data adjudication

Gmail addresses and real phone-shaped examples are removed from current source.
Operational scripts resolve the account from runtime `GOG_ACCOUNT`; the
YouTube helper resolves the phone from `DAIS_PHONE` or `--phone` and fails
closed only when provider verification actually requires it.

The 14 retained matches are synthetic test/eval phone fixtures. Each is bound
to its exact rule, repository path, and value by SHA-256. Moving the same value
to another file, changing it, or adding a new match fails CI. Scanner output
contains only path, line, and rule.

## Local verification

| Command / contract | Result |
|---|---|
| `gitleaks dir .` | PASS, no leaks |
| `gitleaks git ... --log-opts=--all` with exact baseline | PASS, 10,448 commits / 469.73 MB / no leaks |
| `python3 scripts/security/pii_shape_scan.py ...` | PASS, clean |
| declared Python security manifest | PASS, 13 tests |
| AST parse every `*.py` | PASS |
| `bash -n` every `*.sh` | PASS |
| report recipient regression | PASS, 16 tests |

GitHub Actions exact-five status is recorded in the canonical spec only after a
fresh pull request returns gitleaks / PII / TruffleHog / Python / Shell green.
