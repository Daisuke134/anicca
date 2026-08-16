#!/usr/bin/env python3
"""category_bandit.py -- arm = category, reward = funnel depth. Numbers pick the category.

THIS DOCSTRING IS THE SPEC. Same convention as listing_ledger.py: the module that
owns a taxonomy states it. (docs/ sits behind the 2026-07-17 default-deny allowlist,
so design notes that are not explicitly allowlisted do not live in the repo.)
Status and live evidence: docs/loop-engineering/26-gig-loop-asis-tobe-plan.md, X8 row.

WHY THIS EXISTS
  strategy.json's priority_categories / skip_categories were produced entirely by LLM
  hypothesis across 537 passes and 71 experiments. Nothing tied that ordering to what
  actually earned money. This module makes category selection a Thompson-sampling
  bandit over the ledgers, so the ordering is measured rather than asserted.

AUTHORITY BOUNDARY (the whole point of not colliding with the existing self-improver)

  category selection order .... THIS MODULE. Measured outcome beats hypothesis.
  wording / price / templates / profile / search_strategy .... LLM experiments[]
      keep/revert. Those dimensions are linguistic and thinly measured; they are not
      arms.
  skip_categories (capability / ethics exclusions) .... LLM, unchanged. "cannot be
      physically present", "cannot draw", "violates ToS" are not performance claims.
      A bandit that overrides them on reward would win work it cannot deliver. This
      module never resurrects a skipped category.

  Structurally, this module NEVER WRITES strategy.json. It is read-only and emits a
  ranking; the consumer reads it at selection time. keep/revert may keep rewriting
  priority_categories -- the bandit's output depends only on the observation ledgers,
  so two writers never fight over one field.

REWARD (the only hand-set numbers here; they price funnel *stages*, never *arms*)
  applied 0.00 -> engaged 0.15 -> contracted 0.40 -> paid 1.00, highest stage reached.

EVIDENCE GATE
  An observation counts only if the row carries a usable posting identity (same
  placeholder rules as listing_ledger: "N/A" is not an identity) AND a non-empty
  category. Measured: the two rows whose category field held "thread_closeout" /
  "nurture_sweep" both had requestId "N/A" -- the gate drops them without any keyword
  list, because judging a category by a hardcoded string is exactly what this module
  exists to abolish.

ALGORITHM: Thompson sampling (Beta, empirical-Bayes prior). Chosen from the measured
data volume, not from taste. Live ledger: 224 applications, 27 with a category, 23
resolved trials, 29 arms, a few applications per day.

  UCB1        bonus = sqrt(2 ln t / n). At t=25, n=1 that is ~2.5 on a [0,1] reward
              scale, so the confidence term swallows the mean and UCB1 degenerates
              into a deterministic round-robin over 29 arms. Undefined at n=0, so it
              needs ~29 passes of pure exploration before it exploits anything.
  eps-greedy  With zero positive rewards observed, the greedy arm is a tie-break
              artifact, and 1-eps of the traffic goes to it. Cold-start arms receive
              eps/|A| ~ 0.25%. eps must also be hand-set -- a hardcoded judgement.
  Thompson    Posterior width budgets exploration by itself. A zero-observation arm
              keeps the full-width prior and stays reachable forever, so a new
              category is never permanently starved; at n=0 it degrades to sampling
              the prior rather than to an arbitrary argmax. Seeded RNG makes it
              deterministic for tests. Also the better fit for delayed feedback:
              UCB's bonus shrinks at pull time while the reward lands days later.

PRIOR: alpha = k*m + sum(r), beta = k*(1-m) + sum(1-r), with m = mean reward over all
resolved trials (empirical Bayes) and k = PRIOR_STRENGTH = 2 pseudo-trials.
  k=2 because arms hold 1-8 real observations: strong enough that one lucky trial
  cannot vault an arm to the top, weak enough that ~4 observations visibly move the
  posterior. Larger k pins every arm to m and nothing is learned; smaller k learns
  the noise of n=1.
  m rather than 0.5 so a zero-observation arm enters as an *average* arm instead of
  outranking an arm with twenty real observations behind it.

DELAYED FEEDBACK
  Apply -> pay takes days. Counting a fresh application as a zero would make every
  recently-tried category look bad, which kills exploration permanently. Applications
  younger than RESOLUTION_HORIZON_DAYS are excluded from the posterior and reported
  as in_flight.

CONTRACT
  select() never raises, never returns a non-list ranking, and exits 0 from the CLI.
  Below MIN_TRIALS resolved observations -- which is the state as of 2026-07-27, where
  zero categorised applications have any downstream outcome -- it returns
  priority_categories verbatim with status="insufficient_data". A bandit failure must
  never be the reason the loop stops applying.
"""

import argparse
import importlib.util
import json
import random
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

_HERE = Path(__file__).resolve().parent


def _load_sibling(filename: str, alias: str):
    spec = importlib.util.spec_from_file_location(alias, _HERE / filename)
    if spec is None or spec.loader is None:  # pragma: no cover - packaging accident
        raise RuntimeError(f"{filename} not importable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


listing_ledger = _load_sibling("listing_ledger.py", "listing_ledger_for_bandit")
# The bandit does not decide what an application is or how far it got -- that taxonomy
# lives in one place so the funnel, the reports and this file cannot disagree.
application_ledger = _load_sibling("application_ledger.py", "application_ledger_for_bandit")

DAY = 86400.0

# Funnel stage -> reward. Ordered shallow to deep; only the deepest stage reached counts.
STAGE_REWARD: dict[str, float] = {
    "applied": 0.00,
    "engaged": 0.15,
    "contracted": 0.40,
    "paid": 1.00,
}

# Which recorded status means which stage. Anything unrecognised is "applied" (stage 0):
# an unknown status is not evidence of progress.
STATUS_STAGE: dict[str, str] = {
    "replied": "engaged",
    "followed_up": "engaged",
    "delivered_pending": "contracted",
    "delivered": "contracted",
}

PRIOR_STRENGTH = 2.0          # pseudo-trials; see spec 5.2 for why 2 and not 0.5 or 10
RESOLUTION_HORIZON_DAYS = 7.0
MIN_TRIALS = 8
_PRIOR_MEAN_FLOOR = 0.05      # keeps Beta parameters non-degenerate when nothing has paid
_PRIOR_MEAN_CEIL = 0.95


def state_dir() -> Path:
    return listing_ledger.state_dir()


def normalize_label(value: Any) -> str:
    """NFKC, strip, collapse internal whitespace. No case folding -- labels are Japanese."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).strip()
    return " ".join(text.split())


def skip_tokens(entries: Iterable[Any]) -> set[str]:
    """Normalised labels named by skip_categories.

    strategy.json's own format is "label (why it is skipped)" and labels may pack
    variants with slashes ("イラスト/VTuber/Live2D/キャラデザ (art skill required)").
    We parse that format and match EXACTLY on the resulting tokens. Loose/substring
    matching was rejected on measurement: the skip token "データ入力" is a substring of
    the live priority category "文字起こし・データ入力代行", so substring matching would
    silently delete a category the loop is supposed to work. Listing-level capability
    screening (B2) stays the authoritative gate; this filter only stops the bandit from
    *promoting* something already excluded.
    """
    out: set[str] = set()
    for entry in entries or ():
        text = normalize_label(entry)
        if not text:
            continue
        head = text.split(" (", 1)[0].strip()
        for token in head.split("/"):
            token = token.strip()
            if token:
                out.add(token)
    return out


@dataclass
class Arm:
    arm: str
    trials: int = 0
    reward_sum: float = 0.0
    in_flight: int = 0
    paid_trials: int = 0
    stage_counts: dict[str, int] = field(default_factory=dict)

    def observe(self, stage: str, reward: float) -> None:
        self.trials += 1
        self.reward_sum += reward
        self.stage_counts[stage] = self.stage_counts.get(stage, 0) + 1
        if stage == "paid":
            self.paid_trials += 1


def _read_jsonl(path: Path | str | None) -> list[dict] | None:
    """Rows of a jsonl ledger, corrupt lines dropped. None means the file is unreadable."""
    if path is None:
        return None
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _read_strategy(path: Path | str | None) -> dict | None:
    if path is None:
        return None
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def has_identity(row: dict) -> bool:
    """Reuses listing_ledger's placeholder rules -- one definition of 'a real id'."""
    return bool(listing_ledger.normalize_service_ids(row.get("requestId")))


def collect_arms(
    applied_rows: Sequence[dict],
    earnings_rows: Sequence[dict],
    *,
    now: float,
    chain=None,
    horizon_days: float = RESOLUTION_HORIZON_DAYS,
) -> dict[str, Arm]:
    """One trial per 募集, at the deepest stage the application ledger can prove.

    Two things changed here and both were wrong before:
      * a trial used to be a ROW, so one 募集 that was applied to and then replied to
        scored twice -- once as a failure and once as a success;
      * a payment used to be attributed by exact title, because earnings.requestId is a
        talkroom id and applied.requestId is a 募集 id. Attribution now runs through the
        recorded identity chain, and an unlinked payment earns nobody a reward.
    """
    if chain is None:
        chain = application_ledger.IdentityChain.from_links([])
    ledger = application_ledger.build(applied_rows, earnings_rows, chain=chain)
    arms: dict[str, Arm] = {}
    horizon = horizon_days * DAY
    for observation in ledger.observations:
        category = normalize_label(observation.category)
        if not category:
            continue
        arm = arms.setdefault(category, Arm(arm=category))
        stage = observation.stage
        # A trial whose outcome window is still open is neither a success nor a failure,
        # unless it has already resolved upward (a payment is resolved the moment it lands).
        if (observation.ts is not None and now - observation.ts < horizon
                and stage != application_ledger.STAGE_PAID):
            arm.in_flight += 1
            continue
        arm.observe(stage, STAGE_REWARD[stage])
    return arms


def _posterior(arm: Arm, prior_mean: float, prior_strength: float) -> tuple[float, float]:
    alpha = prior_strength * prior_mean + arm.reward_sum
    beta = prior_strength * (1.0 - prior_mean) + (arm.trials - arm.reward_sum)
    return max(alpha, 1e-6), max(beta, 1e-6)


def select(
    *,
    applied_path: Path | str | None = None,
    earnings_path: Path | str | None = None,
    strategy_path: Path | str | None = None,
    listing_path: Path | str | None = None,
    chain_path: Path | str | None = None,
    now: float | None = None,
    seed: int | None = None,
    min_trials: int = MIN_TRIALS,
    horizon_days: float = RESOLUTION_HORIZON_DAYS,
    prior_strength: float = PRIOR_STRENGTH,
) -> dict:
    """Rank categories by Thompson sampling. Never raises; ranking is always a list."""
    try:
        return _select(
            applied_path=applied_path, earnings_path=earnings_path,
            strategy_path=strategy_path, listing_path=listing_path,
            chain_path=chain_path,
            now=now, seed=seed, min_trials=min_trials,
            horizon_days=horizon_days, prior_strength=prior_strength,
        )
    except Exception as exc:  # never let the bandit stop the money path
        priority = []
        data = _read_strategy(strategy_path)
        if data:
            priority = [normalize_label(c) for c in data.get("priority_categories") or []]
        return {
            "status": "error",
            "reason": f"{type(exc).__name__}: {exc}",
            "decided_by": "fallback",
            "ranking": [{"arm": c, "trials": 0} for c in priority if c],
        }


def _fallback(status: str, priority: list[str], **extra) -> dict:
    out = {
        "status": status,
        "decided_by": "fallback",
        "ranking": [{"arm": c, "trials": 0, "in_flight": 0, "paid_trials": 0}
                    for c in priority],
    }
    out.update(extra)
    return out


def _select(*, applied_path, earnings_path, strategy_path, listing_path, chain_path,
            now, seed, min_trials, horizon_days, prior_strength) -> dict:
    import time
    now = time.time() if now is None else float(now)

    strategy = _read_strategy(
        strategy_path if strategy_path is not None else state_dir() / "strategy.json")
    if strategy is None:
        return _fallback("strategy_unavailable", [],
                         reason="strategy.json missing or unparseable")

    priority = [normalize_label(c) for c in strategy.get("priority_categories") or []]
    priority = [c for c in priority if c]
    skipped = skip_tokens(strategy.get("skip_categories") or [])
    priority = [c for c in priority if c not in skipped]

    applied_rows = _read_jsonl(
        applied_path if applied_path is not None else state_dir() / "applied.jsonl")
    if applied_rows is None:
        return _fallback("ledger_unavailable", priority,
                         reason="applied.jsonl missing or unreadable")
    earnings_rows = _read_jsonl(
        earnings_path if earnings_path is not None else state_dir() / "earnings.jsonl") or []

    chain = application_ledger.IdentityChain.load(chain_path)
    arms = collect_arms(applied_rows, earnings_rows, now=now, chain=chain,
                        horizon_days=horizon_days)
    attribution = application_ledger.build(applied_rows, earnings_rows, chain=chain)
    for name in priority:                      # cold-start arms enter the universe
        arms.setdefault(name, Arm(arm=name))
    for name in list(arms):
        if name in skipped:
            del arms[name]

    resolved = sum(a.trials for a in arms.values())
    coverage = {
        "applied_rows": len(applied_rows),
        "rows_with_category": sum(1 for r in applied_rows if normalize_label(r.get("category"))),
        "clean_observations": resolved + sum(a.in_flight for a in arms.values()),
        "resolved_trials": resolved,
        "earnings_rows": len(earnings_rows),
        "listing": _listing_coverage(listing_path),
        # What the identity chain could and could not attribute. Exposed so a thin
        # ranking is legible as "we cannot see outcomes" rather than "these arms are bad".
        "attribution": attribution.coverage(),
    }

    if resolved < min_trials:
        return _fallback(
            "insufficient_data", priority,
            reason=f"{resolved} resolved trials < min_trials={min_trials}",
            coverage=coverage)

    total_reward = sum(a.reward_sum for a in arms.values())
    prior_mean = min(max(total_reward / resolved, _PRIOR_MEAN_FLOOR), _PRIOR_MEAN_CEIL)
    rng = random.Random(seed)

    ranking = []
    for name in sorted(arms):                  # sorted so the seeded draw order is fixed
        arm = arms[name]
        alpha, beta = _posterior(arm, prior_mean, prior_strength)
        ranking.append({
            "arm": name,
            "sample": rng.betavariate(alpha, beta),
            "posterior_mean": alpha / (alpha + beta),
            "alpha": alpha,
            "beta": beta,
            "trials": arm.trials,
            "reward_sum": arm.reward_sum,
            "in_flight": arm.in_flight,
            "paid_trials": arm.paid_trials,
            "stages": dict(arm.stage_counts),
        })
    ranking.sort(key=lambda a: a["sample"], reverse=True)

    return {
        "status": "ok",
        "decided_by": "thompson_sampling",
        "prior_mean": prior_mean,
        "prior_strength": prior_strength,
        # Zero total reward is real evidence (these arms were tried and produced
        # nothing) and should still steer, but the ranking must not read as a
        # confident recommendation when nothing has ever succeeded. Surfaced, not
        # suppressed -- as of 2026-07-27 this is true on the live ledger.
        "no_positive_reward_observed": total_reward <= 0.0,
        "seed": seed,
        "coverage": coverage,
        "ranking": ranking,
    }


def _listing_coverage(listing_path) -> dict:
    """Listing-side diagnostic ONLY -- counted through listing_ledger, never re-derived.

    Not a reward: measured category coverage on shuppin.jsonl is 4/104, so folding it
    into the posterior would let four rows steer everything.
    """
    if listing_path is None:
        return {"consulted": False}
    try:
        events = listing_ledger.load_events(listing_path)
        counts = listing_ledger.count(events)
        return {
            "consulted": True,
            "published_listings": counts.published_listings,
            "known_listings": counts.known_listings,
        }
    except Exception:
        return {"consulted": False}


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--applied", default=None)
    parser.add_argument("--earnings", default=None)
    parser.add_argument("--strategy", default=None)
    parser.add_argument("--listing", default=None)
    parser.add_argument("--chain", default=None,
                        help="identity_chain.jsonl -- 募集 id <-> talkroom id")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--top", type=int, default=0, help="print only the top N arms")
    args = parser.parse_args(argv)

    result = select(
        applied_path=args.applied or state_dir() / "applied.jsonl",
        earnings_path=args.earnings or state_dir() / "earnings.jsonl",
        strategy_path=args.strategy or state_dir() / "strategy.json",
        listing_path=args.listing or state_dir() / "shuppin.jsonl",
        chain_path=args.chain or state_dir() / application_ledger.CHAIN_FILENAME,
        seed=args.seed,
    )
    if args.top > 0:
        result = dict(result, ranking=result["ranking"][:args.top])
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0            # a counter/selector must never fail the pass that calls it


if __name__ == "__main__":
    raise SystemExit(_main())
