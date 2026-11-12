"""Exercise recorder failure handling with tool doubles, never E2E evidence."""

import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "run-soft-paywall-maestro.sh"


class MaestroRecordingGateTests(unittest.TestCase):
    def run_gate(self, mode):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = root / "tool"
            command.write_text(textwrap.dedent("""\
                #!/usr/bin/env python3
                import json, os, pathlib, signal, sys, time
                name = pathlib.Path(sys.argv[0]).name
                args = sys.argv[1:]
                mode = os.environ['RECORDING_GATE_TEST_MODE']
                if name == 'xcodebuild':
                    sys.exit(0)
                if name == 'maestro':
                    if '--version' not in args:
                        time.sleep(1)
                    sys.exit(0)
                if args[:3] == ['simctl', 'list', 'devices']:
                    print(json.dumps({'devices': {'test': [
                        {'name': 'iPhone harness double', 'isAvailable': True, 'udid': 'TEST'}
                    ]}}))
                elif args and args[0] == 'swift':
                    sys.exit(1 if mode == 'invalid-video' else 0)
                elif 'recordVideo' in args:
                    if mode == 'start-failure':
                        sys.exit(7)
                    if mode != 'missing-video':
                        pathlib.Path(args[-1]).write_bytes(b'HARNESS DOUBLE, NOT A VIDEO')
                    def finish(*_):
                        sys.exit(9 if mode == 'recorder-failure' else 0)
                    signal.signal(signal.SIGINT, finish)
                    while True:
                        time.sleep(0.05)
                """))
            command.chmod(0o755)
            for name in ["xcrun", "xcodebuild", "maestro"]:
                (root / name).symlink_to(command)
            environment = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}",
                               RUNNER_TEMP=str(root), RECORDING_GATE_TEST_MODE=mode)
            result = subprocess.run(["bash", str(SCRIPT), str(root / "evidence")],
                                    env=environment, capture_output=True, text=True, timeout=15)
            return result.returncode

    def test_recording_cannot_start_fails_the_job(self):
        self.assertNotEqual(self.run_gate("start-failure"), 0)

    def test_missing_recording_fails_even_when_maestro_passes(self):
        self.assertNotEqual(self.run_gate("missing-video"), 0)

    def test_recorder_failure_fails_even_when_maestro_passes(self):
        self.assertNotEqual(self.run_gate("recorder-failure"), 0)

    def test_undecodable_or_short_video_fails_even_when_maestro_passes(self):
        self.assertNotEqual(self.run_gate("invalid-video"), 0)

    def test_successful_recording_and_validation_allow_success(self):
        self.assertEqual(self.run_gate("success"), 0)


if __name__ == "__main__":
    unittest.main()
