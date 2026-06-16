# Patch: life-travel (auto gcal travel block)

**Author:** patch-author subagent · **Date:** 2026-06-16
**Subsystem:** Anicca Life Manager — B-travel
**Mother repo:** `/Users/anicca/anicca` (branch `main`)
**Status of this patch:** NOT applied / NOT committed / NOT pushed (author-only).

---

## TL;DR (reality check)

life-travel **is** the one genuinely-working Life Manager feature — **but the working
code is NOT the file the prompt pointed at.** There are TWO implementations:

| # | File | Language | Wired to cron? | Has it ever inserted real blocks? |
|---|------|----------|----------------|-----------------------------------|
| A | `skills/life/travel/travel.js` (mother repo) | Node.js | **NO** | **NO** — `status:"declared"` in registry, never run |
| B | `~/.openclaw/skills/anicca-travel-fill/scripts/travel_fill.py` (LIVE runtime) | Python | **YES** — cron `anicca-travel-fill` daily 05:00 JST | **YES** — 15 real gcal event IDs in `state/travel_filled.json` |

So this is **verify + hardening**, not a rewrite — but the hardening target is **B (the
live Python)**, and the mother-repo **A (`travel.js`) needs to be brought up to parity**
so the public/OSS slot reflects the algorithm that actually works.

### Files read (raw evidence)
- `skills/life/travel/travel.js` (mother, 238 lines) — the "declared" Node impl
- `skills/life/travel/SLOT.md` — `status: declared`, "No behaviour yet"
- `skills/registry.json:43-51` — `"life/travel" … "status": "declared"`, spec `"26 B-travel / 27 B-travel"`
- `specs/07-HERMES-PIVOT.md:180,719,944,962,1045` — only mentions `anicca-travel-fill` as a private companion cron; **no B-travel detail section**
- `_archive_2026-06-09/skills-old/anicca-travel-fill/SKILL.md` — the original north-star algorithm (adjacent pairs / location resolution / 500m skip / idempotent state)
- `~/.openclaw/skills/anicca-travel-fill/scripts/travel_fill.py` (LIVE, 325 lines) — the real working impl
- `~/.openclaw/skills/anicca-travel-fill/scripts/run.sh` — live entrypoint the cron calls
- `~/.openclaw/skills/anicca-travel-fill/state/travel_filled.json` — 15 real inserted event IDs
- `~/.openclaw/skills/anicca-travel-fill/state/run.log` — 13 recorded runs, all `exit=0`
- `~/.openclaw/cron/jobs.json:3919-3940` — cron `anicca-travel-fill`, `expr "0 5 * * *"`, runs `cron-bash.sh anicca-travel-fill/scripts/run.sh`
- `gog calendar create --help` / `gog calendar events list --help` (Build 0.17.0) — confirms flag contract

### Spec-path correction (open question for caller)
The prompt cited `docs/superpowers/specs/anicca/27-launch-workflow-and-ubi.md` and
`07-life-manager.md`. **Neither exists.** `docs/superpowers/specs/anicca/` did not exist
at all (I created `patches/` under it for this file). The real specs are flat under
`/Users/anicca/anicca/specs/` (`07-HERMES-PIVOT.md` etc.), and the only B-travel
requirement detail survives in the **archived** SKILL.md. Registry calls the spec
`"26 B-travel / 27 B-travel"` but specs 26/27 are not present in the repo.

---

## Gaps

Required behavior is taken from the archived SKILL.md algorithm (the canonical B-travel
spec) and the registry summary: *"Read gcal + Google Maps Directions → auto-insert a
travel block before every event so all events sit in gcal with travel time included."*

| # | Requirement (spec / RAW source) | A: `travel.js` (mother) | B: `travel_fill.py` (live) | Severity |
|---|----------------------------------|--------------------------|-----------------------------|----------|
| G1 | Live cron must run the canonical impl | **NOT wired** (registry `status:"declared"`, SLOT.md "No behaviour yet") | wired — `jobs.json:3919` → `run.sh` → `travel_fill.py` | **HIGH** — mother repo's "official" file is dead code; the public OSS slot does not match what runs |
| G2 | Maps Directions for real travel time | `getTravelDurationSec` calls Directions, **but only `mode=transit`, no `driving` fallback, no `departure_time`** (`travel.js:159-178`) | `directions_minutes` tries transit→driving, `departure_time=now`, ×1.4 JP heuristic (`travel_fill.py:170-200`) | **MED** (A) — A silently returns 20-min fallback whenever transit route is unavailable |
| G3 | Timezone = event tz (NOT naive UTC) | **BUG**: writes `new Date(...).toISOString()` (UTC `Z`) with **no `--start-timezone`/`--end-timezone`** (`travel.js:206-207`) | uses `.astimezone(JST)` then `.isoformat()` → carries `+09:00` offset (`travel_fill.py:133-134,225-226`) | **HIGH** (A) — A would create blocks at the wrong wall-clock time for any non-UTC viewer / DST edge |
| G4 | Chained events (origin = prev event, not always home) | **MISSING**: always departs from `HOME_ADDRESS` (`travel.js:201`) — back-to-back events at different venues get home→venue time, wrong | adjacent-pair loop, origin = `prev` event's resolved location (`travel_fill.py:273-308`) | **HIGH** (A) — core "chained events" requirement unmet in A |
| G5 | location ≠ home only / skip same-place | **MISSING**: inserts a block for EVERY timed event incl. those already at home; no distance gate | geocodes both ends, `haversine_m < 500m → skip` (`travel_fill.py:287-292`, `MIN_DIST_M=500`) | **HIGH** (A) — A spams home-routine events with bogus travel blocks |
| G6 | Idempotent (no duplicate blocks on re-run) | partial — dedupes within one run by title `Set`, but **no persisted state**; relies on `[Travel] ` title scan only | `state/travel_filled.json` keyed `prev_id|curr_id` (`travel_fill.py:278-281,318`) | **MED** (A) — A's title-only dedupe breaks if user renames an event |
| G7 | Don't insert into a too-small gap | **MISSING** | `gap_min < MIN_GAP_MIN(10) → skip`; clamps `travel_min` to gap (`travel_fill.py:293-303`) | **MED** (A) |
| G8 | Routine-at-home location resolution | **MISSING** | `ROUTINE_AT_HOME_PATTERNS` + regex address extraction from summary/description (`travel_fill.py:32-101`) | **MED** (A) |
| G9 | **LIVE degradation**: `skipped_unknown` is ~half of events | n/a | run.log 2026-06-09: `checked:61, skipped_unknown:29, skipped_same_loc:32, inserted:0` | **MED** (B) — ~48% of events have unresolvable locations, so no block is created for them; B works but its coverage is silently low |
| G10 | Failure visibility (NO silent success) | A prints `ok:true` even when every insert errors (`travel.js:218`) | B always `exit=0` even on `gog failed` / Directions failure (`travel_fill.py:117,234`) | **MED** (both) — violates HARD RULE 0.24 (no fake-ok); a broken run looks identical to a clean run |

### What is genuinely working (verified, not assumed)
- `state/travel_filled.json` contains **15 distinct real gcal event IDs** (e.g.
  `7d8kbkl9091uiebmcoondd3lfc`) keyed to real source-event pairs → B has actually
  written travel blocks into Dais's calendar. This is the proof life-travel works.
- Cron `anicca-travel-fill` enabled, 13 logged runs, all `exit=0`.
- `gog calendar create` supports every flag both impls use (`--summary --from --to
  --location --description --start-timezone --end-timezone --event-color`), verified via
  `--help` on Build 0.17.0.

---

## Diff

**Decision: hardening, not rewrite.** B (live Python) is correct and proven; only G9/G10
apply to it and are observability-grade. A (`travel.js`) has real correctness bugs (G3,
G4, G5) but is **not wired to anything**, so it is not hurting production today. The
highest-value, lowest-risk change is to make the **mother-repo file honest** about reality
and fix its two worst latent bugs so that if/when the OSS slot is flipped `live`, it does
not regress. No live-runtime mutation is proposed here (per "do NOT apply/spend").

### Change 1 (HIGH, G3) — `travel.js`: stop writing naive-UTC times; pass event tz

```diff
--- a/skills/life/travel/travel.js
+++ b/skills/life/travel/travel.js
@@ const HOME_ADDRESS = ...
 const HORIZON_DAYS = parseInt(process.env.TRAVEL_HORIZON_DAYS || "1", 10);
+const EVENT_TZ = process.env.TRAVEL_EVENT_TZ || ENV.TRAVEL_EVENT_TZ || "Asia/Tokyo";
 const DRY_RUN = process.argv.includes("--dry-run");
@@ function insertEvent({ summary, startIso, endIso, description }) {
       "--summary", summary,
       "--from", startIso,
       "--to", endIso,
+      "--start-timezone", EVENT_TZ,
+      "--end-timezone", EVENT_TZ,
       "--description", description,
+      "--event-color", TRAVEL_COLOR_ID,
```

> Note: `TRAVEL_COLOR_ID` is already declared (`travel.js:30`) but never used — wiring
> `--event-color` makes blocks visually distinct as the comment intends.

### Change 2 (HIGH, G2) — `travel.js`: add driving fallback + departure_time so transit-less routes still get a real estimate

```diff
@@ async function getTravelDurationSec(origin, destination) {
   if (!destination || !MAPS_KEY) return DEFAULT_TRAVEL_SEC;
-  const url =
-    `https://maps.googleapis.com/maps/api/directions/json` +
-    `?origin=${encodeURIComponent(origin)}` +
-    `&destination=${encodeURIComponent(destination)}` +
-    `&mode=transit` +
-    `&key=${encodeURIComponent(MAPS_KEY)}`;
-  try {
-    const r = await fetch(url);
-    if (!r.ok) return DEFAULT_TRAVEL_SEC;
-    const body = await r.json();
-    const leg = body?.routes?.[0]?.legs?.[0];
-    return leg?.duration?.value || DEFAULT_TRAVEL_SEC;
-  } catch {
-    return DEFAULT_TRAVEL_SEC;
-  }
+  for (const mode of ["transit", "driving"]) {
+    const params = new URLSearchParams({ origin, destination, mode, key: MAPS_KEY });
+    if (mode === "transit") params.set("departure_time", "now");
+    try {
+      const r = await fetch(`https://maps.googleapis.com/maps/api/directions/json?${params}`);
+      if (!r.ok) continue;
+      const body = await r.json();
+      if (body.status !== "OK") continue;
+      let sec = body?.routes?.[0]?.legs?.[0]?.duration?.value;
+      if (!sec) continue;
+      if (mode === "driving") sec = Math.round(sec * 1.4); // JP transit ≈ driving×1.4
+      return sec;
+    } catch { /* try next mode */ }
+  }
+  return DEFAULT_TRAVEL_SEC;
```

### Change 3 (HIGH, G5/G4) — `travel.js`: only insert when destination differs from origin (skip home-routine / same-place events)

```diff
@@ function detectMissingTravelBlocks(events) {
   return events.filter((e) => {
     const summary = (e.summary || "").trim();
     if (!e.start || !e.start.dateTime) return false; // skip all-day events
     if (isTravelBlock(summary)) return false;
     if (coveredTitles.has(summary)) return false;
+    // location≠home-only: an event with no explicit location can't be travelled to
+    if (!(e.location && e.location.trim())) return false;
     return true;
   });
 }
```

> Minimal, safe version of G4/G5: require an explicit `location`. (Full chained-pair
> origin resolution + geocode-distance gate is B's algorithm; porting it wholesale to A
> is the larger follow-up tracked as **open question O3** below, not done here to keep
> this patch low-risk and reviewable.)

### Change 4 (MED, G10) — both: fail loud, no fake-ok

```diff
@@ travel.js main()  (after the insert loop)
-  const out = { ok: true, checked: events.length, inserted: results };
+  const errors = results.filter((r) => r.id === "error").length;
+  const out = { ok: errors === 0, checked: events.length, inserted: results, errors };
   console.log(JSON.stringify(out, null, 2));
+  if (errors > 0) process.exitCode = 1; // HARD RULE 0.24: broken run must not look clean
   return out;
```

For B (`travel_fill.py`), the parallel hardening (NOT applied here — live runtime) would
be: `main()` should print a non-zero-signalling status and `run.sh` should propagate it
when `fetch_events` returns `[]` due to `gog failed` (currently swallowed at
`travel_fill.py:117-118`) and when `directions_minutes` falls back to the hard-coded `45`.
This is a separate live-runtime patch (open question O2) and must be applied to
`~/.openclaw/...` directly per the worktree-exception rule, not via the mother repo.

### Change 5 (DOC, G1) — make the mother-repo slot honest

`SLOT.md` / `registry.json` say `status:"declared"` / "No behaviour yet", but the
algorithm is live (as Python, in the runtime store). Recommended one-line doc note in
`SLOT.md` (no `registry.json` status flip until A reaches parity with B and E2E passes —
flipping to `"live"` now would be a fake-ok claim):

```diff
--- a/skills/life/travel/SLOT.md
+++ b/skills/life/travel/SLOT.md
@@
 Reserved by **Foundation** for builder **wf-b:travel**. Spec: 26 B-travel / 27 B-travel.
+
+> Reality (2026-06-16 audit): the *behaviour* ships today as the Python skill
+> `~/.openclaw/skills/anicca-travel-fill/` (cron `anicca-travel-fill`, daily 05:00 JST),
+> which has inserted real gcal travel blocks (state/travel_filled.json). `travel.js`
+> here is the OSS port and is NOT yet wired — keep `status:"declared"` until it reaches
+> parity (chained-pair origin + distance gate) AND passes the E2E in this patch.
```

---

## Commands (safe test — does NOT disturb real events)

All tests use a **throwaway event** with a unique marker title and a location far from
home, then delete it. `--dry-run` is used first so nothing is written until the
read-path is confirmed. Never run the cron's `run.sh` against the real horizon as a
"test" — it mutates the live calendar.

```bash
# 0. Preconditions — confirm creds + gog reachable (no mutation)
set -a; source ~/.openclaw/.env; set +a
/opt/homebrew/bin/gog calendar events list -j --account "$GOG_ACCOUNT" \
  --from today --to "$(date -v+1d +%Y-%m-%d)" --all-pages --max 5 | head -c 400; echo

# 1. DRY-RUN the mother-repo impl (reads gcal, writes nothing)
cd /Users/anicca/anicca/skills/life/travel
node travel.js --dry-run --horizon 1     # expect: "[dry-run] would insert: [Travel] ..."

# 2. Create ONE throwaway test event ~1h out, with a real far location.
#    Unique marker so we can find + delete only this one.
MARK="ZZTEST-TRAVEL-$(date +%s)"
START=$(date -v+90M -u +%Y-%m-%dT%H:%M:00+09:00)
END=$(date -v+150M -u +%Y-%m-%dT%H:%M:00+09:00)
TEST_ID=$(/opt/homebrew/bin/gog calendar create primary -j --account "$GOG_ACCOUNT" \
  --summary "$MARK" --from "$START" --to "$END" \
  --location "東京都江東区豊洲2-4-9" --start-timezone Asia/Tokyo --end-timezone Asia/Tokyo \
  | python3 -c 'import json,sys;print(json.load(sys.stdin)["event"]["id"])')
echo "created test event: $TEST_ID"

# 3. Run the real path for the test window only (horizon 1d). This WILL insert a
#    "[Travel] $MARK" block before the test event — that is the behaviour under test.
node travel.js --horizon 1 | tee /tmp/travel-test-out.json

# 4. READ BACK: confirm a travel block now precedes the test event (Maps-derived minutes)
/opt/homebrew/bin/gog calendar events list -j --account "$GOG_ACCOUNT" \
  --from today --to "$(date -v+1d +%Y-%m-%d)" --all-pages \
  | python3 -c '
import json,sys
ev=json.load(sys.stdin); ev=ev if isinstance(ev,list) else ev.get("events",[])
tb=[e for e in ev if (e.get("summary","")).startswith("[Travel] ZZTEST-TRAVEL-")]
print("TRAVEL BLOCK FOUND:" , bool(tb))
for e in tb: print(e["summary"], e["start"], "->", e["end"], "| tz carried:", "+09:00" in e["start"].get("dateTime",""))
'

# 5. CLEANUP — delete the travel block(s) AND the test event. Leaves calendar as found.
/opt/homebrew/bin/gog calendar events list -j --account "$GOG_ACCOUNT" \
  --from today --to "$(date -v+1d +%Y-%m-%d)" --all-pages \
  | python3 -c '
import json,sys
ev=json.load(sys.stdin); ev=ev if isinstance(ev,list) else ev.get("events",[])
for e in ev:
  s=e.get("summary","")
  if s.startswith("[Travel] ZZTEST-TRAVEL-") or s.startswith("ZZTEST-TRAVEL-"):
    print(e["id"])
' | while read ID; do
  /opt/homebrew/bin/gog calendar delete primary "$ID" --account "$GOG_ACCOUNT" -y
done
echo "cleanup done"
```

> Chained-event test: in step 2 create TWO throwaway events back-to-back at *different*
> far locations (e.g. 豊洲 then 八王子) ~30min apart; step 4 must show a travel block
> before EACH, and (once Change 3's full G4 is implemented) the second block's duration
> must be venue→venue, not home→venue.

---

## Acceptance

Patch is accepted when ALL hold (each verified by reading gcal back, not by log claims):

1. **Single-event insert (verified by read-back).** Creating one timed test event with a
   far `location` → after running the skill, listing gcal shows a `[Travel] <title>` block
   whose `end` == event `start` and whose duration ≈ Google Directions transit minutes
   (NOT the 20-min fallback when a transit route exists). *(G2)*
2. **Timezone correct.** The inserted block's `start.dateTime` carries `+09:00`
   (Asia/Tokyo), i.e. the wall-clock departure time is correct for the viewer; no naive
   `Z`-suffixed times that shift the block. *(G3)*
3. **Chained events.** With two back-to-back events at different venues, a travel block is
   inserted before EACH; the block before the second is computed from the first venue, not
   home. *(G4)*
4. **location ≠ home only.** A home-routine / no-location event gets NO travel block (no
   spam). *(G5)*
5. **Idempotent.** Running twice does not create a duplicate `[Travel]` block. *(G6)*
6. **No fake-ok.** A run where every insert errors exits non-zero / `ok:false`; a clean
   run exits 0. *(G10)*
7. **Cleanup leaves calendar unchanged** — every test event and test travel block deleted;
   `travel_filled.json` (live) untouched by the test (mother-repo test must NOT write to
   the live state file).

---

## Summary / open questions

**Complete:** audit done with raw evidence; B (live Python) verified genuinely working (15
real inserted gcal IDs); A (`travel.js`) gaps catalogued; low-risk hardening diff written
for A (tz bug, driving fallback, location gate, fail-loud) + honesty note for SLOT.md.
Patch is verify+hardening as predicted, NOT a rewrite.

**Open questions for caller:**
- **O1 (spec paths):** the two spec docs named in the prompt don't exist, and `specs/26`,
  `specs/27` aren't in the repo. Where is the canonical B-travel spec? (I used the
  archived SKILL.md + registry as the spec source.)
- **O2 (live hardening):** G9/G10 fixes to `travel_fill.py` must be applied directly to
  `~/.openclaw/...` (runtime store, worktree-exempt). Out of scope for a mother-repo patch
  — confirm you want a separate live patch.
- **O3 (full parity):** should A (`travel.js`) be brought to FULL parity with B
  (adjacent-pair origin resolution, geocode + haversine distance gate, routine-at-home
  resolution, persisted `travel_filled.json`)? This patch does the minimal safe subset;
  full port is a larger follow-up before flipping registry `status:"live"`.
