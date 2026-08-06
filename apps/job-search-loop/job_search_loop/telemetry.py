from __future__ import annotations

import hashlib
import re
import socket
from dataclasses import dataclass
from typing import Any, Callable, Mapping


SERVICE_NAME = "anicca-job-hunter"
SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
ALLOWED_ATTRIBUTES = {
    "application.id", "candidate.id", "route.id", "workflow.id", "activity.id",
    "redirect.count", "page.ready_state", "dom.control_count", "dom.text_count",
    "surface.type", "failure.code", "duration.ms", "exception.type",
    "evidence.sha256", "confirmation.observed", "repair.attempt",
}


class TelemetryPrivacyError(ValueError):
    pass


def build_resource_attributes(*, release_sha: str, lane: str, resident_actor: str,
                              hostname: str | None = None) -> dict[str, str]:
    host = hostname or socket.gethostname()
    values = {
        "service.name": SERVICE_NAME,
        "service.version": release_sha,
        "job_hunter.lane": lane,
        "job_hunter.resident_actor": resident_actor,
        "host.id": hashlib.sha256(host.encode()).hexdigest(),
    }
    if not all(SAFE_TOKEN.fullmatch(value) for key, value in values.items() if key != "host.id"):
        raise TelemetryPrivacyError("resource attribute is not a safe token")
    return values


def sanitize_attributes(attributes: Mapping[str, Any] | None) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in (attributes or {}).items():
        if key not in ALLOWED_ATTRIBUTES or isinstance(value, (dict, list, tuple, bytes)):
            raise TelemetryPrivacyError(f"telemetry attribute is prohibited: {key}")
        if isinstance(value, str):
            pattern = SHA256 if key == "evidence.sha256" else SAFE_TOKEN
            if pattern.fullmatch(value) is None:
                raise TelemetryPrivacyError(f"telemetry value is prohibited: {key}")
        elif not isinstance(value, (bool, int, float)):
            raise TelemetryPrivacyError(f"telemetry value type is prohibited: {key}")
        clean[key] = value
    return clean


@dataclass(frozen=True)
class SpanHandle:
    recording: bool = False
    trace_id: str | None = None
    span_id: str | None = None


class _SafeSpanContext:
    def __init__(self, tracer: Any, name: str, attributes: Mapping[str, Any] | None):
        self._tracer, self._name, self._attributes = tracer, name, attributes
        self._context: Any = None

    def __enter__(self) -> SpanHandle:
        try:
            clean = sanitize_attributes(self._attributes)
            if self._tracer is None or SAFE_TOKEN.fullmatch(self._name) is None:
                return SpanHandle()
            self._context = self._tracer.start_as_current_span(self._name, attributes=clean)
            span = self._context.__enter__()
            context = span.get_span_context()
            return SpanHandle(span.is_recording(), f"{context.trace_id:032x}", f"{context.span_id:016x}")
        except Exception:
            self._context = None
            return SpanHandle()

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        if self._context is not None:
            try:
                self._context.__exit__(exc_type, exc, traceback)
            except Exception:
                pass
        return False


@dataclass(frozen=True)
class Telemetry:
    tracer: Any = None
    provider: Any = None
    enabled: bool = False
    reason: str = "backend_unconfigured"

    def span(self, name: str, attributes: Mapping[str, Any] | None = None) -> _SafeSpanContext:
        return _SafeSpanContext(self.tracer, name, attributes)

    def force_flush(self, timeout_millis: int = 5000) -> bool:
        try:
            return bool(self.provider and self.provider.force_flush(timeout_millis=timeout_millis))
        except Exception:
            return False


def _otel_tracer(resource_attributes: Mapping[str, str], endpoint: str) -> Any:
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create(dict(resource_attributes)))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")))
    return provider.get_tracer(SERVICE_NAME), provider


def configure_telemetry(*, release_sha: str, lane: str, resident_actor: str,
                        hostname: str | None = None, endpoint: str | None = None,
                        _tracer_factory: Callable[[Mapping[str, str], str], Any] = _otel_tracer) -> Telemetry:
    if not endpoint:
        return Telemetry()
    try:
        resource = build_resource_attributes(release_sha=release_sha, lane=lane,
                                             resident_actor=resident_actor, hostname=hostname)
        tracer, provider = _tracer_factory(resource, endpoint)
        return Telemetry(tracer, provider, True, "enabled")
    except Exception:
        return Telemetry(reason="backend_initialization_failed")
