# Connector Connpass native known-form Item 14D plan

## Goal

Complete the measured Connpass join form without depending on an unavailable model provider. Reuse the Browser Harness observation, parent-owned value resolver, DOM operator, readback, and step bound. Select only a tiny allowlist of known safe public controls deterministically; unknown labels remain agent fallback and fail safely when no provider is available.

## Live and provider evidence

- Wake `wake-928666cc8425d896f6e85ac9` reached Connpass Browser Harness for the first time. The Harness failed before a DOM action because both local Codex attempts returned usage-limit errors. Final confirmation Submit remained zero.
- Codex resets on 2026-08-16; Claude direct returned monthly spend limit; local Claude proxy returned 403; DeepSeek returned insufficient credits; configured Gemini returned 401.
- OpenClaw with configured free Qwen succeeded, but prepended a wallet warning. The existing OpenClaw result contract deliberately rejects prefix prose and wallet warnings, so using it would require weakening a safety validator. That option is rejected.
- The measured Connpass form has one safe free online-viewing participation radio, one referral-source radio with Connpass as an option, two exact acknowledgement radios `はい、わかりました`, optional text fields, and one final `申し込みを確定する` control.

## Ponytail full gate

- Reuse `inspectPageControls`, `createBoundedActionProposer`, `createPrivateValueResolver`, `operatePageControl`, existing Browser Harness, duplicate guard, and parent readback.
- Add no provider adapter, model config, prompt persistence, form store, selector cache, page, target, session, retry, or schedule.
- Native selection applies only when `provider=connpass` and exactly one pending control matches the next allowlisted meaning: free online viewing (never speaker), exact Connpass referral, or exact affirmative acknowledgement. Optional inputs remain untouched.
- Final selection applies only when no required answer remains and exactly one submittable button has exact label `申し込みを確定する`.
- Unknown, ambiguous, duplicate, negative, speaker, paid, or differently worded controls never receive a native action and fall through to the existing agent path.
- Within one fallback, the first Connpass submit attempt becomes a one-shot effect boundary. A second submit action is rejected as `effect_unknown`, including after a URL change.

## Luna implementation slice

Luna owns only:

1. `apps/mr-bot/lib/connector-production-browser-harness.test.js`
2. `apps/mr-bot/lib/connector-production-browser-harness.js`

Soft target: 2 files; production `+30–55 LOC`; tests `+45–75 LOC`.

### RED

1. A measured Connpass observation sequence must complete in bounded steps with `runAgentRunner` set to throw: online-viewing radio → Connpass referral → first acknowledgement → second acknowledgement → exact final button.
2. Parent value resolution must return boolean `true` only for those exact safe radio options under `provider=connpass`; speaker, negative, other referral, ambiguous and unknown labels return null.
3. A second Connpass submit proposal in the same fallback, including after page-path change, must not call the DOM operator and must return `effect_unknown`.

### GREEN

- Add one pure native Connpass selector before the agent call. It receives only the already-sanitized controls and returns a control token only for a unique allowlisted match.
- Extend the existing parent resolver with the same exact Connpass safe-option predicate.
- Add one fallback-local Connpass submit-attempt latch around the existing operator. Do not change Peatix final-effect logic or generic duplicate signatures.

## Verify and live close

- Focused RED/GREEN plus Harness/adapter/runner/production/workflow/provider/evidence regression, syntax, and diff check.
- Fresh Sol review for allowlist exactness, ambiguity rejection, no private prompt/value persistence, one-shot submit, and non-Connpass regression.
- Update SSOT, commit, and push before another official wake.
- Next live acceptance: agent calls zero for the known Connpass form, only allowlisted radio actions, final confirmation at most one, canonical registered/pending readback, exact Connpass bundle and Calendar event one, positive Telegram message/photo/every-wake IDs, cleanup.

## Result

Luna followed RED→GREEN in the two owned files. The measured simultaneous form fixture completes in five native actions with the agent unavailable: exact free online option, exact Connpass referral, two exact acknowledgements, then the unique final button. The parent resolver supplies only boolean `true`; private profile readers remain untouched. A second Connpass submit in one fallback returns `effect_unknown` before another DOM action.

The first fresh review found two Important fail-open cases: the online allowlist included labels that did not prove free admission, and empty or unknown question context could reach native selection and resolution. Fix round 1 reduced labels and questions to the measured exact literals and added selector plus resolver regressions. Sol's fresh relevant run passed 127/127 with syntax and diff checks. Scoped re-review verdict: both findings addressed, new Critical 0, new Important 0, `ship`. Code commits: `29ca6141b`, `e047723b5`.

The live acceptance remains separate. Read-only preflight keeps all four Connector-related labels unloaded, Git clean/upstream `0/0`, no Connector process or lock, and the existing `:9222` browser healthy. A probe against the stale `tokyo-builders` hostname for event `400028` exposed no radio form, so the official wake must truthfully rediscover the current canonical Connpass host rather than treating the old fixture or hostname as live evidence.
