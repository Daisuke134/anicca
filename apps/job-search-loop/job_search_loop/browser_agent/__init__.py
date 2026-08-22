"""Provider-neutral Job Hunter browser-agent framework."""

API_VERSION = "job-hunter-browser-agent/1"

from .contracts import SessionHandleV1
from .session import BrowserSession

__all__ = ["API_VERSION", "BrowserSession", "SessionHandleV1"]

__all__ = ["API_VERSION"]
