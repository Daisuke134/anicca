"""Read-only bridge from Manager to the already trained HBCP study-arm model.

This is deliberately NOT a general behavior foundation model, not clinical
guidance, not an intervention policy and not permission to contact anyone.
The first real product boundary abstains on sparse/unknown input instead of
pretending the RCT arm model can predict a specific person's health outcome.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Mapping, Any
import json

# No live Manager Core actions are imported; this adapter is read-only.

# Pinned SHA256 of source-controlled, inspectable JSON model weights.
# Only the accepted training job may change this along with a model card.
MODEL_FILE = Path(__file__).resolve().parents[1] / "models/checkpoints/manager-hbcp-ridge-arm-rate-v0.json"
EXPECTED_MODEL_SHA256 = "2e79c075903b95462659f4f8067f5921cb26c7e687d76e62b6d6a48b5455f0bb"


@dataclass(frozen=True)
class ReadOnlyPrediction:
    status: str
    label: str
    predicted_rate_pct: float | None
    evidence_kind: str
    model_id: str | None
    reason: str
    causal_effect_estimated: bool = False
    approved_for_clinical_use: bool = False
    may_execute_intervention: bool = False


def _loaded_model() -> dict:
    if not MODEL_FILE.is_file():
        raise RuntimeError("pinned outcome-head model not deployed")
    content = MODEL_FILE.read_bytes()
    if sha256(content).hexdigest() != EXPECTED_MODEL_SHA256:
        raise ValueError("outcome-head checkpoint digest mismatch")
    return json.loads(content)


def predict_published_study_arm(
    evidence: Mapping[str, Any],
    *,
    aggregate_study_arm_verified: bool = False,
) -> ReadOnlyPrediction:
    """Make a research-only forecast after independent aggregate-scope check.

    Does not log input, send data to a provider, schedule a reminder, diagnose,
    prescribe, act or expose sensitive individual medical history.
    """
    no = lambda reason: ReadOnlyPrediction(
        "ABSTAIN", "research_RCT_arm_rate", None, "NOT_INTERVENTION_EFFICACY",
        None, reason,
    )
    if aggregate_study_arm_verified is not True:
        return no("NOT_VERIFIED_AGGREGATE_RCT_STUDY_ARM")
    if not isinstance(evidence, Mapping):
        return no("WRONG_INPUT_SHAPE")
    try:
        model = _loaded_model()
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError):
        return no("PINNED_MODEL_UNAVAILABLE")
    fields = set(model["feature_names"])
    if set(evidence) - fields:
        return no("UNEXPECTED_FEATURE_OR_IDENTIFIER")
    coded = sum(
        1 for value in evidence.values()
        if value in (0, 1, 0.0, 1.0, "0", "1")
    )
    if coded < 5:
        return no("NOT_ENOUGH_AGGREGATE_STUDY_CONTEXT")
    # Import the domain-specific numeric JSON model only when explicitly called.
    from models.manager_hbcp_ridge_head import predict_json
    try:
        pct = predict_json(model, evidence)
    except (ValueError, KeyError, TypeError):
        return no("UNSUPPORTED_FEATURE_VALUES")
    return ReadOnlyPrediction(
        status="PREDICTION_ONLY",
        label="aggregate_RCT_arm_smoking_cessation_percent",
        predicted_rate_pct=pct,
        evidence_kind="OBSERVATIONAL_FORECAST_ON_ANNOTATED_RCT_ARMS",
        model_id=model["model_id"],
        reason="External published trial-arm outcome projection. No causal or clinical authority.",
    )
