"""Rollout helper for the writing-craft SkillOpt env -- REAL scorer
(spec 47 19-4c T6, BUILD 2), replacing the feasibility-probe stub.

The target model writes a headline for the item's `subject` (never its
real title -- see writing/dataloader.py and build_dataset.py) under the
CURRENT CRAFT.md as its system prompt. The headline is then scored by its
blind pairwise beat rate against real corpus opponents, computed by
REUSING scripts/beat_rate.py's own functions (select_opponent_pool,
sample_opponents, score_candidate, CallBudget, call_judge) -- one judge,
one prompt, one position-bias policy, not a second pairwise judge
reimplemented here. The opponent pool EXCLUDES the item's own corpus row,
or the model would be scored against the very answer it is being asked
to reproduce.

hard/soft mapping: `soft` is the beat_rate itself (already in [0, 1]);
`hard` is 1 if beat_rate > 0.5 (beats the median opponent) else 0, giving
the optimizer's reflection stage a real win/lose contrast instead of the
probe stub's constant. A judge failure inside beat_rate.py's own pairwise
calls already becomes a null pair excluded from that mean (never a zero)
-- this file does not re-implement that guarantee, it inherits it by
calling the real functions.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from skillopt.model import chat_target

_ARTICLE_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
if str(_ARTICLE_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_ARTICLE_SCRIPTS_DIR))

import beat_rate as br  # noqa: E402  (path mutation above is required first)

# Round-4/T15 follow-up: the held-out GATE decision (accept/reject a
# CRAFT.md edit, see craft_train.py) must not run on a noisy sample. Each
# opponent contributes 2 raw binary judge outcomes (both position-bias
# orderings), so n = opponents_k*2 comparisons; the worst-case standard
# error of a proportion is sqrt(0.5*0.5/n). At the old flat default of 5
# opponents (n=10) a real spot-check (same title, two runs) swung
# beat_rate 0.00 -> 0.30 purely from resampling -- at n=8 (4 opponents,
# one of the two runs) SE~=0.18, so a 0.30 swing was under 2 SE: noise
# wearing the costume of a measurement. At GATE_OPPONENTS=15 (n=30)
# SE~=0.09 -- see craft_train.py's MARGIN_MULTIPLIER for how this SE
# becomes an accept/reject decision.
#
# GATE_OPPONENTS=15 for every rollout was the first fix, but 15 opponents
# buys a trustworthy decision only for val/test items -- during a TRAINING
# rollout the score just steers the optimizer's reflection stage, no
# accept/reject decision is made from it, so paying the same 15-opponent
# price there was pure waste (at the real split sizes, ~8,000 judge calls
# and ~22 hours serial, running straight through the 06:00 publish).
# rollout.py itself has no signal distinguishing the two -- SkillOpt's
# trainer.py calls adapter.rollout(env, skill, out_dir) identically for
# both -- so the signal now lives in the DATA instead: build_dataset.py
# stamps item["split"] onto every row it writes (and dataloader.py falls
# back to the directory name for older split files that predate the
# field). TRAIN_OPPONENTS is the cheap rate for split=="train"; every
# other value (val/test, or a missing/unrecognized tag -- fail safe
# toward the trustworthy side, not the cheap one) gets GATE_OPPONENTS.
TRAIN_OPPONENTS = 5
GATE_OPPONENTS = 15
DEFAULT_MAX_CALLS = 60
HARD_WIN_THRESHOLD = 0.5


def _opponents_for_item(item: dict) -> int:
    """GATE_OPPONENTS for val/test (and anything untagged -- fail safe
    toward the trustworthy, more expensive side); TRAIN_OPPONENTS only for
    an item explicitly tagged split=="train"."""
    return TRAIN_OPPONENTS if item.get("split") == "train" else GATE_OPPONENTS


def _corpus_dir() -> Path:
    return Path(os.environ.get(
        "WRITING_CORPUS_DIR",
        str(Path(__file__).resolve().parent.parent.parent.parent / "state" / "writing-corpus"),
    ))


def score_headline(
    headline: str,
    item: dict,
    *,
    run_id: str,
    runner: Path | None = None,
    opponents_k: int = GATE_OPPONENTS,
    max_calls: int = DEFAULT_MAX_CALLS,
    judge_fn=None,
    corpus_rows: list | None = None,
) -> dict:
    """Score one generated headline against real corpus opponents for the
    item's language, excluding the item's own row. Returns beat_rate.py's
    score_candidate() result dict unchanged ({"beat_rate", "pairs", ...}),
    or {"beat_rate": None, "pairs": []} if no opponent pool is available
    (e.g. a language with too few corpus rows) -- an infrastructure gap,
    not a quality verdict, so the caller must not treat it as a loss."""
    lang = item.get("lang", "en")
    rows = corpus_rows if corpus_rows is not None else br.load_corpus_rows(_corpus_dir())
    own_id = str(item.get("id", ""))
    rows_excluding_self = [r for r in rows if str(r.get("id", "")) != own_id]

    pool = br.select_opponent_pool(rows_excluding_self, lang)
    if not pool:
        return {"beat_rate": None, "pairs": []}

    resolved_runner = runner if runner is not None else br._default_runner()
    opponents = br.sample_opponents(pool, run_id, lang, opponents_k)
    budget = br.CallBudget(max_calls)
    resolved_judge_fn = judge_fn if judge_fn is not None else br.call_judge
    return br.score_candidate(
        headline, "chosen", None, opponents,
        runner=resolved_runner, run_id=run_id, budget=budget, judge_fn=resolved_judge_fn,
    )


def build_user_prompt(item: dict) -> str:
    """The exact text sent to the target model. Pure and side-effect free
    so the contract test can assert the real title never appears in it,
    without calling chat_target. Uses ONLY item['subject'] (the neutral,
    framing-stripped line build_dataset.py cached) -- item['title'] and
    item['reference_title'] (the real, previously-published headline)
    must never appear here, or the model could just echo the answer back
    (see build_dataset.py's module docstring)."""
    return (
        "Write ONE headline for this subject, in the language given. Reply "
        "with only the headline, nothing else.\n\n"
        f"Subject: {item['subject']}\n"
        f"Language: {item.get('lang', 'en')}\n"
    )


def _rollout_one(item: dict, skill_content: str, *, prediction_dir: Path,
                 max_completion_tokens: int, run_id: str, corpus_rows: list | None) -> dict:
    system = skill_content
    user = build_user_prompt(item)
    prediction, _usage = chat_target(
        system=system,
        user=user,
        max_completion_tokens=max_completion_tokens,
    )

    scored = score_headline(
        prediction, item, run_id=run_id, corpus_rows=corpus_rows,
        opponents_k=_opponents_for_item(item),
    )
    beat_rate = scored.get("beat_rate")
    soft = beat_rate if beat_rate is not None else 0.0
    hard = 1 if (beat_rate is not None and beat_rate > HARD_WIN_THRESHOLD) else 0

    safe_id = str(item["id"]).replace(":", "_").replace("/", "_")
    task_dir = prediction_dir / safe_id
    task_dir.mkdir(parents=True, exist_ok=True)
    conversation = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
        {"role": "assistant", "content": prediction},
    ]
    (task_dir / "conversation.json").write_text(
        json.dumps(conversation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "id": str(item["id"]),
        "hard": hard,
        "soft": soft,
        "predicted_answer": prediction,
        "task_description": item.get("subject", ""),
        "reference_title": item.get("reference_title", ""),
        "beat_rate": beat_rate,
        "opponent_pairs": scored.get("pairs", []),
        "task_type": item.get("task_type", "writing"),
        "target_system_prompt": system,
        "target_user_prompt": user,
        "n_turns": 1,
    }


def run_batch(*, items: list, skill_content: str, out_root: str,
              workers: int = 1, max_completion_tokens: int = 256,
              run_id: str = "craft-train") -> list:
    """Run a batch of episodes sequentially. Corpus rows are loaded ONCE
    per batch (not once per item) -- it is the same file for every item
    in a run, and the per-item exclusion filter is applied fresh each
    time from that shared, already-loaded list."""
    os.makedirs(out_root, exist_ok=True)
    prediction_dir = Path(out_root, "predictions")
    corpus_rows = br.load_corpus_rows(_corpus_dir())
    results = [
        _rollout_one(item, skill_content,
                     prediction_dir=prediction_dir,
                     max_completion_tokens=max_completion_tokens,
                     run_id=run_id,
                     corpus_rows=corpus_rows)
        for item in items
    ]
    Path(out_root, "rollouts.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return results
