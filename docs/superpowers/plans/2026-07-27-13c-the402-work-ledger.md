# 13c-WORK The402 work ledger implementation plan

1. Add failing tests for strict The402 settlement-to-job classification.
2. Add a pure provenance classifier with exact, unique, terminal-state matching.
3. Extend the existing x402 ledger mapper so WORK and SELL share one dedup key but retain distinct sources and metadata.
4. Wire the production bridge to fetch bounded The402 earnings/jobs evidence and reject unavailable or ambiguous provenance.
5. Run focused and full tests, inspect the branch diff for secrets/PII, commit, push, and merge.
6. Install from canonical main, kick the existing acquisition/worker/observer/settlement/ledger loops, and record honest zero-or-real production evidence.
7. Update the SSOT cursor without treating an external buyer/job wait as a blocking condition.
