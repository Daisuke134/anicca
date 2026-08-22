"""Provider-neutral Job Hunter browser-agent framework."""

API_VERSION = "job-hunter-browser-agent/1"

from .actions import ActionExecutor
from .contracts import (
    ActionReceiptV1,
    ActionTargetV1,
    ObservationV1,
    SessionHandleV1,
    VisibleActionV1,
    VisibleControlV1,
)
from .observation import ObservationBuilder
from .session import BrowserSession

__all__ = [
    "API_VERSION", "ActionExecutor", "ActionReceiptV1", "ActionTargetV1",
    "BrowserSession", "ObservationBuilder", "ObservationV1", "SessionHandleV1",
    "VisibleActionV1", "VisibleControlV1",
]

__all__ = ["API_VERSION"]
