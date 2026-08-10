# CFO-2a2a.4 — Local Usage Attribution Plan

Status: COMPLETE

## Goal

Resolve only evidence-backed local `loop + task_label` identities to the existing CFO financial units, while keeping
every unknown identity visibly unattributed.

## Ponytail gate

- Add only `apps/life-call/lib/cfo-local-agent-usage-attribution.js` and its `.test.js`; edit only the existing
  `apps/life-call/package.json` `test:cfo` command to register the test.
- One pure resolver, one hard-coded versioned rule table, no config loader, DB, I/O, scanner change, reducer change,
  OTel, price logic, task-label enumeration, wildcard engine, or mapping service.
- Production target 42 LOC, tests 45 LOC, package +1/-1; total <=90 additions. Stop before 100 or a fourth file.

## Mapping v1

`resolveLocalAgentUsageAttribution(loop, taskLabel)` returns exact frozen
`{mapping_id, financial_unit_id, attribution_status}`. `mapping_id=local_agent_usage_v1` always. Closed rules:

- `gig_work`: `gig/gig-*`, `gig-loop/self-fix-gig-loop`, `gig-oauth-parity/gig-oauth-*`,
  `freelancer-work-sync/freelancer-*`, `bounty/bounty-*`;
- `job_income`: `job-search/job-search-*`;
- `capafy_marketplace`: `capafy/capafy-*`, `capafy-loop/self-fix-capafy-loop`,
  `capafy-verify/budget-guard-probe`;
- `life_manager_saas`: `life-manager/life-manager-*`, `life-manager-dev/life-manager-dev-*`,
  `life-manager-dev-promote/life-manager-promote-*`, `reddit/reddit-loop-*`,
  `reddit-loop/self-fix-reddit-loop`;
- `anicca_ios`: `larry-marketing/larry-*`, `honne-marketing/reelclaw-honne-*`.

Prefix matching is allowed only for rules shown with `*`; all other task labels are exact. Inputs must be primitive,
non-empty, already-trimmed strings. Invalid inputs throw only
`cfo_local_agent_attribution_invalid:invalid_loop|invalid_task_label` as applicable, without echoing input. Any valid
miss returns `financial_unit_id=null` and `attribution_status=unattributed`.

## Task 1 — RED/GREEN

Write one compact table-driven test proving all rules, fixed mapping ID, exact/frozen receipt, registry target
membership, both `connector/connector-*` and
`connector-outbound-loop/self-fix-connector-outbound-loop` remaining unattributed, and redacted invalid inputs. Record the
missing-module RED, then implement only the resolver and run focused, CFO, full, syntax, diff, and LOC gates.

Evidence: missing-module RED; focused 2/2, CFO 275/275, full suite, syntax, and diff checks PASS. The normal suites
both execute the two named tests. Implementation is exactly three files and +51/-1; the lockfile is unchanged. Fresh
Sol review returned `ship — Spec ✅`.

## Task 2 — Real evidence and close

Read each actual ledger into one Buffer snapshot, resolve each scanned pair, add only `financial_unit_id` to its
context, and feed it to the completed reducer. Print counts only and assert every snapshot row reconciles to exactly
one attributed or unattributed result. Planning observation was 4,946 total = 3,902 attributed + 1,044 unattributed:
Gig Work 3,328, Employment 230, Capafy 85, Life Manager 53, and Anicca iOS 206. The E2E records its own later fixed
snapshot rather than assuming those live counts cannot grow. Fresh Sol review then closes 2a2a.4 before 2a2a.5.

Evidence snapshot at close: 4,949 total = 3,904 attributed + 1,045 unattributed. Targets were Gig Work 3,330,
Employment 230, Capafy 85, Life Manager 53, and Anicca iOS 206. Scanner-to-attribution-to-reducer accepted every row;
stdout contained counts only.
