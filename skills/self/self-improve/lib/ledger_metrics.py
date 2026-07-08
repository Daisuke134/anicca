#!/usr/bin/env python3
"""ledger_metrics.py — shared read-only ledger scoring helper for per-loop evaluators (REQ-LV-110).
Copy+tweak base for the clip/affiliate/video/gig/bounty evaluator.py wrappers. Pure: reads a jsonl
ledger file (read-only) and returns a combined_score float. Deterministic — no randomness, no LLM
judge (Verifier's Law). Never imports an order/post/execution module, never writes to any ledger.
"""
import json


def load_ledger_rows(ledger_path):
    rows = []
    try:
        with open(ledger_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except FileNotFoundError:
        pass
    return rows


def score_from_rows(rows, view_weight=1.0, earn_weight=1.0):
    """Deterministic combined_score: mean views/row (view_weight) + total confirmed earn
    (earn_weight, USDC or JPY depending on the loop's own ledger field). Both terms are optional
    per row — a missing field contributes 0, never a fabricated value.

    Earn field fallback chain (F-ITER3-4 fix): earn_usdc -> earn_jpy -> commission_jpy. Widened
    (never narrowed) to match each real loop ledger's own field name — commission_jpy is what
    affiliate_verify.py actually writes to ~/.cloak/affiliate-metrics.jsonl (REQ-LV-014's row
    shape). Adding this key is purely additive: clip/video/gig/bounty rows never carry a
    commission_jpy field, so their scoring is unaffected."""
    n = len(rows)
    total_views = sum(float(r.get("views") or 0) for r in rows)
    total_earn = sum(float(r.get("earn_usdc") or r.get("earn_jpy") or r.get("commission_jpy") or 0) for r in rows)
    mean_views = (total_views / n) if n else 0.0
    return view_weight * mean_views + earn_weight * total_earn


def evaluate_stage1_generic(ledger_path, view_weight=1.0, earn_weight=1.0):
    rows = load_ledger_rows(ledger_path)
    score = score_from_rows(rows, view_weight=view_weight, earn_weight=earn_weight)
    return {"combined_score": score, "rows_evaluated": len(rows)}
