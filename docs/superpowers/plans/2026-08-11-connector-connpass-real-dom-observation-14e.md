# Connector Connpass real-DOM observation Item 14E plan

## Goal

Normalize the actual Connpass join-page DOM into the existing sanitized Browser Harness contract so the parent can select the safe viewing ticket and referral answer without an agent. Keep unknown forms fail-closed.

## Root cause evidence

- Official wake `wake-382acd76ce42e6a911178743` rediscovered the sole Calendar-free Connpass candidate `connpass-event://event/400028` at `https://osaka-driven-dev.connpass.com/event/400028/`.
- Direct action reached the join page, but Browser Harness failed in step 1 before a DOM action. The saved agent attempt shows only the known Codex usage-limit error.
- A read-only production-inspector probe on the exact join page showed the fixture mismatch:
  - the safe ticket is `input[name=participation_type]` with public label beginning `オンライン視聴枠（YouTube） 無料`; Connpass omits HTML `required`;
  - the unsafe sibling is the speaker ticket `オンライン登壇枠（Zoom） 無料`;
  - custom questions live under `.question_list > .question`; the referral question is `必須 このイベントは何を見て知りましたか？` and the exact option is `Connpass`;
  - the two `はい、わかりました。` controls are optional speaker-only questions and must remain untouched;
  - the unique final button is still `申し込みを確定する`.

## Ponytail full gate

- Reuse `inspectPageControls`, the native selector, parent resolver, operator, submit latch, and readback.
- Change only the existing Harness production/test files. Add no adapter, browser/page/session, model, cache, retry, or schedule.
- On an exact Connpass join URL only, normalize `input[type=radio][name=participation_type]` as one required public `参加枠` group even though the site omits the HTML attribute.
- On the same page, derive custom-radio question text only from its nearest `.question_list > .question`, stripping exactly one leading `必須` or `任意` marker. Do not use full ancestor text containing answers.
- The native safe ticket predicate accepts only a label anchored by exact prefix `オンライン視聴枠（YouTube） 無料`; it must reject the speaker ticket, paid/unknown labels, empty context, duplicates, and non-Connpass pages.
- The referral predicate accepts only exact `Connpass` under exact normalized question `このイベントは何を見て知りましたか？`.
- Remove native acknowledgement selection. Optional speaker-only fields remain untouched; required unknown acknowledgements fall through to the existing agent.

## Luna implementation slice

Ownership:

1. `apps/mr-bot/lib/connector-production-browser-harness.js`
2. `apps/mr-bot/lib/connector-production-browser-harness.test.js`

Soft target: 2 files; production net `-10–+30 LOC`; tests `+35–70 LOC`.

### RED

1. An actual Connpass DOM-shaped inspector fixture must expose viewing and speaker tickets with question `参加枠`, `required=true`, while preserving exact labels and rejecting the speaker from native selection.
2. The same fixture must expose referral question `このイベントは何を見て知りましたか？`, select exact `Connpass`, skip both optional speaker acknowledgements, then expose the unique final button.
3. Non-Connpass pages, wrong URL, wrong radio name, missing/duplicate viewing option, label without explicit `無料`, paid/speaker option, empty/unknown question, and unknown required acknowledgement remain agent fallback or safe failure.

### GREEN

- Add the smallest Connpass-only branches inside the existing browser-context inspector.
- Replace the stale fixture-only allowlists with the measured safe ticket prefix and exact referral question.
- Delete acknowledgement-native code made unnecessary by the actual DOM.

## Verification and live close

- Focused RED/GREEN plus Harness/adapter/runner/production/workflow/provider/evidence regressions, syntax, diff check.
- Fresh Sol review for DOM scope, exact URL/name/question/label constraints, speaker/optional rejection, no private data, and non-Connpass regression.
- SSOT update, commit, and push before one more official wake.
- Live acceptance remains Item 14: same run Luma effect 0 → Connpass, agent call 0 for the known form, safe viewing ticket + referral only, final confirmation at most one, canonical registered/pending readback, exact bundle/Calendar/Telegram lineage, cleanup.

## Fresh review amendment

The first fresh review found that the exact join-page provenance stopped at the browser inspector. A non-join Connpass page could therefore expose a generic `参加枠` legend and reach the native selector, and an exact join page could still borrow generic `.question` text from outside `.question_list`.

- Reuse the existing observation state; set it to `connpass_join` only when the provider and current URL satisfy the same exact join predicate.
- Require that state in both the native selector and the private resolver. The proposer and action operator pass the state through; no new durable field or cache schema is added.
- Pass the same exact-join boolean into the browser-context inspector. On an exact join page, a custom question group has no generic ancestor fallback: only its nearest `.question_list` and direct `.question` child are valid. The special `participation_type` normalization remains unchanged.
- Add RED regressions proving that a safe-looking control on a non-join Connpass page calls the agent once and resolves no private value, and that `.question` outside `.question_list` is not adopted on an exact join page.
- Correct the implementation report from the earlier `80/24` transcription to the measured `94/24` test diff before this fix round.

The scoped re-review confirmed those provenance fixes, then found that the shared URL regex made the path case-insensitive. Keep the browser-normalized lowercase host contract and make the entire literal path case-sensitive; `/EVENT/<id>/JOIN/` and either uppercase path segment must remain non-join. Add that focused negative before the next re-review.

## Result

- Initial actual-DOM RED was 45/48; initial GREEN normalized the measured participation/referral controls and removed obsolete acknowledgement-native handling.
- The first fresh review found join provenance and generic-group scope leaks. Fix round 1 added two RED failures at 49/51, passed `connpass_join` through observation/proposer/resolver/action, rechecked the current URL before resolving, and removed exact-join generic group fallback. Sol independently passed all seven relevant suites at 85/85.
- A read-only probe of the actual current join page observed 16 public controls, selected the safe viewing ticket with resolver `true`, agent calls 0, and browser writes 0; the temporary diagnostic tab was closed.
- The scoped re-review found the whole-regex `/i` path issue. Fix round 2 reproduced it at 50/51, removed `/i`, added uppercase-path negatives, and returned to 85/85. Final scoped review: `ship`, Critical 0, Important 0.
- Production/test commits are `5a757e6c3`, `1c4084ad2`, and `0d1839f7f`; plan constraint commits are `21b5b9d2d` and `13e58195d`. The schedule remains unloaded. Item 14 still requires one official live wake and an actual Connpass applied bundle.
