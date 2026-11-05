"""Research-only catalog of existing behavioral models. No API requests, no payments.

This module is an integration preflight: it does NOT infer behavioral/clinical truth,
assert human benefit, approve restricted datasets, or authorize production action.
Access status reflects official source metadata inspected 2026-11-06.
"""
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Optional


class Access(Enum):
    OPEN_MODEL_GATE = "huggingface_access_required"
    META_BASE_GATE = "meta_llama_community_license"
    PROVIDER_API = "provider_api"
    CLOSED_SERVICE = "external_product_or_demo"


@dataclass(frozen=True)
class BehaviorModel:
    key: str
    display_name: str
    source_url: str
    access: Access
    base_license: str
    min_gpu_gb: Optional[int] = None
    weights_available: bool = False
    specialties: FrozenSet[str] = frozenset()


MODELS = {
    "befm-1.5-4b": BehaviorModel(
        "befm-1.5-4b", "Be.FM 1.5 4B",
        "https://huggingface.co/befm/BeFM1.5-4B",
        Access.OPEN_MODEL_GATE, "Apache-2.0 Qwen3 and LoRA, HF auto-gated",
        24, True, frozenset({"choice", "survey", "personality", "game"}),
    ),
    "centaur-70b": BehaviorModel(
        "centaur-70b", "Centaur Llama 3.1 70B",
        "https://github.com/marcelbinz/Llama-3.1-Centaur-70B",
        Access.META_BASE_GATE, "Llama 3.1 Community License",
        80, True, frozenset({"choice", "cognitive_task"}),
    ),
    "ampersand-v0.1": BehaviorModel(
        "ampersand-v0.1", "humans& Ampersand",
        "https://ampersand.humansand.ai/docs/",
        Access.PROVIDER_API, "Provider terms, API only", None, False,
        frozenset({"collaboration", "long_horizon_conversation"}),
    ),
    "persimmon": BehaviorModel(
        "persimmon", "humans& Persimmon",
        "https://persimmon.humansand.ai/",
        Access.CLOSED_SERVICE, "Access terms not independently cleared",
        None, False, frozenset({"human_conversation_simulation"}),
    ),
    "listen-twins": BehaviorModel(
        "listen-twins", "Listen Labs Listen Twins",
        "https://listenlabs.com/whatsnew/introducing-listen-twins",
        Access.CLOSED_SERVICE, "Customer-research service terms, API scope unconfirmed",
        None, False, frozenset({"interview_based_twin"}),
    ),
}


@dataclass(frozen=True)
class ResearchPreflight:
    model: str
    mode: str
    ready: bool
    blocking_reasons: tuple[str, ...]
    note: str = "Software and access preflight only; no model inference or human outcome verified."


def research_preflight(
    model_key: str,
    *,
    accepted_model_terms: bool = False,
    provider_api_available: bool = False,
    cloud_gpu_gb: int = 0,
    paid_inference_budget_authorized: bool = False,
    commercial_dataset_rights_clear: bool = False,
    uses_behaviorbench_test_data: bool = False,
) -> ResearchPreflight:
    """Fail closed on absent model/compute/rights while keeping actual execution separate.

    Do not pass credentials, card numbers, or private participant records here.
    paid_inference_budget_authorized is only an external-authorization *flag*.
    """
    if model_key not in MODELS:
        raise ValueError("unknown model ID")
    if type(cloud_gpu_gb) is not int or cloud_gpu_gb < 0:
        raise ValueError("nonnegative integer GPU VRAM required")
    model = MODELS[model_key]
    blockers: list[str] = []

    if uses_behaviorbench_test_data and not commercial_dataset_rights_clear:
        blockers.append("BehaviorBench CC BY-NC-ND dataset rights not cleared for commercial use")
    if model.access == Access.CLOSED_SERVICE:
        blockers.append("External provider-controlled demo/service; no confirmed downloadable weights")
    elif model.access == Access.PROVIDER_API:
        if not provider_api_available:
            blockers.append("Provider API access/secret missing")
    else:
        if not accepted_model_terms:
            blockers.append("Model base/adapter access terms not accepted")
        if cloud_gpu_gb < (model.min_gpu_gb or 0):
            blockers.append("Insufficient cloud GPU VRAM")
    if not paid_inference_budget_authorized:
        blockers.append("No external spending authorization")
    return ResearchPreflight(
        model=model_key,
        mode=model.access.value,
        ready=not blockers,
        blocking_reasons=tuple(blockers),
    )
