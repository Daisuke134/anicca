# Manager Phase06 — pin Playwright 1.56.1 to a supported runner (2026-11-05 JST)

## Observed failure

On commit `552141cb25f66b92b098cb78a6feb853afb80ff6`, workflow run #242 failed in the step `Install locked upstream browser and accessibility engines`. The hosted runner resolved `ubuntu-latest` to `ubuntu26.04-x64`; the pinned E2E package uses `@playwright/test` 1.56.1. The log states: `Playwright does not support chromium on ubuntu26.04-x64`. Manager unit contracts, repository boundaries, unchanged task-registry validation and the immutable service bundle build had already succeeded. Browser verification was skipped.

## Primary-source check

Playwright's official installation/system-requirements documentation lists Ubuntu 22.04 and 24.04 as supported stable Linux environments for the installed browser toolchain. The current docs also list Ubuntu 26.04 for newer Playwright releases, but that does not retroactively make pinned Playwright 1.56.1 compatible with the 26.04 runner. The observed 1.56.1 failure is taken from the exact hosted workflow log, not inferred from current docs.

- Playwright installation and system requirements: https://playwright.dev/python/docs/intro
- Playwright browser installation and supported OS guidance: https://playwright.dev/docs/browsers

## Atomic CI correction

- In `.github/workflows/manager-phase06-service.yml`, pin only the browser-verification jobs (`verify` and `verify-live`) to `ubuntu-24.04`.
- Leave the non-browser `publish-owned-prefix` job unchanged.
- Keep the exact Playwright package lock unchanged; no dependency upgrade or lockfile rewrite was necessary.
- The workflow remains scoped to the Manager service; the research branch is the only ref changed.

## Verification boundary

This is a runner compatibility correction, not a browser-test success claim. A new hosted Phase06 run on the updated workflow must complete the browser step before browser verification can be marked successful. The `verify-live` job remains gated by the existing main-only publication path and was not run on this research branch.

No deployment, publication, live external write, personal-data access, or Life Manager runtime/main change occurred.