#!/usr/bin/env bash
# Contract for the writing-corpus harvester (spec 47 section 19.5, round 3).
#
# NO LIVE NETWORK: every check below imports the module and drives its pure
# functions with inline fixtures. The network fetchers (fetch_hn/fetch_devto/
# fetch_zenn) are exercised separately, live, by hand -- see the task's
# verify step.
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
  # Runs a python snippet with harvest_corpus importable, prints its stdout.
  PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}" "$PY" -c "$1" 2>"$TMP/stderr"
}

# 1. Percentile normalisation: highest metric in a group -> 1.0, lowest -> 0.0,
#    and groups (source, lang) are independent -- a huge devto value must not
#    compress the hn group's scores.
OUT="$(pyrun '
import harvest_corpus as hc
rows = [
    hc.build_row(source="hn", native_id="a", lang="en", title="A", text="", url="https://x/a",
                 metric={"points": 10, "comments": 0, "reactions": 0}, slice_name="top", harvested_at="t"),
    hc.build_row(source="hn", native_id="b", lang="en", title="B", text="", url="https://x/b",
                 metric={"points": 20, "comments": 0, "reactions": 0}, slice_name="top", harvested_at="t"),
    hc.build_row(source="hn", native_id="c", lang="en", title="C", text="", url="https://x/c",
                 metric={"points": 30, "comments": 0, "reactions": 0}, slice_name="top", harvested_at="t"),
    hc.build_row(source="devto", native_id="d", lang="en", title="D", text="", url="https://x/d",
                 metric={"points": 0, "comments": 0, "reactions": 1000}, slice_name="top", harvested_at="t"),
]
out = hc.apply_norm_scores(rows)
by_id = {r["id"]: r["norm_score"] for r in out}
print(by_id["hn:a"], by_id["hn:b"], by_id["hn:c"], by_id["devto:d"])
')"
check "lowest hn points normalises to 0.0" "0.0" "$(echo "$OUT" | awk '{print $1}')"
check "mid hn points normalises to 0.5" "0.5" "$(echo "$OUT" | awk '{print $2}')"
check "highest hn points normalises to 1.0" "1.0" "$(echo "$OUT" | awk '{print $3}')"
check "devto singleton group normalises to 1.0 (own group, unaffected by hn)" "1.0" "$(echo "$OUT" | awk '{print $4}')"

# 2. Same-value cross-source check: an hn row and a devto row with numerically
#    equal metrics must NOT both land on 1.0 just because the numbers match --
#    each is ranked only within its own (source, lang) group.
OUT2="$(pyrun '
import harvest_corpus as hc
rows = [
    hc.build_row(source="hn", native_id="a", lang="en", title="A", text="", url="https://x/a",
                 metric={"points": 5, "comments": 0, "reactions": 0}, slice_name="top", harvested_at="t"),
    hc.build_row(source="hn", native_id="b", lang="en", title="B", text="", url="https://x/b",
                 metric={"points": 50, "comments": 0, "reactions": 0}, slice_name="top", harvested_at="t"),
    hc.build_row(source="devto", native_id="c", lang="en", title="C", text="", url="https://x/c",
                 metric={"points": 0, "comments": 0, "reactions": 5}, slice_name="top", harvested_at="t"),
    hc.build_row(source="devto", native_id="d", lang="en", title="D", text="", url="https://x/d",
                 metric={"points": 0, "comments": 0, "reactions": 50}, slice_name="top", harvested_at="t"),
]
out = hc.apply_norm_scores(rows)
by_id = {r["id"]: r["norm_score"] for r in out}
print(by_id["hn:a"], by_id["devto:c"])
')"
check "hn:a (low in its group) is 0.0 despite matching devto:c's raw value" "0.0" "$(echo "$OUT2" | awk '{print $1}')"
check "devto:c (low in its group) is 0.0, groups scored independently" "0.0" "$(echo "$OUT2" | awk '{print $2}')"

# 2b. zenn joins the same (source, lang) percentile grouping on its own
#     primary metric (likes), independent of hn/devto.
OUT2B="$(pyrun '
import harvest_corpus as hc
rows = [
    hc.build_row(source="zenn", native_id="a", lang="ja", title="ア", text="", url="https://zenn.dev/articles/a",
                 metric={"points": 0, "comments": 0, "reactions": 0, "likes": 3}, slice_name="top", harvested_at="t"),
    hc.build_row(source="zenn", native_id="b", lang="ja", title="イ", text="", url="https://zenn.dev/articles/b",
                 metric={"points": 0, "comments": 0, "reactions": 0, "likes": 30}, slice_name="top", harvested_at="t"),
]
out = hc.apply_norm_scores(rows)
by_id = {r["id"]: r["norm_score"] for r in out}
print(by_id["zenn:a"], by_id["zenn:b"])
')"
check "zenn low likes normalises to 0.0" "0.0" "$(echo "$OUT2B" | awk '{print $1}')"
check "zenn high likes normalises to 1.0" "1.0" "$(echo "$OUT2B" | awk '{print $2}')"

# 3. Language detection: ja (CJK), en (plain ASCII), other (non-English
#    Latin-script marker).
check "Japanese title detected as ja" "ja" "$(pyrun 'import harvest_corpus as hc; print(hc.detect_lang("バーチャルズのハンコ承認を読む"))')"
check "ASCII title detected as en" "en" "$(pyrun 'import harvest_corpus as hc; print(hc.detect_lang("The Myth of the Post-Documentation Era"))')"
check "mixed-script title (any CJK) detected as ja" "ja" "$(pyrun 'import harvest_corpus as hc; print(hc.detect_lang("ACP explained for beginners 日本語"))')"
check "Portuguese title detected as other" "other" "$(pyrun 'import harvest_corpus as hc; print(hc.detect_lang("Contribuir para a comunidade open source"))')"
check "Spanish title detected as other" "other" "$(pyrun 'import harvest_corpus as hc; print(hc.detect_lang("Según los datos, más rápido que nunca"))')"
check "French title detected as other" "other" "$(pyrun 'import harvest_corpus as hc; print(hc.detect_lang("Un guide très complet pour avec Rust"))')"

# 4. A row missing a title, or missing a url, is dropped (returns None) rather
#    than written.
check "missing title drops the row" "None" "$(pyrun '
import harvest_corpus as hc
row = hc.build_row(source="hn", native_id="x", lang="en", title="", text="", url="https://x/1",
                    metric={"points": 1, "comments": 0, "reactions": 0}, slice_name="top", harvested_at="t")
print(row)
')"
check "missing url drops the row" "None" "$(pyrun '
import harvest_corpus as hc
row = hc.build_row(source="hn", native_id="x", lang="en", title="Has a title", text="", url="",
                    metric={"points": 1, "comments": 0, "reactions": 0}, slice_name="top", harvested_at="t")
print(row)
')"
check "title and url present keeps the row" "hn:x" "$(pyrun '
import harvest_corpus as hc
row = hc.build_row(source="hn", native_id="x", lang="en", title="Has a title", text="", url="https://x/1",
                    metric={"points": 1, "comments": 0, "reactions": 0}, slice_name="top", harvested_at="t")
print(row["id"])
')"

# 5. Idempotency: writing the same batch twice to the same file leaves the
#    row count unchanged (dedupe on id).
BATCH_TEST="$(pyrun '
import harvest_corpus as hc
from pathlib import Path
rows = [
    hc.build_row(source="hn", native_id=str(i), lang="en", title=f"Title {i}", text="",
                 url=f"https://x/{i}", metric={"points": i, "comments": 0, "reactions": 0},
                 slice_name="top", harvested_at="t")
    for i in range(1, 6)
]
rows = hc.apply_norm_scores(rows)
path = Path("'"$TMP"'/2026-07-26-hn.jsonl")
w1, d1 = hc.append_rows(path, rows)
w2, d2 = hc.append_rows(path, rows)
lines = len(path.read_text(encoding="utf-8").splitlines())
print(w1, d1, w2, d2, lines)
')"
check "first write appends all 5 rows" "5" "$(echo "$BATCH_TEST" | awk '{print $1}')"
check "first write has 0 duplicates" "0" "$(echo "$BATCH_TEST" | awk '{print $2}')"
check "second write appends 0 new rows" "0" "$(echo "$BATCH_TEST" | awk '{print $3}')"
check "second write reports all 5 as duplicates" "5" "$(echo "$BATCH_TEST" | awk '{print $4}')"
check "file still has exactly 5 lines after re-running the batch" "5" "$(echo "$BATCH_TEST" | awk '{print $5}')"

# 6. Schema contract: validate_row_schema raises on a row with a bad field
#    (defends the schema against future edits, mirrors title_candidates.py's
#    CandidateError -> exit 3 pattern).
check "validate_row_schema rejects an out-of-range norm_score" "REJECTED" "$(pyrun '
import harvest_corpus as hc
row = hc.build_row(source="hn", native_id="x", lang="en", title="T", text="", url="https://x/1",
                    metric={"points": 1, "comments": 0, "reactions": 0}, slice_name="top", harvested_at="t")
row["norm_score"] = 5.0
try:
    hc.validate_row_schema(row)
    print("ACCEPTED")
except hc.HarvestContractError:
    print("REJECTED")
')"
check "validate_row_schema accepts a well-formed row" "ACCEPTED" "$(pyrun '
import harvest_corpus as hc
row = hc.build_row(source="hn", native_id="x", lang="en", title="T", text="", url="https://x/1",
                    metric={"points": 1, "comments": 0, "reactions": 0}, slice_name="top", harvested_at="t")
row["norm_score"] = 0.5
try:
    hc.validate_row_schema(row)
    print("ACCEPTED")
except hc.HarvestContractError:
    print("REJECTED")
')"
check "validate_row_schema rejects a bad slice value" "REJECTED" "$(pyrun '
import harvest_corpus as hc
row = hc.build_row(source="hn", native_id="x", lang="en", title="T", text="", url="https://x/1",
                    metric={"points": 1, "comments": 0, "reactions": 0}, slice_name="top", harvested_at="t")
row["norm_score"] = 0.5
row["slice"] = "winner"
try:
    hc.validate_row_schema(row)
    print("ACCEPTED")
except hc.HarvestContractError:
    print("REJECTED")
')"

# 7. stats: counts per source/lang and date range, read straight off disk.
STATS="$(pyrun '
import harvest_corpus as hc
from pathlib import Path
d = Path("'"$TMP"'/stats-corpus")
d.mkdir()
def row(id_, source, lang, slice_):
    return {"id": id_, "source": source, "format": "article", "lang": lang, "title": "t", "text": "",
            "url": "u", "metric": {"points": 1, "comments": 0, "reactions": 0, "likes": 0}, "followers": 0,
            "norm_score": 1.0, "topic_tags": [], "slice": slice_, "harvested_at": "t"}
(d / "2026-07-24-hn.jsonl").write_text(
    hc.json.dumps(row("hn:1", "hn", "en", "top")) + "\n", encoding="utf-8")
(d / "2026-07-25-hn.jsonl").write_text(
    hc.json.dumps(row("hn:2", "hn", "ja", "baseline")) + "\n", encoding="utf-8")
stats = hc.collect_stats(d)
print(stats["total_rows"], stats["by_source"]["hn"]["en"], stats["by_source"]["hn"]["ja"],
      stats["date_range"]["min"], stats["date_range"]["max"])
')"
check "stats total_rows across two days" "2" "$(echo "$STATS" | awk '{print $1}')"
check "stats hn/en count" "1" "$(echo "$STATS" | awk '{print $2}')"
check "stats hn/ja count" "1" "$(echo "$STATS" | awk '{print $3}')"
check "stats date_range.min" "2026-07-24" "$(echo "$STATS" | awk '{print $4}')"
check "stats date_range.max" "2026-07-25" "$(echo "$STATS" | awk '{print $5}')"

# 8. slice field: every row carries "top" or "baseline", set from the caller,
#    and round-trips through append/read unchanged.
SLICE_TEST="$(pyrun '
import harvest_corpus as hc
top_row = hc.build_row(source="hn", native_id="1", lang="en", title="Top", text="", url="https://x/1",
                        metric={"points": 9, "comments": 0, "reactions": 0}, slice_name="top", harvested_at="t")
base_row = hc.build_row(source="hn", native_id="2", lang="en", title="Base", text="", url="https://x/2",
                         metric={"points": 1, "comments": 0, "reactions": 0}, slice_name="baseline", harvested_at="t")
print(top_row["slice"], base_row["slice"])
')"
check "top slice tagged top" "top" "$(echo "$SLICE_TEST" | awk '{print $1}')"
check "baseline slice tagged baseline" "baseline" "$(echo "$SLICE_TEST" | awk '{print $2}')"

# 9. Zenn row shape: metric.likes carries liked_count, url is built from
#    path when present else from slug, id is source-prefixed.
ZENN_TEST="$(pyrun '
import harvest_corpus as hc
row = hc.build_row(source="zenn", native_id="my-slug", lang="ja", title="ゼンの記事", text="",
                    url="https://zenn.dev/articles/my-slug",
                    metric={"points": 0, "comments": 0, "reactions": 0, "likes": 42},
                    slice_name="top", harvested_at="t")
print(row["id"], row["url"], row["metric"]["likes"], row["source"])
')"
check "zenn row id is source-prefixed" "zenn:my-slug" "$(echo "$ZENN_TEST" | awk '{print $1}')"
check "zenn row url" "https://zenn.dev/articles/my-slug" "$(echo "$ZENN_TEST" | awk '{print $2}')"
check "zenn row metric.likes carries liked_count" "42" "$(echo "$ZENN_TEST" | awk '{print $3}')"
check "zenn row source is zenn" "zenn" "$(echo "$ZENN_TEST" | awk '{print $4}')"

# 9b. Hatena row shape (round-4/T15): no native numeric id in the feed, so
#     the entry's own URL is the native id; metric.bookmarks carries
#     hatena:bookmarkcount.
HATENA_TEST="$(pyrun '
import harvest_corpus as hc
row = hc.build_row(source="hatena", native_id="https://blog.example.com/entry/abc",
                    lang="ja", title="はてなの記事", text="",
                    url="https://blog.example.com/entry/abc",
                    metric={"points": 0, "comments": 0, "reactions": 0, "likes": 0, "bookmarks": 87},
                    slice_name="top", harvested_at="t")
print(row["id"], row["url"], row["metric"]["bookmarks"], row["source"])
')"
check "hatena row id is source-prefixed with the URL as native id" \
  "hatena:https://blog.example.com/entry/abc" "$(echo "$HATENA_TEST" | awk '{print $1}')"
check "hatena row url matches the entry URL" "https://blog.example.com/entry/abc" "$(echo "$HATENA_TEST" | awk '{print $2}')"
check "hatena row metric.bookmarks carries bookmarkcount" "87" "$(echo "$HATENA_TEST" | awk '{print $3}')"
check "hatena row source is hatena" "hatena" "$(echo "$HATENA_TEST" | awk '{print $4}')"

# 9c. Qiita row shape (round-4/T15): metric.likes carries likes_count,
#     reusing the same field zenn already uses for the same concept.
QIITA_TEST="$(pyrun '
import harvest_corpus as hc
row = hc.build_row(source="qiita", native_id="abc123def456", lang="ja", title="Qiitaの記事", text="",
                    url="https://qiita.com/user/items/abc123def456",
                    metric={"points": 0, "comments": 3, "reactions": 0, "likes": 55},
                    slice_name="top", harvested_at="t")
print(row["id"], row["url"], row["metric"]["likes"], row["source"])
')"
check "qiita row id is source-prefixed" "qiita:abc123def456" "$(echo "$QIITA_TEST" | awk '{print $1}')"
check "qiita row url" "https://qiita.com/user/items/abc123def456" "$(echo "$QIITA_TEST" | awk '{print $2}')"
check "qiita row metric.likes carries likes_count" "55" "$(echo "$QIITA_TEST" | awk '{print $3}')"
check "qiita row source is qiita" "qiita" "$(echo "$QIITA_TEST" | awk '{print $4}')"

# 9d. _parse_hatena_rss_items: the one XML (not JSON) parser in this file --
#     a fixture RDF/RSS document with the real namespace shape, and a
#     malformed-XML input must yield [] rather than raise (mirrors every
#     other fetcher's "one source's failure must not crash the harvest").
HATENA_XML_TEST="$(pyrun '
import harvest_corpus as hc
fixture = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<rdf:RDF xmlns:rdf=\"http://www.w3.org/1999/02/22-rdf-syntax-ns#\"
 xmlns=\"http://purl.org/rss/1.0/\"
 xmlns:hatena=\"http://www.hatena.ne.jp/info/xmlns#\">
<item rdf:about=\"https://example.com/a\">
<title>Example Title A</title>
<link>https://example.com/a</link>
<hatena:bookmarkcount>123</hatena:bookmarkcount>
</item>
<item rdf:about=\"https://example.com/b\">
<title>Example Title B</title>
<link>https://example.com/b</link>
<hatena:bookmarkcount>4</hatena:bookmarkcount>
</item>
</rdf:RDF>"""
items = hc._parse_hatena_rss_items(fixture)
print(len(items))
print(items[0]["url"])
print(items[0]["title"])
print(items[0]["bookmarks"])
print(items[1]["bookmarks"])
print(hc._parse_hatena_rss_items("not xml at all <<<"))
')"
check "hatena XML fixture parses to 2 items" "2" "$(echo "$HATENA_XML_TEST" | sed -n '1p')"
check "hatena XML fixture item url" "https://example.com/a" "$(echo "$HATENA_XML_TEST" | sed -n '2p')"
check "hatena XML fixture item title" "Example Title A" "$(echo "$HATENA_XML_TEST" | sed -n '3p')"
check "hatena XML fixture first bookmarkcount" "123" "$(echo "$HATENA_XML_TEST" | sed -n '4p')"
check "hatena XML fixture second bookmarkcount" "4" "$(echo "$HATENA_XML_TEST" | sed -n '5p')"
check "malformed XML yields empty list, not an exception" "[]" "$(echo "$HATENA_XML_TEST" | sed -n '6p')"

# 10. metric_primary: build_row stamps the raw number norm_score is computed
#     from -- points for hn, reactions for devto, likes for zenn/qiita,
#     bookmarks for hatena -- so a later gate can read "how did it actually
#     do" without re-deriving it.
PRIMARY_TEST="$(pyrun '
import harvest_corpus as hc
hn_row = hc.build_row(source="hn", native_id="1", lang="en", title="H", text="", url="https://x/1",
                       metric={"points": 77, "comments": 0, "reactions": 999}, slice_name="top", harvested_at="t")
devto_row = hc.build_row(source="devto", native_id="2", lang="en", title="D", text="", url="https://x/2",
                          metric={"points": 999, "comments": 0, "reactions": 33}, slice_name="top", harvested_at="t")
zenn_row = hc.build_row(source="zenn", native_id="3", lang="ja", title="Z", text="", url="https://x/3",
                         metric={"points": 999, "comments": 0, "reactions": 999, "likes": 12}, slice_name="top", harvested_at="t")
hatena_row = hc.build_row(source="hatena", native_id="https://x/4", lang="ja", title="Hatena", text="", url="https://x/4",
                           metric={"points": 999, "comments": 999, "reactions": 999, "likes": 999, "bookmarks": 45},
                           slice_name="top", harvested_at="t")
qiita_row = hc.build_row(source="qiita", native_id="5", lang="ja", title="Qiita", text="", url="https://x/5",
                          metric={"points": 999, "comments": 999, "reactions": 999, "likes": 66},
                          slice_name="top", harvested_at="t")
print(hn_row["metric_primary"], devto_row["metric_primary"], zenn_row["metric_primary"],
      hatena_row["metric_primary"], qiita_row["metric_primary"])
')"
check "hn metric_primary is points, ignoring reactions" "77.0" "$(echo "$PRIMARY_TEST" | awk '{print $1}')"
check "devto metric_primary is reactions, ignoring points" "33.0" "$(echo "$PRIMARY_TEST" | awk '{print $2}')"
check "zenn metric_primary is likes, ignoring points/reactions" "12.0" "$(echo "$PRIMARY_TEST" | awk '{print $3}')"
check "hatena metric_primary is bookmarks, ignoring points/comments/reactions/likes" "45.0" "$(echo "$PRIMARY_TEST" | awk '{print $4}')"
check "qiita metric_primary is likes, ignoring points/comments/reactions" "66.0" "$(echo "$PRIMARY_TEST" | awk '{print $5}')"

# 11. validate_row_schema rejects a row whose metric_primary has gone stale
#     (does not match what primary_metric would derive from `metric` fresh)
#     -- guards against norm_score ever being computed on the wrong number.
check "validate_row_schema rejects a stale metric_primary" "REJECTED" "$(pyrun '
import harvest_corpus as hc
row = hc.build_row(source="hn", native_id="x", lang="en", title="T", text="", url="https://x/1",
                    metric={"points": 10, "comments": 0, "reactions": 0}, slice_name="top", harvested_at="t")
row["metric_primary"] = 999.0
try:
    hc.validate_row_schema(row)
    print("ACCEPTED")
except hc.HarvestContractError:
    print("REJECTED")
')"

# 12. hn: top and baseline are SEPARATE populations, not the same popular set
#     wearing two labels (the round-3 defect). A baseline slice with genuinely
#     low points must anchor the bottom of the group's norm_score with a
#     single-digit metric_primary, and the lowest-scoring row in the group
#     must actually be a baseline row -- not merely the least-popular top row.
HN_SEPARATION_TEST="$(pyrun '
import harvest_corpus as hc
rows = [
    hc.build_row(source="hn", native_id="top1", lang="en", title="Top1", text="", url="https://x/t1",
                 metric={"points": 800, "comments": 0, "reactions": 0}, slice_name="top", harvested_at="t"),
    hc.build_row(source="hn", native_id="top2", lang="en", title="Top2", text="", url="https://x/t2",
                 metric={"points": 500, "comments": 0, "reactions": 0}, slice_name="top", harvested_at="t"),
    hc.build_row(source="hn", native_id="top3", lang="en", title="Top3 least-popular winner", text="", url="https://x/t3",
                 metric={"points": 50, "comments": 0, "reactions": 0}, slice_name="top", harvested_at="t"),
    hc.build_row(source="hn", native_id="base1", lang="en", title="Base1 real loser", text="", url="https://x/b1",
                 metric={"points": 1, "comments": 0, "reactions": 0}, slice_name="baseline", harvested_at="t"),
    hc.build_row(source="hn", native_id="base2", lang="en", title="Base2", text="", url="https://x/b2",
                 metric={"points": 0, "comments": 0, "reactions": 0}, slice_name="baseline", harvested_at="t"),
]
out = hc.apply_norm_scores(rows)
lowest = min(out, key=lambda r: r["norm_score"])
highest = max(out, key=lambda r: r["norm_score"])
slices_present = sorted({r["slice"] for r in out})
print(lowest["slice"], lowest["metric_primary"], highest["slice"], ",".join(slices_present))
')"
check "hn group lowest norm_score row is a baseline row (a real loser)" "baseline" "$(echo "$HN_SEPARATION_TEST" | awk '{print $1}')"
check "hn group lowest metric_primary reaches single digits" "0.0" "$(echo "$HN_SEPARATION_TEST" | awk '{print $2}')"
check "hn group highest norm_score row is a top row" "top" "$(echo "$HN_SEPARATION_TEST" | awk '{print $3}')"
check "hn group contains both slices, not just top" "baseline,top" "$(echo "$HN_SEPARATION_TEST" | awk '{print $4}')"

printf '\n%s passed, %s failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
