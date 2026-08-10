# Life Manager Horse Racing Agent Official Free-Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mac-native zero-cost public-web ingestionでJRA公式primary recordとNAR公式zero-cost primary recordをsource authority付きで観測し、redacted evidence、observed schema、cutoff-safe model、SHADOW、CFO separationをReality Gate順に実装する。`race.netkeiba.com` / `nar.netkeiba.com` は公式情報の欠落時だけ使うPUBLIC_WEB_SECONDARY fallbackであり、公式recordやcash根拠へ昇格しない。

**Architecture:** Mac上でcrwlを公式HTML navigationに使い、binary ZIPはCRWLの`Page.goto: Download is starting`制限を記録したうえでcurlへ切り替える。HRA-2Fがhost、authority、permission、robots/terms、Mac-local raw境界を一つのingest gateで検証し、通過後にのみmanifest、observed schema、audit、model、SHADOWを進める。raw archive/CSV/PDFはMac-local append-onlyに留め、Git・Telegram・cloud・CFOへ出すのはredacted metadataだけにする。

**Tech Stack:** Python 3.12、pytest、`urllib.parse`、`hashlib`、標準ライブラリ中心のpure deterministic contracts、crwl、curl、Mac-local filesystem、redacted YAML/Markdown evidence。新しいpaid SDK、SaaS、public API、browser login、order transportは追加しない。

## Global Constraints

- 個人利用のみ。zero-cost public-web ingestionを許可し、raw page/rowのredistribution、public publication、SaaS化をしない。
- JRA primaryはofficial public pages。JRA robots snapshotは`User-agent:*`とempty `Disallow`、private use/citation境界を記録する。現時点のJRA actual rowは0。
- NAR primaryはofficial `www.keiba.go.jp`。`robots.txt`の`Crawl-delay: 10`とTodayRaceInfo/DataRoom/DataDownloadのDisallowをmanifestへ保持する。NAR probeのpermission basisは`USER_ATTESTED_PERMISSION`（2026-08-10）、`permission_document_verified=false`であり、一般的なbot許可、redistribution/publication許可、cash execution許可とは解釈しない。
- NAR officialのdaily/monthly取得はmanual cadenceを守る。dailyは約2分ごとの更新情報をそれより頻繁にpollせず、monthly dataは毎日午前2時頃の更新を基準にする。pre-raceのdaily odds buttonがdisabledなら`NOT_PUBLISHED`としてbounded retryし、failureやfake zeroに変換しない。
- Evidence classesは`SYNTHETIC_TEST`、`REAL_PUBLIC_WEB_RECORD`、`PUBLIC_WEB_SECONDARY`、`LIVE_SHADOW`、`LIVE_CASH`。HTTP/DOM success、download開始、schema存在だけをrecord completionとしない。
- Manifest必須欄は`evidence_class`、`source_url`、`source_authority`、`jurisdiction`、`retrieved_at`、`page_or_effective_timestamp`、`fetch_exit_code`、`http_status`、`parsed_row_count`、observed schema names/types、`content_sha256`、`robots_snapshot_url/status`、`terms_url/status`、`permission_basis`、`permission_document_verified`、`raw_values_exported=false`、`allowed_scope`、`cash_authorized=false`。official JRA/NARの`allowed_scope`は`private_shadow`、secondaryは`shadow_only`。
- raw snapshotはMac-local private append-only storageだけに保持する。ETag、content hash、source URLでidempotencyを判定し、同一archiveを二重appendしない。raw values、実馬名、credential、secret、subscription id、receiptは外へ出さない。
- `PurchaseExecutor`は常時disabled。HRA-6のterms/order/tax/credential/receipt/reconciliation gate以前に注文・決済・bet・wallet/bank mutationを作らない。`USER_ATTESTED_PERMISSION`だけではcashをauthorizeしない。
- `$10K/month`はevidence-driven target only。ROI、勝率、収益、forecast、guaranteeを作らず、official settled receiptとlater-window evidenceがない値をrevenueへ加算しない。
- Solはplan、gate、verificationを所有し、Lunaはこのplanに記載されたedit、code、command、evidence作成を実行する。
- 未完項目は先頭の一件だけをactiveにする。各sliceは最大3 files、estimated LOC 100以下、RED→GREEN→実E2E/state更新→commit→origin/canonical pushで閉じてから次へ進む。

## Current truth and evidence

| Evidence | 実測値 |
|---|---:|
| real JRA official public-web result rows | 12 |
| real NAR official race rows | 46 |
| real NAR official horse rows | 456 |
| real NAR official monthly odds rows | 327274 |
| real NAR official payback rows | 0 (pre-settlement) |
| real historical backtests | 0 |
| live SHADOW runs | 0 |
| live Telegram runs | 0 |
| live orders/payments | 0 |
| revenue / real P&L | 0 |

JRA official resultはcommits `526381236` + `e79ed1d11`で12 actual rows、`PASS_PRIVATE_SHADOW`、private raw 700/600、`cash_authorized=false`。NARの46/456/327274行、payback 0 pre-settlementはcommit `6a6cdd1356ea9f1d5064cdd24bb05d4342fe6730`から始まるredacted observationで、commits `33ef30c1d` + `a289babba`により`PASS_PRIVATE_SHADOW`。NAR ephemeral raw archiveは不在で`CANNOT_RECOMPUTE_RAW_ARCHIVE_ABSENT`である。backtest、SHADOW、Telegram、orders、revenueは現在値0としてblocked表示する。

## Architecture flow

~~~mermaid
flowchart TD
  A[HRA-0/1 safety and design] --> B[HRA-2F Mac ingest boundary]
  P[Mac + crwl official HTML navigation] --> H[Official JRA/NAR HTML]
  H --> D[curl official binary ZIP download]
  E[CRWL error: Page.goto: Download is starting] -. binary fallback .-> D
  D --> B
  H --> B
  B -- RED/BLOCKED --> X[DATA BLOCKED]
  B -- GREEN --> G{HRA-2R per-source manifest gate}
  G -- JRA official --> J[HRA-2S JRA observed schema/store]
  G -- NAR official --> N[HRA-2S NAR observed schema/store]
  G -- secondary fallback --> S[PUBLIC_WEB_SECONDARY shadow schema]
  J --> R[Mac-local raw snapshot]
  N --> R
  S --> R
  R --> M[Redacted manifest]
  M --> A2[HRA-3D cutoff/coverage audit]
  A2 --> W[HRA-3M cutoff-safe model/walk-forward]
  W --> L[HRA-4 SHADOW/SKIP ledger]
  L --> T[HRA-4b Telegram evidence split]
  T --> C[HRA-5 CFO settled receipt split]
  C --> Q[HRA-6 terms/order/tax/credential/receipt gate]
  Q --> Z[HRA-7/8 blocked cash/scale review]
  S -. allowed_scope=shadow_only .-> Q
  R -. raw_values_exported=false .-> X
~~~

The official NAR source is zero-cost primary; JRA remains official primary. Secondary fallback is a separate authority lane and never changes the official source label. The pipeline is `Mac/crwl HTML -> official HTML/download -> HRA-2F -> Mac raw -> manifest -> schema -> audit -> model -> SHADOW`; binary transport uses curl only after the exact CRWL error is recorded.

## Ordered execution status

| Order | Stage | State | Scope |
|---:|---|---|---|
| 0 | Completed safety and design | complete | historical commits, approved official public-web design, NAR evidence commit |
| 1 | HRA-2F ingest boundary refactor | **complete** | commits `ae56d3524` + `956d1b50d`; focused 24/full 32 PASS |
| 2 | HRA-2R2 NAR official evidence gate validation | **complete** | `PASS_PRIVATE_SHADOW`; commits `33ef30c1d` + `a289babba` |
| 3 | HRA-2R1 JRA public-web record | **complete** | 12 actual rows; commits `526381236` + `e79ed1d11` |
| 4 | HRA-2N NAR official free acquisition component | **ACTIVE** | HTML/curl planner and Mac-local archive contract |
| 5 | HRA-2R3 per-source index/gate | blocked by source records | JRA official, NAR official, optional secondary fallback rows |
| 6 | HRA-2S observed schema/store | blocked by HRA-2R3 | quarantine three files only |
| 7 | HRA-3D audit | blocked by HRA-2S | `data_audit.py` and `test_data_audit.py` |
| 8 | HRA-3Ma/3Mb model and backtest | blocked by HRA-3D | cutoff-safe odds and settled-payback contract |
| 9 | HRA-4 SHADOW decision/outcome ledger | blocked by HRA-3Mb | `decision.py`, `ledger.py`, `test_shadow_ledger.py` |
| 10 | HRA-4b Japanese Telegram | blocked by HRA-4 | `telegram.py` and `test_telegram.py` |
| 11 | HRA-5 CFO adapter | blocked by HRA-4b and CFO-0c | `cfo.py` and `test_cfo.py` |
| 12 | HRA-6 terms/order/tax/receipt gate | blocked research gate | document only, `PurchaseExecutor` disabled |
| 13 | HRA-7 owner-local-day ¥100 gate | blocked future gate | document only, no bet execution |
| 14 | HRA-8 scale review | blocked future gate | evidence-driven target only |

## Task 0: Completed safety and design baseline

**State:** complete. Sol verifies these commits before activating Task 1.

Historical correction: commit `0fe627cd` is a superseded boundary record and is not an active dependency. It does not override the Mac-native official public-web design. Commit `6a6cdd1356ea9f1d5064cdd24bb05d4342fe6730` is the committed NAR official probe evidence; it records real observation while keeping HRA-2F and HRA-2R gates blocked.

- `d743b153`: registry v2 candidate and CFO-0c exact-seven dependency.
- `89d48910`: `PurchaseExecutor` disabled and side-effect-free.
- `0fe627cd`: superseded boundary history only.
- `9b9b78346`: design switched to free public-web sources, evidence classes, and Mac-local raw boundary.
- `509955401`: HRA-2F made active because the old boundary implementation was not compatible.
- `6a6cdd135`: NAR official redacted evidence, 46/456/327274 rows, pre-settlement payback 0, hashes, and permission/robots metadata.

~~~sh
git show --no-patch --format=%H d743b153
git show --no-patch --format=%H 89d48910
git show --no-patch --format=%H 0fe627cd
git show --no-patch --format=%H 9b9b78346
git show --no-patch --format=%H 509955401
git show --no-patch --format=%H 6a6cdd135
~~~

Task 0 close verified that all six commits resolve and the NAR evidence exists. The current active item is tracked only in the ordered status table.

## Task 1: HRA-2F TDD refactor of the official free-web ingest boundary (COMPLETE)

**State:** complete at commits `ae56d3524` and `956d1b50d`. TDD evidence: initial RED 23 failures, GREEN focused 23/full 31; traversal review RED 1 failure/23 pass, final focused 24/full 32. Fresh Sol review found the traversal defect and scoped re-review confirmed it addressed with no new Critical/Important finding.

**Files:**
- Modify: `apps/horse-racing-agent/src/horse_racing_agent/ingest.py`
- Modify: `apps/horse-racing-agent/tests/test_ingest_boundary.py`

**Plan size:** 2 files, estimated 95 LOC total. No other code, fixture, evidence, or quarantine file may change in this task.

**Interface:**

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
    permission_basis: str,
    permission_document_verified: bool,
) -> dict[str, str | int | bool]:
    ...
~~~

Exact accepted source combinations:

| host | authority | jurisdiction | allowed_scope |
|---|---|---|---|
| `www.jra.go.jp` | `official` | `JRA` | `private_shadow` |
| `www.keiba.go.jp` | `official` | `NAR` | `private_shadow` |
| `race.netkeiba.com` | `secondary` | `JRA` | `shadow_only` |
| `nar.netkeiba.com` | `secondary` | `NAR` | `shadow_only` |

Parse with `urlsplit` and compare hostname by exact equality. Require HTTPS, `host_os=macos`, `storage_scope=mac_local_private`, `export_destination=local_raw_snapshot`, a str/bytes payload, non-empty permission metadata, and boolean `permission_document_verified`. Allow official keiba.go.jp TodayRaceInfo, DataRoom, DataDownload, MonthlyConveneInfo, and PDF paths when the tuple is exact. Hostname spoofing such as `evil-jra.go.jp` and `race.netkeiba.com.evil.example` is rejected.

Return only redacted metadata: source fields, Mac-local fields, `content_sha256`, byte `payload_size`, robots/terms fields, `permission_basis`, `permission_document_verified`, `raw_payload_exported=false`, `allowed_scope`, and `cash_authorized=false`. Never include/write/log/serialize `raw_payload` or decoded values. Error contract: invalid URL/authority/path raises `ValueError("source URL/authority mismatch")`; environment raises `ValueError("Mac-local storage contract")`; invalid payload raises `ValueError("raw payload must be str or bytes")`; permission errors raise `ValueError("permission metadata")`.

- [x] Step 1: Write failing tests.

~~~python
def test_accepts_nar_official_dynamic_path_and_permission_metadata():
    metadata = ingest_raw_boundary(
        "https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily",
        "official", "NAR", "macos", "mac_local_private", b"synthetic",
        "local_raw_snapshot", "https://www.keiba.go.jp/robots.txt",
        "Crawl-delay: 10; TodayRaceInfo/DataRoom/DataDownload disallowed",
        "https://www.keiba.go.jp/terms.html", "USER_ATTESTED_PERMISSION_DOCUMENT_UNVERIFIED",
        "USER_ATTESTED_PERMISSION", False,
    )
    assert metadata["allowed_scope"] == "private_shadow"
    assert metadata["permission_document_verified"] is False
    assert metadata["cash_authorized"] is False
    assert metadata["raw_payload_exported"] is False
    assert "raw_payload" not in metadata

@pytest.mark.parametrize(
    ("source_url", "authority", "jurisdiction"),
    [("https://www.jra.go.jp/", "official", "JRA"),
     ("https://race.netkeiba.com/", "secondary", "JRA"),
     ("https://nar.netkeiba.com/", "secondary", "NAR")],
)
def test_authority_matrix_and_shadow_scope(source_url, authority, jurisdiction):
    metadata = ingest_raw_boundary(
        source_url, authority, jurisdiction, "macos", "mac_local_private",
        "synthetic", "local_raw_snapshot", "https://example.test/robots.txt",
        "unverified", "unavailable", "unverified", "USER_ATTESTED_PERMISSION", False,
    )
    expected = "private_shadow" if authority == "official" else "shadow_only"
    assert metadata["allowed_scope"] == expected
    assert metadata["cash_authorized"] is False

@pytest.mark.parametrize("source_url", ["https://evil-jra.go.jp/race", "https://race.netkeiba.com.evil.example/race"])
def test_rejects_hostname_spoof(source_url):
    with pytest.raises(ValueError, match="source URL/authority mismatch"):
        ingest_raw_boundary(
            source_url, "official", "JRA", "macos", "mac_local_private",
            "synthetic", "local_raw_snapshot", "https://www.jra.go.jp/robots.txt",
            "observed", "https://www.jra.go.jp/use/", "observed",
            "JRA_PRIVATE_USE_POLICY", False,
        )
~~~

Add one case for the fourth accepted combination and invalid environment/payload/permission cases. The NAR dynamic path case must pass; it replaces the old dynamic-path rejection. All payloads are synthetic mechanics input and never real-data evidence.

- [x] Step 2: Run RED.

~~~sh
cd /Users/anicca/anicca-project/.worktrees/horse-racing-agent-spec/apps/horse-racing-agent
rtk python3.12 -m pytest tests/test_ingest_boundary.py -q
~~~

Expected: FAIL because the legacy boundary does not accept official NAR authority/permission fields or the redacted return contract; no network, credential, or source fetch is allowed.

- [x] Step 3: Implement the minimal boundary.

Use exact host/authority allowlists, permit official keiba.go.jp dynamic paths, compute UTF-8/bytes SHA-256 and byte size, and return fixed metadata. Set `allowed_scope=private_shadow` for official and `shadow_only` for secondary; always set `cash_authorized=false`.

- [x] Step 4: Run GREEN and package suite.

~~~sh
cd /Users/anicca/anicca-project/.worktrees/horse-racing-agent-spec/apps/horse-racing-agent
rtk python3.12 -m pytest tests/test_ingest_boundary.py -q
rtk python3.12 -m pytest -q
~~~

Expected: official JRA/NAR matrix, secondary scope, spoof rejection, hash/size, raw absence, permission metadata, and full suite PASS.

- [x] Step 5: Verify E2E/state and close the slice.

~~~sh
cd /Users/anicca/anicca-project/.worktrees/horse-racing-agent-spec
git diff --check -- apps/horse-racing-agent/src/horse_racing_agent/ingest.py apps/horse-racing-agent/tests/test_ingest_boundary.py
git status --short
git add apps/horse-racing-agent/src/horse_racing_agent/ingest.py apps/horse-racing-agent/tests/test_ingest_boundary.py
git commit -m "feat(horse-racing): refactor free-web ingest boundary"
git push origin HEAD
git push canonical HEAD
~~~

Expected: only the two owned files are staged; quarantine remains untracked; Task 1 is GREEN before Task 2 or Task 3 becomes active.

## Task 2: HRA-2R2 NAR official Reality Gate validation (COMPLETE)

**State:** complete at commits `33ef30c1d` + `a289babba`. Sol decision: `PASS_PRIVATE_SHADOW`; `cash_authorized=false`; raw archive absent/CANNOT_RECOMPUTE. Fresh review fix round aligned exact URL/timestamps and canonical schema keys, then scoped re-review returned ship.

**Files:**
- Modify only if verification exposes an error: `docs/evidence/horse-racing/nar-official-data-probe.md`

**Consumes:** committed probe `6a6cdd135`, HRA-2F metadata contract.
**Produces:** a gate judgment for NAR official data; it does not refetch raw archives merely to manufacture freshness.

- [x] Step 1: Verify the committed manifest fields.

~~~sh
cd /Users/anicca/anicca-project/.worktrees/horse-racing-agent-spec
rg -n 'REAL_PUBLIC_WEB_RECORD|source_authority: official|jurisdiction: NAR|race_rows: 46|horse_rows: 456|odds_rows: 327274|payback_rows: 0|USER_ATTESTED_PERMISSION|permission_document_verified: false|raw_values_exported: false|cash_authorized: false|PASS_PRIVATE_SHADOW|CANNOT_RECOMPUTE_RAW_ARCHIVE_ABSENT' docs/evidence/horse-racing/nar-official-data-probe.md
~~~

Expected: every required field is present. Missing data remains visible; `payback_rows=0` means pre-settlement, not a zero payout.

- [x] Step 2: Recompute only redacted structural checks from the Mac-local archive when it still exists.

Check content hashes, archive entry names, line counts, UTF-8 BOM, and header names. Do not print runner/person/raw odds values. If the ephemeral archive is gone, keep the committed hash/count evidence and schedule the next official bounded acquisition; never synthesize a replacement.

- [x] Step 3: Sol records the judgment.

PASS requires HRA-2F GREEN plus exact source URL, official authority, timestamps, HTTP/fetch evidence, parsed rows, observed raw schema types, hashes, permission metadata, and raw non-export. `USER_ATTESTED_PERMISSION` keeps `cash_authorized=false`. Commit a correction only when the evidence file actually changes.

## Task 3: HRA-2R1 JRA official actual record (COMPLETE)

**State:** complete at commits `526381236` + `e79ed1d11`. Official home discovery produced the most recent 2026-08-09 result URL; private HTML hash matched, one result table contained 12 actual rows x 14 fields, fresh Sol review approved, and the final gate is `PASS_PRIVATE_SHADOW` with cash false.
**File:** create `docs/evidence/horse-racing/jra-public-web-probe.md`.

- [x] Step 1: Discover a current official JRA race/result URL from `https://www.jra.go.jp/` with crwl; do not hardcode a stale race id.
- [x] Step 2: Capture one bounded official page under the JRA private-use policy. Store raw only under `/Users/anicca/Library/Application Support/Anicca/horse-racing/raw/`; keep it outside Git.
- [x] Step 3: Parse at least one actual race row and record source URL, authority, jurisdiction, retrieved/effective time, fetch exit/HTTP status, schema names/raw types, SHA-256, robots/terms status, permission basis, and `raw_values_exported=false`.
- [x] Step 4: Verify and commit.

~~~sh
git diff --check -- docs/evidence/horse-racing/jra-public-web-probe.md
git add docs/evidence/horse-racing/jra-public-web-probe.md
git commit -m "docs(horse-racing): record JRA official web probe"
git push origin HEAD
git push canonical HEAD
~~~

Expected: `parsed_row_count>=1` and `REAL_PUBLIC_WEB_RECORD`; HTTP/DOM success alone fails.

## Task 4: HRA-2N NAR official acquisition component

**State:** ACTIVE. HRA-2F and both official source Reality Gates are complete; this task creates only the pure acquisition planner/classifier.

**Files:**
- Create: `apps/horse-racing-agent/src/horse_racing_agent/nar_source.py`
- Create: `apps/horse-racing-agent/tests/test_nar_source.py`

**Interfaces:**

~~~python
@dataclass(frozen=True)
class FetchRequest:
    url: str
    transport: Literal["crwl", "curl"]
    artifact_kind: Literal["navigation", "daily_race", "daily_odds", "monthly_race", "monthly_odds"]
    not_before: datetime

def plan_nar_fetch(now: datetime, today_html: str, monthly_html: str) -> tuple[FetchRequest, ...]: ...
def classify_download(*, http_status: int, content_type: str, body_sha256: str, previous_sha256: str | None) -> Literal["NEW", "UNCHANGED", "NOT_PUBLISHED", "INVALID"]: ...
~~~

- [ ] Step 1: Write RED tests proving URLs are discovered from official HTML, not permanently hardcoded to August 2026; binary endpoints use curl; HTML uses crwl; duplicate hashes return `UNCHANGED`; disabled odds return `NOT_PUBLISHED`.
- [ ] Step 2: Run RED.

~~~sh
cd /Users/anicca/anicca-project/.worktrees/horse-racing-agent-spec/apps/horse-racing-agent
rtk python3.12 -m pytest tests/test_nar_source.py -q
~~~

- [ ] Step 3: Implement the pure planner/classifier. Enforce HTTPS exact host `www.keiba.go.jp`, daily polling no faster than 2 minutes, monthly acquisition after the documented approximately 02:00 update, and append-only identity `(source_url, content_sha256)`.
- [ ] Step 4: Run focused and full GREEN; commit/push only the two files.

Runtime contract: crwl navigates Today/DataRoom/Monthly HTML. When crwl reports `Page.goto: Download is starting`, curl retrieves the linked ZIP. Race data covers 1998-01 onward; odds cover 2026-03 onward. Daily odds can be unavailable before publication. Payback remains pending until official settlement.

## Task 5: HRA-2R3 per-source Reality Gate index

**File:** create `docs/evidence/horse-racing/reality-gate-index.md`.

Create independent rows for JRA official, NAR official, JRA secondary fallback, and NAR secondary fallback. Each row carries its evidence class, URL, authority, jurisdiction, permission status, record counts, hash, schema status, allowed scope, cash authorization, gate state, and evidence link. JRA PASS never changes NAR; fallback never upgrades to official.

Verify with `git diff --check`, commit `docs(horse-racing): index public data reality gates`, and push both remotes.

## Task 6: HRA-2S observed schema and append-only store

**Files:**
- Modify/adopt: `apps/horse-racing-agent/src/horse_racing_agent/store.py`
- Modify/adopt: `apps/horse-racing-agent/tests/fixtures/normalized_races.json`
- Modify/adopt: `apps/horse-racing-agent/tests/test_store.py`

These are the current three untracked quarantine files. Luna must rewrite them from accepted manifest field names/raw types before adding them. Existing synthetic-only content is not evidence.

**Interface:** `append(record) -> StoredRecord`; duplicate semantic ids, overwrite, post-save caller mutation, jurisdiction/source mismatch, stale replacement, and raw value export are rejected.

RED tests cover NAR official, JRA official, secondary scope, duplicate, alias mutation, and stale records. GREEN requires both focused tests and the package suite. Commit only after Sol confirms the fixture contains normalized non-sensitive example values derived from observed schema, not copied runner data.

## Task 7: HRA-3D actual coverage and cutoff audit

**Files:**
- Create: `apps/horse-racing-agent/src/horse_racing_agent/data_audit.py`
- Create: `apps/horse-racing-agent/tests/test_data_audit.py`

**Interface:** `audit_records(records, manifests) -> AuditReport` with coverage dates, row counts, duplicates, missingness, timestamp order, cutoff violations, odds snapshot freshness, settled-payback coverage, hashes, evidence class, allowed scope, and cash authorization.

RED tests reject missing manifests, future features, random ordering, duplicate races, and secondary-to-official promotion. GREEN accepts official JRA/NAR `REAL_PUBLIC_WEB_RECORD`; secondary remains `shadow_only`. No model task activates until actual chronological coverage and leakage audit pass.

## Task 8: HRA-3M cutoff-safe baseline, model, and backtest

**Slices:**

1. `features.py`, `model.py`, `test_model.py`: fixed pre-race cutoff features; market-implied probability baseline; win/place initial market; no post-race or late-odds leakage.
2. `backtest.py`, `test_backtest.py`: time-series walk-forward only; no random split; calibration; slippage stress; later-window holdout.

Required metrics: Brier score, log loss, ECE, realized ROI with confidence interval, max drawdown, bet/skip count, source coverage, and odds snapshot age. A challenger replaces the champion only when later-window evidence improves calibration and risk without violating cutoff or source gates.

## Task 9: HRA-4 live SHADOW decision and outcome ledger

**Files:**
- Create: `apps/horse-racing-agent/src/horse_racing_agent/decision.py`
- Create: `apps/horse-racing-agent/src/horse_racing_agent/ledger.py`
- Create: `apps/horse-racing-agent/tests/test_shadow_ledger.py`

Every eligible race produces `SHADOW` or `SKIP`. Decision records contain source/evidence, data time, cutoff odds, probability, confidence-adjusted EV, candidate, reason, threshold gap, model version, and immutable decision id. Outcome records arrive separately after official result/payback publication and never rewrite the decision. `NOT_PUBLISHED`, stale data, missing odds, and missing reconciliation are visible skips.

## Task 10: HRA-4b Japanese Telegram UX

**Files:**
- Create: `apps/horse-racing-agent/src/horse_racing_agent/telegram.py`
- Create: `apps/horse-racing-agent/tests/test_telegram.py`

Pre-race message: evidence label, jurisdiction/venue/race/start, action (`SHADOW`/`SKIP`), candidate, cutoff odds, probability/EV range, stake=`¥0` in SHADOW, freshness, concise Japanese reason, decision id.

Result message: placing, official payout/refund/void state, shadow stake/return/P&L, real P&L separately, model lesson, and reconciliation id.
Blocked message: exact missing source/permission/odds/payback reason and next retry time. Raw rows and credentials never appear.

## Task 11: HRA-5 CFO evidence adapter

**Files:**
- Create: `apps/horse-racing-agent/src/horse_racing_agent/cfo.py`
- Create: `apps/horse-racing-agent/tests/test_cfo.py`

`record_receipt(event)` is idempotent by official receipt id. Only `LIVE_CASH + official + settled` can become revenue/real P&L. SHADOW, synthetic, secondary-only, pending payback, deposits, withdrawals, and bank internal settlement never count as revenue. CFO-0c remains a dependency.

## Task 12: HRA-6 cash-enablement evidence gate

**Document-only research gate; PurchaseExecutor remains disabled.** Required evidence:

- source permission terms and the scope of `USER_ATTESTED_PERMISSION`;
- official/allowed ordering path and account eligibility;
- tax treatment and reporting boundary;
- credential isolation and owner-local-day spend cap;
- official purchase-history receipt, settlement receipt, refund/void handling;
- failure, timeout, duplicate-submit, and reconciliation behavior.

Permission to crawl does not equal permission to place a bet. No DOM-success receipt and no unsupported private ordering endpoint can pass this gate.

## Task 13: HRA-7 one minimum live transaction

**Blocked until every HRA-6 item passes.** At action time obtain the required confirmation for an irreversible debit from the user's account. Owner-local-day total stake is at most `¥100`, only with positive confidence-adjusted EV, fresh data, pre-message success, and deterministic idempotency key. Any uncertainty becomes SKIP. Martingale, chasing, auto-escalation, and repeated submit are forbidden.

Completion requires official purchase-history receipt plus settled payout/refund/void receipt and matching Telegram/CFO reconciliation. A browser success page alone is not completion.

## Task 14: HRA-8 evidence-driven scale and $10K review

No calendar-based stake increase. Promotion requires a statistically credible later window, positive net ROI confidence interval after costs/slippage, acceptable calibration, bounded max drawdown, bankroll survival, market capacity, source uptime, receipt reconciliation, and no policy breach.

`$10K/month` is a target to evaluate, not a promise. The scale report must show the required turnover and edge, best/base/worst results, capacity limit, probability of ruin, and the strongest reason to stop. If evidence does not support the target, the agent remains SHADOW or minimum-size rather than manufacturing activity.

## Close condition for every task

Luna executes the task's edits/commands. Sol verifies fresh outputs, source truth, diff scope, quarantine status, and acceptance. Each task closes only after focused/full verification, state-table update, commit, push to `origin` and `canonical`, fetch, and `local=origin=canonical`. Failure leaves the current item ACTIVE/BLOCKED; the next item does not start.
