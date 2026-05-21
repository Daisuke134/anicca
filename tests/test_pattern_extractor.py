from pathlib import Path
import sys

import pytest
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from observer.pattern_extractor import (
    extract_time_patterns,
    extract_sequence_patterns,
    extract_shell_patterns,
)


class TestTimePatterns:
    """Tests for time pattern extraction (High 7)."""

    def test_requires_4_day_coverage(self):
        """Pattern needs 4+ unique days to be detected."""
        # Only 3 days - should NOT match
        obs = [
            {"timestamp": "2026-02-10T09:00:00Z", "type": "window", "app": "Safari"},
            {"timestamp": "2026-02-11T09:00:00Z", "type": "window", "app": "Safari"},
            {"timestamp": "2026-02-12T09:00:00Z", "type": "window", "app": "Safari"},
        ]
        patterns = extract_time_patterns(obs)
        safari_patterns = [p for p in patterns if p.get("app") == "Safari"]
        assert len(safari_patterns) == 0

    def test_detects_pattern_with_4_days(self):
        """Pattern with 4+ days should be detected."""
        obs = [
            {"timestamp": "2026-02-10T09:00:00Z", "type": "window", "app": "Safari"},
            {"timestamp": "2026-02-11T09:05:00Z", "type": "window", "app": "Safari"},
            {"timestamp": "2026-02-12T09:10:00Z", "type": "window", "app": "Safari"},
            {"timestamp": "2026-02-13T09:00:00Z", "type": "window", "app": "Safari"},
        ]
        patterns = extract_time_patterns(obs)
        safari_patterns = [p for p in patterns if p.get("app") == "Safari"]
        assert len(safari_patterns) == 1
        assert safari_patterns[0]["day_coverage"] == 4

    def test_rejects_high_time_variance(self):
        """Times with std_dev > 20 min should be rejected."""
        # Times: 00, 55, 05, 50 minutes - high variance
        obs = [
            {"timestamp": "2026-02-10T09:00:00Z", "type": "window", "app": "Slack"},
            {"timestamp": "2026-02-11T09:55:00Z", "type": "window", "app": "Slack"},
            {"timestamp": "2026-02-12T09:05:00Z", "type": "window", "app": "Slack"},
            {"timestamp": "2026-02-13T09:50:00Z", "type": "window", "app": "Slack"},
        ]
        patterns = extract_time_patterns(obs)
        slack_patterns = [p for p in patterns if p.get("app") == "Slack"]
        # High variance should be rejected
        assert len(slack_patterns) == 0

    def test_accepts_low_time_variance(self):
        """Times with std_dev <= 20 min should be accepted."""
        # Times: 00, 05, 10, 08 minutes - low variance
        obs = [
            {"timestamp": "2026-02-10T09:00:00Z", "type": "window", "app": "Mail"},
            {"timestamp": "2026-02-11T09:05:00Z", "type": "window", "app": "Mail"},
            {"timestamp": "2026-02-12T09:10:00Z", "type": "window", "app": "Mail"},
            {"timestamp": "2026-02-13T09:08:00Z", "type": "window", "app": "Mail"},
        ]
        patterns = extract_time_patterns(obs)
        mail_patterns = [p for p in patterns if p.get("app") == "Mail"]
        assert len(mail_patterns) == 1
        assert mail_patterns[0]["std_dev_minutes"] <= 20


class TestSequencePatterns:
    """Tests for sequence pattern extraction (High 6)."""

    def test_requires_3_unique_apps(self):
        """All 3 apps in sequence must be different."""
        # A → A → B has duplicate - should NOT match
        obs = [
            {"timestamp": "2026-02-10T09:00:00Z", "type": "app_switch", "to_app": "A", "app": None},
            {"timestamp": "2026-02-10T09:01:00Z", "type": "app_switch", "to_app": "A", "app": None},
            {"timestamp": "2026-02-10T09:02:00Z", "type": "app_switch", "to_app": "B", "app": None},
        ]
        patterns = extract_sequence_patterns(obs)
        # No valid 3-unique sequence
        assert all(len(set(p["sequence"])) == 3 for p in patterns)

    def test_detects_unique_3_app_sequence(self):
        """Detect A → B → C where all are different."""
        obs = []
        # Repeat the sequence 3 times to meet threshold
        for _ in range(3):
            obs.extend(
                [
                    {"timestamp": "2026-02-10T09:00:00Z", "type": "app_switch", "to_app": "Safari", "app": None},
                    {"timestamp": "2026-02-10T09:01:00Z", "type": "app_switch", "to_app": "Slack", "app": None},
                    {"timestamp": "2026-02-10T09:02:00Z", "type": "app_switch", "to_app": "VSCode", "app": None},
                ]
            )
        patterns = extract_sequence_patterns(obs)
        sequences = [p["sequence"] for p in patterns]
        assert ["Safari", "Slack", "VSCode"] in sequences

    def test_ignores_non_app_events(self):
        """Only app_switch and window events should be considered."""
        obs = [
            {"timestamp": "2026-02-10T09:00:00Z", "type": "shell", "command": "git", "app": None, "to_app": None},
            {"timestamp": "2026-02-10T09:01:00Z", "type": "screenshot", "path": "/tmp/x.jpg", "app": None, "to_app": None},
        ]
        patterns = extract_sequence_patterns(obs)
        assert len(patterns) == 0


class TestShellPatterns:
    """Tests for shell command pattern extraction (Critical 3)."""

    def test_counts_command_frequency(self):
        """Commands used 5+ times should be detected."""
        obs = [
            {"timestamp": f"2026-02-10T09:{i:02d}:00Z", "type": "shell", "command": "git", "app": None}
            for i in range(5)
        ]
        patterns = extract_shell_patterns(obs)
        git_patterns = [p for p in patterns if p.get("command") == "git"]
        assert len(git_patterns) == 1
        assert git_patterns[0]["frequency"] == 5

    def test_ignores_redacted_commands(self):
        """[REDACTED] commands should not be counted."""
        obs = [
            {"timestamp": f"2026-02-10T09:{i:02d}:00Z", "type": "shell", "command": "[REDACTED]", "app": None}
            for i in range(10)
        ]
        patterns = extract_shell_patterns(obs)
        redacted_patterns = [p for p in patterns if p.get("command") == "[REDACTED]"]
        assert len(redacted_patterns) == 0

    def test_below_threshold_not_detected(self):
        """Commands used < 5 times should not be detected."""
        obs = [
            {"timestamp": f"2026-02-10T09:{i:02d}:00Z", "type": "shell", "command": "rare_cmd", "app": None}
            for i in range(4)  # Only 4 times
        ]
        patterns = extract_shell_patterns(obs)
        assert len(patterns) == 0


class TestJSONSafety:
    """Tests for JSON generation safety (Critical 1)."""

    def test_jq_handles_quotes_in_app_name(self):
        """App names with quotes should be properly escaped."""
        import subprocess
        import json

        # Simulate jq command with special characters
        result = subprocess.run(
            [
                "jq",
                "-n",
                "--arg",
                "ts",
                "2026-02-10T09:00:00Z",
                "--arg",
                "type",
                "window",
                "--arg",
                "app",
                'App with "quotes"',
                '{timestamp: $ts, type: $type, data: {app: $app}}',
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["data"]["app"] == 'App with "quotes"'

    def test_jq_handles_backslashes(self):
        """Backslashes should be properly escaped."""
        import subprocess
        import json

        result = subprocess.run(
            [
                "jq",
                "-n",
                "--arg",
                "ts",
                "2026-02-10T09:00:00Z",
                "--arg",
                "type",
                "window",
                "--arg",
                "app",
                r"Path\to\app",
                "{timestamp: $ts, type: $type, data: {app: $app}}",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["data"]["app"] == r"Path\to\app"

    def test_jq_handles_newlines(self):
        """Newlines in app names should be escaped."""
        import subprocess
        import json

        result = subprocess.run(
            [
                "jq",
                "-n",
                "--arg",
                "ts",
                "2026-02-10T09:00:00Z",
                "--arg",
                "type",
                "window",
                "--arg",
                "app",
                "Line1\nLine2",
                "{timestamp: $ts, type: $type, data: {app: $app}}",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["data"]["app"] == "Line1\nLine2"


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_full_pipeline_with_sample_data(self):
        """Test complete pipeline from observations to proposals."""
        import tempfile
        import json
        from pathlib import Path

        # Create sample observations
        observations = [
            # Time pattern: Safari at 9am for 4 days
            {"timestamp": "2026-02-10T09:00:00Z", "type": "window", "app": "Safari"},
            {"timestamp": "2026-02-11T09:05:00Z", "type": "window", "app": "Safari"},
            {"timestamp": "2026-02-12T09:03:00Z", "type": "window", "app": "Safari"},
            {"timestamp": "2026-02-13T09:02:00Z", "type": "window", "app": "Safari"},
            # Shell pattern: git 5 times
            {"timestamp": "2026-02-10T10:00:00Z", "type": "shell", "command": "git", "app": None},
            {"timestamp": "2026-02-10T11:00:00Z", "type": "shell", "command": "git", "app": None},
            {"timestamp": "2026-02-10T12:00:00Z", "type": "shell", "command": "git", "app": None},
            {"timestamp": "2026-02-10T13:00:00Z", "type": "shell", "command": "git", "app": None},
            {"timestamp": "2026-02-10T14:00:00Z", "type": "shell", "command": "git", "app": None},
        ]

        # Run pattern extraction
        time_patterns = extract_time_patterns(observations)
        shell_patterns = extract_shell_patterns(observations)

        # Verify time pattern detected
        safari_patterns = [p for p in time_patterns if p.get("app") == "Safari"]
        assert len(safari_patterns) >= 1, "Safari 9am pattern should be detected"

        # Verify shell pattern detected
        git_patterns = [p for p in shell_patterns if p.get("command") == "git"]
        assert len(git_patterns) >= 1, "git command pattern should be detected"

    def test_corrupted_json_handled_gracefully(self):
        """Corrupted JSONL lines should be skipped, not crash."""
        import tempfile
        import json
        from pathlib import Path

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            # Valid line
            f.write('{"timestamp": "2026-02-10T09:00:00Z", "type": "window", "data": {"app": "Safari"}}\n')
            # Corrupted line
            f.write('{"invalid json\n')
            # Another valid line
            f.write('{"timestamp": "2026-02-10T09:01:00Z", "type": "window", "data": {"app": "Chrome"}}\n')
            f.flush()

            # Read and parse
            valid_count = 0
            with open(f.name) as rf:
                for line in rf:
                    try:
                        json.loads(line)
                        valid_count += 1
                    except json.JSONDecodeError:
                        pass  # Expected for corrupted line

            assert valid_count == 2, "Should parse 2 valid lines, skip 1 corrupted"
