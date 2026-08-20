"""SkillOpt env package for the writing-craft feasibility probe.

Why this exists: spec 47 section 19-4b/20 gave us tools that find which rule
is guilty (beat_rate.py, rule_blame.py, goodhart.py, rule_conflicts.py).
Nothing so far EDITS the guilty rule. SkillOpt is a candidate for that job
(bounded edits, held-out gate, learning rate, automatic revert) -- this
package is a feasibility PROBE of whether SkillOpt's harness can even run
against our infrastructure, not a real training environment yet. See
../FEASIBILITY.md for what one epoch actually did.
"""
