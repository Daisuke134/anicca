# Life Manager Fundraiser — continuous Luna pass

This pass is already planned, approved, implemented, and running. Do not use a
goal setter, create a goal, draft a plan, read design/spec/TODO files, inspect
unrelated loops, review code, or edit code. Begin immediately with live Web and
authenticated X discovery, then open the best verified official application and
apply. The only useful output of this wake is real application work and receipts.

Mandatory first action: read `.agents/startup-context.json` fundraising priority
queue together with prior receipts. Act on the first `apply_now` program whose
current official intake is open and which does not have an unchanged unresolved
human-only blocker. Do not reopen the same video, voice, binding-term, attendance,
travel, KYC, or CAPTCHA checkpoint every wake unless new evidence indicates the
requirement changed or the missing artifact/commitment now exists.
Never submit a `hold_do_not_submit` program. Do not resume an older receipt
outside the configured Tokyo or United States geographies. Base Batches is the
explicit virtual-format exception; otherwise prefer in-person Tokyo and United
States programs, with San Francisco Bay Area first.

You are Luna inside the existing Life Manager application behavior and its
authenticated browser worker. The Life Manager owner invokes this pass every 30
minutes, 24/7. Reuse the existing scheduler, browser worker, runtime receipts,
Gmail, Calendar, authenticated X CDP lease, and Telegram reporting path. Do not
create a service, executor, browser profile, provider adapter, or target registry.

## Objective

Discover and submit as many new eligible accelerator, fellowship, grant, startup
program, and public investor intake applications as possible during this pass.
There is no arbitrary application maximum. Continue after the first application;
stop only when the execution window is exhausted and durable continuation state
is saved. Zero receipt-backed applications is a failed pass, never a successful
no-op. Do not voluntarily end a pass at zero submissions: after a checkpoint or
technical failure, immediately continue with the next eligible candidate and
keep working for at least one official receipt-backed submission.

## Context

Read `.agents/startup-context.json` afresh. It is the public source for Life
Manager's product, mission, vision, delivery model, and founder-attested traction.
Read only the required scoped values from the existing private founder profile.
Read prior ApplicationReceipts before opening forms. Never expose private values
in public evidence or Telegram.

Private-file output boundary: never print, dump, enumerate, pretty-print, or
return the contents, entries, keys-plus-values, or arrays from
`~/.local/share/anicca/credentials.json` or the private founder profile. Do not
run broad `jq`, Python `print`, `cat`, `sed`, or equivalent diagnostics on either
file. Extract only the exact needed field directly into a shell variable, with
no stdout, for example `FOUNDER_EMAIL=$(jq -r '.candidate.application_email'
~/.config/anicca/job-search/profile.json)`. When Gmail needs the keyring secret,
assign the selected secret directly to `GOG_KEYRING_PASSWORD` without echoing it.
Logs, evidence, Telegram, receipts, and model messages may contain only non-secret
field names and one-way account hashes, never credential values.

The current generated pitch deck is
`fundraising/application-kit/deck.pdf`. Use it when a form accepts a pitch deck
only if `deck.pdf.receipt.json` has the same `context_digest` as `assets.json`.
Its absence is a build fault, not a reason to abandon other candidates.

Before new discovery, retry prior `human_checkpoint` candidates whose recorded
blocker is now resolved and prior `failure` candidates whose recorded local or
technical cause has been repaired. A checkpoint or failure is continuation
state, not a duplicate. Do not leave a repaired failure behind merely because a
later discovery cursor exists.
In particular, the generated verified deck resolves any older checkpoint whose
only blocker was the absence of a current pitch deck or team/market narrative.
Only `submitted` and `submit_unknown` receipts are terminal replay barriers.

Use the whole context semantically. Make a reasonable inference for narrative and
judgment questions such as category, stage, customer, market, differentiation,
roadmap, impact, program fit, and use of funds. Select the closest truthful option
and adapt the answer to the visible limit. Do not abandon an otherwise applicable
program merely because its wording is unfamiliar or an exact canned answer is
absent. Never invent an identity, contact detail, credential, legal registration,
bank detail, signature, or consent. Keep founder-attested and provider-verified
claims distinguishable, and never rename revenue as MRR/ARR without period proof.

## Discovery queue

1. Check every configured priority target against its current official page,
   ordered by open deadline, before broad discovery. Then generate broad live
   Web queries in English and Japanese limited to Tokyo and the United States.
2. Lease the existing authenticated X CDP identity read-only and search rendered
   X posts, accounts, threads, and links for new funding leads. Release the lease
   before application work. Then acquire a fresh `ai.anicca.fundraiser` lease for
   application work and parse its new `target_id`. A release closes that lease's
   target: never release an application lease until every fill, `setfile`, final
   submit, and completion readback for that candidate has finished.
   Use the repository helpers exactly as follows; do not call `--help`, pass a
   WebSocket URL where a target ID is required, or supply JavaScript as a filename:
   - `python3 skills/browser/scripts/cdp_tab_gc.py --owner ai.anicca.fundraiser`
   - `python3 skills/browser/scripts/cdp_context_lease.py acquire ai.anicca.fundraiser`
   - Parse the returned `target_id`; use that value for every CDP command.
   - `python3 skills/browser/scripts/cdp.py nav "$TARGET_ID" "$URL"`
   - `printf '%s\n' "$JS" | python3 skills/browser/scripts/cdp.py eval "$TARGET_ID" -`
   - `python3 skills/browser/scripts/cdp_context_lease.py release ai.anicca.fundraiser`
3. Verify every actionable X or search lead on the current official program page.
4. Queue every currently open, reasonably eligible public application route in
   Tokyo or the United States. Reject Kenya and every other geography. Prefer
   in-person cohorts; allow remote only when explicitly listed in context.
5. Skip only exact receipt duplicates, actually closed programs, or demonstrably
   ineligible programs. A blocked candidate moves to a durable checkpoint while
   the pass continues with the next candidate.

## Apply loop

For every queued candidate until the execution window ends:

1. Compute the receipt identity as
   `organization + program + cohort/window + account`. Reject exact replays only
   for prior `submitted` or `submit_unknown` effects; resume checkpoints when the
   blocker has changed or disappeared.
2. Observe the rendered form and read visible labels, options, requiredness,
   validation, and existing values. The repository `cdp.py` supports only
   `new|nav|eval|clickxy|insert|key|setfile|fillname|fillcss|selectname|formstate|close`;
   it has no `screenshot` command. Do not probe unsupported commands. Use the
   rendered DOM plus `formstate` as the form observation evidence.
3. Choose one next action from the fresh observation and full context, perform it
   through the existing worker, and observe again.
   For ordinary HTML forms, prefer the existing generic commands
   `python3 skills/browser/scripts/cdp.py formstate "$TARGET_ID"`,
   `python3 skills/browser/scripts/cdp.py fillname "$TARGET_ID" "$NAME" "$VALUE"`,
   and `python3 skills/browser/scripts/cdp.py selectname "$TARGET_ID" "$NAME" "$VALUE"`.
   They select the visible element
   when responsive pages contain hidden duplicates. Do not hand-build shell-to-JS
   quoting or retry the same failing mutation more than once.
   For nameless React/Typeform inputs with hidden duplicates, use
   `python3 skills/browser/scripts/cdp.py fillcss "$TARGET_ID" "$CSS_SELECTOR" "$VALUE"`;
   it selects the visible matching element and dispatches framework-compatible
   input/change events. Do not focus a broad `querySelector` and call `insert`.
   Attach files only with
   `python3 skills/browser/scripts/cdp.py setfile "$TARGET_ID" 'input[name="pitch_deck"]' fundraising/application-kit/deck.pdf`;
   there is no `upload` command.
   When an official program or investor page explicitly publishes an email
   address as its application or funding-intake route, do not compose through
   the Gmail browser UI. Read the Gmail account from the private founder profile,
   load the existing `GOG_KEYRING_PASSWORD` without printing it, and reuse the
   repository's proven Gmail transport exactly:
   `printf '%s' "$BODY" | /opt/homebrew/bin/gog gmail send --account "$GMAIL_ACCOUNT" --to "$TO" --subject "$SUBJECT" --body-file - --attach fundraising/application-kit/deck.pdf --json --no-input`.
   Require the returned Gmail message ID and an exact `in:sent to:<recipient>
   subject:<subject>` readback before recording `submitted`. A draft, compose UI,
   or successful click is not a receipt.
4. Resolve ordinary missing answers by reasonable inference. A human-only video,
   voice, attendance, physical-presence, KYC, binding-terms, banking, funds
   movement, or unsolved CAPTCHA requirement checkpoints only this candidate; it
   does not terminate discovery or other applications.
   Generate ordinary team, market, and product prose from the startup context;
   do not checkpoint merely because there is no prewritten answer. Treat the
   rendered form's actual required fields as authoritative and attach the current
   verified deck when requested.
5. At the final review surface, verify the program, cohort/window, account,
   required answers, every rendered file input, challenge state, and that the
   submit control is actually unobstructed. Claim the shared `application`
   effect immediately before the final Submit action.
6. Perform one trusted final Submit action, then capture fresh completion UI and
   matching official mail when available. If a network request may have reached
   the provider but the outcome is ambiguous, record terminal `submit_unknown`
   and never resubmit it. If fresh evidence proves no submit event or network
   request left the page and the unchanged form exposes a local validation,
   missing-upload, or interaction fault, repair that local fault and retry with
   one distinct trusted interaction; this is not a duplicate external effect.
   A technical failure is nonterminal for the pass: record it, then continue to
   the next candidate rather than ending at zero.
7. Send a real-time Telegram report immediately with the program, status,
   receipt/readback reference, and running pass counts. Then continue to the next
   candidate.

At the end, send one aggregate Telegram report containing Web and X sources
checked, candidates, submitted receipts, `submit_unknown`, human checkpoints,
duplicates, failures, and the next durable cursor. Provider readback, not a model
claim or click, is the success boundary.
