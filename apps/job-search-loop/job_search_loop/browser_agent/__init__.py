"""Provider-neutral Job Hunter browser-agent framework."""

API_VERSION = "job-hunter-browser-agent/1"

from .actions import ActionExecutor
from .checkpoint import CheckpointStore, EvidenceStore
from .candidate_memory import CandidateMemoryView, build_candidate_memory
from .contracts import (
    ActionReceiptV1,
    ActionPlanV1,
    ActionTargetV1,
    CheckpointReceiptV1,
    EvidenceReceiptV1,
    ObservationV1,
    PolicyContextV1,
    RowCheckpointV1,
    SessionHandleV1,
    VisibleActionV1,
    VisibleControlV1,
    StepEvidenceV1,
)
from .observation import ObservationBuilder
from .policy import AgentPolicy
from .session import BrowserSession

__all__ = [
    "API_VERSION", "ActionExecutor", "ActionPlanV1", "ActionReceiptV1",
    "ActionTargetV1", "AgentPolicy",
    "BrowserSession", "CandidateMemoryView", "CheckpointReceiptV1", "CheckpointStore", "EvidenceReceiptV1",
    "EvidenceStore", "ObservationBuilder", "ObservationV1", "PolicyContextV1",
    "RowCheckpointV1", "SessionHandleV1", "StepEvidenceV1", "VisibleActionV1",
    "VisibleControlV1", "build_candidate_memory",
]
