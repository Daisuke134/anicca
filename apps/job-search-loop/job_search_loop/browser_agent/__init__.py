"""Provider-neutral Job Hunter browser-agent framework."""

API_VERSION = "job-hunter-browser-agent/1"

from .actions import ActionExecutor
from .answer_memory import AnswerMemory, AnswerRecordV1
from .answers import AnswerResolver
from .checkpoint import CheckpointStore, EvidenceStore
from .candidate_memory import CandidateMemoryView, build_candidate_memory
from .contracts import (
    ActionReceiptV1,
    ActionPlanV1,
    ActionTargetV1,
    CheckpointReceiptV1,
    EvidenceReceiptV1,
    FieldQuestionV1,
    ObservationV1,
    PolicyContextV1,
    RowCheckpointV1,
    ResolvedAnswerV1,
    SessionHandleV1,
    VisibleActionV1,
    VisibleControlV1,
    StepEvidenceV1,
)
from .observation import ObservationBuilder
from .inference import ExperienceIntervalV1, InferenceDecisionV1, StableInferencePolicy
from .policy import AgentPolicy
from .session import BrowserSession
from .workday_account import MachineWorkdayCredentialStore
from .workday_auth import WorkdayAuthReceiptV1, WorkdayAuthTool

__all__ = [
    "API_VERSION", "ActionExecutor", "ActionPlanV1", "ActionReceiptV1", "AnswerMemory",
    "AnswerRecordV1", "AnswerResolver",
    "ActionTargetV1", "AgentPolicy",
    "BrowserSession", "CandidateMemoryView", "CheckpointReceiptV1", "CheckpointStore", "EvidenceReceiptV1",
    "EvidenceStore", "ExperienceIntervalV1", "FieldQuestionV1", "InferenceDecisionV1",
    "ObservationBuilder", "ObservationV1",
    "PolicyContextV1", "ResolvedAnswerV1", "RowCheckpointV1", "SessionHandleV1",
    "StepEvidenceV1", "VisibleActionV1",
    "MachineWorkdayCredentialStore", "StableInferencePolicy", "VisibleControlV1",
    "WorkdayAuthReceiptV1", "WorkdayAuthTool",
    "build_candidate_memory",
]
