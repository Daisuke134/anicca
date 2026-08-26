"""Provider-neutral Job Hunter browser-agent framework."""

API_VERSION = "job-hunter-browser-agent/1"

from .actions import ActionExecutor
from .answer_memory import AnswerMemory, AnswerRecordV1
from .answers import AnswerResolver
from .checkpoint import CheckpointStore, EvidenceStore
from .completion import record_completion_evidence, verify_completion_ui
from .challenge import assess_challenge
from .candidate_memory import CandidateMemoryView, build_candidate_memory
from .contracts import (
    ActionReceiptV1,
    ActionPlanV1,
    ActionTargetV1,
    CheckpointReceiptV1,
    ChallengeAssessmentV1,
    EvidenceReceiptV1,
    FieldQuestionV1,
    ObservationV1,
    PolicyContextV1,
    RowCheckpointV1,
    ResolvedAnswerV1,
    ResumeVerificationV1,
    ResumeCursorV1,
    QueueRowReceiptV1,
    FinalReviewReceiptV1,
    SubmissionFenceLeaseV1,
    CompletionEvidenceV1,
    SessionHandleV1,
    VisibleActionV1,
    VisibleControlV1,
    ValidationFeedbackV1,
    StepEvidenceV1,
)
from .observation import ObservationBuilder
from .outcome_reporting import build_hourly_outcome_message, send_hourly_outcomes
from .inference import ExperienceIntervalV1, InferenceDecisionV1, StableInferencePolicy
from .policy import AgentPolicy
from .session import BrowserSession
from .resume import ResumeVerifier
from .resume_cursor import RowResumer
from .queue import RowQueueSupervisor
from .review import verify_final_review
from .submission_fence import SubmissionFence
from .workday_account import MachineWorkdayCredentialStore
from .workday_auth import WorkdayAuthReceiptV1, WorkdayAuthTool
from .validation import validation_feedback

__all__ = [
    "API_VERSION", "ActionExecutor", "ActionPlanV1", "ActionReceiptV1", "AnswerMemory",
    "AnswerRecordV1", "AnswerResolver",
    "ActionTargetV1", "AgentPolicy",
    "BrowserSession", "CandidateMemoryView", "CheckpointReceiptV1", "CheckpointStore", "EvidenceReceiptV1",
    "ChallengeAssessmentV1", "assess_challenge",
    "EvidenceStore", "ExperienceIntervalV1", "FieldQuestionV1", "InferenceDecisionV1",
    "ObservationBuilder", "ObservationV1",
    "PolicyContextV1", "ResolvedAnswerV1", "RowCheckpointV1", "SessionHandleV1",
    "ResumeVerificationV1", "ResumeVerifier",
    "ResumeCursorV1", "RowResumer",
    "QueueRowReceiptV1", "RowQueueSupervisor",
    "FinalReviewReceiptV1", "verify_final_review",
    "SubmissionFenceLeaseV1", "SubmissionFence",
    "CompletionEvidenceV1", "verify_completion_ui",
    "record_completion_evidence",
    "build_hourly_outcome_message", "send_hourly_outcomes",
    "StepEvidenceV1", "VisibleActionV1",
    "MachineWorkdayCredentialStore", "StableInferencePolicy", "VisibleControlV1",
    "WorkdayAuthReceiptV1", "WorkdayAuthTool",
    "ValidationFeedbackV1", "validation_feedback",
    "build_candidate_memory",
]
