"""Provider-neutral Job Hunter browser-agent framework."""

API_VERSION = "job-hunter-browser-agent/1"

from .contracts import ObservationV1, SessionHandleV1, VisibleControlV1
from .observation import ObservationBuilder
from .session import BrowserSession

__all__ = [
    "API_VERSION", "BrowserSession", "ObservationBuilder", "ObservationV1",
    "SessionHandleV1", "VisibleControlV1",
]

__all__ = ["API_VERSION"]
