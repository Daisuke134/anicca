"""G3 Manager Zero-UI P0 *offline* public-aggregate shadow.

NOT a covert observer, an autonomous action executor or a user profiling
service. The product need not show extra UI after a legitimate host-provided
grant, but the host's real consent/revocation remains mandatory. HMAC fixture
grants demonstrate only offline tests; this code cannot authorize live effects.

There are no provider imports, network calls, disk writes or actuators.
All receipts say world_action=NO_ACTION, even with a valid grant and a
candidate model score. Only 30+ public aggregate observations are admissible.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import isfinite
import re
from typing import Any

from .authority import AuthorityVerifier, Grant

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
SCHEMA = "manager.zero_ui.shadow.v0"


def _deny(reason: str)->dict:
    return {
        "schema":SCHEMA,
        "status":"NO_ACTION",
        "reason":reason,
        "world_action":"NO_ACTION",
        "requires_extra_ui_or_prompt":False,
        "notifications_sent":0,
        "provider_writes":0,
        "personal_profile_created":False,
        "real_world_intervention":False,
        "no_live_authority_from_fixture":True,
    }


def _valid_public_observation(signal: Any, at: datetime) -> bool:
    if type(signal) is not dict or set(signal) != {
            "source","group_size","source_sha256","observed_at"}:
        return False
    if signal["source"] != "public_aggregate":
        return False
    if type(signal["group_size"]) is not int or signal["group_size"]<30:
        return False
    if not isinstance(signal["source_sha256"],str) or not _HEX64.fullmatch(signal["source_sha256"]):
        return False
    if type(signal["observed_at"]) is not str:
        return False
    try:
        obs=datetime.fromisoformat(signal["observed_at"])
    except (ValueError,TypeError):
        return False
    return (obs.utcoffset() is not None
            and obs <= at <= obs+timedelta(days=7))


def _valid_model_receipt(model: Any) -> bool:
    if type(model) is not dict or set(model)!={
        "source","domain","model_sha256","prediction",
        "train_mean_baseline","promoted_for_real_users"}:
        return False
    if (model["source"]!="trained_public_aggregate_head"
            or model["domain"]!="HBCP_PUBLISHED_SMOKING_CESSATION_RCT_ARMS"
            or model["promoted_for_real_users"] is not False
            or not isinstance(model["model_sha256"],str)
            or not _HEX64.fullmatch(model["model_sha256"])):
        return False
    return all(type(model[k]) in (float,int)
               and isfinite(model[k])
               and 0<=model[k]<=100
               for k in ("prediction","train_mean_baseline"))


def evaluate_shadow(signal: dict,
                    aggregate_model_receipt: dict,
                    *,
                    enabled: bool = False,
                    at: datetime | None = None,
                    verifier: AuthorityVerifier | None = None,
                    grant: Grant | None = None,
                    signature: str | None = None) -> dict:
    """Return a bounded counterfactual research receipt; cannot deliver anything.

    No interactive input or per-event confirmation is asked. Valid consent
    must originate in the authorized host environment. A developer-signed
    offline fixture grant is *not* real-world consent, nor is public
    aggregate information a proxy for personally observed behavior.
    """
    if type(enabled) is not bool:
        raise ValueError("exact enabled bool required")
    if not enabled:
        return _deny("SHADOW_DISABLED")
    if not isinstance(at,datetime) or at.utcoffset() is None:
        return _deny("MISSING_RELIABLE_TIME")
    if type(verifier) is not AuthorityVerifier or type(grant) is not Grant or type(signature) is not str:
        return _deny("NO_VERIFIED_SCOPE")
    try:
        verifier.authorize(
            grant,signature,domain="manager",action="shadow.observe",
            target="public_aggregate",cost=0.,at=at)
    except (PermissionError,ValueError,TypeError):
        return _deny("NO_VERIFIED_SCOPE")
    if not _valid_public_observation(signal,at):
        return _deny("PUBLIC_SIGNAL_INADMISSIBLE")
    if not _valid_model_receipt(aggregate_model_receipt):
        return _deny("MODEL_RECEIPT_INADMISSIBLE")
    return {
        **_deny("PUBLIC_AGGREGATE_RESEARCH_ONLY"),
        "status":"SHADOW_ONLY",
        "reference_type":"PUBLIC_AGGREGATE_NO_PERSONAL_DATA",
        "source_sha256":signal["source_sha256"],
        "model_sha256":aggregate_model_receipt["model_sha256"],
        "aggregate_n":signal["group_size"],
        "comparison":{
            "candidate":float(aggregate_model_receipt["prediction"]),
            "baseline":float(aggregate_model_receipt["train_mean_baseline"]),
            "unit":"study_arm_cessation_percentage_points",
        },
        "prediction_is_not_intervention":True,
        "model_promoted_for_real_users":False,
    }
