# Connector Item 23E — portable OSS boundary

## Goal

Make the canonical tree self-contained while preserving environment overrides and legacy retirement behavior.

## Scope

- Runtime scripts: 3 files. Use portable state-home defaults; legacy archived plists use install-time placeholders and are rendered by the existing retirement script.
- Tests/docs: replace developer-local roots and personal defaults with synthetic or portable references; add the smallest legacy-render regression.
- Manifest: recompute the final `runtime/agent-runner/config.json` SHA-256 and `skills/anicca-booking` tracked inventory using the verifier's exact algorithm.
- Do not exempt new files from the verifier and do not change its forbidden-root rules.

## Verification

1. Run focused Node and shell tests plus `bash -n` for changed scripts.
2. Run `node --test test/oss-self-contained.test.mjs` and `node scripts/verify-oss-self-contained.mjs`; require PASS.
3. Re-run gitleaks and PII gates, then the full Connector suite and `git diff --check`.

