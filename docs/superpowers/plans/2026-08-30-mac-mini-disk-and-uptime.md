# Mac Mini Disk Reclamation & Permanent Uptime — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Free at least 60GB on the Mac Mini and keep Claude iOS Remote Control permanently connected, without a single Life Manager loop changing state.

**Architecture:** Every deletion is bracketed by a `loop-guard.sh` snapshot/diff pair that watches 100 lines of loop health (running set, non-zero exits, dangling release refs). A step that changes any of those lines is rolled back before the next step runs. Deletions proceed strictly outside-in by tier: unrelated software first, dead experiments second, core regenerables last.

**Tech Stack:** bash, launchd (`launchctl`), Homebrew, `du`/`lsof`/`df`.

**Read first:** `specs/MAC-MINI-INFRA.md` (the ledger: what is already deleted, what was spared and why, the 5-step deletion test). `~/.local/bin/loop-guard.sh` (the safety harness).

---

## Baseline (measured 2026-08-30)

| Metric | Value |
|---|---|
| Volume | `/System/Volumes/Data`, 228GB total |
| Free at session start | 1GB |
| Free now | 25GB |
| Target | **≥ 60GB free** |
| Loops running | 48 |
| Known pre-existing breakage | `ai.anicca.fundraiser` → missing release `20260827T205200-48c54b52` |

Confirmed **not** worth touching (measured, all tiny): `~/Downloads` 134M, `~/Documents` 92M, `~/Movies` 1M, `~/Desktop` 1M, `~/Pictures` 0M, `~/Music` 1M.

Invariant across every task: `~/.cloak`, `~/anicca-rtdash`, `~/anicca-monk-factory`, `**/memory/`, `**/state/*.jsonl`, `~/.config/ai/`, `~/.claude` transcripts are never touched.

---

## File Structure

| Path | Responsibility |
|---|---|
| `~/.local/bin/loop-guard.sh` | Snapshot/diff loop health. Already written and self-tested. |
| `~/.local/bin/disk-watchdog.sh` | Periodic automatic reclaim. Exists; Task 7 raises its floor. |
| `~/Library/LaunchAgents/com.anicca.disk-watchdog.plist` | Schedules the watchdog. Exists. |
| `specs/MAC-MINI-INFRA.md` | The ledger. Updated at the end of every task. |
| `~/.local/state/loop-guard/` | Snapshot storage. Created by the harness. |

---

## Task 1: Measure the last unmeasured regions

Nothing may be deleted from a region whose size is unknown — that is how the wrong thing gets deleted. Three regions remain unmeasured because `du` over them exceeded a 10-minute timeout.

**Files:**
- Create: `~/.local/state/loop-guard/measurements.txt`

- [ ] **Step 1: Measure `~/Library` one level deep, in the background**

`~/Library` timed out at 10 minutes in the foreground. Run it detached and collect later.

```bash
nohup bash -c 'du -sxm ~/Library/* 2>/dev/null | sort -rn | head -12' \
  > ~/.local/state/loop-guard/measure-library.txt 2>&1 &
echo started
```

- [ ] **Step 2: Measure the two system regions**

```bash
du -sxm /private/var/* 2>/dev/null | sort -rn | head -8
du -sxm /Library/* 2>/dev/null | sort -rn | head -8
```

Expected: totals near the earlier top-level figures (`/private/var` ≈ 6G, `/Library` ≈ 9G). If a single child holds most of it, that child is the Task 5 candidate.

- [ ] **Step 3: Collect the `~/Library` result**

```bash
cat ~/.local/state/loop-guard/measure-library.txt
```

Expected: 12 lines, largest first. `Caches` and `Application Support` are the usual leaders.

- [ ] **Step 4: Record all three into the ledger**

Append a "measured 2026-08-30" table to the `### ホームディレクトリ内訳` section of `specs/MAC-MINI-INFRA.md` with one row per region ≥ 500MB.

- [ ] **Step 5: Commit**

```bash
cd ~/Projects/life-manager
git add specs/MAC-MINI-INFRA.md
git commit -m "docs: measure the regions du could not finish in the foreground"
```

---

## Task 2: Tier 1 — `/Applications`

11GB remains after Adobe. Each app is judged by last-use date and whether a loop invokes it.

**Files:**
- Modify: `specs/MAC-MINI-INFRA.md`

- [ ] **Step 1: Snapshot loop health**

```bash
~/.local/bin/loop-guard.sh save apps
```

Expected: `saved /Users/anicca/.local/state/loop-guard/apps.txt (N lines)` where N ≈ 100.

- [ ] **Step 2: Get last-use date and size for every app ≥ 500MB**

```bash
du -sxm /Applications/* 2>/dev/null | sort -rn | head -15 | while read s a; do
  echo "${s}M  $(mdls -name kMDItemLastUsedDate -raw "$a" 2>/dev/null)  $a"
done
```

`(null)` means Spotlight holds no launch record — corroborate with Step 3 before trusting it.

- [ ] **Step 3: Check whether any loop invokes each candidate**

For each app whose date is `(null)` or older than 30 days, substitute its binary name for `<app>`:

```bash
grep -rl '<app>' ~/Library/LaunchAgents ~/loops/releases ~/.local/bin ~/.config 2>/dev/null | head -3
```

Empty output is the only result that permits deletion.

- [ ] **Step 4: Delete only the apps that passed both checks**

```bash
sudo rm -rf "/Applications/<name>.app"
[ -e "/Applications/<name>.app" ] && echo STILL_THERE || echo DELETED
df -g /System/Volumes/Data | awk 'NR==2{print "free="$4"G"}'
```

Known candidates from the measured list, each still requiring Step 3 to pass: `Google Chrome.app` (2G — CloakBrowser is the daily driver), `ChatGPT.app` (2G), `Openscreen.app`, `Koharu.app`, `LibreOffice.app`, `quarto`. **`Xcode-26.6.0.app` (4G) is excluded** — Life Manager builds for iOS.

- [ ] **Step 5: Verify no loop changed**

```bash
~/.local/bin/loop-guard.sh diff apps
```

Expected: `UNCHANGED — no loop was harmed`. On `CHANGED`, reinstall the app just deleted and stop.

- [ ] **Step 6: Record and commit**

Add one row per deleted app to the `### 削除済み（永久）` table with the evidence that justified it.

```bash
cd ~/Projects/life-manager
git add specs/MAC-MINI-INFRA.md
git commit -m "docs: record which applications went and what cleared them"
```

---

## Task 3: Tier 1 — Homebrew

17GB. `brew leaves` lists only formulae nothing else depends on, so removing a leaf can never orphan a dependent. `brew autoremove` then collects the dependencies the leaf was holding.

**Files:**
- Modify: `specs/MAC-MINI-INFRA.md`

- [ ] **Step 1: Snapshot loop health**

```bash
~/.local/bin/loop-guard.sh save brew
```

- [ ] **Step 2: List leaves ≥ 50MB with their loop usage**

```bash
brew leaves 2>/dev/null | while read f; do
  s=$(du -sxm /opt/homebrew/Cellar/$f 2>/dev/null | awk '{print $1}')
  [ -n "$s" ] && [ "$s" -ge 50 ] && \
    echo "${s}M $f uses=$(grep -rl "\b$f\b" ~/Library/LaunchAgents ~/loops/releases ~/.local/bin 2>/dev/null | wc -l | tr -d ' ')"
done | sort -rn
```

Measured leaves ≥ 50MB: `pandoc` 264M, `go` 258M, `semgrep` 238M, `mise` 138M, `trufflehog` 111M, `python@3.12` 83M, `postgresql@18` 83M, `livekit-cli` 83M, `node` 79M, `cmake` 76M, `cocoapods` 73M, `shellcheck` 67M, `fastlane` 63M, `node@22` 60M, `ffmpeg-full` 58M, `cliproxyapi` 56M.

- [ ] **Step 3: Uninstall only leaves with `uses=0`**

```bash
brew uninstall <formula> 2>&1 | tail -2
```

**Never uninstall regardless of the count:** `node`, `node@22`, `python@3.12`, `go`, `mise` (language runtimes the loops execute through), `cliproxyapi` (the proxy this session's model routing depends on), `ffmpeg-full` (the video skills call it).

- [ ] **Step 4: Collect orphaned dependencies**

```bash
brew autoremove 2>&1 | tail -5
df -g /System/Volumes/Data | awk 'NR==2{print "free="$4"G"}'
```

- [ ] **Step 5: Verify no loop changed**

```bash
~/.local/bin/loop-guard.sh diff brew
```

Expected: `UNCHANGED`. On `CHANGED`, `brew install <formula>` the last one removed and stop.

- [ ] **Step 6: Prove the toolchain still runs**

```bash
node --version && python3 --version && go version 2>/dev/null; echo "exit=$?"
```

Expected: three version strings.

- [ ] **Step 7: Record and commit**

```bash
cd ~/Projects/life-manager
git add specs/MAC-MINI-INFRA.md
git commit -m "docs: record the homebrew leaves removed and the runtimes kept"
```

---

## Task 4: Tier 1 — Stale release directories

`~/loops/releases` accumulates ~1.2GB per release. Task already run once (5 removed); this makes it repeatable as releases keep landing.

**Files:**
- Modify: `specs/MAC-MINI-INFRA.md`

- [ ] **Step 1: Snapshot loop health**

```bash
~/.local/bin/loop-guard.sh save releases
```

- [ ] **Step 2: List releases no plist references**

```bash
refs=$(cat ~/Library/LaunchAgents/*.plist 2>/dev/null | grep -oE 'releases/[0-9A-Za-z-]+' | sed 's|releases/||' | sort -u)
for r in $(ls ~/loops/releases 2>/dev/null); do
  echo "$refs" | grep -qx "$r" || echo "UNREFERENCED $r $(du -sxm ~/loops/releases/$r 2>/dev/null | awk '{print $1}')M"
done
```

- [ ] **Step 3: Exclude any release a process holds open**

```bash
for r in <unreferenced list>; do
  echo "$r open=$(lsof -n 2>/dev/null | grep -c "loops/releases/$r")"
done
```

Only `open=0` may be deleted. A release with `open=1` is in use even though no plist names it.

- [ ] **Step 4: Delete, keeping the newest unreferenced one as a rollback**

Releases are written read-only, so `sudo` is required.

```bash
sudo rm -rf ~/loops/releases/<old-unreferenced>
ls ~/loops/releases
df -g /System/Volumes/Data | awk 'NR==2{print "free="$4"G"}'
```

- [ ] **Step 5: Verify no loop changed and no reference dangles**

```bash
~/.local/bin/loop-guard.sh diff releases
```

Expected: `UNCHANGED`. The harness's `missing-release-refs` section catches a plist left pointing at a deleted release — the exact failure mode `ai.anicca.fundraiser` already sits in.

- [ ] **Step 6: Commit**

```bash
cd ~/Projects/life-manager
git add specs/MAC-MINI-INFRA.md
git commit -m "docs: record which releases aged out of the rotation"
```

---

## Task 5: Tier 1 — System caches outside the home directory

`/private/var` ≈ 6G and `/Library` ≈ 9G, sized precisely in Task 1.

**Files:**
- Modify: `specs/MAC-MINI-INFRA.md`

- [ ] **Step 1: Snapshot loop health**

```bash
~/.local/bin/loop-guard.sh save syscache
```

- [ ] **Step 2: Clear the regenerable system caches**

```bash
sudo rm -rf /Library/Caches/* 2>/dev/null
sudo rm -rf /private/var/folders/*/*/C/* 2>/dev/null
df -g /System/Volumes/Data | awk 'NR==2{print "free="$4"G"}'
```

`/Library/Caches` and the `C` (cache) subtrees of `/private/var/folders` are rebuilt on demand by macOS. **Do not touch** `/private/var/db`, `/private/var/log`, or the `T` (temp) subtrees — running processes hold state there.

- [ ] **Step 3: Verify no loop changed**

```bash
~/.local/bin/loop-guard.sh diff syscache
```

Expected: `UNCHANGED`. Clearing a cache a running process was mid-read on shows up here.

- [ ] **Step 4: Commit**

```bash
cd ~/Projects/life-manager
git add specs/MAC-MINI-INFRA.md
git commit -m "docs: record the system caches cleared and the state dirs spared"
```

---

## Task 6: Tier 2 — Dead experiments

Only entered after Tasks 2-5. Every candidate examined so far turned out to be live, so this task's default outcome is "nothing qualifies."

**Files:**
- Modify: `specs/MAC-MINI-INFRA.md`

- [ ] **Step 1: Snapshot loop health**

```bash
~/.local/bin/loop-guard.sh save tier2
```

- [ ] **Step 2: Run the full 5-step test on each remaining candidate**

For each of `~/.codex-acct2`, `~/.anicca`, `~/.rustup`, `~/.bun`, and any directory ≥ 2GB Task 1 newly surfaced:

```bash
t=<candidate>
echo "code refs: $(grep -rl "$t" ~/loops/releases ~/Projects ~/.local/bin ~/.config 2>/dev/null | wc -l | tr -d ' ')"
echo "plist refs: $(grep -l "$HOME/$t" ~/Library/LaunchAgents/*.plist 2>/dev/null | wc -l | tr -d ' ')"
echo "open files: $(lsof -n 2>/dev/null | grep -c "$t")"
```

All three must read `0`. A plist that references it counts as live **even when `launchctl` prints `not running`** — a `StartInterval` job is idle between runs, not dead. Confirm with:

```bash
launchctl print gui/$UID/<label> 2>/dev/null | grep -E 'state|runs ='
```

A non-zero `runs` count means the job has fired and is in service.

- [ ] **Step 3: Delete only candidates that scored 0/0/0**

```bash
sudo rm -rf ~/<candidate>
df -g /System/Volumes/Data | awk 'NR==2{print "free="$4"G"}'
```

- [ ] **Step 4: Verify no loop changed**

```bash
~/.local/bin/loop-guard.sh diff tier2
```

- [ ] **Step 5: Commit**

```bash
cd ~/Projects/life-manager
git add specs/MAC-MINI-INFRA.md
git commit -m "docs: record the tier 2 verdicts, including what stayed"
```

---

## Task 7: Raise the watchdog floor so the disk never fills again

The watchdog currently fires below 8GB. Once headroom is large, the floor should rise so it intervenes long before tools start failing.

**Files:**
- Modify: `~/.local/bin/disk-watchdog.sh` (the `MIN_GB` assignment)

- [ ] **Step 1: Raise the threshold to 25GB**

```bash
sed -i '' 's/^MIN_GB=8$/MIN_GB=25/' ~/.local/bin/disk-watchdog.sh
grep '^MIN_GB=' ~/.local/bin/disk-watchdog.sh
```

Expected: `MIN_GB=25`

- [ ] **Step 2: Run it and confirm it is a no-op above the floor**

```bash
~/.local/bin/disk-watchdog.sh
echo "exit=$?"
tail -3 ~/Library/Logs/disk-watchdog.log 2>/dev/null
```

Expected: `exit=0`. With free space above 25GB the script exits before pruning, so the log gains no new line.

- [ ] **Step 3: Prove it actually fires below the floor**

A guard that never runs is not a guard. Force the branch with a temporary threshold:

```bash
MIN_GB=999 bash -c 'sed "s/^MIN_GB=25$/MIN_GB=999/" ~/.local/bin/disk-watchdog.sh > /tmp/wd-test.sh; bash /tmp/wd-test.sh'
tail -3 ~/Library/Logs/disk-watchdog.log
rm -f /tmp/wd-test.sh
```

Expected: two new log lines, `free=NG below 999G — pruning` and `after prune free=NG`.

- [ ] **Step 4: Reload the agent so launchd runs the edited script**

```bash
launchctl kickstart -k gui/$UID/com.anicca.disk-watchdog
launchctl print gui/$UID/com.anicca.disk-watchdog | grep -E 'state|runs ='
```

Expected: `runs` incremented by at least 1.

- [ ] **Step 5: Commit**

```bash
cd ~/Projects/life-manager
git add specs/MAC-MINI-INFRA.md
git commit -m "docs: raise the watchdog floor now that headroom allows early intervention"
```

---

## Task 8: Final verification

- [ ] **Step 1: Confirm the disk target**

```bash
df -h /System/Volumes/Data | tail -1
```

Expected: available ≥ 60GB.

- [ ] **Step 2: Confirm every loop survived the whole run**

```bash
launchctl list 2>/dev/null | grep -E 'ai\.anicca|com\.anicca' | awk '$1 != "-"' | wc -l
```

Expected: ≥ 48, the count measured before any deletion.

- [ ] **Step 3: Confirm no new dangling release reference**

```bash
for p in ~/Library/LaunchAgents/*.plist; do
  for r in $(grep -oE "$HOME/loops/releases/[0-9A-Za-z-]+" "$p" 2>/dev/null | sort -u); do
    [ -d "$r" ] || echo "MISSING $(basename $p .plist)"
  done
done | sort -u
```

Expected: exactly one line, `MISSING ai.anicca.fundraiser` — the breakage that predates this work. Any second line is a regression this plan caused.

- [ ] **Step 4: Confirm Remote Control is still serving iOS**

```bash
launchctl print gui/$UID/com.anicca.claude-remote-control | grep -E 'state|pid ='
claude auth status | head -3
```

Expected: `state = running` with a pid, and `"loggedIn": true`.

- [ ] **Step 5: Prove Remote Control self-heals after a kill**

```bash
pid=$(launchctl print gui/$UID/com.anicca.claude-remote-control | awk '/pid =/{print $3}')
kill -9 "$pid"
sleep 20
launchctl print gui/$UID/com.anicca.claude-remote-control | grep -E 'state|pid ='
```

Expected: `state = running` with a **different** pid.

- [ ] **Step 6: Close out the ledger**

Update the `### 推移` table with the final free-space figure and mark Tasks 1-8 complete in section 8 of `specs/MAC-MINI-INFRA.md`.

```bash
cd ~/Projects/life-manager
git add specs/MAC-MINI-INFRA.md
git commit -m "docs: close out the cleanup with final free space and loop count"
```
