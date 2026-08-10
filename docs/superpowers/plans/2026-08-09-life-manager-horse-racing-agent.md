# Life Manager Horse Racing Agent Official Free-Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mac-native zero-cost public-web ingestionでJRA公式primary recordとNAR公式zero-cost primary recordをsource authority付きで観測し、redacted evidence、observed schema、cutoff-safe model、SHADOW、CFO separationをReality Gate順に実装する。`race.netkeiba.com` / `nar.netkeiba.com` は公式情報の欠落時だけ使うPUBLIC_WEB_SECONDARY fallbackであり、公式recordやcash根拠へ昇格しない。

**Architecture:** Mac上でcrwlを公式HTML navigationに使い、binary ZIPはCRWLの`Page.goto: Download is starting`制限を記録したうえでcurlへ切り替える。HRA-2Fがhost、authority、permission、robots/terms、Mac-local raw境界を一つのingest gateで検証し、通過後にのみmanifest、observed schema、audit、model、SHADOWを進める。raw archive/CSV/PDFはMac-local append-onlyに留め、Git・Telegram・cloud・CFOへ出すのはredacted metadataだけにする。

**Tech Stack:** Python 3.12、pytest、`urllib.parse`、`hashlib`、標準ライブラリ中心のpure deterministic contracts、crwl、curl、Mac-local filesystem、redacted YAML/Markdown evidence。新しいpaid SDK、SaaS、public API、browser login、order transportは追加しない。

## Global Constraints

- 個人利用のみ。zero-cost public-web ingestionを許可し、raw page/rowのredistribution、public publication、SaaS化をしない。
- JRA primaryはofficial public pages。JRA robots snapshotは`User-agent:*`とempty `Disallow`、private use/citation境界を記録する。現時点のJRA actual result rowは12。
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
| 4 | HRA-2N NAR official free acquisition component | **complete** | commits `d22fff7ae..b67198e6`; focused 17/full 49 PASS |
| 5 | HRA-2R3 per-source index/gate | **complete** | commit `ab39e8546`; four independent lanes, no secondary promotion |
| 6 | HRA-2S observed schema/store | **complete** | commits `2feb29cfe` + `3f9f036f4`; focused 29/full 75 PASS |
| 7 | HRA-3D audit implementation | **complete; actual gate blocked** | commits `1426d4e23..05c03391c`; actual records 0, model_ready false |
| 7A | HRA-3C monthly NAR materialization probe | **complete; cutoff blocked** | commit `d4a2389ea`; 321 joined settled candidates, cutoff-safe records 0 |
| 7B | HRA-3C daily cutoff snapshot probe | **complete** | commits `3c003293d` + `9063ebfc6`; fixed win complete 7 races/76 runners |
| 7C1 | HRA-3C normalized market dimension | **complete** | commit `204d26e9e`; focused 37/full 119 PASS |
| 7C2 | HRA-3C win-market materializer | **complete** | commits `fb0038409` + `e8abb094c` + `72d152356`; actual 7/76 |
| 7D1 | HRA-3C official win outcome parser | **complete** | commit `0b5177452`; actual 321 outcomes/322 payouts |
| 7D2a | HRA-3D reject caller-declared settlement | **complete** | commit `8d344a97f`; production guard 2 LOC, full 148 PASS |
| 7D2b | HRA-3C current-day settlement capture | **ACTIVE-WAITING** for 2026-08-10 races to settle | target 7 race IDs, one fetch after final finish |
| 8 | HRA-3Ma/3Mb model and backtest | blocked by HRA-3C/3D actual gate | cutoff-safe odds and settled-payback contract |
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

**State:** COMPLETE. HRA-2F and both official source Reality Gates are complete; this task creates only the pure acquisition planner/classifier.

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

- [x] Step 1: Write RED tests proving URLs are discovered from official HTML, not permanently hardcoded to August 2026; binary endpoints use curl; HTML uses crwl; duplicate hashes return `UNCHANGED`; disabled odds links are omitted; empty/HTML/204 odds responses return `NOT_PUBLISHED`; raw and percent-encoded dot-segment traversal is rejected. URL validation is fail-closed at 4,096 raw path characters and 16 percent-decode rounds; input that exceeds either bound or has not stabilized within the decode bound is rejected.
- [x] Step 2: Run RED.

~~~sh
cd /Users/anicca/anicca-project/.worktrees/horse-racing-agent-spec/apps/horse-racing-agent
rtk python3.12 -m pytest tests/test_nar_source.py -q
~~~

- [x] Step 3: Implement the pure planner/classifier. Enforce HTTPS exact host `www.keiba.go.jp`, decoded path-segment safety with the 4,096-character/16-round fail-closed resource bound, one request per canonical URL, daily polling no faster than 2 minutes, monthly acquisition after the documented approximately 02:00 update, and case-normalized SHA-256 comparison. `previous_sha256` is the caller's prior hash for that request URL.
- [x] Step 4: Run focused and full GREEN; commit/push only the two files.

Runtime contract: crwl navigates Today/DataRoom/Monthly HTML. When crwl reports `Page.goto: Download is starting`, curl retrieves the linked ZIP. A disabled daily-odds link creates no fetch request; an empty/HTML/204 response from an attempted odds endpoint is `NOT_PUBLISHED`. Task 4 is pure and does not persist archives: Task 6 owns append-only identity `(source_url, normalized content_sha256)` and supplies the per-URL `previous_sha256`. Race data covers 1998-01 onward; odds cover 2026-03 onward. Payback remains pending until official settlement.

Completion evidence: commits `d22fff7ae..b67198e6`; final focused 17/full 49 tests PASS, compileall and diff-check PASS, local/origin/canonical parity PASS. Fresh Sol review found and Luna closed traversal, identity, cadence, publication-state, and resource-bound defects; scoped re-review is CLEAN. Cash authorization remains false.

## Task 5: HRA-2R3 per-source Reality Gate index

**State:** COMPLETE. This task indexes accepted evidence without fetching new records or upgrading unobserved secondary candidates.

**File:** create `docs/evidence/horse-racing/reality-gate-index.md`.

Create independent rows for JRA official, NAR official, JRA secondary fallback, and NAR secondary fallback. Each row carries its evidence class, URL, authority, jurisdiction, permission status, record counts, hash, schema status, allowed scope, cash authorization, gate state, and evidence link. JRA PASS never changes NAR; fallback never upgrades to official.

Verify with `git diff --check`, commit `docs(horse-racing): index public data reality gates`, and push both remotes.

Completion evidence: commit `ab39e8546`; exactly one index file, four independent lanes, official JRA/NAR `PASS_PRIVATE_SHADOW`, secondary candidates `NOT_OBSERVED`, `cash_authorized=false`, diff-check and local/origin/canonical parity PASS.

## Task 6: HRA-2S observed schema and append-only store

**State:** COMPLETE. The former quarantine files are adopted only after Sol verifies their content against the accepted source manifests and Reality Gate index.

**Files:**
- Modify/adopt: `apps/horse-racing-agent/src/horse_racing_agent/store.py`
- Modify/adopt: `apps/horse-racing-agent/tests/fixtures/normalized_races.json`
- Modify/adopt: `apps/horse-racing-agent/tests/test_store.py`

These are the current three untracked quarantine files. Luna must rewrite them from accepted manifest field names/raw types before adding them. Existing synthetic-only content is not evidence.

**Interface:** `append(record) -> StoredRecord`; duplicate semantic ids, overwrite, post-save caller mutation, jurisdiction/source mismatch, stale replacement, and raw value export are rejected.

**Normalized record contract:** exact top-level fields are `schema_version`, `record_id`, `event_id`, `race_id`, `source_url`, `source_authority`, `jurisdiction`, `evidence_class`, `allowed_scope`, `permission_document_verified`, `raw_values_exported`, `race_at`, `snapshot_at`, `cutoff_at`, `freshness`, `surface`, `track_condition`, and `runners`. Runner fields are exactly `runner_id`, `horse_number`, `odds`, and `body_weight_kg`. IDs are opaque non-empty strings; actual horse/person names are not stored. `odds` and `body_weight_kg` are either a finite positive number or `null=NOT_OBSERVED`; `surface` and `track_condition` are either a non-empty string or `null=NOT_OBSERVED`. Missing observation is never coerced to zero or an invented value. Timestamps are timezone-aware and ordered `snapshot_at <= cutoff_at <= race_at`. Freshness is `{status: fresh|stale, age_seconds: non-negative number}`.

Reuse the accepted `ingest._source_scope` exact HTTPS host/authority/jurisdiction mapping rather than adding another source registry. `REAL_PUBLIC_WEB_RECORD` requires official + `private_shadow`; `PUBLIC_WEB_SECONDARY` requires secondary + `shadow_only`; `SYNTHETIC_TEST` requires `test_only`. `permission_document_verified` must be boolean and `raw_values_exported` must be exactly false. This schema/store gate does not authorize cash.

`canonical_content_hash` excludes storage-only `record_id` and `event_id`, so the append identity is `(source_url, normalized content_sha256)` as established in Task 4. `AppendOnlyStore.append(record)` rejects duplicate `record_id`, duplicate `event_id`, duplicate source/hash identity, and for an existing `(jurisdiction, race_id)` rejects a snapshot whose `snapshot_at` is not strictly later. It deep-copies on append/get and exposes no overwrite/update method. `StoredRecord` returns only redacted ids/hash/source metadata, not the raw runner payload.

RED tests cover accepted NAR official and JRA official scope-contract examples, a correctly labeled secondary scope-contract example, source/jurisdiction/scope mismatch, `raw_values_exported=true`, nullable `NOT_OBSERVED` values versus invalid zero/non-finite values, deterministic hash excluding storage ids, duplicate ids/source-hash, caller/return alias mutation, and stale/equal snapshot replacement. The committed JSON fixture must itself be machine-labeled `SYNTHETIC_TEST` + `test_only`, use the exact accepted official source URLs, contain only normalized opaque test values, use `null` for unobserved content, and copy no horse/person/raw row. Tests may create ephemeral copies to exercise REAL/secondary source-scope branches, but must never persist or describe those copies as observed evidence. GREEN requires focused tests, the full package suite, compileall, diff-check, and exactly these three files. Target: one in-memory store, no DB/service/serialization layer, no new dependency, no extra file. Commit only after Sol confirms the fixture boundary.

Completion evidence: commits `2feb29cfe` + `3f9f036f4`; final focused 29/full 75 tests PASS, compileall/diff-check PASS, local/origin/canonical parity PASS. Fresh Sol review caught synthetic-to-real promotion; Luna changed committed fixtures to `SYNTHETIC_TEST/test_only`, nullable unobserved content, and accepted official URLs; scoped re-review is CLEAN. Cash authorization remains false.

## Task 7: HRA-3D actual coverage and cutoff audit

**State:** IMPLEMENTATION COMPLETE; ACTUAL GATE BLOCKED. Audit only accepted stored records/manifests; do not create or infer historical coverage.

**Files:**
- Create: `apps/horse-racing-agent/src/horse_racing_agent/data_audit.py`
- Create: `apps/horse-racing-agent/tests/test_data_audit.py`

**Interface:** `audit_records(records, manifests) -> AuditReport` with coverage dates, row counts, duplicates, missingness, timestamp order, cutoff violations, odds snapshot freshness, settled-payback coverage, hashes, evidence class, allowed scope, and cash authorization.

`AuditReport` is a frozen redacted dataclass with `coverage_start`, `coverage_end`, `record_count`, `race_count`, `duplicate_count`, `missingness`, `timestamp_ordered`, `cutoff_violations`, `max_odds_snapshot_age_seconds`, `settled_payback_rows`, `content_hashes`, `evidence_classes`, `allowed_scopes`, `cash_authorized`, `model_ready`, and `blockers`. It contains no runner values. A manifest is keyed by exact `source_url` and supplies `source_authority`, `jurisdiction`, `evidence_class`, `allowed_scope`, `parsed_row_count`, `content_sha256`, `settled_payback_rows`, `settled_race_ids`, and `cash_authorized`. `settled_race_ids` is a duplicate-free sequence of opaque race IDs actually covered by that source's official settled-payback evidence; its count cannot exceed `settled_payback_rows`.

Reuse `validate_normalized_race` and `canonical_content_hash`. Every record requires a matching manifest whose source authority, jurisdiction, evidence class, and allowed scope agree exactly. Input records must be ordered by `snapshot_at`; duplicate semantic snapshot `(jurisdiction, race_id, snapshot_at)` is rejected, while a strictly later snapshot of the same race is allowed. Any `snapshot_at > cutoff_at`, record timestamp beyond `race_at`, source/evidence promotion, missing manifest, invalid manifest hash/count/type, or pre-HRA-6 `cash_authorized=true` is rejected. Missingness counts `null` surface/track/odds/body weight; it never converts unknown to zero. Secondary stays `shadow_only` and can never make `model_ready=true` by itself.

`records=[]` with non-empty valid accepted manifests is a valid audit result, not an exception: coverage is `null`, counts are 0, `model_ready=false`, and blockers include `NO_NORMALIZED_ACTUAL_RECORDS`; official `settled_payback_rows=0` adds `NO_SETTLED_PAYBACK`; no official observed odds adds `NO_OBSERVED_ODDS`. Empty manifests are rejected. This is the current real execution and must be recorded after unit GREEN. `model_ready=true` requires at least two distinct official `REAL_PUBLIC_WEB_RECORD` race IDs at at least two distinct `race_at` timestamps; every included official race must be `fresh`, have at least one observed positive odds value, use a matching official manifest with `parsed_row_count>0`, and appear in that same manifest's `settled_race_ids`. Only official manifest payback rows count toward the report/readiness gate. Synthetic/secondary records or unused manifests can never supply odds, settlement, freshness, race count, or chronology for readiness. Zero cutoff violations and no blocker remain mandatory. This only unlocks model evaluation, not cash.

RED tests reject missing/empty/mismatched manifests, invalid or duplicate `settled_race_ids`, settlement count mismatch, future/leaking timestamps, random ordering, duplicate semantic snapshots, invalid hashes/counts, cash promotion, and secondary-to-official promotion. Explicit regressions prove that secondary odds/payback cannot unlock official readiness, same-time official races cannot satisfy chronology, unused manifest settlements cannot settle a record, and stale records or zero-row manifests remain blocked. GREEN mechanics may use only `SYNTHETIC_TEST/test_only` fixture records or ephemeral scope-contract copies explicitly marked not evidence. After focused/full GREEN, run the current actual audit with zero normalized records plus the two accepted official manifest summaries (`settled_race_ids=[]`) and persist only its redacted result in the Task 7 completion evidence. Expected current gate: `model_ready=false`; Task 8 remains blocked. No model task activates until a later actual chronological coverage and leakage audit passes.

Completion evidence: commits `1426d4e23..05c03391c`; final focused 36/full 111 tests PASS, compileall/diff-check PASS, local/origin/canonical parity PASS. Fresh Sol review counterexamples closed secondary/synthetic readiness, same-time chronology, unmatched settlement, stale/zero-row manifests, empty manifests, and per-official-race odds. Current actual audit is `records=0`, coverage `null`, `model_ready=false`, `cash_authorized=false`, with blockers `INSUFFICIENT_CHRONOLOGY`, `NO_NORMALIZED_ACTUAL_RECORDS`, `NO_OBSERVED_ODDS`, and `NO_SETTLED_PAYBACK`. Task 8 stays blocked.

## Task 7A: HRA-3C actual NAR materialization Reality Probe

**State:** COMPLETE — `BLOCKED_NO_CUTOFF_TIMESTAMP`. This is an evidence probe before parser implementation; Luna executes commands/evidence edits, Sol owns the follow-on parser plan.

**File:** create `docs/evidence/horse-racing/nar-normalized-materialization-probe.md` only. Raw artifacts stay outside Git under `/Users/anicca/Library/Application Support/Anicca/horse-racing/raw/nar/` with directory mode 700 and files mode 600.

Use CRWL on the official Today/Monthly navigation pages to discover the current daily/monthly race and odds links; use curl only for the official ZIP endpoints after recording CRWL's binary-download limitation. Fetch the current monthly race archive and current monthly odds archive, plus daily race archive only if needed for current publication status. Respect the documented cadence and do not loop/poll. Do not use remembered month-specific URLs when navigation provides the current links.

Inspect locally without exporting row values. Record only retrieval/effective timestamps, exact official URLs, HTTP/content type/bytes/SHA-256, archive entry names, encoding, header names/types, per-file and total data-row counts, distinct date/race-key counts, duplicate-key counts, earliest/latest dates, null/missing counts, whether odds keys join race/runner keys, whether payback keys join race keys, settled race-id count, and cutoff fields actually available before race start. No horse/person names, odds values, payouts, credentials, or raw rows enter Git/chat.

Gate outcomes are `PASS_MATERIALIZATION_PLAN`, `BLOCKED_NO_SETTLED_PAYBACK`, `BLOCKED_NO_JOIN_KEY`, `BLOCKED_NO_CUTOFF_TIMESTAMP`, or `BLOCKED_SOURCE`. HTTP/ZIP/schema success alone is not a normalized record. The probe must state the exact number of actual normalized records that can be constructed without invention; unknown is not zero. Cash/revenue/model readiness remain false. Verify evidence has no raw values, `git diff --check`, commit `docs(horse-racing): record NAR materialization probe`, push both remotes, and keep raw files private/non-Git.

Completion evidence: commit `d4a2389ea`; monthly race 494, runners 4805, odds 327274, payback rows 322, settled race IDs 321, race+odds+settled candidates 321. All joins are real, but monthly odds expose no row-level snapshot timestamp, so cutoff-safe normalized records are 0 and the gate is `BLOCKED_NO_CUTOFF_TIMESTAMP`. Raw directory/files are 700/600, local/origin/canonical parity PASS, cash/model/revenue false.

## Task 7B: HRA-3C one actual daily cutoff snapshot

**State:** ACTIVE. One bounded fetch only; no polling loop, parser code, model, or cash.

**File:** create `docs/evidence/horse-racing/nar-daily-cutoff-snapshot.md` only. Raw stays in the same Mac-private NAR directory with 700/600 modes and is never committed.

Use CRWL once on the official TodayRaceInfo page and discover the current daily race and daily odds controls/links from the page. Preserve disabled/not-published state. If enabled, invoke CRWL once per binary link to record the limitation, then curl each exact official ZIP once. The HTTP completion time in Asia/Tokyo is the snapshot timestamp for that archive; do not reuse the monthly retrieval time and do not infer per-row timestamps.

Parse locally and join only by observed official keys. Build each race's scheduled timestamp from official race date + `発走時刻` in Asia/Tokyo. Use a conservative fixed operational cutoff of scheduled start minus 10 minutes. A candidate is cutoff-safe only when the daily-odds HTTP completion timestamp is at or before that cutoff and at least one observed single-runner odds row joins the race/runner key. Past races, disabled/not-published odds, missing start time, missing runner join, non-positive/blank odds, and archive retrieval after cutoff remain excluded/blocked; do not replace unknown with zero.

Evidence records only redacted URLs/timestamps/hashes/schema/counts: future race count, pre-cutoff race count, joined single-runner key count, excluded counts by reason, and exact safely materializable race/runner counts. No odds values, names, payouts, or raw rows. A normalized market record must use one exact observed bet type and must cover every official horselist runner for that race with one unique positive odds row; cross-bet-type `single-runner` aggregates are candidates only. For v1 use exact `賭式=単勝`; incomplete markets are excluded, never silently drop a runner. Gate is one of `PASS_DAILY_CUTOFF_SNAPSHOT`, `NOT_PUBLISHED`, `BLOCKED_NO_FUTURE_RACE`, `BLOCKED_NO_JOIN_KEY`, or `BLOCKED_SOURCE`. Even PASS authorizes only parser implementation and later SHADOW data collection; model/cash/revenue stay false. Commit `docs(horse-racing): record NAR daily cutoff snapshot`, push both, verify modes/parity.

Post-probe aggregate correction: all single-runner bet types yielded 12 races/126 runner candidates, but bet types are not interchangeable. Exact positive `単勝` yielded 12 races/125 runners; only 7 races/76 runners had complete positive win-odds coverage for every horselist runner. Five races were incomplete with six total missing runners and zero extra odds keys. The evidence must present 7/76 as safely materializable v1 win records and retain 12/126 only as cross-bet-type candidates. Snapshot transport/cutoff gate remains `PASS_DAILY_CUTOFF_SNAPSHOT`; parser/model/cash remain blocked until this truth correction is committed.

Completion evidence: commits `3c003293d` + `9063ebfc6`; daily race/odds HTTP 200 real snapshot at 2026-08-10T10:46:23+09:00, all 46 races before start-minus-10-minute cutoff. Fixed `単勝` v1 has 7 complete races/76 runners; five incomplete races are excluded. Gate `PASS_DAILY_CUTOFF_SNAPSHOT`, raw 700/600, local/origin/canonical parity PASS, cash/model/revenue false.

## Task 7C1: HRA-3C normalized market dimension

**State:** COMPLETE. Sol defines the schema; Luna edits/tests only.

**Files:** modify only `store.py`, `tests/fixtures/normalized_races.json`, and `test_store.py`.

Add exact top-level field `market` with allowed normalized values `win` and `place`; fixtures remain `SYNTHETIC_TEST/test_only` and use `market=win`. `StoredRecord` exposes the redacted market string. Canonical content hash includes market. Append-only latest-snapshot identity becomes `(jurisdiction, race_id, market)`, so win/place records for the same race/snapshot may coexist, while stale/equal replacement within the same market remains rejected. Source/hash identity stays `(source_url, content_sha256)` and therefore also differs by market content.

RED tests cover missing/unknown market rejection, StoredRecord market output, deterministic hash changing by market, same-race same-time win/place coexistence, and same-market stale/equal rejection. No parser, place-odds claim, model, or cash behavior is added. Focused/full/compileall/diff-check, commit `feat(horse-racing): add normalized odds market`, push both/parity.

Completion evidence: commit `204d26e9e`; focused 37/full 119 PASS, compileall/diff-check PASS, exact three files, local/origin/canonical parity PASS. `market` is explicit in validation/hash/StoredRecord/latest-snapshot identity; no actual place record or cash behavior was created.

## Task 7C2: HRA-3C actual daily win materializer

**State:** ACTIVE. Parse the existing private daily archives into exact complete `market=win` records only.

**Files:** create only `src/horse_racing_agent/nar_materialize.py`, `tests/test_nar_materialize.py`, and `docs/evidence/horse-racing/nar-daily-materialized-records.md`.

**Interface:** `materialize_daily_win(race_zip_path, odds_zip_path, *, snapshot_at, expected_race_sha256, expected_odds_sha256, evidence_class) -> tuple[dict[str, object], ...]`. Paths must be explicit existing files; expected SHA-256 values are required and compared case-insensitively before parsing. Use stdlib `zipfile`, `csv`, `zoneinfo`, and `hashlib`; no pandas/database/new dependency. Reject more than 8 ZIP entries, path traversal/symlink entries, any member over 50 MB uncompressed, missing/duplicate required CSVs, non-UTF-8-BOM input, missing required headers, duplicate keys, malformed dates/HHMM/numbers, or input mutation.

Required observed headers are race `競馬場/競走年月日/レース番号/発走時刻/芝ダート区分/馬場`, horse `競馬場/競走年月日/レース番号/馬番/馬体重`, and odds `競馬場/競走年月日/レース番号/賭式/番号1/番号2/番号3/オッズ`. Join on the official race tuple and runner number. Market is exact `賭式=単勝`, with `番号1` nonblank and `番号2/番号3` blank, one unique finite positive odds row per official horselist runner. A race is excluded unless every horselist runner has exactly one such row and there is no extra odds runner key. It is also excluded unless `snapshot_at <= race_at - 10 minutes`.

Record mapping is deterministic and name-free: `race_id = nar-race- + sha256(venue/date/race_number)`, `runner_id = nar-runner- + sha256(race_id/horse_number)`, and record/event IDs hash race ID + `market=win` + snapshot timestamp + odds archive hash. `source_url` is the exact NAR daily odds URL; authority official, jurisdiction NAR, market win, actual run evidence `REAL_PUBLIC_WEB_RECORD/private_shadow`, permission document false, raw export false. `race_at` is official date+HHMM Asia/Tokyo, `cutoff_at=race_at-10m`, `snapshot_at` is HTTP completion, freshness is fresh/0 at acquisition. Surface/track preserve non-empty observed text or null; body weight is finite positive or null. Runners sort by horse number; records sort by race timestamp then opaque ID. Validate every output through `validate_normalized_race`; never include names/pedigree/jockey/trainer/owner/breeder/result fields.

Tests construct only ephemeral synthetic ZIPs under temp directories, pass `SYNTHETIC_TEST`, and never persist them as evidence. RED covers hash mismatch, ZIP safety/header/encoding, cutoff, exact win filter, duplicate odds, incomplete field exclusion, deterministic opaque IDs/order, market label, nullable weight, and absence of name/raw fields. Actual execution uses the private daily ZIP hashes `60c8fb659d6b31369453bf6121576d1af082ddc274e3380dd19e3135403d0135` and `feaa43d6bdaa019aa748a7ce05f527235647531bc90bfcc38fb0eadb5dc8c515`, snapshot `2026-08-10T10:46:23+09:00`; expected exact output is 7 records/76 runners. Then run `audit_records` with an official daily-odds manifest (`settled_payback_rows=0`, `settled_race_ids=[]`): expected `record_count=7`, `race_count=7`, official odds observed, `model_ready=false`, `NO_SETTLED_PAYBACK`, cash false. Evidence contains only hashes/counts/times/status, no IDs/names/odds/raw rows. Commit `feat(horse-racing): materialize daily win records`, push both/parity; model and cash stay blocked.

**REAL promotion boundary:** caller-supplied `evidence_class` plus caller-supplied hashes is not provenance. The module contains an accepted-real allowlist keyed by the exact tuple `(race_sha256, odds_sha256, snapshot_at)` from the committed Task 7B Reality Gate; currently it contains only the hashes/timestamp above. `REAL_PUBLIC_WEB_RECORD` is rejected unless the full tuple matches. Arbitrary conforming ZIPs remain `SYNTHETIC_TEST/test_only`; a future real snapshot needs its own accepted evidence update before promotion. For exact `単勝` rows, register the race+runner key and detect duplicate/extra keys before filtering blank/non-positive odds, so `0 + positive` duplicates and horselist-missing extra keys cannot disappear. Evidence wording must say private normalized records contain numeric odds (and possibly weight) while the committed redacted evidence/audit report exports none.

Completion evidence: commits `fb0038409` + `e8abb094c` + `72d152356`; final focused 13/full 132 PASS, compileall/diff-check PASS, fresh Sol re-review CLEAN, local/origin/canonical parity PASS. Exact accepted provenance produced 7 private records/76 runners; audit is 7/7, `model_ready=false`, `NO_SETTLED_PAYBACK`, cash false. Private records contain numeric odds/optional weight; Git evidence/AuditReport export none.

## Task 7D1: HRA-3C official win outcome parser

**State:** complete. Current-day target execution stays blocked until races settle.

**Files:** create `src/horse_racing_agent/nar_outcome.py`, create `tests/test_nar_outcome.py`, and modify `nar_materialize.py` only to expose deterministic `nar_race_id(venue,date,race_number)` and `nar_runner_id(race_id,horse_number)` helpers used by both parsers.

**Interface:** `materialize_nar_win_outcomes(race_zip_path, *, captured_at, expected_sha256, source_url, evidence_class) -> tuple[WinOutcome, ...]`. `WinOutcome` and nested `WinPayout` are frozen `repr=False` dataclasses; private fields are opaque race/runner IDs, market=`win`, status=`settled`, official source metadata, capture timestamp/hash, and one or more `(winner_runner_id, payout_yen_per_100)` items. No horse/person names. Public `redacted_summary(outcomes)` returns counts/hash/status only and never IDs/payout values.

Reuse the materializer ZIP safety/BOM/key parsing rather than creating a second permissive ZIP reader. Required horselist fields are race key + `馬番/着順`; payback fields are race key + `単勝組番/単勝払戻金（円）`. A payback row is settled only when winner number is digits-only positive and payout is a finite positive integer. Multiple rows for one race are allowed only for distinct winners (dead heat); exact duplicate/conflicting winner rows reject. For every settled race, the payback winner-number set must exactly equal the horselist rows with `着順=1`; missing/extra winner, missing horse join, duplicate horse key, or invalid payout rejects. Unsettled races with no payback are omitted, not zero-filled.

REAL promotion uses an accepted provenance allowlist. Initial accepted actual tuple is the committed monthly race URL/hash/capture from Task 7A: URL `https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=monthly&k_year=2026&k_month=8`, SHA `ca512328b477054738f0a926710c3c5c16b1e25d9f7e4ffaf7f9cfc9604c2149`, captured_at `2026-08-10T10:37:13+09:00`. Arbitrary self-hashed synthetic ZIPs cannot request REAL. Tests use ephemeral ZIPs and `SYNTHETIC_TEST`, covering normal/dead heat, unsettled omission, mismatch/duplicate/conflict, invalid payout/key, provenance, opaque deterministic IDs, repr/redacted leakage, ZIP/hash safety. Actual monthly execution must yield exactly 321 outcomes/322 winner-payout items with all joins complete, but it does not unlock the model because those monthly odds lack cutoff timestamps. Focused/full/compileall/diff-check, commit `feat(horse-racing): parse official win outcomes`, push both/parity; no current-day settlement, model, cash, Telegram, or CFO.

Completion evidence: commit `0b5177452`; TDD RED was the expected missing-helper import failure, focused 16/full 148/compileall/diff-check PASS, accepted private monthly ZIP produced the redacted aggregate 321 outcomes/322 winner-payout items/status settled, local/origin/canonical parity PASS, and fresh Sol review SHIP with no findings. The output parser does not unlock model or cash because this monthly odds source has no row-level cutoff timestamp.

## Task 7D2: HRA-3C current-day settlement capture

**State:** ACTIVE-WAITING. The unverified-manifest path is closed; actual capture waits on race completion.

### Task 7D2a: reject caller-declared settlement

**Ponytail result:** do not add a reconciler, new service, scheduler, or dependency. Existing `nar_outcome` is the sole parser and existing `audit_records` remains the audit. The current audit accepts caller-populated `settled_payback_rows/settled_race_ids` in an odds manifest without requiring parser-produced official outcome evidence; a fabricated dict can therefore make `model_ready=true`. Fail closed before adding the verified positive path.

**Files:** modify only `src/horse_racing_agent/data_audit.py` and `tests/test_data_audit.py`; estimated production change under 10 LOC and only the tests whose expected behavior changes. TDD RED proves the current implementation accepts a nonzero caller-declared settlement. GREEN adds one validation guard: every manifest must have `settled_payback_rows == 0` and empty `settled_race_ids`, otherwise raise `AuditRejected("settlement evidence is unverified")`. Rewrite the old synthetic test that claimed `model_ready=true` from manifest values into a rejection regression. Adjust only dependent tests so chronology/staleness/odds/row gates remain covered with zero settlement. Full suite, compileall, diff-check, fresh task review, commit `fix(horse-racing): reject unverified settlement`, push both/parity. This slice intentionally keeps `model_ready=false`; it adds no positive settlement API.

Completion evidence: commit `8d344a97f`; RED failed with expected `DID NOT RAISE`, GREEN focused 36/full 148/compileall/diff-check PASS, production diff 2 LOC, local/origin/canonical parity PASS, task review Spec ✅ / Quality ✅ / ship with no Critical or Important findings. One non-anchored test regex observation is deferred Minor and does not alter the exact production exception or gate behavior.

### Task 7D2b: actual current-day capture and verified positive path

**State:** ACTIVE-WAITING on external race completion. The seven 2026-08-10 cutoff-safe target races span 11:40–18:10 JST. Do not claim settlement or fetch before completion. At or after 18:20 JST, perform one official daily race-archive fetch with the existing fixed `curl` route. Write a unique private `.part`, require HTTPS success/HTTP 200/ZIP content type/nonempty archive/ZIP validation, record HTTP completion time and SHA-256, chmod 600, then atomically rename; never overwrite the morning archive. If all seven targets are not settled, record `NOT_ALL_TARGETS_SETTLED` and remain waiting without zero-fill or repeated polling.

Only after Sol observes the exact daily URL/SHA/captured-at tuple may Luna add that tuple to `nar_outcome`'s REAL allowlist. The RED is the actual daily parser call rejecting the previously unaccepted provenance; GREEN is the same call producing parser-backed outcomes. Add the smallest typed outcome input to `audit_records` so readiness is derived from accepted `WinOutcome` objects, never caller-declared manifest IDs. Require exact 7/7 target race-ID coverage, no extra target substitution, official/private-shadow provenance, and include the outcome source hash in the redacted audit evidence. Rerun the existing daily materializer from the immutable morning ZIPs, bind the accepted outcome objects, then require `record_count=7`, `race_count=7`, `settled_payback_rows >= 7`, no matching-settlement blocker, and cash false. This unlocks only Task 8 data work; it does not authorize Telegram advice or purchase.

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
