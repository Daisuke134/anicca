# Peer Review Response Editor — verified demonstration

## Concrete input

```text
Decision: Major revision. Resubmit within 60 days.

Reviewer 1: "The manuscript needs a sensitivity analysis to show whether the
primary finding changes under an alternative exclusion rule. Please clarify the
methods and revise the discussion accordingly."

Manuscript evidence:
- The submitted study used the pre-specified primary exclusion rule.
- No alternative exclusion-rule analysis has been run.
- Methods section 2.4 currently says: "Participants meeting the pre-specified
exclusion criteria were removed before the primary analysis."
- Discussion section 4.2 currently says: "The finding should be interpreted in
the context of the pre-specified analysis plan."

Constraint: Do not state that a new analysis was completed. Draft a respectful
response and a revision plan.
```

## Actual output

```text
Decision summary
Major revision; the supplied deadline is 60 days. Reviewer 1 requests an
alternative exclusion-rule sensitivity analysis plus clearer methods and
discussion text. The supplied evidence does not show that the analysis has been
completed.

Response to Reviewer 1
Thank you for identifying the need to assess how the primary finding behaves
under an alternative exclusion rule. The submitted analysis used the
pre-specified exclusion criteria. We will not state that an alternative analysis
has been completed because no result was supplied. In the revision, we will
[TBD: decide whether to run and report the requested sensitivity analysis]. We
will also clarify in Methods section 2.4 that the primary analysis followed the
pre-specified exclusion criteria, and revise Discussion section 4.2 to describe
this as a limitation of the current evidence.

Revision plan
| Comment | Status | Manuscript location | Action | Evidence gap |
| --- | --- | --- | --- | --- |
| Alternative exclusion-rule sensitivity analysis | needs evidence | [TBD: Results section] | Decide whether to run the analysis; report only author-supplied results | No analysis result supplied |
| Clarify methods | supported | 2.4 | State that the primary analysis used pre-specified exclusion criteria | Confirm final wording |
| Revise discussion | supported | 4.2 | Add limitation that alternative-rule robustness is not established here | Confirm author-approved wording |

Honesty check
- No new analysis, result, citation, page number, or completed revision was asserted.
- [TBD] remains for the decision and any result from the requested sensitivity analysis.
```

## Verification notes

1. The output contains a separate response for the supplied reviewer request.
2. Every factual statement is traceable to the concrete input: the decision,
   the request, the pre-specified rule, the absence of the alternative analysis,
   and the two supplied section locations.
3. The output explicitly avoids saying the sensitivity analysis was completed;
   it marks the analysis and its result as `[TBD]`.
4. The output follows the skill contract: decision summary, point-by-point
   response, revision plan, and honesty check. It does not browse, access a
   journal system, contact an editor, or submit anything.
