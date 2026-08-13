# Lancers G4A Canonical Sales Source Implementation Plan

## Goal

Replace the mutable, fulfillment-only `work-sync` runtime with one canonical, exact-release, read-only 5-minute source that sees both application replies and storefront inquiry/order boards. It must not send, click, mutate provider state, append ledger events, or claim a contract.

## Ponytail decision

Reuse the existing `ai.anicca.lancers-revenue-work-sync` owner, account/browser lock, Playwright CDP session, exact-SHA installer, and release manifest. Do not add a scheduler, DB, schema, queue, model call, or generic marketplace abstraction.

Rejected:

- Copying the 274-line deployed observer unchanged: it watches only `working` and can emit `order_awarded` without an official contract receipt.
- Keeping the old owner and adding `sales-loop`: it creates two polling owners for one account and one source.
- Adding `ContractReceipt`/capacity now: the current official board has empty `with`, so no complete contract instance exists to validate.

The release plumbing makes this five touched files even though the behavior is one small source. Skipping those files would leave mutable repo-external code in production.

## Ownership and size

Luna/Terra owns all production code, tests, commands, commit, and push for this plan. Primary Sol owns this plan, acceptance, deployment decision, and final evidence.

| File | Change | Soft target |
|---|---|---:|
| `skills/earn/lancers/scripts/work_sync.py` | canonical read-only boards/detail/messages tick | 90–130 production LOC |
| `apps/lancers-revenue/tests/test_work_sync.py` | normal snapshot plus duplicate/failure/secret regressions | 100–150 test LOC |
| `apps/lancers-revenue/launchd/ai.anicca.lancers-revenue-work-sync.plist` | existing 300s owner template, no `RunAtLoad` | 25–35 LOC |
| `apps/lancers-revenue/scripts/install-local.sh` | archive/render the work-sync exact-release file and plist | 25–45 changed LOC |
| `apps/lancers-revenue/tests/test_install_local.py` | manifest/path/schedule/single-owner assertions | 20–35 changed LOC |

Production exceeds the normal 100 LOC/3-file soft target only because source ownership and exact-release deployment are part of the same safety boundary. No shared contract, schema, ledger, reporter, application, or listing files change.

## Direct implementation

Do not run a RED-first phase. Implement the finished contract directly, then add only the regressions below and run the existing suites.

### 1. Canonical bounded source

Implement `work_sync.py` using the existing `application_tick.py` loader and helpers for `CDP_URL`, account readiness, `account_lock`, owned page creation/close, and Playwright cleanup.

One tick must:

1. Acquire the existing `work-sync.json` account lock.
2. Verify the owned browser and logged-in Lancers account.
3. Use page-context same-origin `fetch` with credentials to GET the official boards list, then each bounded board detail and messages resource.
4. Treat boards/messages as arrays and detail as an object. Validate raw snake_case fields. IDs must be non-empty opaque strings or integers normalized to strings.
5. Follow the provider's observed cursors: boards use `limit=20&modified=<last modified>`; message history uses `limit=20&message_id=<oldest id>&direction=prev`. Stop only on an empty page within the bounded maximum. Duplicate conflicts, a non-advancing cursor, malformed envelopes, HTTP failure, or reaching the maximum before an empty page fail closed.
6. Correlate only explicit `with.proposal.id`, `with.job.id`, and `with.serviceItemContract.id`. Empty/missing `with` remains unknown and never becomes a contract.
7. Return a deterministic JSON snapshot with `ok`, `logged_in`, `source_complete`, `board_count`, `required_reply_count`, `unread_count`, `application_board_count`, `storefront_contract_candidate_count`, and opaque board/message IDs plus SHA-256 hashes where needed for identity.
8. Never output message bodies, names, emails, cookies, headers, tokens, or arbitrary provider payloads.
9. Never call POST/PUT/PATCH/DELETE, click provider actions, call a model, append ledger events, or modify application/listing state.
10. Guarantee bounded process exit after the JSON line. Page/runtime cleanup exceptions, including Playwright dialog teardown races, must be caught and converted to a stable failed result without leaving the Python or driver process spinning.

If the provider envelope cannot prove completeness, return `ok=false`, `source_complete=false`, and a stable error. Do not report zero leads from an incomplete source.

### 2. Exact-release owner

Add the work-sync file to the immutable release archive and manifest. Render the existing work-sync label to the release path with `--json`, `WorkingDirectory=release`, `StartInterval=300`, `ProcessType=Background`, `Umask=63`, isolated stdout/stderr paths, and no `RunAtLoad`.

The installer must not call `launchctl`. It only writes exact-release artifacts atomically, matching the existing application/reporter pattern. There must be one work-sync plist and one work-sync label.

### 3. Minimal regressions

After implementation, verify only:

- A valid snake_case board/detail/messages fixture produces a complete sanitized snapshot and correct application/storefront candidate counts.
- Empty `with` stays unknown and produces no contract/event/ledger write.
- Duplicate board/message ID, malformed/incomplete provider response, or unsupported truncation fails closed.
- The serialized result does not contain fixture message text, buyer identity, cookie, token, or arbitrary payload fields.
- Installer manifest contains `work_sync.py`; rendered plist uses the immutable release path, 300 seconds, no `RunAtLoad`, and no unresolved placeholders.
- Cleanup failure regression proves `main` returns a stable non-zero result and does not escape an unhandled teardown exception. Live process exit is verified during deployment, not mocked as proof.

Run the new focused test, all `apps/lancers-revenue/tests`, agent-runner tests, `py_compile` for release Python files, plist lint, JSON output parse, and production diff check. Record exact counts and SHA.

## One adversarial review

Use one fresh Sol adversarial verifier, exactly once. It must try to disprove:

1. every provider call is read-only;
2. incomplete or malformed source cannot be reported as zero/healthy;
3. empty `with` cannot become `contract_active` or `order_awarded`;
4. message content or secrets cannot escape in JSON/logs;
5. only one 300-second work-sync owner exists and it points to an exact release;
6. application/listing state and ledger are not written.
7. one tick cannot remain resident or spin after emitting JSON, including on browser/page/runtime cleanup failure.

Critical/Important findings return once to the same implementer. Primary then performs mechanical verification; no second review.

## Deploy and live acceptance

Primary records pre-deploy SHA-256 for application state, listing state, and ledger. After the implementation commit is on `origin/main`, install the exact main SHA, lint the rendered plist, replace the existing mutable work-sync owner, and kickstart that real launchd owner once.

This is a production scheduler/state change, so announce it immediately before execution. The live tick is read-only but must be real, not mock/dry-run.

Accept only when:

- exit code is 0 and stderr is empty;
- stdout is one valid sanitized JSON snapshot from official boards/detail/messages;
- the deployed manifest and plist point to the exact main release;
- one work-sync label is loaded at 300 seconds;
- the kicked process exits within the bounded observation window, launchd returns idle, and no orphan work-sync Python/Playwright driver remains;
- application/listing/ledger hashes match pre-deploy values;
- no provider message, offer, order, listing, application, or ledger event is created.

## Next item after G4A

Update the SSOT with the observed source shape and evidence, then close Storefront integrity/canonicalization read-only. Only after a complete official `serviceItemContract` instance is observed do G4B `ContractReceipt`, G3C capacity, and G4C reply/offer actions begin.
