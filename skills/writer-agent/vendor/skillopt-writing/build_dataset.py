#!/usr/bin/env python3
"""Build the writing_split/{train,val,test} dataset for the SkillOpt
"writing" env from the real writing-corpus (spec 47 19-4c T6, BUILD 1).

Why a derived SUBJECT and not the real title: the rollout asks the target
model, under the current CRAFT.md, to write ITS OWN headline for a topic --
that is precisely what is being trained. If the item's prompt handed the
model the real, already-published headline, the model could just echo it
back (or a trivial paraphrase) and score perfectly without CRAFT.md doing
any work at all -- the benchmark would become copying, not writing. So
every row gets a NEUTRAL SUBJECT: one short line naming what the piece is
about with the rhetorical framing (the hook, the promise, the twist)
stripped out, generated once through the judge broker and cached in the
split file. The real title still travels WITH the item (for the scorer's
opponent-exclusion check and for humans reading the split file) -- it is
just never placed in the text handed to the rollout's target model. See
writing/rollout.py, which reads item["subject"], never item["title"] or
item["reference_title"], for the prompt it sends.

Reuses beat_rate.py's own judge-calling machinery (call_judge,
load_corpus_rows) for the SAME reason BUILD 2 reuses its scoring
functions: one judge path, not a second one invented here.

Language handling (post-review fix): only "ja" and "en" are the published
languages, and CRAFT.md is shared across both -- an edit validated on one
language alone can silently degrade the other. So the dataset is
STRATIFIED BY LANGUAGE, not split as one shuffled global list: each of
train/val/test gets its own target row count PER LANGUAGE
(TARGET_COUNTS_PER_LANG), and a corpus lang like "other" (we do not
publish in Portuguese) stays in the corpus but is never eligible for a
split. A split that would come out empty for either language is a fatal
defect, not a quiet zero -- build() refuses (raises EmptySplitError) and
writes nothing, rather than silently producing a val split that can never
gate anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

_ARTICLE_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_ARTICLE_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_ARTICLE_SCRIPTS_DIR))

import beat_rate as br  # noqa: E402  (path mutation above is required first)

CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "state" / "writing-corpus"
SPLIT_DIR = Path(__file__).resolve().parent / "data" / "writing_split"
SPLIT_NAMES = ("train", "val", "test")
# The two published languages. "other" (e.g. the Portuguese devto rows) is
# real, honestly-harvested corpus data -- it just never becomes a training
# or evaluation item, since we do not publish in Portuguese.
LANGS = ("ja", "en")
# Deterministic percentage buckets a row-id hash falls into, same
# per-language for both -- not a specified ratio, simplest reasonable
# 70/15/15 default (documented, not asked for a specific split beyond
# "train/val/test").
SPLIT_WEIGHTS = {"train": 70, "val": 15, "test": 15}
DEFAULT_SPLIT_SEED = "writing-craft-split-v1"
# Soft caps per language per split -- "roughly 60/20/20 per language,
# taking whatever is available if fewer exist" (post-review fix). Capping
# only trims a split's membership down to size; it never reassigns a row
# to a different split.
TARGET_COUNTS_PER_LANG = {"train": 60, "val": 20, "test": 20}
# Post-review fix: a daily rebuild (after harvest_corpus.py adds rows) must
# not re-spend judge calls at full-corpus scale every time. Capping the
# ELIGIBLE POOL per language to this size, BEFORE stratification, bounds
# every rebuild to at most ~2x this many judge calls total (both
# languages), regardless of how large the corpus grows.
DEFAULT_MAX_PER_LANG = 100

SUBJECT_PROMPT = """You are shown a real, published headline. Describe, in \
ONE short neutral line, what the piece is actually ABOUT -- the underlying \
topic, finding, or subject -- with every rhetorical hook, promise, or \
framing device stripped out. Do not describe the headline's style or why \
it might get clicked; describe only what a reader would learn the piece \
covers. Reply with EXACTLY one JSON object and nothing else:
{{"subject": "<one neutral line>"}}

Headline: {title}"""


class EmptySplitError(ValueError):
    """Raised when a (language, split) combination would be written empty.
    An empty val/test split cannot gate anything -- it would either divide
    by zero or silently accept every edit -- so this is fatal, not a
    warning, and build() writes NOTHING to disk when it is raised."""


# Post-review fix: an HN link submission whose title is a bare product
# name ("Claude Sonnet 5") scored on the product being announced, not on
# any craft in the headline -- the Stephen Hawking contamination pattern
# wearing a different shape. Training/evaluating against it teaches the
# model to name a product, which directly violates title-best-practices.md
# ban 1 ("an undefined proper noun in the headline"). Thresholds measured
# against the real corpus: <20 chars for en catches exactly 8 items, all
# bare product/topic labels with no visible false positive; <12 for ja
# catches zero (the ja corpus has no equivalent contamination today).
MIN_TITLE_LENGTH = {"en": 20, "ja": 12}


def is_bare_title(title: str, lang: str) -> bool:
    """True if `title` is too short to carry any craft for its language --
    see MIN_TITLE_LENGTH's derivation above."""
    threshold = MIN_TITLE_LENGTH.get(lang, MIN_TITLE_LENGTH["en"])
    return len((title or "").strip()) < threshold


def _passes_lang_slice_metric(row: dict) -> bool:
    return (
        row.get("slice") == "top" and row.get("metric_primary", 0) > 1
        and row.get("lang") in LANGS
    )


def eligible_rows(rows: list) -> list:
    """Same eligibility rule beat_rate.py's opponent pool uses (real,
    performing writing, slice=="top", not noise-floor rows), PLUS: only
    the languages we actually publish (a lang=="other" row, e.g.
    Portuguese, is real corpus data and stays in the corpus -- it is just
    never eligible here), PLUS: not a bare title too short to carry any
    craft (see is_bare_title)."""
    return [
        r for r in rows
        if _passes_lang_slice_metric(r)
        and not is_bare_title(str(r.get("title", "")), r.get("lang"))
    ]


def count_bare_title_excluded(rows: list) -> int:
    """How many rows were otherwise eligible (right slice, right
    metric_primary, a published language) but dropped for a bare title --
    reported by --stats so this filter is never silent."""
    return sum(
        1 for r in rows
        if _passes_lang_slice_metric(r) and is_bare_title(str(r.get("title", "")), r.get("lang"))
    )


def cap_eligible_per_lang(rows: list, max_per_lang: int | None) -> list:
    """Keep at most max_per_lang rows PER LANGUAGE, selecting the HIGHEST
    metric_primary first (id as a deterministic tie-break) -- "the top of
    the distribution is what we want to imitate," not an arbitrary first-N
    by id (which would churn on every rebuild as new rows shift the
    id-sort order). None or 0 means no cap. Applied BEFORE
    stratified_membership, so this -- not the per-split target_counts --
    is what actually bounds total judge-call spend on a rebuild."""
    if not max_per_lang:
        return rows
    by_lang: dict = defaultdict(list)
    for row in rows:
        by_lang[row.get("lang")].append(row)
    capped: list = []
    for lang_rows in by_lang.values():
        lang_rows.sort(key=lambda r: (-r.get("metric_primary", 0), str(r.get("id", ""))))
        capped.extend(lang_rows[:max_per_lang])
    return capped


def bucket_for(row_id: str, seed: str = DEFAULT_SPLIT_SEED) -> str:
    """Deterministic, seeded by row id: which split a row falls into is a
    pure function of its own id, not of what else is in the corpus this
    run -- adding new rows never reshuffles an existing row out of the
    split it was already in. Applied identically regardless of language;
    stratification then happens by grouping+capping per language, not by
    changing this function."""
    digest = hashlib.sha256(f"{seed}:{row_id}".encode("utf-8")).hexdigest()
    value = int(digest[:8], 16) % 100
    if value < SPLIT_WEIGHTS["train"]:
        return "train"
    if value < SPLIT_WEIGHTS["train"] + SPLIT_WEIGHTS["val"]:
        return "val"
    return "test"


def stratified_membership(
    rows: list, *, seed: str = DEFAULT_SPLIT_SEED,
    target_counts: dict | None = None,
) -> dict:
    """rows (already filtered to LANGS by eligible_rows) -> {lang: {split:
    [rows]}}. Each row is bucketed by bucket_for (seeded by its own id,
    language-independent), then GROUPED by language, then each
    (lang, split) list is deterministically capped (sorted by id, keep the
    first N) to target_counts[split] -- a soft cap, "taking whatever is
    available if fewer exist", never a hard requirement to hit the
    target."""
    caps = target_counts or TARGET_COUNTS_PER_LANG
    raw: dict = {lang: defaultdict(list) for lang in LANGS}
    for row in rows:
        lang = row.get("lang")
        if lang not in LANGS:
            continue
        raw[lang][bucket_for(str(row.get("id", "")), seed)].append(row)

    result: dict = {}
    for lang in LANGS:
        result[lang] = {}
        for split in SPLIT_NAMES:
            bucketed = sorted(raw[lang][split], key=lambda r: str(r.get("id", "")))
            cap = caps.get(split)
            if cap is not None and len(bucketed) > cap:
                bucketed = bucketed[:cap]
            result[lang][split] = bucketed
    return result


def find_empty_splits(membership: dict) -> list:
    """[(lang, split), ...] for every combination with zero rows -- the
    exact defect this whole stratification exists to catch (an all-en
    train split with a silently empty val, or a language missing
    entirely)."""
    return sorted(
        (lang, split)
        for lang in membership
        for split in membership[lang]
        if not membership[lang][split]
    )


def derive_subject(title: str, *, runner: Path, run_id: str, judge_fn=None) -> str | None:
    """One judge call: title -> a neutral, framing-stripped subject line.
    None on any parse/infrastructure failure -- the caller skips the row
    rather than caching a bad subject."""
    call = judge_fn if judge_fn is not None else br.call_judge
    raw = call(runner, SUBJECT_PROMPT.format(title=title), run_id)
    obj = br._extract_last_json_object(raw)
    if not obj:
        return None
    subject = str(obj.get("subject", "")).strip()
    return subject or None


SUBJECT_CACHE_FILENAME = "subject-cache.json"


def default_cache_path(split_dir: Path) -> Path:
    """data/subject-cache.json, a sibling of data/writing_split -- NOT
    inside split_dir, so `rm -rf data/writing_split` (the exact command
    that lost every already-paid-for subject from the first full build)
    cannot touch it."""
    return split_dir.parent / SUBJECT_CACHE_FILENAME


def load_subject_cache(cache_path: Path) -> dict:
    """id -> subject, from the dedicated persistent cache file. Missing or
    corrupt cache is treated as empty, never an error -- the split files
    remain a secondary source in that case (see load_existing_subjects)."""
    if not cache_path.exists():
        return {}
    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {str(k): str(v) for k, v in raw.items()} if isinstance(raw, dict) else {}


def save_subject_cache(cache_path: Path, cache: dict) -> None:
    """Overwrites the whole cache file with the current in-memory dict.
    Called after EVERY successful derivation (not just at the end of a
    build) so a process killed mid-run loses at most the one call in
    flight, never everything already paid for. Atomic via
    write-to-temp-then-replace so a kill mid-write cannot corrupt the
    existing cache."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_name(f".{cache_path.name}.tmp{os.getpid()}")
    tmp_path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8",
    )
    tmp_path.replace(cache_path)


def load_existing_subjects(split_dir: Path, cache_path: Path | None = None) -> dict:
    """id -> cached subject. PRIMARY source is the dedicated persistent
    cache (survives `rm -rf data/writing_split`, the exact sequence that
    lost the first full build's subjects); split files already on disk
    are only a SECONDARY, supplementary source for ids the cache does not
    have (e.g. a cache file that predates this mechanism, or one that was
    itself lost). Cache entries always win on conflict."""
    resolved_cache_path = cache_path if cache_path is not None else default_cache_path(split_dir)
    result: dict = dict(load_subject_cache(resolved_cache_path))

    for name in SPLIT_NAMES:
        path = split_dir / name / "items.json"
        if not path.exists():
            continue
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for item in items:
            row_id = item.get("id")
            subject = item.get("subject")
            if row_id and subject and str(row_id) not in result:
                result[str(row_id)] = str(subject)
    return result


def _counts_by_lang(items_by_split: dict) -> dict:
    counts: dict = {lang: {split: 0 for split in SPLIT_NAMES} for lang in LANGS}
    for split in SPLIT_NAMES:
        for item in items_by_split[split]:
            lang = item.get("lang")
            if lang in counts:
                counts[lang][split] += 1
    return counts


def build(
    corpus_dir: Path,
    split_dir: Path,
    *,
    limit: int = 0,
    runner: Path,
    run_id: str = "build-dataset",
    judge_fn=None,
    target_counts: dict | None = None,
    max_per_lang: int | None = DEFAULT_MAX_PER_LANG,
    cache_path: Path | None = None,
    rebuild_subjects: bool = False,
) -> dict:
    raw_rows = br.load_corpus_rows(corpus_dir)
    bare_title_excluded = count_bare_title_excluded(raw_rows)
    rows = eligible_rows(raw_rows)
    rows.sort(key=lambda r: str(r.get("id", "")))  # deterministic processing order
    if limit:
        rows = rows[:limit]
    rows_precap = len(rows)
    rows = cap_eligible_per_lang(rows, max_per_lang)

    membership = stratified_membership(rows, target_counts=target_counts)
    empties = find_empty_splits(membership)
    if empties:
        names = ", ".join(f"{lang}/{split}" for lang, split in empties)
        raise EmptySplitError(
            f"refusing to write dataset: empty split(s) for {names} -- not "
            "enough eligible rows to stratify safely; writes nothing"
        )

    resolved_cache_path = cache_path if cache_path is not None else default_cache_path(split_dir)
    # `cache` starts as a FULL copy of everything ever persisted (even ids
    # outside this run's membership) so re-saving it after each new
    # derivation never drops an entry -- --rebuild-subjects only changes
    # whether THIS run's rows are allowed to reuse their cached value, it
    # never deletes the cache itself.
    cache = dict(load_existing_subjects(split_dir, resolved_cache_path))
    generated = 0
    reused = 0
    skipped = 0
    items_by_split: dict = {name: [] for name in SPLIT_NAMES}

    for lang in LANGS:
        for split in SPLIT_NAMES:
            for row in membership[lang][split]:
                row_id = str(row.get("id", ""))
                if not row_id or not row.get("title"):
                    continue
                subject = None if rebuild_subjects else cache.get(row_id)
                if subject is None:
                    subject = derive_subject(row["title"], runner=runner, run_id=run_id, judge_fn=judge_fn)
                    if subject is None:
                        skipped += 1
                        continue
                    generated += 1
                    cache[row_id] = subject
                    # Persist after EVERY successful derivation, not just at
                    # the end of the run -- a process killed at call 600
                    # must lose at most the one call in flight, never the
                    # 600 already paid for.
                    save_subject_cache(resolved_cache_path, cache)
                else:
                    reused += 1
                items_by_split[split].append({
                    "id": row_id,
                    "subject": subject,
                    "lang": row.get("lang", "en"),
                    "title": row["title"],
                    "metric_primary": row.get("metric_primary", 0),
                    # T15 wall-clock follow-up: writing/rollout.py has no
                    # other way to tell a training-batch rollout from a
                    # held-out gate rollout (SkillOpt calls
                    # adapter.rollout() identically for both) -- this tag
                    # is that signal, carried in the data instead of
                    # trainer internals. val/test items get GATE_OPPONENTS
                    # (the score decides accept/reject); train items get
                    # the cheaper TRAIN_OPPONENTS (the score only steers
                    # reflection, no decision is made from it).
                    "split": split,
                })

    # Subject-derivation failures happen per-row, AFTER the membership
    # check above -- a skipped row can itself hollow out a (lang, split)
    # that looked fine going in. Check again post-generation so that
    # failure mode cannot silently produce an empty split either.
    counts_by_lang = _counts_by_lang(items_by_split)
    post_empties = sorted(
        (lang, split) for lang in LANGS for split in SPLIT_NAMES
        if counts_by_lang[lang][split] == 0
    )
    if post_empties:
        names = ", ".join(f"{lang}/{split}" for lang, split in post_empties)
        raise EmptySplitError(
            f"refusing to write dataset: subject generation left empty "
            f"split(s) for {names}; writes nothing"
        )

    for name in SPLIT_NAMES:
        out_dir = split_dir / name
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "items.json").write_text(
            json.dumps(items_by_split[name], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return {
        "eligible_rows_total": rows_precap,
        "eligible_rows_considered": len(rows),
        "bare_title_excluded": bare_title_excluded,
        "subjects_generated": generated,
        "subjects_reused": reused,
        "rows_skipped": skipped,
        "counts": {name: len(items_by_split[name]) for name in SPLIT_NAMES},
        "counts_by_lang": counts_by_lang,
    }


def stats(split_dir: Path, corpus_dir: Path | None = None) -> dict:
    """Read whatever split files already exist on disk and report counts
    per split per language -- so an empty-val-silent-accept defect (or a
    missing language) is visible without opening the JSON files by hand.
    When corpus_dir is given, also reports bare_title_excluded live from
    the corpus -- the bare-product-title filter must never be silent."""
    items_by_split: dict = {name: [] for name in SPLIT_NAMES}
    for name in SPLIT_NAMES:
        path = split_dir / name / "items.json"
        if not path.exists():
            continue
        try:
            items_by_split[name] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            items_by_split[name] = []
    result = {
        "counts": {name: len(items_by_split[name]) for name in SPLIT_NAMES},
        "counts_by_lang": _counts_by_lang(items_by_split),
    }
    if corpus_dir is not None:
        result["bare_title_excluded"] = count_bare_title_excluded(br.load_corpus_rows(corpus_dir))
    return result


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", default=str(CORPUS_DIR))
    parser.add_argument("--split-dir", default=str(SPLIT_DIR))
    parser.add_argument("--limit", type=int, default=0, help="cap how many eligible rows are processed (0 = all)")
    parser.add_argument("--max-per-lang", type=int, default=DEFAULT_MAX_PER_LANG,
                         help="cap the eligible pool PER LANGUAGE to this many rows (highest metric_primary "
                              "first) before stratifying -- bounds judge-call spend on every rebuild "
                              "regardless of corpus size; 0 disables the cap")
    parser.add_argument("--run-id", default="build-dataset")
    parser.add_argument("--stats", action="store_true",
                         help="print counts per split per language from the split files already on disk, and exit (no build)")
    parser.add_argument("--rebuild-subjects", action="store_true",
                         help="explicit opt-in: force re-derivation of subjects for this run's rows even if "
                              "already cached (the persistent cache itself is NEVER deleted -- this only "
                              "skips reusing cached values for rows that are part of this run). Default off.")
    args = parser.parse_args(argv)

    if args.stats:
        print(json.dumps(stats(Path(args.split_dir), Path(args.corpus_dir)), ensure_ascii=False))
        return 0

    try:
        result = build(
            Path(args.corpus_dir), Path(args.split_dir),
            limit=args.limit, runner=br._default_runner(), run_id=args.run_id,
            max_per_lang=args.max_per_lang, rebuild_subjects=args.rebuild_subjects,
        )
    except EmptySplitError as exc:
        print(f"build_dataset.py: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
