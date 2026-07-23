# Life Manager Repository Rename Design

## Status and authority

Status: complete. Final evidence is `/Users/anicca/.codex/evidence/life-manager-repository-rename/final-completion-report.md`, with the full private checksum inventory in `manifest.sha256`.

The user approves this design in full. The product, AI, agent, mission, runtime, and single public monorepo are all **Life Manager** at `Daisuke134/life-manager`. `Anicca` is the company name only. This decision is closed and does not require another choice or review gate.

Repository Tasks 1–4 are partially executed and recorded below. All continuation, including the redirect repair, follows `docs/superpowers/plans/2026-07-23-life-manager-repository-rename.md` in a separately reviewed scoped run.

## Scope

This design covers only the collision-safe rename of two public GitHub repositories, their local remotes, GitHub redirects, GitHub Pages, and live repository URL references.

It does not rename, archive, delete, merge, deploy, or otherwise change `Daisuke134/anicca-products` (repository ID `1245528469`), Railway, product code, secrets, or any Life Manager §10 product/runtime work. The content/history import from `life-manager-v0` is a later migration and must finish with equivalence proof before that repository can be archived.

## Measured documentation boundary

The target `/Users/anicca/anicca` tree does not contain `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`. Its currently tracked `docs/superpowers/specs/**` and `docs/superpowers/plans/**` files are pre-consolidation historical artifacts, so their truthful old-name statements are preserved rather than rewritten. The current canonical consolidation SSOT is this documentation worktree's `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`, which already names final product/repository slug `Life Manager` / `life-manager`.

The live-reference guard may exclude those two measured historical directories only while the target canonical path remains absent. Task 5 asserts that boundary before creating the guard and records the tracked-file inventory. If the canonical file or a post-consolidation live document appears in the target, execution stops and narrows the exclusion before continuing; it never silently treats future documents as historical.

## Approved repository identities

Repository identity is tracked first by immutable numeric ID. The initial collision-safe move resolves each repository through the numeric REST endpoint and uses its GraphQL node ID. The redirect repair is the one explicit exception: GitHub's documented rename path and official CLI use a slug-addressed REST `PATCH`, so Task 4R permits two tightly bounded REST mutations only after the slug and numeric identity agree immediately before each call.

| Repository ID | Measured GraphQL node ID | Pre-execution name | Final/current name | Required state |
|---:|---|---|---|---|
| `1273052304` | `R_kgDOS-E8kA` | `Daisuke134/life-manager` | `Daisuke134/life-manager-v0` | public, unarchived, undeleted until history/content import and equivalence verification finish |
| `1248111245` | `R_kgDOSmSqjQ` | `Daisuke134/anicca` | `Daisuke134/life-manager` | public, unarchived, canonical product monorepo |

The intermediate slug `Daisuke134/life-manager-v0` returns `404` before execution. The final slug is currently occupied by repository ID `1273052304`, so a direct rename cannot be collision-safe.

## Observed execution state and redirect repair

Tasks 1–3 finish the collision-safe identity move:

- ID `1273052304` / node `R_kgDOS-E8kA` is now public, unarchived `Daisuke134/life-manager-v0`; its local clone uses the explicit `life-manager-v0` remote.
- ID `1248111245` / node `R_kgDOSmSqjQ` is now public, unarchived `Daisuke134/life-manager`; the shared clone and all 22 linked worktrees use the final remote.
- Before/after refs, default HEADs, issue identities, and stargazer identities are byte-identical for both IDs. `Daisuke134/anicca-products` metadata is byte-identical and Railway/product side effects remain zero.

Task 4 exposes one failure only: old `Daisuke134/anicca` returns web/API `404` and Git `ls-remote` fails. The false hypothesis is **GraphQL `updateRepository` establishes the same compatibility redirects as GitHub's documented repository rename path**. Name and identity preservation succeed, but redirect creation does not.

Task 4R repairs only that missing compatibility surface. It performs an official REST rename roundtrip on ID `1248111245`, `life-manager → anicca → life-manager`, after exact numeric/node/slug/collision checks. Both REST legs succeed on their first attempt. GitHub's edge briefly returns the previous redirect after the final leg, then stabilizes for three consecutive observations: final `life-manager` returns HTTP 200 and old `anicca` redirects to `life-manager`. No local remote changes occur during the roundtrip. The roundtrip is not a general rollback and does not authorize creation of a new `anicca` repository.

Fresh review finds no missing baseline ref name. Two branches advance concurrently after the baseline snapshot, and both changes are same-name fast-forwards whose old commits remain ancestors of the current tips. Therefore preservation is proved as no missing ref plus unchanged-or-fast-forward ancestry, rather than a false byte-equality requirement across unrelated concurrent pushes.

## Collision-safe sequence

1. Capture ID-keyed metadata and complete branch/tag refs, issue identities, stargazer identities, Pages state, Action manifests, webhooks, rulesets, and local remotes for both repositories.
2. Immediately re-read numeric ID `1273052304`, record and verify its current `full_name`, GraphQL `node_id`, public visibility, and unarchived state, then call `updateRepository(input:{repositoryId:$repositoryId,name:$name})` with that verified node ID to rename it to `life-manager-v0`.
3. Immediately update `/Users/anicca/Projects/life-manager` so `origin` is `https://github.com/Daisuke134/life-manager-v0.git`; fetch and verify the remote before continuing.
4. Immediately re-read numeric ID `1248111245`, record and verify the same identity tuple, then call the same GraphQL mutation with its verified node ID to rename it to `life-manager`.
5. Immediately update the shared remote of `/Users/anicca/anicca` so `origin` is `https://github.com/Daisuke134/life-manager.git`; verify the base clone and every linked worktree resolve the same remote.
6. Compare the ID-keyed before/after evidence, validate redirects and takeover behavior, update live URLs in a separate TDD-scoped commit, and redeploy/verify Pages at its new project URL.

No step deletes a repository, force-pushes a ref, rewrites history, archives either repository, or creates a replacement repository.

## Redirect semantics and the old names

GitHub redirects repository web traffic and Git operations after a rename, but project-site URLs are an explicit exception. Therefore:

- `https://github.com/Daisuke134/anicca` and `https://github.com/Daisuke134/anicca.git` must resolve to repository ID `1248111245` after the final rename.
- A second or replacement repository must never be created at old `anicca`; that reuse would disable the redirect GitHub establishes for existing links and clones. Task 4R's temporary rename of the same ID is the only exception and ends immediately back at final `life-manager`.
- The first rename temporarily makes old `Daisuke134/life-manager` links redirect to ID `1273052304`. The second rename deliberately takes over that slug with ID `1248111245`; afterward, `Daisuke134/life-manager` must identify the final monorepo and the former repository is reachable only as `Daisuke134/life-manager-v0`.
- Redirects are compatibility behavior, not the desired local configuration. Both local remotes are updated immediately after their respective rename.

## Pages, Actions, webhooks, and rulesets

The current `Daisuke134/anicca` repository has a workflow-built project site:

| Surface | Measured state before rename | Required post-rename state |
|---|---|---|
| GitHub Pages | `https://daisuke134.github.io/anicca/`, `build_type=workflow`, source `gh-pages:/`, `cname=null` | Pages API reports `https://daisuke134.github.io/life-manager/`; workflow ID `307239134` succeeds on `gh-pages`; logged-out HTTP read succeeds |
| Action manifests | all fetched remote heads/tags have `0` files named `action.yml` or `action.yaml` | still `0`; the hosted-action redirect exception is inapplicable |
| Repository webhooks | `0` | still `0`; no endpoint migration is required |
| Repository rulesets | `0` | still `0`; no ruleset target rewrite is required |

Pages is not covered by the normal repository redirect. The new Pages URL and deployment workflow are mandatory verification items, and every live `github.com/Daisuke134/anicca`, `raw.githubusercontent.com/Daisuke134/anicca`, and `daisuke134.github.io/anicca` reference is updated in a later TDD-scoped commit. Truthful historical evidence remains unchanged and is explicitly excluded from the live-reference guard.

## Local clone and worktree mapping

| Local shared Git directory | Final `origin` | Notes |
|---|---|---|
| `/Users/anicca/Projects/life-manager` | `https://github.com/Daisuke134/life-manager-v0.git` | preserves access to repository ID `1273052304` for later import/equivalence work |
| `/Users/anicca/anicca` and its linked worktrees | `https://github.com/Daisuke134/life-manager.git` | shared Git config means one remote update applies to all linked worktrees; each worktree is read-verified |

This documentation worktree belongs to `Daisuke134/anicca-products`; its remote is not changed by the rename run.

## Fail-closed and rollback rules

- Immediately before every rename or conditional rollback, fetch the target through `repositories/{numeric_id}`, record its identity tuple, and require the expected numeric ID, `full_name`, `node_id`, public visibility, and unarchived state. The mutation uses only that verified node ID. Any mismatch, lost admin access, unexpected webhook/ruleset/Action manifest, or occupied intermediate slug stops before mutation.
- If the first rename fails, change nothing else.
- If the first rename succeeds and the second fails before ID `1248111245` moves, stop. If the `life-manager` lookup still redirects to ID `1273052304` and no different repository owns that slug, the only permitted rollback is renaming ID `1273052304` back to `life-manager` and restoring its local remote. Otherwise preserve both repositories and escalate; never delete or overwrite a colliding repository.
- Once ID `1248111245` successfully becomes `Daisuke134/life-manager`, do not create a repository named `anicca` and do not rename backward as an improvised rollback. The only permitted temporary reuse is reviewed Task 4R's two-leg REST roundtrip on the same immutable ID, with the second leg attempted immediately even when the first-leg redirect observation fails.
- If Task 4R's first REST mutation succeeds and the final REST mutation fails, re-read both numeric IDs and retry the same `anicca → life-manager` REST mutation once. Do not use GraphQL fallback, create/delete/archive, force-push, or move ID `1273052304`. A second failure stops with exact state evidence; the first REST leg is expected to keep the canonical `life-manager` URL compatible with the temporarily named same repository.
- A failed comparison, Pages deployment, or live-reference test is a failed migration. It does not authorize deletion, archive, force-push, history replacement, repository creation, Railway changes, or changes to `anicca-products`.

## Exact done conditions

The rename is done only when one evidence bundle proves all of the following:

- ID `1273052304` is exactly `Daisuke134/life-manager-v0`, public and unarchived; ID `1248111245` is exactly `Daisuke134/life-manager`, public and unarchived.
- Every baseline ref name still exists. Each ref SHA is either unchanged or its baseline SHA is an ancestor of the current same-name ref; every concurrent advance is recorded. Issue IDs/numbers/states and stargazer IDs are byte-identical for each repository ID, and default branches and their head SHAs match. This proves no lost history, branches, tags, issues, or stars without treating legitimate concurrent fast-forwards as loss.
- `/Users/anicca/Projects/life-manager` and `/Users/anicca/anicca` use their approved final remotes, all linked worktrees agree, and fetch/`ls-remote` succeed.
- Old `anicca` web and Git URLs resolve to ID `1248111245`; final `life-manager` resolves to ID `1248111245`; explicit `life-manager-v0` resolves to ID `1273052304`.
- Pages API and successful workflow evidence identify `https://daisuke134.github.io/life-manager/`, and a logged-out request succeeds. No custom domain appears unexpectedly.
- Action manifest, webhook, and ruleset counts remain zero.
- The live-reference RED→GREEN test passes, the scoped URL-change commit is reviewed, pushed, merged, and its remote SHA is recorded. Historical evidence remains unchanged.
- `Daisuke134/anicca-products` remains ID `1245528469` with the same name, and no Railway or §10 product/runtime side effect occurs.
- The evidence contains every command exit result and no secret. Both repositories still exist; neither history is deleted.

## Sources and direct evidence

Each material operational decision above is grounded in the following source or live GitHub response:

- Final product name: [Life Manager README](https://github.com/Daisuke134/life-manager#readme) / direct quote: “Life Manager”.
- Repository ID `1273052304`: [GitHub REST live repository response](https://api.github.com/repositories/1273052304) / direct quote: `"id": 1273052304`, `"node_id": "R_kgDOS-E8kA"`, and `"full_name": "Daisuke134/life-manager"`.
- Repository ID `1248111245`: [GitHub REST live repository response](https://api.github.com/repositories/1248111245) / direct quote: `"id": 1248111245`, `"node_id": "R_kgDOSmSqjQ"`, and `"full_name": "Daisuke134/anicca"`.
- Redirect and Pages exception: [Renaming a repository — GitHub Docs](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository) / direct quote: “with the exception of project site URLs, is automatically redirected”.
- Never create a replacement at old `anicca`, and hosted-Action caveat: [リポジトリの名前を変更する — GitHub Docs](https://docs.github.com/ja/repositories/creating-and-managing-repositories/renaming-a-repository) / direct quote: 「元の名前を再利用しないでください」「アクションに呼び出しがリダイレクトされることはありません」。
- Local remote update: [Managing remote repositories — GitHub Docs](https://docs.github.com/en/get-started/git-basics/managing-remote-repositories) / direct quote: `git remote set-url origin REMOTE-URL`.
- Immutable mutation target: [GitHub GraphQL `UpdateRepositoryInput`](https://docs.github.com/en/graphql/reference/input-objects#updaterepositoryinput) / live schema descriptions: “The ID of the repository to update.” and “The new name of the repository.”
- Official redirect-producing rename path: [GitHub CLI `RenameRepo`](https://github.com/cli/cli/blob/trunk/api/queries_repo.go) / source uses `client.REST(..., "PATCH", path, ...)` against `repos/{owner}/{repo}` with the new `name`.
- Task 4 live failure: private evidence `/Users/anicca/.codex/evidence/life-manager-repository-rename/task4-preservation-verification-report.md`, SHA-256 `13eaf0c6b4b4205aef227d0b29dd6e5ff39166698b18c0ee3d782aa432238c81`; refs/HEAD/issues/stars pass while old web/API/Git redirect fails.
- Task 4R repair review: private evidence `/Users/anicca/.codex/evidence/life-manager-repository-rename/task4r-redirect-repair-report.md`; old web/API/Git redirect, repository identities, ref ancestry, HEAD, issues, stars, remotes, dirty fingerprints, and `anicca-products` preservation all pass with no material finding.
- Pages state: [GitHub Pages live API response](https://api.github.com/repos/Daisuke134/anicca/pages) / direct quote: `"html_url":"https://daisuke134.github.io/anicca/"` and `"cname":null`.
- Webhook absence: [GitHub repository hooks live API](https://api.github.com/repos/Daisuke134/anicca/hooks) / authenticated live response: `[]`.
- Ruleset absence: [GitHub repository rulesets live API](https://api.github.com/repos/Daisuke134/anicca/rulesets) / authenticated live response: `[]`.
- Documentation boundary: target-tree measurement reports `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` absent; the canonical [Life Manager consolidation SSOT](2026-07-19-anicca-one-repo-consolidation-spec.md) directly states `canonical GitHub slug=life-manager`.
