# Life Manager Horse Racing Agent Free-Web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mac-native zero-cost public-web ingestionからJRA公式primary recordとNAR二次recordをsource authority付きで観測し、redacted evidence、observed schema、SHADOW、CFO separationをReality Gate順に実装する。

**Architecture:** crwlはrobots/termsとcourteous rate limitを守って公開ページだけを取得する。raw snapshotはMac-local private append-only boundaryに留め、Git・Telegram・cloud・CFOへ出すのはredacted manifestだけにする。JRA officialとNAR secondaryは独立gateで、NAR secondaryはschema/audit/SHADOWだけをunlockし、LIVE_CASHには進めない。

**Tech Stack:** Python 3.12、pytest、標準ライブラリ中心のpure deterministic contracts、crwl、Mac-local filesystem、redacted YAML/Markdown evidence。新しいpaid SDK、SaaS、public API、browser automationは追加しない。

## Global Constraints

- 個人利用のみ。zero-cost public-web ingestionのみを許可し、raw page/rowのredistribution、public publication、SaaS化をしない。
- JRA primaryはofficial public pages。JRA robots snapshotはUser-agent:*とempty Disallow、利用範囲はprivate use/citation境界を記録する。
- NAR official keiba.go.jpのTodayRaceInfo/DataRoom/DataDownloadはCrawl-delay: 10とDisallowのためcrawlしない。推測DataRoom/DataDownload URLの404からZIP/CSV/APIを主張しない。
- NAR initial sourceはnar.netkeiba.com、classificationはPUBLIC_WEB_SECONDARY、termsはunverified、SHADOW-only。JRA fallbackに使う場合もsecondary labelを保持する。
- evidence classesはSYNTHETIC_TEST、REAL_PUBLIC_WEB_RECORD、PUBLIC_WEB_SECONDARY、LIVE_SHADOW、LIVE_CASH。HTTP/DOM successだけはrecordとしない。
- manifest必須欄はevidence_class、source_url、source_authority official|secondary、jurisdiction、retrieved_at、page_or_effective_timestamp、fetch_exit_code、http_status、parsed_row_count>=1、observed schema field names/types、content_sha256、robots_snapshot_url/status、terms_url/status、raw_values_exported=false。
- raw snapshotはMac-local private append-only storageだけに保持し、raw values、実馬名、credential、secret、subscription id、receiptを外へ出さない。
- PurchaseExecutorは常時disabled。HRA-6のterms/order/tax/credential/receipt/reconciliation gate以前に注文・決済・bet・wallet/bank mutationを作らない。
- $10K/monthはevidence-driven target only。ROI、勝率、収益、forecast、guaranteeを作らず、settled receiptとlater-window evidenceがない値をrevenueへ加算しない。
- Solはplan、gate、verificationを所有し、Lunaはこのplanに記載されたedit、code、command、evidence作成を実行する。
- 未完項目は先頭の一件だけをactiveにする。各sliceは最大3 files、estimated LOC 100以下、RED→GREEN→実E2E/state更新→commit→origin/canonical pushで閉じてから次へ進む。

## Current truth and evidence

| Evidence | 実測値 |
|---|---:|
| real JRA public-web records | 0 |
| real NAR public-web records | 0 |
| real historical backtests | 0 |
| live SHADOW runs | 0 |
| live Telegram runs | 0 |
| live orders/payments | 0 |

未取得、terms未検証、manifest欠落、parsed row 0はBLOCKEDと表示する。SYNTHETIC_TESTはmechanicsだけで、public-web record、historical backtest、SHADOW、Telegram、CFO revenueのcompletion evidenceではない。

## Architecture flow

~~~mermaid
flowchart TD
  A[HRA-0/1 safety complete] --> B[HRA-2F TDD free-web ingest boundary]
  B -- RED/BLOCKED --> X[DATA BLOCKED]
  B -- GREEN --> G{HRA-2R per-source record gate}
  G -- JRA official PASS --> J[HRA-2S observed schema/store]
  G -- NAR secondary PASS --> N[HRA-2S secondary schema/store]
  G -- missing row/manifest --> X
  J --> D[HRA-3D audit]
  N --> D
  D --> M[HRA-3Ma/3Mb model and backtest]
  M --> S[HRA-4 SHADOW/SKIP]
  S --> T[HRA-4b Telegram evidence split]
  T --> C[HRA-5 CFO receipt adapter]
  C --> R[HRA-6 research gate]
  R --> Q[HRA-7 document-only micro-live gate]
  Q --> Z[HRA-8 evidence-driven scale review]
  N -. never unlocks LIVE_CASH alone .-> R
~~~

## Ordered execution status

| Order | Stage | State | Scope |
|---:|---|---|---|
| 0 | Completed safety and design | complete | historical commits and approved free-web design |
| 1 | HRA-2F ingest boundary refactor | **ACTIVE** | exactly ingest.py and test_ingest_boundary.py |
| 2 | HRA-2R1 JRA public-web record | blocked by HRA-2F GREEN | one evidence file |
| 3 | HRA-2R2 NAR secondary public-web record | blocked by HRA-2F GREEN | one evidence file |
| 4 | HRA-2R3 per-source index/gate | blocked by records | one evidence file |
| 5 | HRA-2S observed schema/store | blocked by HRA-2R3 | quarantine three files only |
| 6 | HRA-3D audit | blocked by HRA-2S | data_audit.py and test_data_audit.py |
| 7 | HRA-3Ma/3Mb model and backtest | blocked by HRA-3D | exact legacy filenames retained |
| 8 | HRA-4 SHADOW decision/outcome ledger | blocked by HRA-3Mb | decision.py, ledger.py, test_shadow_ledger.py |
| 9 | HRA-4b Japanese Telegram | blocked by HRA-4 | telegram.py and test_telegram.py |
| 10 | HRA-5 CFO adapter | blocked by HRA-4b and CFO-0c | cfo.py and test_cfo.py |
| 11 | HRA-6 terms/order/tax/receipt gate | blocked research gate | document only, PurchaseExecutor disabled |
| 12 | HRA-7 ¥100 micro-live gate | blocked future gate | document only, no bet execution |
| 13 | HRA-8 scale review | blocked future gate | evidence-driven target only |

## Task 0: Completed safety and design baseline

**State:** complete. Sol verifies these commits before activating Task 1.

Historical rejection only: 0fe627cd proves the superseded Windows/JRA-VAN/Data Lab/JV-Link/UmaConn/NV-Link/JRDB/paid-source boundary; it is not compatible with this free-web plan and has no active dependency.

- d743b153: registry v2 candidate and CFO-0c exact-seven dependency.
- 89d48910: PurchaseExecutor disabled and side-effect-free.
- 0fe627cd: superseded boundary record described above; never treat it as HRA-2F or HRA-2R evidence.
- 9b9b78346: design switched to free public-web sources, evidence classes, Mac-local raw boundary.
- 509955401: HRA-2F made active because the old boundary implementation is not compatible.

Verification:

~~~sh
git show --no-patch --format=%H d743b153
git show --no-patch --format=%H 89d48910
git show --no-patch --format=%H 0fe627cd
git show --no-patch --format=%H 9b9b78346
git show --no-patch --format=%H 509955401
~~~

Expected: all five commits resolve, Task 1 is the sole active item, and evidence table values remain zero.

## Task 1: HRA-2F TDD refactor of the free-web ingest boundary (ACTIVE)

**Files:**
- Modify: apps/horse-racing-agent/src/horse_racing_agent/ingest.py
- Modify: apps/horse-racing-agent/tests/test_ingest_boundary.py

**Plan size:** 2 files, estimated 90 LOC total. No other code, fixture, evidence, or quarantine file may change in this task.

**Interface:** Replace the legacy boundary with this exact signature and return contract.

~~~python
def ingest_raw_boundary(
    source_url: str,
    source_authority: str,
    jurisdiction: str,
    host_os: str,
    storage_scope: str,
    raw_payload: str | bytes,
    export_destination: str,
    robots_snapshot_url: str,
    robots_status: str,
    terms_url: str,
    terms_status: str,
) -> dict[str, str | int | bool]:
    ...
~~~

Accepted source combinations are exact host equality: www.jra.go.jp + official + JRA, race.netkeiba.com + secondary + JRA, and nar.netkeiba.com + secondary + NAR. Require host_os=macos, storage_scope=mac_local_private, export_destination=local_raw_snapshot, and raw_payload as str or bytes. Reject https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/, https://www.keiba.go.jp/KeibaWeb/DataRoom/, https://www.keiba.go.jp/KeibaWeb/DataDownload/, and every hostname substring spoof such as evil-jra.go.jp or race.netkeiba.com.evil.example.

Return only redacted metadata: source_url, source_authority, jurisdiction, host_os=macos, storage_scope=mac_local_private, export_destination=local_raw_snapshot, sha256, payload_size, robots_snapshot_url, robots_status, terms_url, terms_status, raw_payload_exported=false, and allowed_scope=private_shadow for official JRA or shadow_only for secondary. Never include raw_payload or decoded raw values.

- [ ] Step 1: Write the failing test.

~~~python
def test_free_web_authority_matrix_and_redacted_return():
    metadata = ingest_raw_boundary(
        "https://www.jra.go.jp/",
        "official",
        "JRA",
        "macos",
        "mac_local_private",
        "synthetic mechanics payload",
        "local_raw_snapshot",
        "https://www.jra.go.jp/robots.txt",
        "User-agent:*; Disallow:",
        "https://www.jra.go.jp/use/",
        "observed",
    )
    assert metadata["allowed_scope"] == "private_shadow"
    assert metadata["raw_payload_exported"] is False
    assert "raw_payload" not in metadata

def test_rejects_keiba_dynamic_and_hostname_spoof():
    with pytest.raises(ValueError, match="source URL"):
        ingest_raw_boundary(
            "https://www.keiba.go.jp/KeibaWeb/DataRoom/DataDownload",
            "official", "NAR", "macos", "mac_local_private",
            "synthetic", "local_raw_snapshot", "https://www.keiba.go.jp/robots.txt",
            "Crawl-delay: 10; Disallow", "https://www.keiba.go.jp/terms.html",
            "blocked",
        )
    with pytest.raises(ValueError, match="source URL"):
        ingest_raw_boundary(
            "https://evil-jra.go.jp/race",
            "official", "JRA", "macos", "mac_local_private",
            "synthetic", "local_raw_snapshot", "https://www.jra.go.jp/robots.txt",
            "observed", "https://www.jra.go.jp/use/", "observed",
        )
~~~

Add one parameterized case for each accepted combination and one secondary return assertion for allowed_scope=shadow_only. Every payload in these tests is synthetic mechanics input and must not be labeled real data.

- [ ] Step 2: Run RED and record the expected failure.

~~~sh
cd /Users/anicca/anicca-project/.worktrees/horse-racing-agent-spec/apps/horse-racing-agent
rtk python3.12 -m pytest tests/test_ingest_boundary.py -q
~~~

Expected: FAIL because the legacy boundary rejects the approved public-web authority matrix or exposes the old local contract; no network, credential, or source fetch is allowed.

- [ ] Step 3: Implement the minimal boundary.

Parse source_url with urllib.parse.urlsplit and compare hostname by exact equality. Reject non-https URLs, host_os/storage_scope/export_destination mismatches, non-str/bytes payloads, disallowed keiba.go.jp paths, and source authority/jurisdiction mismatches. Convert str to UTF-8 bytes, compute hashlib.sha256, report byte payload_size, and construct the fixed redacted dictionary. Do not write, return, log, or serialize raw_payload.

- [ ] Step 4: Run GREEN and the package suite.

~~~sh
cd /Users/anicca/anicca-project/.worktrees/horse-racing-agent-spec/apps/horse-racing-agent
rtk python3.12 -m pytest tests/test_ingest_boundary.py -q
rtk python3.12 -m pytest -q
~~~

Expected: boundary matrix, spoof rejection, keiba dynamic rejection, byte-size/hash, raw_payload absence, and full package suite PASS.

- [ ] Step 5: Verify E2E/state and close the slice.

~~~sh
cd /Users/anicca/anicca-project/.worktrees/horse-racing-agent-spec
git diff --check -- apps/horse-racing-agent/src/horse_racing_agent/ingest.py apps/horse-racing-agent/tests/test_ingest_boundary.py
git status --short
git add apps/horse-racing-agent/src/horse_racing_agent/ingest.py apps/horse-racing-agent/tests/test_ingest_boundary.py
git commit -m "feat(horse-racing): refactor free-web ingest boundary"
git push origin HEAD
git push canonical HEAD
~~~

Expected: only the two owned files are staged; quarantine remains untracked; Task 1 is GREEN before Task 2 becomes active.

## Task 2: HRA-2R1 JRA actual public-web record

**State:** blocked until Task 1 GREEN. **File:** docs/evidence/horse-racing/jra-public-web-probe.md only. No code file or source promotion is allowed.

- [ ] Step 1: Discover a current race-card or result link from official JRA navigation.

~~~sh
crwl https://www.jra.go.jp/ -o /tmp/jra-official-navigation.md
~~~

Set JRA_PAGE_URL to the exact race-card/result href printed by that official navigation output. Do not choose a search result, secondary page, or guessed endpoint.

- [ ] Step 2: Fetch once with robots/terms and rate-limit evidence.

~~~sh
crwl "$JRA_PAGE_URL" -o /tmp/jra-public-page.md
printf '%s\n' "$?" > /tmp/jra-crwl-exit.txt
~~~

Record the exact URL, crwl exit code, HTTP status observed by the fetch, retrieved_at, page_or_effective_timestamp or unavailable, robots snapshot URL/status, JRA use-policy URL/status, and courteous delay. Store any raw snapshot only under /Users/anicca/Library/Application Support/Anicca/horse-racing/raw and keep that path outside Git.

- [ ] Step 3: Parse and write the redacted evidence.

Write jra-public-web-probe.md with evidence_class=REAL_PUBLIC_WEB_RECORD, source_authority=official, jurisdiction=JRA, parsed_row_count>=1, observed schema field names/types, content_sha256, raw_values_exported=false. HTTP 200, DOM success, a link, or an empty parse is not a record; row_count 0 is BLOCKED. Do not copy raw values, runner names, secrets, or secondary links.

- [ ] Step 4: Sol verifies and closes the evidence slice.

~~~sh
git diff --check -- docs/evidence/horse-racing/jra-public-web-probe.md
git add docs/evidence/horse-racing/jra-public-web-probe.md
git commit -m "docs(horse-racing): record JRA public-web probe"
git push origin HEAD
git push canonical HEAD
~~~

Expected: Sol can reproduce the URL, timestamp, fetch exit/HTTP status, parsed row count, schema names/types, hash, robots/terms status, and raw non-export. A secondary page never upgrades to official JRA evidence.

## Task 3: HRA-2R2 NAR secondary actual public-web record

**State:** blocked until Task 1 GREEN. **File:** docs/evidence/horse-racing/nar-secondary-web-probe.md only.

- [ ] Step 1: Discover a current public race-card/result page on nar.netkeiba.com.

~~~sh
crwl https://nar.netkeiba.com/ -o /tmp/nar-secondary-navigation.md
~~~

Set NAR_PAGE_URL to the exact public race-card/result href printed by that command. Keep source_authority=secondary and jurisdiction=NAR regardless of page labels.

- [ ] Step 2: Fetch with courteous delay and preserve terms uncertainty.

~~~sh
crwl "$NAR_PAGE_URL" -o /tmp/nar-secondary-page.md
printf '%s\n' "$?" > /tmp/nar-secondary-crwl-exit.txt
~~~

Never request keiba.go.jp TodayRaceInfo, DataRoom, or DataDownload paths. Record robots snapshot/status, terms_url/status=unverified, exact URL, retrieved_at, page_or_effective_timestamp or unavailable, fetch exit, HTTP status, and rate-limit observation.

- [ ] Step 3: Write the secondary redacted evidence.

Write evidence_class=PUBLIC_WEB_SECONDARY, source_authority=secondary, jurisdiction=NAR, parsed_row_count>=1, observed schema names/types, content_sha256, raw_values_exported=false. Keep the lane SHADOW-only. Terms uncertainty, HTTP/DOM success, link existence, or row_count 0 is not LIVE_CASH evidence.

- [ ] Step 4: Sol verifies and closes.

~~~sh
git diff --check -- docs/evidence/horse-racing/nar-secondary-web-probe.md
git add docs/evidence/horse-racing/nar-secondary-web-probe.md
git commit -m "docs(horse-racing): record NAR secondary web probe"
git push origin HEAD
git push canonical HEAD
~~~

Expected: NAR evidence remains secondary and SHADOW-only; no official NAR ZIP/CSV/API claim appears.

## Task 4: HRA-2R3 per-source Reality Gate index

**State:** blocked until Tasks 2 and 3 each have a manifest. **File:** docs/evidence/horse-racing/reality-gate-index.md only.

Define two independent rows: JRA official and NAR secondary. Each row links its own evidence file, source URL, authority, jurisdiction, retrieved/effective time, fetch exit/HTTP status, parsed row count, schema names/types, hash, robots/terms status, and raw_values_exported=false. JRA PASS never changes NAR; NAR PASS never unlocks LIVE_CASH.

- [ ] Step 1: Write the index from the two manifests.
- [ ] Step 2: Verify the index has exactly one state per source and no cross-source promotion.
- [ ] Step 3: Close with Sol gate and repository state.

~~~sh
git diff --check -- docs/evidence/horse-racing/reality-gate-index.md
git add docs/evidence/horse-racing/reality-gate-index.md
git commit -m "docs(horse-racing): index public-web reality gates"
git push origin HEAD
git push canonical HEAD
~~~

Expected: both records are still zero until their evidence files contain parsed_row_count>=1; missing terms/robots/hash leaves that source BLOCKED.

## Task 5: HRA-2S observed schema and append-only store

**State:** blocked until Task 4 PASS for the source being stored. **Files:** apps/horse-racing-agent/src/horse_racing_agent/store.py, apps/horse-racing-agent/tests/fixtures/normalized_races.json, apps/horse-racing-agent/tests/test_store.py. These three quarantine files remain untouched until manifests exist.

**Interface:** Provide AppendOnlyRaceStore(records_path: str), append(record: Mapping[str, object]) -> str, and records() -> tuple[Mapping[str, object], ...]. Accept only fields observed in a source manifest; preserve source_url, source_authority, jurisdiction, evidence_class, timestamps, opaque runner identifiers, and observed odds fields. Reject duplicate race/event identity, overwrite, caller alias mutation, and stale status transitions.

- [ ] Step 1: Write failing tests for duplicate, overwrite, alias, stale, and observed-schema acceptance.

~~~python
def test_store_rejects_duplicate_and_alias_mutation(tmp_path):
    store = AppendOnlyRaceStore(str(tmp_path / "races.jsonl"))
    record = {"race_id": "JRA-2026-01-01-01", "source_url": "https://www.jra.go.jp/", "status": "observed"}
    store.append(record)
    record["status"] = "mutated"
    assert store.records()[0]["status"] == "observed"
    with pytest.raises(ValueError, match="duplicate"):
        store.append({"race_id": "JRA-2026-01-01-01", "source_url": "https://www.jra.go.jp/", "status": "observed"})

def test_store_rejects_stale_transition():
    store = AppendOnlyRaceStore("races.jsonl")
    with pytest.raises(ValueError, match="stale"):
        store.append({"race_id": "NAR-2026-01-01-01", "status": "stale", "source_authority": "secondary"})
~~~

- [ ] Step 2: Run RED.

~~~sh
cd /Users/anicca/anicca-project/.worktrees/horse-racing-agent-spec/apps/horse-racing-agent
rtk python3.12 -m pytest tests/test_store.py -q
~~~

Expected: FAIL because the observed-schema append-only contract is not yet adopted from a Reality Gate manifest.

- [ ] Step 3: Implement only observed-field append/replay and redacted canonical hashing. Do not put raw values or synthetic-only fields in normalized_races.json.
- [ ] Step 4: Run GREEN.

~~~sh
rtk python3.12 -m pytest tests/test_store.py -q
rtk python3.12 -m pytest -q
~~~

Expected: duplicate/overwrite/alias/stale rejection and full package suite PASS; manifest-derived schema is the only completion evidence.

- [ ] Step 5: Close with store replay E2E, state update, and commit.

~~~sh
git diff --check -- apps/horse-racing-agent/src/horse_racing_agent/store.py apps/horse-racing-agent/tests/fixtures/normalized_races.json apps/horse-racing-agent/tests/test_store.py
git add apps/horse-racing-agent/src/horse_racing_agent/store.py apps/horse-racing-agent/tests/fixtures/normalized_races.json apps/horse-racing-agent/tests/test_store.py
git commit -m "feat(horse-racing): adopt observed public-web schema store"
git push origin HEAD
git push canonical HEAD
~~~

## Task 6: HRA-3D historical coverage and cutoff audit

**State:** blocked until Task 5. **Files:** apps/horse-racing-agent/src/horse_racing_agent/data_audit.py and apps/horse-racing-agent/tests/test_data_audit.py. Estimated 75 LOC.

**Interface:** audit_records(records: Sequence[Mapping[str, object]], manifests: Sequence[Mapping[str, object]]) -> AuditReport. AuditReport contains source_url, jurisdiction, row_count, duplicate_count, missing_timestamp_count, cutoff_violation_count, freshness_age, content_sha256, fetch_exit_code, evidence_class, allowed_scope, and cash_authorized. A report requires evidence_class=REAL_PUBLIC_WEB_RECORD or PUBLIC_WEB_SECONDARY; PUBLIC_WEB_SECONDARY carries allowed_scope=shadow_only and cash_authorized=False, and never authorizes LIVE_CASH or revenue.

- [ ] Step 1: Test manifest-required actual coverage and future-leak rejection.

~~~python
@pytest.mark.parametrize(
    ("evidence_class", "allowed_scope"),
    [("REAL_PUBLIC_WEB_RECORD", "private_shadow"), ("PUBLIC_WEB_SECONDARY", "shadow_only")],
)
def test_audit_accepts_public_web_classes(evidence_class, allowed_scope):
    report = audit_records(
        [{"race_id": "race-1", "timestamp": "2026-01-01T00:00:00+09:00"}],
        [{"evidence_class": evidence_class, "parsed_row_count": 1, "fetch_exit_code": 0, "content_sha256": "a" * 64}],
    )
    assert report.allowed_scope == allowed_scope
    assert report.cash_authorized is False

@pytest.mark.parametrize("manifest", [{"evidence_class": "SYNTHETIC_TEST"}, {}])
def test_audit_rejects_synthetic_or_missing_manifest(manifest):
    with pytest.raises(ValueError, match="evidence_class must be REAL_PUBLIC_WEB_RECORD or PUBLIC_WEB_SECONDARY"):
        audit_records(
            [{"race_id": "race-1", "timestamp": "2026-01-01T00:00:00+09:00"}],
            [manifest],
        )
~~~

- [ ] Step 2: Run RED.

~~~sh
cd /Users/anicca/anicca-project/.worktrees/horse-racing-agent-spec/apps/horse-racing-agent
rtk python3.12 -m pytest tests/test_data_audit.py -q
~~~

Expected: FAIL because audit_records is absent or rejects/omits the required REAL_PUBLIC_WEB_RECORD and PUBLIC_WEB_SECONDARY distinction; the exact invalid-class error is not yet implemented.

- [ ] Step 3: Implement chronological ordering, source/jurisdiction separation, duplicate detection, missing/freshness counters, cutoff check, and required manifest class/hash/exit checks. Never fabricate historical rows.
- [ ] Step 4: Run GREEN and full package suite.

~~~sh
rtk python3.12 -m pytest tests/test_data_audit.py -q
rtk python3.12 -m pytest -q
~~~

Expected: actual manifest-backed audit PASS; random split and future fields are rejected.

- [ ] Step 5: Commit only these two files after Sol verifies audit output.

~~~sh
git add apps/horse-racing-agent/src/horse_racing_agent/data_audit.py apps/horse-racing-agent/tests/test_data_audit.py
git commit -m "feat(horse-racing): audit public-web coverage and cutoff"
git push origin HEAD
git push canonical HEAD
~~~

## Task 7: HRA-3Ma/3Mb baseline, model, walk-forward, calibration

**State:** blocked until Task 6. Keep exact filenames from the prior plan.

### HRA-3Ma files and interfaces

Files: apps/horse-racing-agent/src/horse_racing_agent/features.py, apps/horse-racing-agent/src/horse_racing_agent/model.py, apps/horse-racing-agent/tests/test_model.py. Estimated 95 LOC.

Interfaces: build_features(record: Mapping[str, object], cutoff: datetime) -> Mapping[str, float]; fit_market_model(rows: Sequence[Mapping[str, object]]) -> ModelArtifact. ModelArtifact stores model_version, source_url, jurisdiction, evidence_class, manifest_hashes, baseline_name, and cutoff_field. Features are cutoff-safe market-implied probability, win/place fields, and fixed snapshot age; future timestamp fields raise ValueError.

- [ ] Write test_model.py for cutoff-after-feature rejection, baseline probability, and source evidence linkage.
- [ ] Run RED from apps/horse-racing-agent with rtk python3.12 -m pytest tests/test_model.py -q; expected FAIL with missing cutoff-safe feature/model contract.
- [ ] Implement only deterministic features and a model artifact that stores evidence_class, source_url, jurisdiction, and manifest hash. Do not report synthetic metrics as performance.
- [ ] Run from apps/horse-racing-agent: rtk python3.12 -m pytest tests/test_model.py -q and rtk python3.12 -m pytest -q; expected PASS with no future feature accepted.
- [ ] Close HRA-3Ma with git add on the three listed files, commit message feat(horse-racing): add cutoff-safe model contract, then push origin HEAD and canonical HEAD.

### HRA-3Mb files and interfaces

Files: apps/horse-racing-agent/src/horse_racing_agent/backtest.py, apps/horse-racing-agent/tests/test_backtest.py. Estimated 80 LOC.

Interfaces: walk_forward(rows: Sequence[Mapping[str, object]], model: ModelArtifact, snapshot_minutes: int) -> BacktestReport; BacktestReport contains Brier score, logloss, ECE, slippage stress, later-window result, source manifest hashes, and chronological window IDs.

- [ ] Write test_backtest.py to reject random split/future ordering and to require Brier/logloss/ECE fields.
- [ ] Run RED from apps/horse-racing-agent with rtk python3.12 -m pytest tests/test_backtest.py -q; expected FAIL because walk_forward and BacktestReport are absent.
- [ ] Implement chronological walk-forward, fixed snapshot, calibration, odds slippage stress, and later-window reporting. Keep actual historical evidence as a prerequisite; zero-row history stays BLOCKED.
- [ ] Run from apps/horse-racing-agent: rtk python3.12 -m pytest tests/test_backtest.py -q and rtk python3.12 -m pytest -q; expected PASS with no future leakage.
- [ ] Close HRA-3Mb with the two files, commit message feat(horse-racing): add walk-forward calibration backtest, and push both remotes.

## Task 8: HRA-4 SHADOW decision and immutable outcome ledger

**State:** blocked until Task 7 HRA-3Mb. **Files:** apps/horse-racing-agent/src/horse_racing_agent/decision.py, apps/horse-racing-agent/src/horse_racing_agent/ledger.py, apps/horse-racing-agent/tests/test_shadow_ledger.py. Estimated 95 LOC.

**Interfaces:** decide_race(model: ModelArtifact, race: Mapping[str, object]) -> Decision; OutcomeLedger.append_decision(decision: Decision) -> str; OutcomeLedger.append_outcome(decision_id: str, outcome: Mapping[str, object]) -> None. Decision carries action, source_url, source_authority, jurisdiction, evidence_class, reason, freshness, and decision_id. Secondary records cannot produce LIVE_CASH.

- [ ] Write tests for all eligible-race SHADOW/SKIP, duplicate outcome rejection, immutable decision replay, and secondary cash rejection.
- [ ] Run RED from apps/horse-racing-agent with rtk python3.12 -m pytest tests/test_shadow_ledger.py -q; expected FAIL because decision and ledger contracts are absent.
- [ ] Implement append-only decision/outcome records, idempotent outcome identity, SKIP reason/threshold gap, and no-revenue shadow semantics.
- [ ] Run the focused test and full suite; expected PASS with every synthetic mechanic labeled SYNTHETIC_TEST.
- [ ] Close with Sol ledger replay E2E, exact three-file commit message feat(horse-racing): add shadow outcome ledger, and push both remotes.

## Task 9: HRA-4b Japanese Telegram pre/result messages

**State:** blocked until Task 8. **Files:** apps/horse-racing-agent/src/horse_racing_agent/telegram.py and apps/horse-racing-agent/tests/test_telegram.py. Estimated 75 LOC.

**Interfaces:** render_pre_message(event: Mapping[str, object]) -> str; render_result_message(event: Mapping[str, object]) -> str; dedupe_key(event: Mapping[str, object]) -> str. Every message starts with Life Manager::: 競馬AI and one truth label.

- [ ] Write tests for DATA BLOCKED, REAL DATA · SHADOW, LIVE · ¥100 labels; source URL/authority, jurisdiction, retrieved/effective time, reason, evidence class, decision_id, real P&L, and shadow P&L; and duplicate-key suppression.
- [ ] Run RED from apps/horse-racing-agent with rtk python3.12 -m pytest tests/test_telegram.py -q; expected FAIL because render and dedupe interfaces are absent.
- [ ] Implement deterministic Japanese pre/result schemas with no raw values or credentials. NAR secondary remains SHADOW-only; blocked paths emit no prediction.
- [ ] Run focused and full pytest; expected PASS with truth separation and dedupe.
- [ ] Close with Telegram schema E2E, commit message feat(horse-racing): add evidence-labeled telegram schemas, and push both remotes.

## Task 10: HRA-5 CFO receipt/evidence adapter

**State:** blocked until Task 9 and CFO-0c. **Files:** apps/horse-racing-agent/src/horse_racing_agent/cfo.py and apps/horse-racing-agent/tests/test_cfo.py. Estimated 85 LOC.

**Interface:** record_receipt(event: Mapping[str, object]) -> ReceiptEntry; is_revenue(entry: ReceiptEntry) -> bool. ReceiptEntry carries receipt_id, evidence_class, settled_status, payout, stake, refund, and source_url. Revenue is true only for LIVE_CASH with official settled receipt; SYNTHETIC_TEST, PUBLIC_WEB_SECONDARY, and unsettled LIVE_SHADOW are zero revenue. Receipt identity is idempotent and bank internal settlement never double-counts payout.

- [ ] Write tests for official settled receipt acceptance, shadow/secondary revenue zero, refund/void handling, duplicate receipt rejection, and bank settlement non-double-count.
- [ ] Run RED from apps/horse-racing-agent with rtk python3.12 -m pytest tests/test_cfo.py -q; expected FAIL because receipt interfaces are absent or CFO-0c gate is false.
- [ ] Implement the adapter without changing existing CFO state/spec and without adding any purchase path.
- [ ] Run focused and full pytest; expected PASS only when CFO-0c state and evidence class are explicit.
- [ ] Close with Sol CFO reconciliation E2E, commit message feat(horse-racing): add settled receipt evidence adapter, and push both remotes.

## Task 11: HRA-6 terms/order/tax/credential/receipt/reconciliation research gate

**State:** blocked research gate; no code or order implementation. **File:** docs/evidence/horse-racing/hra-6-compliance-gate.md.

- [ ] Record written terms resolution for each source, permitted use, credential separation, tax review, action-time cap, official result/payout receipt path, reconciliation rules, and failure behavior.
- [ ] Record that NAR secondary terms remain unverified until resolution and cannot authorize LIVE_CASH.
- [ ] Keep PurchaseExecutor disabled. Do not build DOM ordering, browser login, unofficial order transport, bet, or wallet/bank mutation before the gate.
- [ ] Sol reviews the redacted document and marks PASS or BLOCKED; Luna commits only this evidence file after review.

~~~sh
git diff --check -- docs/evidence/horse-racing/hra-6-compliance-gate.md
git add docs/evidence/horse-racing/hra-6-compliance-gate.md
git commit -m "docs(horse-racing): record HRA-6 compliance gate"
git push origin HEAD
git push canonical HEAD
~~~

## Task 12: HRA-7 owner-local-day micro-live gate (document only)

**State:** blocked until Task 11 PASS; no live action in this plan slice. **File:** docs/evidence/horse-racing/hra-7-micro-live-gate.md.

- [ ] Document one owner-local-day total <= ¥100, action-time financial confirmation, official purchase history, settled receipt, positive confidence-adjusted EV, stale/pre-message/reconciliation fail-closed, and no martingale/chasing.
- [ ] Document that secondary-only evidence cannot unlock the gate and PurchaseExecutor remains disabled until Sol verifies every HRA-6 condition.
- [ ] Sol reviews the evidence checklist; no bet, subscription, purchase, or external action is executed while this state is BLOCKED.

~~~sh
git diff --check -- docs/evidence/horse-racing/hra-7-micro-live-gate.md
git add docs/evidence/horse-racing/hra-7-micro-live-gate.md
git commit -m "docs(horse-racing): define HRA-7 micro-live gate"
git push origin HEAD
git push canonical HEAD
~~~

## Task 13: HRA-8 evidence-driven scale review

**State:** blocked future gate; no scale implementation. **File:** docs/evidence/horse-racing/hra-8-scale-gate.md.

- [ ] Require positive later-window evidence, ROI confidence interval, calibration, maximum drawdown, bankroll constraints, market capacity, official settled receipts, and reconciliation before any scale review.
- [ ] Keep $10K/month as a target only; never guarantee it, forecast it, or convert shadow/secondary values into revenue.
- [ ] Sol records PASS or BLOCKED with source authority and evidence class; Luna commits only the redacted gate document after verification.

~~~sh
git diff --check -- docs/evidence/horse-racing/hra-8-scale-gate.md
git add docs/evidence/horse-racing/hra-8-scale-gate.md
git commit -m "docs(horse-racing): define HRA-8 scale evidence gate"
git push origin HEAD
git push canonical HEAD
~~~

## Close-before-next and handoff

Every task closes only after focused tests or evidence E2E, full relevant verification, state-table update, owned-file diff check, commit, push to origin and canonical, and fetch proving local=origin=canonical. A failed check leaves the current task ACTIVE/BLOCKED and does not activate the next task. Quarantine files remain untracked until Task 5 is explicitly activated after per-source manifests.
