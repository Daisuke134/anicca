"""Provider-neutral Job Hunter browser-agent framework."""

API_VERSION = "job-hunter-browser-agent/1"

from .actions import ActionExecutor
from .contracts import (
    ActionReceiptV1,
    ActionPlanV1,
    ActionTargetV1,
    ObservationV1,
    PolicyContextV1,
    SessionHandleV1,
    VisibleActionV1,
    VisibleControlV1,
)
from .observation import ObservationBuilder
from .policy import AgentPolicy
from .session import BrowserSession

__all__ = [
    "API_VERSION", "ActionExecutor", "ActionPlanV1", "ActionReceiptV1",
    "ActionTargetV1", "AgentPolicy",
    "BrowserSession", "ObservationBuilder", "ObservationV1", "SessionHandleV1",
    "PolicyContextV1", "VisibleActionV1", "VisibleControlV1",
]
