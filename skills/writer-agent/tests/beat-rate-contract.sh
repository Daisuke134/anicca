#!/usr/bin/env bash
# Contract for the blind pairwise beat-rate scorer (spec 47 section 19.3).
#
# NO LIVE MODEL CALLS: every check below imports the module and drives its
# pure functions with an injected `judge_fn` (a plain python callable passed
# explicitly into score_ledger/score_candidate/score_one_pair -- see
# beat_rate.py's module docstring "Testing seam" for why explicit injection
# is used instead of monkeypatching the module attribute). A real CLI run
# against a fake $ARTICLE_MODEL_RUNNER script is exercised separately, by
# hand, for the task's verify step -- never here.
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
  # Runs a python snippet with beat_rate importable, prints its stdout.
  PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}" "$PY" -c "$1" 2>"$TMP/stderr"
}

# 1. Opponent selection is deterministic for the same (run_id, lang) and
#    differs across languages.
OUT1="$(pyrun '
import beat_rate as br

def mk(id_, lang, metric):
    return {"id": id_, "lang": lang, "slice": "top", "metric_primary": metric, "title": f"T-{id_}"}

corpus = [mk(f"hn:{i}", "en", 10 + i) for i in range(1, 21)] + [mk(f"zenn:{i}", "ja", 10 + i) for i in range(1, 21)]
pool_en = br.select_opponent_pool(corpus, "en")
pool_ja = br.select_opponent_pool(corpus, "ja")

opp1 = br.sample_opponents(pool_en, "run-A", "en", 3)
opp2 = br.sample_opponents(pool_en, "run-A", "en", 3)
opp3 = br.sample_opponents(pool_ja, "run-A", "ja", 3)

ids1 = [o["id"] for o in opp1]
ids2 = [o["id"] for o in opp2]
ids3 = [o["id"] for o in opp3]
print(len(pool_en), len(pool_ja), ids1 == ids2, ids1 != ids3)
')"
check "opponent pool is 20% of 20 eligible rows" "4" "$(echo "$OUT1" | awk '{print $1}')"
check "ja pool is independently 20% of its own 20 rows" "4" "$(echo "$OUT1" | awk '{print $2}')"
check "same (run_id, lang) samples the same opponents" "True" "$(echo "$OUT1" | awk '{print $3}')"
check "different lang samples different opponents" "True" "$(echo "$OUT1" | awk '{print $4}')"

# 2. Both orderings are issued for every pair; a judge that always answers
#    "A" yields beat_rate exactly 0.5 for every candidate -- the
#    position-bias control. A biased judge must NOT produce a winner.
OUT2="$(pyrun '
import beat_rate as br
from pathlib import Path

def mk(id_, metric):
    return {"id": id_, "lang": "en", "slice": "top", "metric_primary": metric, "title": f"Real winner {id_}"}

corpus = [mk(f"hn:{i}", 10 + i) for i in range(1, 11)]

def always_a(runner, prompt, run_id):
    return "{\"winner\":\"A\",\"why\":\"x\"}"

ledger = {
    "lang": "en",
    "chosen": {"title": "Chosen headline", "why": "test"},
    "rejected": [
        {"title": "Rejected one", "reason": "test", "cited_rule": "x:1"},
        {"title": "Rejected two", "reason": "test", "cited_rule": "x:2"},
    ],
}
result = br.score_ledger(ledger, corpus, run_id="run-B", runner=Path("/unused"), opponents_k=2, judge_fn=always_a)
rates = [c["beat_rate"] for c in result["candidates"]]
print(all(r == 0.5 for r in rates), result["calls_used"])
')"
check "an always-A judge yields beat_rate 0.5 for every candidate" "True" "$(echo "$OUT2" | awk '{print $1}')"
check "3 candidates x 2 opponents x 2 orders = 12 calls" "12" "$(echo "$OUT2" | awk '{print $2}')"

# 3. A rejected candidate outscoring the chosen one sets selection_inverted
#    true -- the alarm the whole design exists to raise.
OUT3="$(pyrun '
import beat_rate as br
from pathlib import Path

def mk(id_, metric):
    return {"id": id_, "lang": "en", "slice": "top", "metric_primary": metric, "title": f"Opponent {id_}"}

corpus = [mk(f"hn:{i}", 10 + i) for i in range(1, 11)]

def title_aware_judge(runner, prompt, run_id):
    lines = prompt.splitlines()
    a_title = next(l[3:] for l in lines if l.startswith("A: "))
    b_title = next(l[3:] for l in lines if l.startswith("B: "))
    if "STRONG" in a_title:
        return "{\"winner\":\"A\",\"why\":\"x\"}"
    if "STRONG" in b_title:
        return "{\"winner\":\"B\",\"why\":\"x\"}"
    return "{\"winner\":\"A\",\"why\":\"x\"}"

ledger = {
    "lang": "en",
    "chosen": {"title": "Ordinary chosen headline", "why": "test"},
    "rejected": [{"title": "STRONG rejected headline", "reason": "test", "cited_rule": "x:1"}],
}
result = br.score_ledger(ledger, corpus, run_id="run-C", runner=Path("/unused"), opponents_k=3, judge_fn=title_aware_judge)
print(result["chosen_beat_rate"], result["best_rejected_beat_rate"], result["selection_inverted"])
')"
check "chosen (no marker) gets the position-bias 0.5" "0.5" "$(echo "$OUT3" | awk '{print $1}')"
check "rejected with the winning marker beats every opponent" "1.0" "$(echo "$OUT3" | awk '{print $2}')"
check "rejected outscoring chosen sets selection_inverted true" "True" "$(echo "$OUT3" | awk '{print $3}')"

# 4. Unparseable judge output produces a null pair score and is EXCLUDED
#    from the mean, never counted as a loss.
OUT4="$(pyrun '
import beat_rate as br
from pathlib import Path

def mixed_judge(runner, prompt, run_id):
    if "Loser-opponent" in prompt:
        return "not json at all"
    lines = prompt.splitlines()
    a_title = next(l[3:] for l in lines if l.startswith("A: "))
    b_title = next(l[3:] for l in lines if l.startswith("B: "))
    if "CAND" in a_title:
        return "{\"winner\":\"A\",\"why\":\"x\"}"
    if "CAND" in b_title:
        return "{\"winner\":\"B\",\"why\":\"x\"}"
    return "{\"winner\":\"A\",\"why\":\"x\"}"

budget = br.CallBudget(100)
result = br.score_candidate(
    "CAND headline", "chosen", None,
    [{"id": "opp-win", "title": "Winner-opponent"}, {"id": "opp-lose", "title": "Loser-opponent"}],
    runner=Path("/unused"), run_id="run-D", budget=budget, judge_fn=mixed_judge,
)
scores = {p["opponent_id"]: p["score"] for p in result["pairs"]}
print(scores["opp-win"], scores["opp-lose"], result["beat_rate"])
')"
check "the parseable opponent scores a clean win" "1.0" "$(echo "$OUT4" | awk '{print $1}')"
check "the unparseable opponent's pair score is null (None), not a loss" "None" "$(echo "$OUT4" | awk '{print $2}')"
check "beat_rate excludes the null pair from the mean (not 0.5)" "1.0" "$(echo "$OUT4" | awk '{print $3}')"

# 5. The --max-calls budget stops the run and marks partial true.
OUT5="$(pyrun '
import beat_rate as br
from pathlib import Path

def mk(id_, metric):
    return {"id": id_, "lang": "en", "slice": "top", "metric_primary": metric, "title": f"Opponent {id_}"}

corpus = [mk(f"hn:{i}", 10 + i) for i in range(1, 11)]

def always_a(runner, prompt, run_id):
    return "{\"winner\":\"A\",\"why\":\"x\"}"

ledger = {
    "lang": "en",
    "chosen": {"title": "Chosen headline", "why": "test"},
    "rejected": [
        {"title": "Rejected one", "reason": "test", "cited_rule": "x:1"},
        {"title": "Rejected two", "reason": "test", "cited_rule": "x:2"},
    ],
}
# 3 candidates x 3 opponents x 2 orders = 18 calls needed; budget only 5.
result = br.score_ledger(ledger, corpus, run_id="run-E", runner=Path("/unused"), opponents_k=3, max_calls=5, judge_fn=always_a)
print(result["calls_used"], result["partial"])
')"
check "calls_used stops exactly at the budget cap" "5" "$(echo "$OUT5" | awk '{print $1}')"
check "partial is true when the budget was hit" "True" "$(echo "$OUT5" | awk '{print $2}')"

# 6. hn is NEVER selected as an opponent (round-4/T15): its top slice mixes
#    real writing craft with breaking news / product announcements
#    ("Judge approves $1.5B Anthropic settlement..."), scored on the event
#    not the headline -- the wrong reference class. A mixed pool (hn +
#    zenn, hn scoring HIGHER so a naive top-20%-by-metric pick would favor
#    it) must select zenn only.
OUT6="$(pyrun '
import beat_rate as br

def mk(id_, source, metric):
    return {"id": id_, "source": source, "lang": "en", "slice": "top",
            "metric_primary": metric, "title": f"T-{id_}"}

corpus = (
    [mk(f"hn:{i}", "hn", 900 + i) for i in range(1, 11)]
    + [mk(f"zenn:{i}", "zenn", 10 + i) for i in range(1, 11)]
)
pool = br.select_opponent_pool(corpus, "en")
sources = sorted({row["source"] for row in pool})
opponents = br.sample_opponents(pool, "run-F", "en", 10)
opp_sources = sorted({o["source"] for o in opponents})
print(",".join(sources))
print(",".join(opp_sources))
')"
check "opponent pool never contains an hn row even when hn outscores everything" "zenn" "$(echo "$OUT6" | sed -n '1p')"
check "hn is absent from a fully-sampled opponent set too" "zenn" "$(echo "$OUT6" | sed -n '2p')"

# 6b. score_candidate/score_ledger report which sources the opponents came
#     from, so the reference class a beat_rate was measured against is
#     never invisible again.
OUT6B="$(pyrun '
import beat_rate as br
from pathlib import Path

def mk(id_, source, metric):
    return {"id": id_, "source": source, "lang": "en", "slice": "top",
            "metric_primary": metric, "title": f"T-{id_}"}

corpus = [mk(f"zenn:{i}", "zenn", 10 + i) for i in range(1, 11)]

def always_a(runner, prompt, run_id):
    return "{\"winner\":\"A\",\"why\":\"x\"}"

ledger = {"lang": "en", "chosen": {"title": "Chosen headline", "why": "test"}, "rejected": []}
result = br.score_ledger(ledger, corpus, run_id="run-G", runner=Path("/unused"), opponents_k=3, judge_fn=always_a)
print(",".join(result["opponent_sources"]))
print(",".join(result["candidates"][0]["opponent_sources"]))
')"
check "score_ledger reports opponent_sources" "zenn" "$(echo "$OUT6B" | sed -n '1p')"
check "score_candidate reports opponent_sources per candidate too" "zenn" "$(echo "$OUT6B" | sed -n '2p')"

# 7. A pool that is only hn rows for a language yields a CLEAR refusal
#    (BeatRateError), never a silent fall-through to scoring against zero
#    opponents (which would produce beat_rate 0.0 for every candidate --
#    indistinguishable from "lost every pair", exactly the invisible-wrong-
#    yardstick failure this whole fix exists to end).
OUT7="$(pyrun '
import beat_rate as br
from pathlib import Path

def mk(id_, metric):
    return {"id": id_, "source": "hn", "lang": "en", "slice": "top",
            "metric_primary": metric, "title": f"T-{id_}"}

corpus = [mk(f"hn:{i}", 10 + i) for i in range(1, 11)]
ledger = {"lang": "en", "chosen": {"title": "Chosen headline", "why": "test"}, "rejected": []}
try:
    br.score_ledger(ledger, corpus, run_id="run-H", runner=Path("/unused"), judge_fn=lambda r, p, i: "{\"winner\":\"A\",\"why\":\"x\"}")
    print("NO_ERROR_RAISED")
except br.BeatRateError as exc:
    print("REFUSED", "hn" in str(exc) or "EXCLUDED_OPPONENT_SOURCES" in str(exc))
')"
check "an all-hn pool refuses rather than silently scoring against news" "REFUSED True" "$(echo "$OUT7")"

printf '\n%s passed, %s failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
