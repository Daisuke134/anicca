import hashlib
import unittest

from job_search_loop.telemetry import (
    TelemetryPrivacyError,
    build_resource_attributes,
    configure_telemetry,
    sanitize_attributes,
)


class TelemetryTests(unittest.TestCase):
    def test_sdk_never_auto_records_exception_message_or_stack(self):
        captured = {}
        class Context:
            def __enter__(self):
                class Span:
                    def get_span_context(self): return type("C", (), {"trace_id": 1, "span_id": 2})()
                    def is_recording(self): return True
                return Span()
            def __exit__(self, *_): return False
        class Tracer:
            def start_as_current_span(self, _name, **kwargs):
                captured.update(kwargs)
                return Context()

        telemetry = configure_telemetry(
            release_sha="a" * 40, lane="daily", resident_actor="job_hunter_codex_terra",
            hostname="host", endpoint="http://127.0.0.1:4318",
            _tracer_factory=lambda *_: (Tracer(), object()),
        )
        with self.assertRaisesRegex(RuntimeError, "private answer"):
            with telemetry.span("form.fill"):
                raise RuntimeError("private answer")

        self.assertFalse(captured["record_exception"])
        self.assertFalse(captured["set_status_on_exception"])

    def test_resource_contains_only_non_private_runtime_identity(self):
        resource = build_resource_attributes(
            release_sha="a" * 40,
            lane="daily",
            resident_actor="job_hunter_codex_terra",
            hostname="private-mac-name",
        )

        self.assertEqual(resource, {
            "service.name": "anicca-job-hunter",
            "service.version": "a" * 40,
            "job_hunter.lane": "daily",
            "job_hunter.resident_actor": "job_hunter_codex_terra",
            "host.id": hashlib.sha256(b"private-mac-name").hexdigest(),
        })
        self.assertNotIn("private-mac-name", resource.values())

    def test_privacy_boundary_rejects_private_keys_and_values(self):
        for key in ("name", "email", "phone", "resume_text", "answer", "raw_html", "url", "screenshot"):
            with self.subTest(key=key), self.assertRaises(TelemetryPrivacyError):
                sanitize_attributes({key: "private"})
        for value in ("person@example.com", "https://jobs.example/apply?token=secret"):
            with self.subTest(value=value), self.assertRaises(TelemetryPrivacyError):
                sanitize_attributes({"exception.type": value})

    def test_allowlisted_diagnostics_survive_without_private_payloads(self):
        self.assertEqual(sanitize_attributes({
            "redirect.count": 2,
            "page.ready_state": "complete",
            "surface.type": "ashby_apply",
            "failure.code": "unsupported_control",
            "evidence.sha256": "b" * 64,
        }), {
            "redirect.count": 2,
            "page.ready_state": "complete",
            "surface.type": "ashby_apply",
            "failure.code": "unsupported_control",
            "evidence.sha256": "b" * 64,
        })

    def test_unconfigured_or_broken_backend_is_non_fatal(self):
        disabled = configure_telemetry(
            release_sha="a" * 40, lane="daily", resident_actor="job_hunter_codex_terra",
            hostname="host", endpoint=None,
        )
        self.assertFalse(disabled.enabled)
        self.assertEqual(disabled.reason, "backend_unconfigured")
        with disabled.span("hourly_pass", {"email": "person@example.com"}) as span:
            self.assertFalse(span.recording)

        broken = configure_telemetry(
            release_sha="a" * 40, lane="daily", resident_actor="job_hunter_codex_terra",
            hostname="host", endpoint="http://127.0.0.1:4318",
            _tracer_factory=lambda *_: (_ for _ in ()).throw(RuntimeError("offline")),
        )
        self.assertFalse(broken.enabled)
        self.assertEqual(broken.reason, "backend_initialization_failed")


if __name__ == "__main__":
    unittest.main()
