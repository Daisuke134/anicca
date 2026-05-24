---
name: xcode-build-analyzer
description: Analyze Xcode build logs — timing, warnings, errors, slow compiles, and build history from DerivedData.
homepage: https://clawhub.ai/alexissan/xcode-build-analyzer
metadata: {"clawdbot":{"emoji":"🔨","requires":{"bins":["plutil","gunzip","sqlite3"],"os":"darwin"}}}
---

# Xcode Build Analyzer

Analyze Xcode build performance, warnings, errors, and history by reading DerivedData build logs on macOS.

## Requirements

- **macOS only** — reads from `~/Library/Developer/Xcode/DerivedData/`
- **Xcode** must be installed and have built at least one project
- **plutil**, **gunzip**, **sqlite3** (all pre-installed on macOS)
- Full Disk Access may be required depending on the process running queries

## Key paths

```
DERIVED_DATA=~/Library/Developer/Xcode/DerivedData
```

Each project has a folder named `<ProjectName>-<hash>` containing:
- `info.plist` — project workspace path and last accessed date
- `Logs/Build/LogStoreManifest.plist` — structured index of all builds (timing, status, warnings, errors)
- `Logs/Build/*.xcactivitylog` — gzip-compressed SLF build logs with per-step timing and full compiler output

> **Important:** All queries are read-only. Never modify DerivedData contents.

## List all projects in DerivedData

```bash
for dir in ~/Library/Developer/Xcode/DerivedData/*-*; do
  [ -d "$dir" ] || continue
  NAME="$(basename "$dir" | sed 's/-[a-z]*$//')"
  WORKSPACE="$(plutil -extract WorkspacePath raw "$dir/info.plist" 2>/dev/null || echo "unknown")"
  LAST_ACCESS="$(plutil -extract LastAccessedDate raw "$dir/info.plist" 2>/dev/null || echo "unknown")"
  echo "$NAME | $WORKSPACE | Last accessed: $LAST_ACCESS"
done
```

## Build history for a project

Parse the `LogStoreManifest.plist` for structured build data. This is the most reliable source — it contains timing, error/warning counts, and scheme info for every build without needing to decompress logs.

```bash
# Replace PROJECT_DIR with the project's DerivedData folder
# To find it: ls ~/Library/Developer/Xcode/DerivedData/ | grep -i "ProjectName"
PROJECT_DIR="$(ls -d ~/Library/Developer/Xcode/DerivedData/PROJECT_NAME-* 2>/dev/null | head -1)"
MANIFEST="$PROJECT_DIR/Logs/Build/LogStoreManifest.plist"

plutil -convert json -o - "$MANIFEST" 2>/dev/null | python3 -c "
import json, sys
from datetime import datetime, timezone, timedelta

data = json.load(sys.stdin)
EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)
builds = []

for uid, log in data.get('logs', {}).items():
    start = log.get('timeStartedRecording', 0)
    stop = log.get('timeStoppedRecording', 0)
    duration = stop - start
    obs = log.get('primaryObservable', {})
    dt = EPOCH + timedelta(seconds=start)
    builds.append({
        'date': dt.strftime('%Y-%m-%d %H:%M'),
        'duration': f'{duration:.1f}s',
        'scheme': log.get('schemeIdentifier-schemeName', '?'),
        'status': obs.get('highLevelStatus', '?'),
        'errors': obs.get('totalNumberOfErrors', 0),
        'warnings': obs.get('totalNumberOfWarnings', 0),
        'analyzer': obs.get('totalNumberOfAnalyzerIssues', 0),
        'file': log.get('fileName', ''),
    })

builds.sort(key=lambda b: b['date'], reverse=True)
for b in builds:
    status = {'S': 'OK', 'W': 'Warnings', 'E': 'Error'}.get(b['status'], b['status'])
    print(f\"{b['date']}  {b['duration']:>8s}  {status:<10s}  {b['errors']}E {b['warnings']}W {b['analyzer']}A  [{b['scheme']}]\")
"
```

Replace `PROJECT_NAME` with the project name (case-insensitive grep match is fine).

**Status codes:** S = Succeeded, W = Succeeded with Warnings, E = Failed with Errors

## Latest build summary (all projects)

```bash
for dir in ~/Library/Developer/Xcode/DerivedData/*-*; do
  [ -d "$dir" ] || continue
  MANIFEST="$dir/Logs/Build/LogStoreManifest.plist"
  [ -f "$MANIFEST" ] || continue
  NAME="$(basename "$dir" | sed 's/-[a-z]*$//')"

  plutil -convert json -o - "$MANIFEST" 2>/dev/null | python3 -c "
import json, sys
from datetime import datetime, timezone, timedelta

data = json.load(sys.stdin)
EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)
name = '$NAME'
latest = None

for uid, log in data.get('logs', {}).items():
    start = log.get('timeStartedRecording', 0)
    if latest is None or start > latest[0]:
        latest = (start, log)

if latest:
    start, log = latest
    stop = log.get('timeStoppedRecording', 0)
    obs = log.get('primaryObservable', {})
    dt = EPOCH + timedelta(seconds=start)
    duration = stop - start
    status = {'S': 'OK', 'W': 'Warn', 'E': 'Err'}.get(obs.get('highLevelStatus', '?'), '?')
    print(f\"{name:<30s} {dt.strftime('%Y-%m-%d %H:%M')}  {duration:>6.1f}s  {status:<5s} {obs.get('totalNumberOfErrors',0)}E {obs.get('totalNumberOfWarnings',0)}W\")
" 2>/dev/null
done
```

## Extract warnings and errors from a build log

```bash
# Find the latest xcactivitylog for a project
PROJECT_DIR="$(ls -d ~/Library/Developer/Xcode/DerivedData/PROJECT_NAME-* 2>/dev/null | head -1)"
LATEST_LOG="$(ls -t "$PROJECT_DIR/Logs/Build/"*.xcactivitylog 2>/dev/null | head -1)"

# Extract warnings
gunzip -c "$LATEST_LOG" 2>/dev/null | strings | grep -E "\.swift:[0-9]+:[0-9]+: warning:" | sort -u

# Extract errors
gunzip -c "$LATEST_LOG" 2>/dev/null | strings | grep -E "\.swift:[0-9]+:[0-9]+: error:" | sort -u
```

## Warning summary (grouped by type)

```bash
PROJECT_DIR="$(ls -d ~/Library/Developer/Xcode/DerivedData/PROJECT_NAME-* 2>/dev/null | head -1)"
LATEST_LOG="$(ls -t "$PROJECT_DIR/Logs/Build/"*.xcactivitylog 2>/dev/null | head -1)"

gunzip -c "$LATEST_LOG" 2>/dev/null | strings \
  | grep -oE "warning: .*" \
  | sed 's/\[.*//; s/'"'"'[^'"'"']*'"'"'//g' \
  | sort | uniq -c | sort -rn | head -20
```

## Build step timing (find slow steps)

The xcactivitylog contains per-task `TaskMetrics` JSON with wall-clock duration in microseconds.

```bash
PROJECT_DIR="$(ls -d ~/Library/Developer/Xcode/DerivedData/PROJECT_NAME-* 2>/dev/null | head -1)"
LATEST_LOG="$(ls -t "$PROJECT_DIR/Logs/Build/"*.xcactivitylog 2>/dev/null | head -1)"

gunzip -c "$LATEST_LOG" 2>/dev/null | strings \
  | grep -o '{"wcDuration":[^}]*}' \
  | python3 -c "
import json, sys

tasks = []
for line in sys.stdin:
    try:
        m = json.loads(line.strip())
        tasks.append(m)
    except: pass

tasks.sort(key=lambda t: t.get('wcDuration', 0), reverse=True)
print(f'Total tasks: {len(tasks)}')
print(f'Top 10 slowest (wall-clock microseconds):')
for i, t in enumerate(tasks[:10]):
    wc = t['wcDuration']
    rss = t.get('maxRSS', 0)
    print(f'  {i+1}. {wc/1000:.1f}ms  (RSS: {rss/1024/1024:.1f}MB)')
"
```

## DerivedData disk usage

```bash
echo "Total DerivedData size:"
du -sh ~/Library/Developer/Xcode/DerivedData/ 2>/dev/null

echo ""
echo "Per project:"
for dir in ~/Library/Developer/Xcode/DerivedData/*-*; do
  [ -d "$dir" ] || continue
  NAME="$(basename "$dir" | sed 's/-[a-z]*$//')"
  SIZE="$(du -sh "$dir" 2>/dev/null | cut -f1)"
  echo "  $SIZE  $NAME"
done | sort -rh
```

## Clean DerivedData for a project

Only suggest this when the user explicitly asks. This deletes the build cache and will force a full rebuild.

```bash
# Replace PROJECT_NAME with the project name
PROJECT_DIR="$(ls -d ~/Library/Developer/Xcode/DerivedData/PROJECT_NAME-* 2>/dev/null | head -1)"
echo "Will delete: $PROJECT_DIR ($(du -sh "$PROJECT_DIR" 2>/dev/null | cut -f1))"
echo "Run: rm -rf \"$PROJECT_DIR\""
```

> **Warning:** Always confirm with the user before deleting. Suggest printing the size and path first.

## Build trend (all builds for a project over time)

```bash
PROJECT_DIR="$(ls -d ~/Library/Developer/Xcode/DerivedData/PROJECT_NAME-* 2>/dev/null | head -1)"
MANIFEST="$PROJECT_DIR/Logs/Build/LogStoreManifest.plist"

plutil -convert json -o - "$MANIFEST" 2>/dev/null | python3 -c "
import json, sys
from datetime import datetime, timezone, timedelta

data = json.load(sys.stdin)
EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)
builds = []

for uid, log in data.get('logs', {}).items():
    start = log.get('timeStartedRecording', 0)
    stop = log.get('timeStoppedRecording', 0)
    builds.append((start, stop - start))

builds.sort()
if builds:
    print(f'Builds tracked: {len(builds)}')
    durations = [d for _, d in builds]
    print(f'Fastest: {min(durations):.1f}s')
    print(f'Slowest: {max(durations):.1f}s')
    print(f'Average: {sum(durations)/len(durations):.1f}s')
    print(f'Median:  {sorted(durations)[len(durations)//2]:.1f}s')
    print()
    print('Timeline:')
    for start, dur in builds:
        dt = EPOCH + timedelta(seconds=start)
        bar = '█' * max(1, int(dur / max(durations) * 30))
        print(f'  {dt.strftime(\"%m/%d %H:%M\")}  {dur:>6.1f}s  {bar}')
"
```

## Concurrency issues (Swift 6 readiness)

Extract Swift concurrency warnings that will become errors in Swift 6:

```bash
PROJECT_DIR="$(ls -d ~/Library/Developer/Xcode/DerivedData/PROJECT_NAME-* 2>/dev/null | head -1)"
LATEST_LOG="$(ls -t "$PROJECT_DIR/Logs/Build/"*.xcactivitylog 2>/dev/null | head -1)"

gunzip -c "$LATEST_LOG" 2>/dev/null | strings \
  | grep -E "(data race|Sendable|actor-isolated|crossing into|concurrency)" \
  | grep "warning:" \
  | sort -u
```

## CLI builds (xcodebuild)

**Important:** `xcodebuild` CLI builds do **not** write to `LogStoreManifest.plist` or generate `.xcactivitylog` files unless you pass `-resultBundlePath`. This means the build history section above will only show Xcode IDE builds.

To detect CLI builds, check the build product timestamps and DerivedData info:

```bash
for dir in ~/Library/Developer/Xcode/DerivedData/*-*; do
  [ -d "$dir" ] || continue
  NAME="$(basename "$dir" | sed 's/-[a-z]*$//')"
  WORKSPACE="$(plutil -extract WorkspacePath raw "$dir/info.plist" 2>/dev/null || echo "unknown")"

  # Detect if this is a worktree build (workspace path outside main project dir, e.g. /tmp/)
  SOURCE=""
  PROJ_DIR="$(dirname "$WORKSPACE")"
  if [ -d "$PROJ_DIR" ] && git -C "$PROJ_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    BRANCH="$(git -C "$PROJ_DIR" branch --show-current 2>/dev/null)"
    IS_WORKTREE="$(git -C "$PROJ_DIR" rev-parse --is-inside-work-tree 2>/dev/null)"
    MAIN_WORKTREE="$(git -C "$PROJ_DIR" worktree list 2>/dev/null | head -1 | awk '{print $1}')"
    if [ "$PROJ_DIR" != "$MAIN_WORKTREE" ]; then
      SOURCE=" (worktree: $BRANCH @ $PROJ_DIR)"
    else
      SOURCE=" (branch: $BRANCH)"
    fi
  fi

  # Check Debug simulator product
  APP="$(ls -dt "$dir/Build/Products/Debug-iphonesimulator/"*.app 2>/dev/null | head -1)"
  if [ -n "$APP" ]; then
    MTIME="$(stat -f '%Sm' -t '%Y-%m-%d %H:%M' "$APP" 2>/dev/null)"
    VERSION=""
    PLIST="$APP/Info.plist"
    if [ -f "$PLIST" ]; then
      SHORT="$(plutil -extract CFBundleShortVersionString raw "$PLIST" 2>/dev/null)"
      BUILD="$(plutil -extract CFBundleVersion raw "$PLIST" 2>/dev/null)"
      VERSION=" v${SHORT}(${BUILD})"
    fi
    echo "$NAME | Last build: $MTIME |$VERSION | $(basename "$APP")$SOURCE"
  fi

  # Check Release product
  APP="$(ls -dt "$dir/Build/Products/Release-iphoneos/"*.app 2>/dev/null | head -1)"
  if [ -n "$APP" ]; then
    MTIME="$(stat -f '%Sm' -t '%Y-%m-%d %H:%M' "$APP" 2>/dev/null)"
    echo "$NAME | Last release: $MTIME | $(basename "$APP")$SOURCE"
  fi
done
```

> **Worktrees:** When building from a git worktree, Xcode creates a separate DerivedData entry (different hash) because the workspace path differs. The script above detects worktree builds by checking the git state of the workspace path and shows the branch name and worktree location.

### Combined build history (IDE + CLI)

To get a complete picture of all builds (both Xcode IDE and CLI), run both the LogStoreManifest parser and the build product check. The manifest gives detailed history for IDE builds; the product timestamps give the latest CLI build per configuration.

```bash
echo "=== IDE Builds (from LogStoreManifest) ==="
for dir in ~/Library/Developer/Xcode/DerivedData/*-*; do
  [ -d "$dir" ] || continue
  MANIFEST="$dir/Logs/Build/LogStoreManifest.plist"
  [ -f "$MANIFEST" ] || continue
  NAME="$(basename "$dir" | sed 's/-[a-z]*$//')"

  plutil -convert json -o - "$MANIFEST" 2>/dev/null | python3 -c "
import json, sys
from datetime import datetime, timezone, timedelta

data = json.load(sys.stdin)
EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)
name = '$NAME'

for uid, log in sorted(data.get('logs', {}).items(), key=lambda x: x[1].get('timeStartedRecording', 0), reverse=True):
    start = log.get('timeStartedRecording', 0)
    stop = log.get('timeStoppedRecording', 0)
    obs = log.get('primaryObservable', {})
    dt = EPOCH + timedelta(seconds=start)
    duration = stop - start
    status = {'S': 'OK', 'W': 'Warn', 'E': 'Err'}.get(obs.get('highLevelStatus', '?'), '?')
    scheme = log.get('schemeIdentifier-schemeName', '?')
    print(f'  {name:<25s} {dt.strftime(\"%Y-%m-%d %H:%M\")}  {duration:>6.1f}s  {status:<5s} [{scheme}]  (IDE)')
" 2>/dev/null
done

echo ""
echo "=== CLI Builds (from build products) ==="
for dir in ~/Library/Developer/Xcode/DerivedData/*-*; do
  [ -d "$dir" ] || continue
  NAME="$(basename "$dir" | sed 's/-[a-z]*$//')"
  for APP in "$dir/Build/Products/"*/*.app; do
    [ -d "$APP" ] || continue
    MTIME="$(stat -f '%Sm' -t '%Y-%m-%d %H:%M' "$APP" 2>/dev/null)"
    CONFIG="$(basename "$(dirname "$APP")")"
    echo "  $NAME  $MTIME  [$CONFIG]  $(basename "$APP")  (CLI)"
  done 2>/dev/null
done
```

## Notes

- `LogStoreManifest.plist` is the fastest way to get build history — no decompression needed
- `xcactivitylog` files are gzip-compressed SLF (Structured Log Format); use `gunzip -c` + `strings` for quick extraction
- Core Data timestamps: seconds since 2001-01-01 (`+ 978307200` to convert to Unix epoch)
- Build logs are kept until DerivedData is cleaned — Xcode may prune very old logs
- The `highLevelStatus` field: `S` = success, `W` = warnings, `E` = errors
- TaskMetrics `wcDuration` is in microseconds; `maxRSS` is in bytes
- All operations are **read-only** — never modify DerivedData while Xcode is running
