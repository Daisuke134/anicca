# PANEL-0 six-blocker rescue — behavior RED only

Fresh `gpt-5.6-sol` builder. Work only in `/Users/anicca/anicca-project/.worktrees/lm-panel-control-center`. Exact branch HEAD/upstream/PR #331 head is `c3fbf22ebe3148a52d4768dd36d00d4230e3fa28`. The only allowed starting dirt is untracked `apps/life-call/lib/panel-permanent-session.test.js`, SHA-256 `8ca3f3e9b43159d9d0739d31df6d89a2b9763f38b1e7b22c68c722adb94d9553`. If any other path is dirty or any SHA differs, stop. Do not delegate.

Read `/Users/anicca/anicca-project/.worktrees/lm-spec-sync-core8d/.claude/sol-orders/order-panel-permanent-session.md` for the six product blockers, desired behavior, implementation constraints, and verification. This rescue overrides its RED instructions where necessary. Do not resolve this path relative to the feature worktree.

Method 1 was rejected before commit: it produced 15 failures, but most were source-string/regex assertions. False hypothesis: `source shape assertion is equivalent to production-path behavior RED`. Preserve the file as input, then rewrite/split it into executable behavior tests. Do not commit the rejected version.

## Hard RED quality gate

- A product behavior test must invoke the exported production function or drive the real HTTP handler/selector/provider path and assert returned state, recorded fetch/RPC calls, mutations, response status/headers/body, or emitted/unhandled errors.
- `fs.readFileSync(source)` + regex/string matching does **not** count for session lifecycle, runtime toggles, rebind, provider mutation/readback, personalization, command convergence, or stream safety. Static inspection is permitted only as a supplementary check for SQL DDL/RPC grants and rendered semantic HTML/CSS after calling the renderer.
- Missing new exports may fail a behavior test initially, but each blocker must also include at least one test that drives the existing public path and reproduces the wrong current outcome.
- Test fixtures may emulate Supabase/Composio as deterministic state machines, but may not pass already-enriched preference rows directly to hide production selectors.
- RED commit changes tests/evidence only. Production/auth/API/UI/scheduler/discovery/server/migration implementation diff must be zero.

## Required executed RED cases

1. Start a local HTTP server with real `handlePanelRequest`: a valid cookie at +25h currently fails but should render/rotate; missing cookie currently returns plaintext 401 but should return HTTP 200 login HTML; bootstrap still redirects query-free.
2. Exercise the real session resolver against a stateful fake RPC: concurrent rotation, dropped response/retry, old token/family revoke, current `uid+chat_id`, other-user isolation. Assert exact hashed RPC inputs and never raw secrets.
3. Drive real logout HTTP handling with POST/GET, Origin and CSRF variants; assert exact revoke calls, cookie clear, and no mutation on negatives.
4. Drive real `getUserByUid`, default scheduler/Inngest entry, and default discovery selector with fetch-backed user + preference responses. OFF must produce zero call/travel/ask/discovery/notification for that user; peer remains active. A preference fetch 500 must not become all-true.
5. Drive real panel page/API/OAuth handlers with a session whose stored chat binding differs from current `lm_users.telegram_chat_id`; assert zero token claim, provider call, read, and mutation.
6. Drive `composioCalendarStart` and `composioCalendarDisconnect` through stateful fake account responses. Mutate account A, return account B or fake ACTIVE-but-disabled, and assert failure plus exact rollback verification and honest result.
7. Call real timeline/settings/control-center/rendered UI for two scoped users with different timezone/language/wake policy/calendar provider truth. Assert different outputs. Click/dispatch visible language/timezone/wake-policy controls through the same command endpoint and assert scoped stored results.
8. Send >32 KiB through a real request/EventEmitter into `readJson`/command handler, then emit a late `error`. Capture `uncaughtException`/error listener behavior safely; assert one response, zero mutation, no retained body and no unhandled error.
9. Rebind between command validation and write using a stateful store/RPC barrier. Assert zero preference/user/provider mutation at the write boundary.

Run the new tests against exact base and report total/pass/fail plus a one-line mapping from every six blocker to at least one executed failing test. Existing focused/full/eval/smoke remain positive control. Commit/push RED tests separately only after this gate is met.

Then implement the smallest GREEN described in `order-panel-permanent-session.md`, run all required verification, commit/push implementation/evidence separately, and prove clean `HEAD==upstream==PR head`. No external side effect, deploy, merge, provider/OAuth call, send, or L3. End `RESULT=PRODUCT-LOCAL-GREEN` or `RESULT=BLOCKED` with the exact substantive blocker.
