# Lancers Storefront Read-only Inventory Plan

## Goal

Produce one complete, sanitized, official inventory of all Lancers storefront listings and their public offer fingerprints without publishing, adopting, archiving, deleting, messaging, or changing state. Explain the six duplicate-looking listings and the current `listing_readback_mismatch` with provider evidence.

## Ponytail decision

Do not canonicalize the 1,467-line mutable publisher. Do not add a scheduler, DB, state file, schema, general storefront framework, or continuous public-page poller. Add one exact-release diagnostic command and run it once.

Reuse:

- `application_tick.py`: CDP endpoint, account readiness, account lock, owned page lifecycle.
- `work_sync.py`: same-script parent watchdog/process-group cleanup and 120-second whole-command deadline.
- `install-local.sh`: immutable exact-SHA archive/manifest.

Do not reuse the publisher's global menu-link selector or exact local-tag comparison; both are proven false boundaries.

## Ownership and soft size

Luna/Terra owns production/test implementation and commands only. Primary owns this plan, review, deploy, live read-only execution, interpretation, and SSOT update.

| File | Change | Soft target |
|---|---|---:|
| `skills/earn/lancers/scripts/listing_inventory.py` | one-shot management/public reader plus sanitized projection | 100–150 production LOC |
| `apps/lancers-revenue/tests/test_listing_inventory.py` | complete six-row case and bounded fail-closed regressions | 80–120 test LOC |
| `apps/lancers-revenue/scripts/install-local.sh` | include inventory command in exact release | 1–5 changed LOC |
| `apps/lancers-revenue/tests/test_install_local.py` | manifest assertion | 1–5 changed LOC |

Four files are necessary because executable source and exact-release ownership cannot be separated. No plist changes; no owner is added.

## Task 1: Implement the exact-release inventory command

Do not run a RED-first phase. Implement the fixed contract, then add only the minimal regressions.

### Management inventory

The worker acquires the existing work-sync account lock, attaches to the owned Lancers browser, verifies the account, and reads these four routes with GET/navigation only:

- `published`: `/myplan`
- `paused`: `/myplan/paused`
- `hidden`: `/myplan/archived`
- `draft`: `/myplan/draft`

On the first page, validate the four official anchor counts. For each state, read only containers under `.p-project-plan-myplan__stores .p-project-plan-myplan__store`. Each container must have exactly one visible `.p-project-plan-myplan__store-content-over-title-link`, one numeric `/menu/detail/{id}` target, and one non-empty normalized title. Ignore `.p-project-plan-myplan__update-hint` completely.

If the official state count exceeds the first page, navigate `?page=N` in ascending order, maximum 20 pages, until the unique row count equals the official count. Empty/non-advancing page before the count, count overflow, duplicate ID/title conflict, cross-state duplicate, query/route drift, or page limit fails closed. Zero count requires zero management containers.

### Public offer fingerprint

For every inventory row, GET its exact public URL and require HTTP 200, exact route ID, one h1, one subtitle, one canonical link, one og:url equal to the visited URL, one business-description section, one order-notice section, and at least one complete plan. Extract deterministic public truth:

- listing ID/status/public URL/title
- canonical URL and its target listing ID
- plan prices and delivery days
- normalized product fields needed to hash title, subtitle, description, notice, plan descriptions/prices/delivery, and all provider-visible tag text/hrefs

Return only IDs, URLs, title, state, plan prices/delivery, `content_sha256`, and canonical target. Do not emit description/notice, seller profile, review text, messages, buyer data, cookies, headers, tokens, or raw HTML/payloads.

Group listing IDs by identical `content_sha256` deterministically. A canonical target is an observed fact, not permission to mutate. The command must not compare public tags to the local product JSON or claim a listing is the revenue canonical.

### Process and output

The launch-facing CLI is only a manual exact-release command with `--json` and a hidden worker flag. Use the existing work-sync watchdog to run the worker in a new process group with the existing 120-second deadline. Output exactly one JSON line. No launchd plist or schedule is created.

The result includes `ok`, `logged_in`, `source_complete`, four state counts, `listing_count`, sanitized listings, content groups, and stable error. Failures return nonzero. Cleanup/timeout cannot leave a Python/Playwright descendant.

## Minimal regression and verification

After direct implementation, test:

1. A complete fixture with six published management containers, zero other states, one unrelated update-hint link, and six complete public payloads returns six unique IDs, correct counts, one deterministic content group/canonical target, and no raw description/secret text.
2. Official count mismatch, duplicate/cross-state ID, malformed public route/og/plan, or page-limit fails closed and never returns healthy zero.
3. Static scan finds no POST/PUT/PATCH/DELETE, click, publisher/adopt import, ledger append, state write, or launchctl.
4. Installer manifest contains `listing_inventory.py`; existing three launchd plists and schedules remain unchanged.

Run focused tests, all `apps/lancers-revenue` tests, agent-runner tests, release Python compile, plist lint, installer exact-release tests, JSON one-line parse, diff check, and the static mutation guard. Commit and push only the feature branch.

## Task 2: Primary review and live acceptance

### One adversarial review

Use one fresh Sol reviewer exactly once. It must try to disprove management-container scoping, count/pagination completeness, public ID/og integrity, secret/raw-body exclusion, GET-only behavior, process deadline/orphan cleanup, exact-release inclusion, and absence of a new scheduler. Critical/Important findings return once to the same implementer; primary mechanically verifies the correction without a second review.

### Live acceptance

After the reviewed commit is on main, install the exact main release. Do not reload or alter application/report/work-sync schedules merely to run inventory. Execute the exact-release inventory command once while existing owners are idle, using the real browser and state root. Accept only when:

- one valid JSON line, exit 0, stderr 0, bounded completion, orphan 0;
- official counts equal the unique rows and the six expected provider IDs are observed or any provider change is explicitly reported;
- all rows have complete public fingerprints and canonical targets;
- application, listing, ledger, and existing launchd configuration hashes are unchanged;
- no provider message, application, listing publication, adoption, archive, delete, or ledger event occurs.

Primary then updates the SSOT with the verified canonical/content groups and begins the separate Storefront offer-alignment slice. No listing mutation is authorized by this plan.
