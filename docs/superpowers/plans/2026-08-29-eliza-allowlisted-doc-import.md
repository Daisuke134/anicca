# Eliza Allowlisted Legacy Docs Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import only the audited public Life Manager architecture/spec/evidence documents into the joined Eliza fork under one namespace.

**Architecture:** Extract an explicit 21-file allowlist from the fixed legacy commit into a temporary directory, run the repository's existing PII scanner plus gitleaks and TruffleHog, then copy only passing Markdown files into `docs/legacy-life-manager/`. Commit a hash manifest on a new branch and write one private receipt.

**Tech Stack:** Git, POSIX shell, Python 3 existing scanner, gitleaks, TruffleHog, `jq`, `shasum`.

**Spec:** `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

## Global Constraints

- Joined source commit is exactly `152ad359358fa1456ff92e84ecef3bae91122862`.
- Legacy document source is exactly `c9bea215b87755434704a5d16dd8c0a55aff1981`.
- Migration repository is `/Users/anicca/Projects/life-manager-eliza-migration`.
- Create and push only new branch `migration/eliza-docs`.
- Import exactly the 21 named Markdown files and one generated manifest under `docs/legacy-life-manager/`.
- PII shape, gitleaks, TruffleHog verified credential, credential/state path, non-Markdown source, and out-of-namespace findings must all be zero.
- Do not import code, runtime state, JSONL, credentials, cookies, sessions, `.env`, legacy allowlists, or dirty working-tree content.
- Do not modify either repository's `main`, force-push, delete a repository, install dependencies, run CI, or touch runtime/model/provider/browser/credential/loop state.
- Verification is the manifest/hash/scan contract plus one bounded adversarial review. No unit test or full suite is added for a docs-only import atom.

---

### Task 1: Import the audited public docs and bind them to a manifest

**Files:**
- Create in migration fork: `docs/legacy-life-manager/import-manifest.json`
- Create in migration fork: the 21 manifest targets under `docs/legacy-life-manager/`
- Create outside repo: `/Users/anicca/.local/state/life-manager/migration/elz-f/history-import-receipt.json`
- Create outside repo: `/Users/anicca/Projects/life-manager-main/.worktrees/elz-f12-plan/.superpowers/sdd/2026-08-29-eliza-allowlisted-doc-import/task-1-report.md`

**Interfaces:**
- Consumes: joined branch commit `152ad359358fa1456ff92e84ecef3bae91122862` and legacy second parent `c9bea215b87755434704a5d16dd8c0a55aff1981`.
- Produces: remote branch `migration/eliza-docs`, generated hash manifest, and private receipt; ELZ-F13 clean clone consumes this branch.

- [ ] **Step 1: Fail closed and create the exact temporary allowlist**

```bash
set -e
cd /Users/anicca/Projects/life-manager-eliza-migration
JOIN_SHA=152ad359358fa1456ff92e84ecef3bae91122862
LEGACY_SHA=c9bea215b87755434704a5d16dd8c0a55aff1981
test "$(git rev-parse HEAD)" = "$JOIN_SHA"
test "$(git branch --show-current)" = migration/eliza-history
test -z "$(git status --porcelain=v1)"
test -z "$(git branch --list migration/eliza-docs)"
test -z "$(git ls-remote --heads origin refs/heads/migration/eliza-docs)"
test "$(git ls-remote origin refs/heads/migration/eliza-history | awk '{print $1}')" = "$JOIN_SHA"
FREE_KIB_BEFORE=$(df -Pk /Users/anicca | awk 'END {print $4}')
test "$FREE_KIB_BEFORE" -ge 1048576
STAGE=/Users/anicca/.local/state/life-manager/migration/elz-f/f12-import-stage
test ! -e "$STAGE"
mkdir -m 700 "$STAGE"
mkdir -p "$STAGE/source"
printf '%s\n' "$FREE_KIB_BEFORE" > "$STAGE/free-kib-before.txt"
printf '%s\n' \
  'docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md' \
  'docs/superpowers/specs/2026-08-24-life-manager-oss-onboarding-design.md' \
  'docs/superpowers/specs/2026-06-30-gig-self-improving-multiapply-loop-design.md' \
  'docs/superpowers/specs/2026-07-01-outer-improvement-loop-design.md' \
  'docs/superpowers/specs/2026-07-01-proactive-loop-architecture-and-cleanup-design.md' \
  'docs/superpowers/plans/2026-08-28-general-agent-application-effect-kernel.md' \
  'docs/superpowers/plans/2026-08-28-general-agent-bounded-specialist-runtime.md' \
  'docs/superpowers/plans/2026-08-28-general-agent-capability-manifest.md' \
  'docs/superpowers/plans/2026-08-28-general-agent-clean-release.md' \
  'docs/superpowers/plans/2026-08-28-general-agent-dependency-retirement.md' \
  'docs/superpowers/plans/2026-08-28-general-agent-first-application-canary.md' \
  'docs/superpowers/plans/2026-08-28-general-agent-goal-work-item.md' \
  'docs/superpowers/plans/2026-08-28-general-agent-oss-manifest.md' \
  'docs/superpowers/plans/2026-08-28-hosted-general-agent-e2e.md' \
  'docs/superpowers/plans/2026-08-28-hosted-general-agent-slice.md' \
  'docs/superpowers/plans/2026-08-28-hosted-general-agent-worker.md' \
  'docs/superpowers/plans/2026-08-29-eliza-local-foundation.md' \
  'docs/evidence/oss/oss-merge-1.md' \
  'docs/evidence/oss/oss-security-baseline-1.md' \
  'docs/evidence/repository/2026-07-29-life-manager-v0-retirement.md' \
  'docs/evidence/repository/2026-07-29-x402-source-consolidation.md' \
  > "$STAGE/allowlist.txt"
test "$(wc -l < "$STAGE/allowlist.txt" | tr -d ' ')" = 21
test "$(sort -u "$STAGE/allowlist.txt" | wc -l | tr -d ' ')" = 21
! rg -n -i '(^|/)(credentials?|state|sessions?|cookies?|\.env)(/|\.|$)|\.jsonl$' "$STAGE/allowlist.txt"
test "$(rg -c '\.md$' "$STAGE/allowlist.txt")" = 21
```

Expected: every gate exits `0`; the allowlist is 21 unique Markdown paths and contains no private-state path class.

- [ ] **Step 2: Extract the exact committed files and scanner inputs**

```bash
cd /Users/anicca/Projects/life-manager-eliza-migration
STAGE=/Users/anicca/.local/state/life-manager/migration/elz-f/f12-import-stage
LEGACY_SHA=c9bea215b87755434704a5d16dd8c0a55aff1981
git archive "$LEGACY_SHA" \
  $(tr '\n' ' ' < "$STAGE/allowlist.txt") \
  .gitleaks.toml scripts/security/pii_shape_scan.py \
  | tar -x -C "$STAGE/source"
while IFS= read -r source_path; do
  test -f "$STAGE/source/$source_path"
done < "$STAGE/allowlist.txt"
test -f "$STAGE/source/.gitleaks.toml"
test -f "$STAGE/source/scripts/security/pii_shape_scan.py"
```

Expected: all 21 source files and the two staging-only scanner inputs come from the exact legacy commit.

- [ ] **Step 3: Run the three focused pre-import scans**

```bash
cd /Users/anicca/Projects/life-manager-eliza-migration
STAGE=/Users/anicca/.local/state/life-manager/migration/elz-f/f12-import-stage
python3 "$STAGE/source/scripts/security/pii_shape_scan.py" \
  --allowlist "$STAGE/no-allowlist" \
  $(sed "s#^#$STAGE/source/#" "$STAGE/allowlist.txt") \
  > "$STAGE/pii-pre.txt"
gitleaks dir "$STAGE/source/docs" \
  --config "$STAGE/source/.gitleaks.toml" \
  --no-banner --redact \
  > "$STAGE/gitleaks-pre.txt" 2>&1
trufflehog filesystem "$STAGE/source/docs" \
  --json --no-update --results=verified \
  > "$STAGE/trufflehog-pre.jsonl" 2> "$STAGE/trufflehog-pre.err"
test "$(wc -l < "$STAGE/trufflehog-pre.jsonl" | tr -d ' ')" = 0
```

Expected: PII and gitleaks exit `0`; TruffleHog emits zero verified credential records. Unverified public deployment UUID heuristics do not satisfy the credential finding boundary.

- [ ] **Step 4: Create the branch and copy only allowlisted files into the namespace**

```bash
cd /Users/anicca/Projects/life-manager-eliza-migration
STAGE=/Users/anicca/.local/state/life-manager/migration/elz-f/f12-import-stage
JOIN_SHA=152ad359358fa1456ff92e84ecef3bae91122862
LEGACY_SHA=c9bea215b87755434704a5d16dd8c0a55aff1981
git switch -c migration/eliza-docs "$JOIN_SHA"
NAMESPACE=docs/legacy-life-manager
mkdir -p "$NAMESPACE"
: > "$STAGE/entries.jsonl"
while IFS= read -r source_path; do
  relative_path=${source_path#docs/}
  destination="$NAMESPACE/$relative_path"
  mkdir -p "$(dirname "$destination")"
  cp "$STAGE/source/$source_path" "$destination"
  digest=$(shasum -a 256 "$destination" | awk '{print $1}')
  jq -nc \
    --arg source "$source_path" \
    --arg target "$destination" \
    --arg sha "$digest" \
    '{source_path:$source,target_path:$target,sha256:$sha}' \
    >> "$STAGE/entries.jsonl"
done < "$STAGE/allowlist.txt"
jq -s \
  --arg source_commit "$LEGACY_SHA" \
  --arg namespace "$NAMESPACE" \
  '{version:1,source_repository:"Daisuke134/life-manager",source_commit:$source_commit,namespace:$namespace,entries:.}' \
  "$STAGE/entries.jsonl" \
  > "$NAMESPACE/import-manifest.json"
test "$(jq '.entries | length' "$NAMESPACE/import-manifest.json")" = 21
```

Expected: exactly 21 source-derived Markdown files plus one generated JSON manifest exist under the namespace.

- [ ] **Step 5: Verify every hash and scan the final namespace**

```bash
cd /Users/anicca/Projects/life-manager-eliza-migration
STAGE=/Users/anicca/.local/state/life-manager/migration/elz-f/f12-import-stage
NAMESPACE=docs/legacy-life-manager
jq -c '.entries[]' "$NAMESPACE/import-manifest.json" | while IFS= read -r entry; do
  target_path=$(printf '%s' "$entry" | jq -r .target_path)
  expected_sha=$(printf '%s' "$entry" | jq -r .sha256)
  test "$target_path" = "$NAMESPACE/${target_path#${NAMESPACE}/}"
  test -f "$target_path"
  test "$(shasum -a 256 "$target_path" | awk '{print $1}')" = "$expected_sha"
done
test "$(find "$NAMESPACE" -type f | wc -l | tr -d ' ')" = 22
test "$(find "$NAMESPACE" -type f -name '*.md' | wc -l | tr -d ' ')" = 21
test "$(find "$NAMESPACE" -type f -name '*.json' | wc -l | tr -d ' ')" = 1
! find "$NAMESPACE" -type f | rg -i '(^|/)(credentials?|state|sessions?|cookies?|\.env)(/|\.|$)|\.jsonl$'
python3 "$STAGE/source/scripts/security/pii_shape_scan.py" \
  --allowlist "$STAGE/no-allowlist" "$NAMESPACE" \
  > "$STAGE/pii-post.txt"
gitleaks dir "$NAMESPACE" \
  --config "$STAGE/source/.gitleaks.toml" \
  --no-banner --redact \
  > "$STAGE/gitleaks-post.txt" 2>&1
trufflehog filesystem "$NAMESPACE" \
  --json --no-update --results=verified \
  > "$STAGE/trufflehog-post.jsonl" 2> "$STAGE/trufflehog-post.err"
test "$(wc -l < "$STAGE/trufflehog-post.jsonl" | tr -d ' ')" = 0
git check-ignore -q "$NAMESPACE/import-manifest.json"
test -z "$(git ls-files "$NAMESPACE")"
```

Expected: all hashes match; file counts are exact; all three post-import scans pass; the existing `docs/*` ignore rule is confirmed before the exact force-add gate.

- [ ] **Step 6: Commit, push the new branch, and verify remote readback**

```bash
cd /Users/anicca/Projects/life-manager-eliza-migration
JOIN_SHA=152ad359358fa1456ff92e84ecef3bae91122862
git add -f docs/legacy-life-manager
git -c core.whitespace=-trailing-space diff --cached --check
test "$(git diff --cached --name-only | wc -l | tr -d ' ')" = 22
! git diff --cached --name-only | rg -v '^docs/legacy-life-manager/'
git commit -m "docs: import allowlisted Life Manager history"
IMPORT_SHA=$(git rev-parse HEAD)
git push -u origin migration/eliza-docs
REMOTE_IMPORT_SHA=$(git ls-remote origin refs/heads/migration/eliza-docs | awk '{print $1}')
test "$REMOTE_IMPORT_SHA" = "$IMPORT_SHA"
test "$(git ls-remote origin refs/heads/main | awk '{print $1}')" = 29bed1bb394a2c0c7c0df6dc12babbe28667efbe
test "$(git ls-remote origin refs/heads/migration/eliza-history | awk '{print $1}')" = "$JOIN_SHA"
test -z "$(git status --porcelain=v1)"
```

Expected: the source-preserving cached check ignores only the two audited legacy trailing-space lines; only the new branch is pushed; both prior remote refs remain unchanged; working tree is clean.

- [ ] **Step 7: Write the private receipt and remove only the temporary staging directory**

```bash
cd /Users/anicca/Projects/life-manager-eliza-migration
STAGE=/Users/anicca/.local/state/life-manager/migration/elz-f/f12-import-stage
JOIN_SHA=152ad359358fa1456ff92e84ecef3bae91122862
LEGACY_SHA=c9bea215b87755434704a5d16dd8c0a55aff1981
NAMESPACE=docs/legacy-life-manager
IMPORT_SHA=$(git rev-parse HEAD)
REMOTE_IMPORT_SHA=$(git ls-remote origin refs/heads/migration/eliza-docs | awk '{print $1}')
MANIFEST_SHA=$(shasum -a 256 "$NAMESPACE/import-manifest.json" | awk '{print $1}')
INVENTORY_SHA=$(jq -r '.entries[] | "\(.sha256)  \(.target_path)"' "$NAMESPACE/import-manifest.json" | shasum -a 256 | awk '{print $1}')
FREE_KIB_BEFORE=$(tr -d ' ' < "$STAGE/free-kib-before.txt")
FREE_KIB_AFTER=$(df -Pk /Users/anicca | awk 'END {print $4}')
jq -n \
  --arg join "$JOIN_SHA" \
  --arg legacy "$LEGACY_SHA" \
  --arg imported "$IMPORT_SHA" \
  --arg remote "$REMOTE_IMPORT_SHA" \
  --arg manifest "$MANIFEST_SHA" \
  --arg inventory "$INVENTORY_SHA" \
  --argjson free_before "$FREE_KIB_BEFORE" \
  --argjson free_after "$FREE_KIB_AFTER" \
  '{
    atom:"ELZ-F12",status:"passed",join_sha:$join,legacy_source_sha:$legacy,
    import_sha:$imported,remote_readback_sha:$remote,namespace:"docs/legacy-life-manager",
    imported_markdown_files:21,manifest_files:1,manifest_sha256:$manifest,inventory_sha256:$inventory,
    pii_findings:0,gitleaks_findings:0,trufflehog_verified_findings:0,credential_state_paths:0,
    non_markdown_source_files:0,out_of_namespace_changes:0,dirty_code_imports:0,
    force_pushes:0,main_mutations:0,free_kib_before:$free_before,free_kib_after:$free_after
  }' > /Users/anicca/.local/state/life-manager/migration/elz-f/history-import-receipt.json
chmod 600 /Users/anicca/.local/state/life-manager/migration/elz-f/history-import-receipt.json
jq -e '
  .atom=="ELZ-F12" and .status=="passed" and .join_sha=="152ad359358fa1456ff92e84ecef3bae91122862" and
  .legacy_source_sha=="c9bea215b87755434704a5d16dd8c0a55aff1981" and .import_sha==.remote_readback_sha and
  .imported_markdown_files==21 and .manifest_files==1 and .pii_findings==0 and .gitleaks_findings==0 and
  .trufflehog_verified_findings==0 and .credential_state_paths==0 and .non_markdown_source_files==0 and
  .out_of_namespace_changes==0 and .dirty_code_imports==0 and .force_pushes==0 and .main_mutations==0
' /Users/anicca/.local/state/life-manager/migration/elz-f/history-import-receipt.json
test "$(stat -f '%Lp' /Users/anicca/.local/state/life-manager/migration/elz-f/history-import-receipt.json)" = 600
test "$(realpath "$STAGE")" = "$STAGE"
find "$STAGE" -mindepth 1 -depth -delete
rmdir "$STAGE"
test ! -e "$STAGE"
```

Expected: receipt predicate exits `0`, mode is `0600`, and only the regenerable temporary stage is removed.

- [ ] **Step 8: Report focused evidence**

Write `task-1-report.md` with branch/local/remote SHAs, exact counts, namespace, manifest/inventory hashes, all scan counts, changed-path proof, free KiB, receipt mode, and concerns. Do not run product tests, full suites, or CI.

## Plan Self-Review

- Spec coverage: the single task closes only ELZ-F12 and produces its named receipt.
- Placeholder scan: every source path, target namespace, count, tool, SHA, and receipt field is explicit.
- Value consistency: the same join/legacy SHAs, 21-file count, namespace, and scan-zero contract appear in every step.
- Scope: ELZ-F13 clean-clone replay, plugin code, Lancers, cutover, and cloud are excluded.

## Execution Handoff

Execute with `superpowers:subagent-driven-development`: one Luna implementer, one focused primary verification, and one bounded read-only adversarial review. A finding returns only to the same implementer and only that finding is re-reviewed.
