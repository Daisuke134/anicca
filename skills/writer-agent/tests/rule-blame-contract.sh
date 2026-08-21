#!/usr/bin/env bash
# Contract for the rule-blame accumulator (spec 47 section 19-4a).
#
# NO LIVE NETWORK, NO MODEL CALLS: every check imports the module and drives
# its pure functions with inline beat-rate-shaped fixtures.
set -uo pipefail

SCRIPT_DIR="${ARTICLE_SKILL_DIR:-$HOME/profitable-claude/skills/writer-agent}/scripts"
PY=/opt/homebrew/bin/python3
command -v "$PY" >/dev/null 2>&1 || PY=python3
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0
FAIL=0

check() {
  local name="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    PASS=$((PASS + 1))
    printf 'ok   %s\n' "$name"
  else
    FAIL=$((FAIL + 1))
    printf 'FAIL %s (expected %s got %s)\n' "$name" "$expected" "$actual"
  fi
}

pyrun() {
  PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}" "$PY" -c "$1" 2>"$TMP/stderr"
}

# 1. A run with selection_inverted false records cleans, not losses.
OUT1="$(pyrun '
import rule_blame as rb
data = {
    "run_id": "run-1", "lang": "ja", "chosen_beat_rate": 0.7, "selection_inverted": False,
    "candidates": [
        {"title": "Chosen", "role": "chosen", "cited_rule": None, "beat_rate": 0.7},
        {"title": "Rej1", "role": "rejected", "cited_rule": "SKILL.md:10", "beat_rate": 0.6},
        {"title": "Rej2", "role": "rejected", "cited_rule": "SKILL.md:20", "beat_rate": 0.65},
    ],
}
obs = rb.observations_from_run(data, ts="2026-07-26T00:00:00Z")
verdicts = sorted(o["verdict"] for o in obs)
print(len(obs), verdicts == ["clean", "clean"])
')"
check "non-inverted run yields one observation per rejection" "2" "$(echo "$OUT1" | awk '{print $1}')"
check "non-inverted run's observations are all clean, no losses" "True" "$(echo "$OUT1" | awk '{print $2}')"

# 2. Magnitude is the difference between rejected and chosen beat rates; a
#    rejected candidate that did NOT beat chosen (even in an inverted run)
#    gets no observation at all.
OUT2="$(pyrun '
import rule_blame as rb
data = {
    "run_id": "run-2", "lang": "ja", "chosen_beat_rate": 0.5, "selection_inverted": True,
    "candidates": [
        {"title": "Chosen2", "role": "chosen", "cited_rule": None, "beat_rate": 0.5},
        {"title": "RejWin", "role": "rejected", "cited_rule": "SKILL.md:99", "beat_rate": 0.9},
        {"title": "RejLose", "role": "rejected", "cited_rule": "SKILL.md:88", "beat_rate": 0.3},
    ],
}
obs = rb.observations_from_run(data, ts="t")
print(len(obs), obs[0]["verdict"], obs[0]["cited_rule"], round(obs[0]["magnitude"], 4))
')"
check "inverted run yields exactly one observation (only the winner)" "1" "$(echo "$OUT2" | awk '{print $1}')"
check "that observation is a loss" "loss" "$(echo "$OUT2" | awk '{print $2}')"
check "the loss is cited against the winning rejection's rule" "SKILL.md:99" "$(echo "$OUT2" | awk '{print $3}')"
check "magnitude is rejected_beat_rate minus chosen_beat_rate (0.9-0.5)" "0.4" "$(echo "$OUT2" | awk '{print $4}')"

# 3. The same observation collected twice does not duplicate (idempotency
#    key: run_id, lang, cited_rule, rejected_title).
OUT3="$(pyrun '
import rule_blame as rb
from pathlib import Path
data = {
    "run_id": "run-3", "lang": "en", "chosen_beat_rate": 0.4, "selection_inverted": True,
    "candidates": [
        {"title": "Chosen3", "role": "chosen", "cited_rule": None, "beat_rate": 0.4},
        {"title": "RejWin3", "role": "rejected", "cited_rule": "SKILL.md:50", "beat_rate": 0.8},
    ],
}
obs = rb.observations_from_run(data, ts="t")
path = Path("'"$TMP"'/rule-blame.jsonl")
w1, d1 = rb.append_observations(path, obs)
w2, d2 = rb.append_observations(path, obs)
lines = len(path.read_text(encoding="utf-8").splitlines())
print(w1, d1, w2, d2, lines)
')"
check "first collect writes the one observation" "1" "$(echo "$OUT3" | awk '{print $1}')"
check "first collect has 0 duplicates" "0" "$(echo "$OUT3" | awk '{print $2}')"
check "second collect writes 0 new observations" "0" "$(echo "$OUT3" | awk '{print $3}')"
check "second collect reports the observation as duplicate" "1" "$(echo "$OUT3" | awk '{print $4}')"
check "the ledger file still has exactly 1 line" "1" "$(echo "$OUT3" | awk '{print $5}')"

# 4. The report ranks by total loss magnitude and shows cleans alongside --
#    a rule with one bad day must not look the same as one that is
#    consistently wrong.
OUT4="$(pyrun '
import rule_blame as rb

observations = [
    # SKILL.md:AAA: one big loss, no cleans -- one bad day.
    {"run_id": "r1", "lang": "ja", "cited_rule": "SKILL.md:AAA", "verdict": "loss",
     "magnitude": 0.9, "rejected_title": "x", "chosen_title": "y"},
    # SKILL.md:BBB: two small losses -- consistently a little wrong.
    {"run_id": "r2", "lang": "ja", "cited_rule": "SKILL.md:BBB", "verdict": "loss",
     "magnitude": 0.3, "rejected_title": "x", "chosen_title": "y"},
    {"run_id": "r3", "lang": "ja", "cited_rule": "SKILL.md:BBB", "verdict": "loss",
     "magnitude": 0.3, "rejected_title": "x2", "chosen_title": "y2"},
    # SKILL.md:CCC: clean only, no losses at all -- reliably right.
    {"run_id": "r4", "lang": "ja", "cited_rule": "SKILL.md:CCC", "verdict": "clean",
     "magnitude": 0.0, "rejected_title": "x3", "chosen_title": "y3"},
]
rows = rb.aggregate_by_rule(observations)
order = [r["cited_rule"] for r in rows]
ccc = next(r for r in rows if r["cited_rule"] == "SKILL.md:CCC")
aaa = next(r for r in rows if r["cited_rule"] == "SKILL.md:AAA")
print(order[0], ccc["losses"], ccc["cleans"], round(aaa["total_magnitude"], 4))
table = rb.format_report_table(rows, 10)
print("SKILL.md:CCC" in table and "SKILL.md:AAA" in table)
')"
check "the rule ranked #1 is the one with the highest total loss magnitude" "SKILL.md:AAA" "$(echo "$OUT4" | head -1 | awk '{print $1}')"
check "a clean-only rule shows 0 losses" "0" "$(echo "$OUT4" | head -1 | awk '{print $2}')"
check "a clean-only rule shows its 1 clean observation" "1" "$(echo "$OUT4" | head -1 | awk '{print $3}')"
check "AAA's total_magnitude is its single loss (0.9)" "0.9" "$(echo "$OUT4" | head -1 | awk '{print $4}')"
check "the printed table includes both the clean-only and loss rules" "True" "$(echo "$OUT4" | tail -1)"

# 5. `collect` with an explicit --ledger leaves the REAL default ledger
#    (state/rule-blame.jsonl) untouched -- the round-2 defect: pointing
#    --state-root at a scratch dir used to silently deposit scratch
#    observations into production state.
OUT5="$(pyrun '
import contextlib
import io
import json
from pathlib import Path

import rule_blame as rb

# Snapshot the actual production default ledger before touching anything.
default_ledger = rb._default_ledger_path()
before = default_ledger.read_bytes() if default_ledger.exists() else None

# A scratch run under a scratch state root, scored nowhere near the repo.
state_root = Path("'"$TMP"'/scratch-state-root")
gates_dir = state_root / "gates"
gates_dir.mkdir(parents=True)
data = {
    "run_id": "scratch-run", "lang": "en", "chosen_beat_rate": 0.5, "selection_inverted": True,
    "candidates": [
        {"title": "Chosen", "role": "chosen", "cited_rule": None, "beat_rate": 0.5},
        {"title": "Winner", "role": "rejected", "cited_rule": "SKILL.md:ISOLATION-TEST", "beat_rate": 0.9},
    ],
}
(gates_dir / "beat-rate-en.json").write_text(json.dumps(data), encoding="utf-8")

explicit_ledger = Path("'"$TMP"'/scratch-ledger.jsonl")
# rb.main()'"'"'s cmd_collect prints its own JSON report to stdout -- swallow
# that here so it does not interleave with this snippet'"'"'s own result line.
with contextlib.redirect_stdout(io.StringIO()):
    rc = rb.main(["collect", "--state-root", str(state_root), "--ledger", str(explicit_ledger)])

after = default_ledger.read_bytes() if default_ledger.exists() else None
explicit_content = explicit_ledger.read_text(encoding="utf-8") if explicit_ledger.exists() else ""

print(rc, before == after, "SKILL.md:ISOLATION-TEST" in explicit_content)
')"
check "collect --ledger exits 0" "0" "$(echo "$OUT5" | awk '{print $1}')"
check "the real default ledger is byte-for-byte unchanged" "True" "$(echo "$OUT5" | awk '{print $2}')"
check "the explicit --ledger file received the scratch observation" "True" "$(echo "$OUT5" | awk '{print $3}')"

# A judge outage is not a verdict. beat_rate.py reports selection_inverted
# null when the chosen candidate had zero scorable pairs; coercing that to
# false would bank clean evidence for every cited rule on a night nothing was
# measured, and a clean streak is what keeps a rule off the deletion list.
cat > "$TMP/noevidence.json" <<'JSON'
{"run_id":"outage","lang":"ja","chosen_beat_rate":0.0,"best_rejected_beat_rate":0.4,
 "selection_inverted":null,
 "candidates":[{"title":"chosen","role":"chosen","beat_rate":0.0,"scorable_pairs":0,"cited_rule":null},
               {"title":"rejected","role":"rejected","beat_rate":0.4,"scorable_pairs":3,
                "cited_rule":"SKILL.md:124"}]}
JSON
OUT_NOEV=$(NOEV="$TMP/noevidence.json" pyrun '
import json, os
import rule_blame
data = json.load(open(os.environ["NOEV"]))
print(len(rule_blame.observations_from_run(data, ts="t")))
')
check "a judge outage records neither loss nor clean" "0" "$OUT_NOEV"

printf '\n%s passed, %s failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
