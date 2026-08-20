#!/usr/bin/env bash
# Contract for the rulebook contradiction scanner (spec 47 section 19-4b,
# round-3 recalibration).
#
# NO LIVE NETWORK, NO MODEL CALLS: every check imports the module and
# drives its pure functions with in-memory/on-disk fixtures. Direct/drift
# checks go through the REAL end-to-end extract_statements pipeline (raw
# source text -> marker classification -> detection), not hand-set
# is_ban/is_recommend flags, so the fixtures cannot silently drift out of
# sync with what the real marker functions actually classify. The real
# scan against the actual rulebook sources is exercised separately, by
# hand, for the task's verify step.
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

# Stopword-only padding: never becomes a candidate term (see extract_terms),
# so it pushes a .sh line past the 400-char long-line threshold without
# adding any vocabulary that could affect distinctiveness/overlap math.
PADDING='the a an of to in on at for from with by as is are was were this that these those it its we you your our not no do does did has have had can will would should could may might if so but and or what which own into out up down than then there here one two all any each other same '

# 1. THE HISTORICAL-CASE FIXTURE (spec's explicit round-3 requirement): a
#    planted direct conflict modelled on the real 2026 incident -- one
#    file banning all self-reference, another presenting a first-person
#    confessional as a proven, rewarded pattern -- sharing TWO rare terms
#    ("self"/"reference", plus "author"/"naming"/"voice"). Under the
#    round-3 absolute-occurrence threshold (<=3 statements total) this
#    needs no decoy padding: with only 2 statements in the whole corpus,
#    every term trivially occurs at most twice. Proves tightening the
#    detector (round-3) did not silence the exact case it exists to catch
#    -- a detector reporting nothing is as broken as one reporting 1205,
#    and this is the test that tells the two apart.
OUT1="$(pyrun '
import rule_conflicts as rc

sources = {
    "SKILL.md": "Self-reference naming the author voice is banned everywhere in this draft.\n",
    "reference/title-best-practices.md": "First-person self-reference naming the author voice is a proven, rewarded pattern readers love.\n",
}
statements = rc.extract_statements(sources)
findings, suppressed = rc.detect_direct_conflicts(statements)
hit = next((f for f in findings if f["side1"] == "SKILL.md:1" and f["side2"] == "reference/title-best-practices.md:1"), None)
shared_count = len(hit["subject"].split(", ")) if hit else 0
print(len(findings), suppressed, shared_count >= 2)
')"
check "the historical-case pair is found after round-3 tightening" "1" "$(echo "$OUT1" | awk '{print $1}')"
check "nothing was suppressed for a 1-pair corpus" "0" "$(echo "$OUT1" | awk '{print $2}')"
check "the finding cites at least the required 2 shared rare terms" "True" "$(echo "$OUT1" | awk '{print $3}')"

# 2. Statements that genuinely share raw words -- but only common function
#    words ("the", "is", "same") -- are NOT reported, because the stopword
#    list excludes them from ever becoming candidate terms in the first
#    place (independent of the round-3 occurrence-count change).
OUT2="$(pyrun '
import rule_conflicts as rc

sources = {
    "SKILL.md": "The image is never uploaded twice to the same platform.\n",
    "reference/title-best-practices.md": "This proven pattern is a curated list about the same number of items.\n",
}
statements = rc.extract_statements(sources)
raw_shared = rc._english_tokens(statements[0]["text"]) & rc._english_tokens(statements[1]["text"])
findings, suppressed = rc.detect_direct_conflicts(statements)
print(sorted(raw_shared) == ["same", "the"], len(findings))
')"
check "the fixture genuinely shares raw words (the, same) before filtering" "True" "$(echo "$OUT2" | awk '{print $1}')"
check "but statements sharing only common function words are NOT reported" "0" "$(echo "$OUT2" | awk '{print $2}')"

# 3. A term that is NOT a stopword but occurs MORE than the absolute cap
#    (3 statements) is excluded from distinctiveness -- this is the actual
#    round-3(a) mechanism (an absolute ceiling, not a relative 20%): a
#    term appearing in 5 statements is ordinary vocabulary, not a subject,
#    regardless of what fraction of a small or large corpus that is.
OUT3="$(pyrun '
import rule_conflicts as rc

sources = {
    "SKILL.md": "Never publish a widget headline without checking format.\n",
    "reference/title-best-practices.md": "This proven widget approach checks format for readers.\n",
    "SKILL2.md": "Do not skip the format check before publishing widget copy.\n",
    "ref2.md": "This proven format widget review helps writers ship.\n",
    "ref3.md": "This proven format widget listing is rewarded by readers.\n",
}
statements = rc.extract_statements(sources)
doc_count = {}
for s in statements:
    for t in rc.extract_terms(s["text"]):
        doc_count[t] = doc_count.get(t, 0) + 1
findings, suppressed = rc.detect_direct_conflicts(statements)
print(doc_count.get("widget"), doc_count.get("format"), len(findings))
')"
check "a word appearing in 5 statements is over the absolute cap" "5" "$(echo "$OUT3" | awk '{print $1}')"
check "so is the other shared word" "5" "$(echo "$OUT3" | awk '{print $2}')"
check "with its only shared terms over-cap, the pair is not reported" "0" "$(echo "$OUT3" | awk '{print $3}')"

# 4. Exactly ONE shared rare term is a coincidence, not a subject, and must
#    NOT be reported (round-3(b): require >=2). Adding a second shared
#    rare term to the SAME pair flips it to reported.
OUT4="$(pyrun '
import rule_conflicts as rc

one_shared = {
    "SKILL.md": "Never mention the widget brand name in the closing section.\n",
    "reference/title-best-practices.md": "This proven pattern names the widget clearly for new readers.\n",
}
findings1, _ = rc.detect_direct_conflicts(rc.extract_statements(one_shared))

two_shared = {
    "SKILL.md": "Never mention the widget gadget brand name in the closing section.\n",
    "reference/title-best-practices.md": "This proven pattern names the widget gadget clearly for new readers.\n",
}
findings2, _ = rc.detect_direct_conflicts(rc.extract_statements(two_shared))
print(len(findings1), len(findings2))
')"
check "exactly one shared rare term is NOT reported" "0" "$(echo "$OUT4" | awk '{print $1}')"
check "adding a second shared rare term makes it reported" "1" "$(echo "$OUT4" | awk '{print $2}')"

# 5. Cap and rank (round-3(c)): more than MAX_DIRECT_FINDINGS (20)
#    qualifying pairs -> only the top 20 are returned, and the report says
#    how many were suppressed. 25 independent pairs, each sharing exactly
#    2 unique rare terms with nothing else, planted here.
OUT5="$(pyrun '
import rule_conflicts as rc

words_a = ["zeldon","quarnix","plovek","trindel","wexoria","glumtar","yorvik","snibble","draxton","melquin",
           "forsythe","undrick","kaelith","vosgrim","plenroy","harkwyn","tolvane","brindale","ozmerith","farvool",
           "stangret","wyverlon","crendal","folmwick","arjenta"]
words_b = ["brakto","sillum","morvent","tazril","glindor","vestrun","ohkalin","prundle","yastrix","kelmoor",
           "wandrek","ozveil","trisken","falgrim","undoril","crevane","malfrit","sonquil","driftel","yswarth",
           "plombir","estrand","vinkata","sourwen","marlith"]
sources = {}
for i in range(25):
    sources[f"ban{i}.md"] = f"Never mention {words_a[i]} {words_b[i]} in the closing section.\n"
    sources[f"rec{i}.md"] = f"This proven pattern names {words_a[i]} {words_b[i]} clearly for readers.\n"
statements = rc.extract_statements(sources)
findings, suppressed = rc.detect_direct_conflicts(statements)
shared_counts = [len(f["subject"].split(", ")) for f in findings]
ranked_ok = shared_counts == sorted(shared_counts, reverse=True)
print(len(findings), suppressed, len(findings) + suppressed, ranked_ok)
')"
check "at most 20 pairs are returned even though 25 qualify" "20" "$(echo "$OUT5" | awk '{print $1}')"
check "the report says 5 were suppressed" "5" "$(echo "$OUT5" | awk '{print $2}')"
check "returned plus suppressed accounts for all 25 candidates" "25" "$(echo "$OUT5" | awk '{print $3}')"
check "returned pairs are ranked by shared-term count descending" "True" "$(echo "$OUT5" | awk '{print $4}')"

# 6. A planted drifted paraphrase (cross-file, high term overlap, one side
#    adds an absolute qualifier) is found -- the daily-prompt-tightens-the-
#    reference-ban shape. Drift inherits the round-3(a) rare-term fix
#    automatically (same compute_distinctive_terms), verified here rather
#    than assumed.
OUT6="$(pyrun '
import rule_conflicts as rc

padding = "'"$PADDING"'" * 2
sources = {
    "reference/title-best-practices.md": "This proven pattern promises a discovered number or result to the reader.\n",
    "article-daily.sh": padding + "This proven pattern must promise a discovered number or result to the reader, non-negotiable.\n",
}
assert len(sources["article-daily.sh"].splitlines()[0]) > 400, "fixture line must exceed the .sh long-line threshold"
statements = rc.extract_statements(sources)
findings = rc.detect_drifted_paraphrases(statements)
hit = any(f["side1"] == "reference/title-best-practices.md:1" and f["side2"] == "article-daily.sh:1" for f in findings)
print(hit)
')"
check "the cross-file high-overlap pair with an added absolute qualifier is found" "True" "$(echo "$OUT6" | awk '{print $1}')"

# 6b. The SAME kind of pair, if BOTH or NEITHER side carries a qualifier,
#     must NOT be reported as drift -- it is specifically the asymmetry
#     that makes it drift, not mere overlap.
OUT6B="$(pyrun '
import rule_conflicts as rc

padding = "'"$PADDING"'" * 2
both_sources = {
    "reference/title-best-practices.md": "This proven pattern must always promise a discovered number or result to the reader.\n",
    "article-daily.sh": padding + "This proven pattern must promise a discovered number or result to the reader, non-negotiable.\n",
}
neither_sources = {
    "reference/title-best-practices.md": "This proven pattern promises a discovered number or result to the reader.\n",
    "article-daily.sh": padding + "This proven pattern also promises a discovered number or result to the reader.\n",
}
both = rc.detect_drifted_paraphrases(rc.extract_statements(both_sources))
neither = rc.detect_drifted_paraphrases(rc.extract_statements(neither_sources))
print(len(both), len(neither))
')"
check "both sides carrying a qualifier is not drift" "0" "$(echo "$OUT6B" | awk '{print $1}')"
check "neither side carrying a qualifier is not drift" "0" "$(echo "$OUT6B" | awk '{print $2}')"

# 7. Dead-path multi-root resolution (round-3 problem 2): a reference that
#    only resolves under the scripts/ root (not the bare skill root) must
#    NOT be reported dead -- this is the note-publish/publish-paid.py false
#    positive shape exactly. A reference that resolves under NO root is
#    still reported. A reference that exists directly under the skill
#    root is still not reported (regression check on the simple case).
mkdir -p "$TMP/skill/scripts/note-publish"
cat > "$TMP/skill/scripts/note-publish/publish-paid.py" <<'EOF'
print("hello")
EOF
cat > "$TMP/skill/SKILL.md" <<'EOF'
See `note-publish/publish-paid.py` for the implementation.
See `scripts/does-not-exist.py` for the missing one.
EOF
cat > "$TMP/skill/scripts/does-exist.py" <<'EOF'
print("hello")
EOF
OUT7="$(pyrun '
import rule_conflicts as rc
from pathlib import Path
skill_dir = Path("'"$TMP"'/skill")
sources = rc.load_sources(["SKILL.md"], skill_dir)
findings = rc.detect_dead_paths(sources, skill_dir)
subjects = sorted(f["subject"] for f in findings)
print(len(findings), subjects)
')"
check "a scripts/-only-resolvable reference is NOT reported dead (multi-root fix)" "1" "$(echo "$OUT7" | awk '{print $1}')"
check "the only survivor is the genuinely nonexistent script" "['scripts/does-not-exist.py']" "$(echo "$OUT7" | cut -d' ' -f2-)"

# 8. A gates/<name>.json that no script writes and that appears in no
#    recent run directory is found; one that a script does write
#    (constructs "gates/<name>" as a literal substring) is not. No run
#    directories exist yet in this fixture, so this is the
#    script-only-evidence path.
mkdir -p "$TMP/skill/state/runs"
cat > "$TMP/skill/scripts/writer.py" <<'EOF'
path = run_dir / "gates/alive-gate.json"
EOF
cat > "$TMP/skill/SKILL.md" <<'EOF'
Read the verdict from `gates/dead-gate.json` after the run.
Read the verdict from `gates/alive-gate.json` after the run.
EOF
OUT8="$(pyrun '
import rule_conflicts as rc
from pathlib import Path
skill_dir = Path("'"$TMP"'/skill")
sources = rc.load_sources(["SKILL.md"], skill_dir)
findings = rc.detect_dead_gates(sources, skill_dir / "scripts", skill_dir / "state" / "runs")
subjects = sorted(f["subject"] for f in findings)
print(len(findings), subjects[0] if subjects else None)
')"
check "a gates/<name>.json no script writes is found" "1" "$(echo "$OUT8" | awk '{print $1}')"
check "the dead subject is the unwritten gate" "gates/dead-gate.json" "$(echo "$OUT8" | awk '{print $2}')"

# 9. Round-4 fix: "no script writes it" is incomplete evidence on its own
#    -- the daily prompt orders the MODEL to write several gates directly,
#    so a script grep alone cannot tell alive from dead. An artifact
#    PRESENT in a recent run directory must NOT be reported (something
#    produces it, whatever that something is); one absent from EVERY run
#    directory must still be reported. Neither script writes either gate
#    here, so this isolates the run-directory evidence specifically.
mkdir -p "$TMP/skill2/scripts" "$TMP/skill2/state/runs/run-old/gates" "$TMP/skill2/state/runs/run-mid/gates" "$TMP/skill2/state/runs/run-new/gates"
touch "$TMP/skill2/scripts/.keep"
cat > "$TMP/skill2/state/runs/run-new/gates/model-written-gate-ja.json" <<'EOF'
{"verdict": "PASS"}
EOF
# Backdate the older two run dirs so mtime ordering is deterministic
# regardless of filesystem timestamp resolution.
touch -t 202601010000 "$TMP/skill2/state/runs/run-old"
touch -t 202601020000 "$TMP/skill2/state/runs/run-mid"
cat > "$TMP/skill2/SKILL.md" <<'EOF'
Read the verdict from `gates/model-written-gate-ja.json` after the run.
Read the verdict from `gates/never-produced-gate.json` after the run.
EOF
OUT9="$(pyrun '
import rule_conflicts as rc
from pathlib import Path
skill_dir = Path("'"$TMP"'/skill2")
sources = rc.load_sources(["SKILL.md"], skill_dir)
findings = rc.detect_dead_gates(sources, skill_dir / "scripts", skill_dir / "state" / "runs")
subjects = sorted(f["subject"] for f in findings)
print(len(findings), subjects)
')"
check "an artifact present in a recent run dir is NOT reported dead" "1" "$(echo "$OUT9" | awk '{print $1}')"
check "the only survivor is the one absent from every run dir" "['gates/never-produced-gate.json']" "$(echo "$OUT9" | cut -d' ' -f2-)"

printf '\n%s passed, %s failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
