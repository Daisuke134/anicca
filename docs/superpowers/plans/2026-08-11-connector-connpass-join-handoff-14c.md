# Connector Connpass join-form handoff Item 14C plan

## Goal

Prevent the initial Connpass application-link click from being mistaken for a completed registration when it lands on the event join form. Return a verified direct failure on that noncanonical page so the existing bounded Browser Harness can fill the form and press the one final confirmation control. Keep canonical parent readback and evidence recovery as the only completion proof.

## Live evidence

- Recovery wake `wake-74fc59b0adddc2abc8603791` repeated the same real event `400028` path. It recorded direct action success, post-action readback success, then the new canonical navigate and canonical readback success; terminal remained `circuit_open/evidence_completion_failed` with Connpass receipt/checkpoint/artifact/bundle zero.
- Browser Harness action count remained zero. The canonical recovery action itself did not throw, so the only runner path to the terminal is a canonical state that was not `registered|pending`.
- Therefore the earlier post-link state on the join page was a false positive. The final join-form control `申し込みを確定する` has not been executed by either live wake.
- Existing direct code clicks only the event-page application link, waits, and trusts the page-state text result. It does not require that the resulting URL is the candidate canonical URL before returning completed.

## Ponytail full gate

- Keep the existing direct click, script-first state reader, runner fallback, Browser Harness, canonical recovery, and evidence chain.
- Add no form implementation, selector list, account logic, state store, retry, browser target, or schedule.
- Direct action may return completed only when its result is `registered|pending` and the same owned page is still at the exact candidate canonical URL.
- A same-event join, confirmation, query, hash, other event, or opaque URL after the click is a known `direct_action_unverified`; the runner then invokes the existing bounded Harness on that same page.

## Luna implementation slice

Luna owns only:

1. `apps/mr-bot/lib/connector-connpass-workflow.test.js`
2. `apps/mr-bot/lib/connector-connpass-workflow.js`

Soft target: 2 files; production `+8–15 LOC`; tests `+25–45 LOC`.

### RED

Create a direct-action fixture whose page begins at the exact candidate URL, whose supplied submit method returns `registered`, and whose current URL becomes the same-event `/join/` page. The current workflow incorrectly returns completed. Require `failed/direct_action_unverified`.

### GREEN

- Read the owned page URL after the supplied direct action.
- Return completed only for an exact canonical URL and `registered|pending` result.
- Reject join/complete/query/hash/wrong-event/about:blank/missing-or-throwing URL as the existing safe direct failure. Do not navigate, click, or read credentials in this guard.
- Preserve canonical direct completion, parent pre-readback, discovery, and all non-Connpass behavior.

## Verify and live close

- Focused RED/GREEN plus workflow/provider/Harness/runner/production regression, syntax, and diff check.
- Fresh Sol review for exact URL identity, same-page handoff, no extra click, and failure reason safety.
- Update SSOT, commit, and push before another official wake.
- The next official wake may invoke Browser Harness once on the real join form. Acceptance requires final confirmation Submit at most one, canonical parent readback registered/pending, exact Connpass bundle and Calendar event one, positive Telegram message/photo/every-wake IDs, and cleanup. If Harness cannot prove the effect, stop safely without another final Submit.

## Result

- RED added the real join handoff plus an exact URL rejection matrix. Current code passed only the canonical fixture and incorrectly returned completed for join/noncanonical states.
- GREEN reads only `page.url()` after the supplied direct action and returns completed only for `registered|pending` at the exact candidate canonical URL. Join, completion, query, hash, wrong event, `about:blank`, missing URL, and throwing URL all return the existing safe direct failure without an extra browser action.
- Final scope is the two owned files. Sol independent workflow/provider/runner/production/operations/Harness regression passes 98/98; syntax and diff check pass. Fresh Sol review: `ship`.
