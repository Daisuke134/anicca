# Graphiti temporal projection audit — 2026-11-25

Upstream https://github.com/getzep/graphiti/tree/38eef1eb9f9e993effc9801d64cb73aaf9d3cbbd (Apache-2.0); temporal_edge_utils.py blob 6a8e161e7510fcd5349828ff773ff686c6f05f78; datetime_utils.py upstream blob 06f4057c3d6d0448db7b48046b7a1ac82dea15b6; edges.py blob 65fccc95b9b3f512ccbe1638b8ec77f785093c6d. No upstream code vendored. Existing November 4 Graphiti 0.31.2 type-only receipt reused, not a new install. Local Python 3.13.5, graphiti_core/neo4j/falkordb absent, git ls-remote DNS failure. No paid API, personal data, database, embedding or LLM calls.

## Executed targeted audit
Exact upstream temporal_edge_utils.py file copied to temporary local directory and Git blob SHA matched. Executed it with import seams (EntityEdge=object, copied ensure_utc function from upstream; whole datetime_utils file hash did not match, so do not claim whole-module equivalence). Only normalize_future_temporal_bounds was invoked. Reference time 2026-11-25T00:00Z, d=2026-11-26T00:00Z, yesterday=2026-11-24T00:00Z. Eight authored cases, not official test suite. Inputs and actual (valid_at,invalid_at):
| fact | input bounds | output bounds | intended semantics match |
| --- | --- | --- | --- |
| I will meditate tomorrow | d,None | ref,None | yes |
| I plan to meditate by tomorrow | d,d | ref,None | yes |
| The room will be unavailable until tomorrow | None,d | ref,d | yes |
| I meditated yesterday | yesterday,None | yesterday,None | yes |
| I intend to meditate | None,None | ref,None | yes |
| 明日は瞑想する予定です | d,None | d,None | no |
| 明日までに瞑想するつもりです | d,d | d,d | no |
| I will meditate tomorrow | d in +09:00,None | ref,None | yes |

6/8 authored semantic expectations matched; Japanese examples are outside the English regex. This is not a general multilingual accuracy rate or a Graphiti end-to-end failure claim. Explicit typed intent/outcome provenance avoids relying on this regex for Anicca's own events.

## Adapter
project() returns arguments for upstream EntityEdge; to_edge() imports upstream directly. No new graph engine. Opaque trusted owner/branch namespace derives group, source, target and edge IDs; deterministic replay, not encryption/authentication. Separates HAS_PLAN from REPORTED_COMPLETION, uses observation time for valid_at, retains intended date as metadata and never equates deadline to invalidation. No automatic extraction. Explicit completion type is supplied by caller and not independently verified. This does not validate true completion, time of ingestion, retention, graph authorization, invalidation or historical point-in-time retrieval. Current Manager journal stays canonical. Graph writes, provenance authenticity checks, consent/deletion, versioned transaction-time replay and actual group-isolated queries remain required. Do not send user data to a new provider. No production code modified.

Local python -m unittest -v test_graphiti_projection: 7 pass, 1 skipped (actual Graphiti type). Executed source Git blob 2872c6bb1e31ac71833bf29b51c791e3cb8dd6c8; test blob 822d5129881ca363aa3a3ea02887d51c6628a525. Next reuse earlier isolated Graphiti environment if available, run upstream package and isolation tests with synthetic two owners/two branches, late arrival and correction cases, no future leakage; compare with existing journal before considering graph adoption. Never treat model-generated simulation as observed person history. Integrate via existing Manager/ManagerBench decision IDs, not separate app or new storage until a measured gap. Concordia next.

## Article / abstract / slide / social draft (not published)
Temporal memory distinguishes a plan, its intended date, an observed action and the date at which evidence becomes available. In an eight-case component audit, the English-oriented Graphiti temporal helper matched six intended cases, including six English/offset cases, and missed two authored Japanese plan cases. A typed event projection passed seven local contract tests, with the upstream type test skipped. This is engineering evidence, not human benefit or Graphiti retrieval performance.

Talk outline: (1) changing person state (2) valid versus transaction time (3) English/Japanese cases (4) typed projection and scope separation (5) future isolation, deletion and heldout human evaluation. Social draft: Plans are not outcomes. We audited an open-source temporal normalization component and found two Japanese plan cases requiring explicit provenance. Code and limitations in the research PR. No claim of live app improvement.
