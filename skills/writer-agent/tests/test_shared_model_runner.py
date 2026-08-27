import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "runtime/shared-model-runner.py"
LEGACY_ENTRY = ROOT / "runtime/model-runner.sh"


class SharedModelRunnerTest(unittest.TestCase):
    def test_judge_preserves_legacy_stdout_through_canonical_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / "agent-runner.py"
            fake.write_text("""#!/usr/bin/env python3
import json,pathlib,sys
a=sys.argv[1:]; e=pathlib.Path(a[a.index('--evidence-dir')+1]); e.mkdir(parents=True)
r=e/'result.json'; r.write_text('{"classification":"ACCEPTED"}')
(e/'summary.json').write_text(json.dumps({'result_path':str(r)}))
""")
            fake.chmod(0o755)
            prompt = root / "prompt.txt"; prompt.write_text("classify this message")
            env = {**os.environ, "AGENT_RUNNER_BIN": str(fake),
                   "WRITER_SHARED_RUNNER_STATE": str(root / "state")}
            result = subprocess.run(
                [sys.executable, str(ADAPTER), "judge", "--prompt-file", str(prompt)],
                env=env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {"classification": "ACCEPTED"})

    def test_adapter_contains_no_direct_provider_or_auth_selection(self):
        source = ADAPTER.read_text(encoding="utf-8")
        for forbidden in ("CODEX_HOME", "auth.json", "codex exec", "ARTICLE_PROVIDER"):
            self.assertNotIn(forbidden, source)

    def test_production_legacy_entry_delegates_to_canonical_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); fake = root / "agent-runner.py"
            fake.write_text("""#!/usr/bin/env python3
import json,pathlib,sys
a=sys.argv[1:]; e=pathlib.Path(a[a.index('--evidence-dir')+1]); e.mkdir(parents=True)
r=e/'result.json'; r.write_text('{"delegated":true}')
(e/'summary.json').write_text(json.dumps({'result_path':str(r)}))
"""); fake.chmod(0o755)
            prompt=root/'prompt.txt'; prompt.write_text('delegate this judge')
            env={key:value for key,value in os.environ.items()
                 if key not in {'ARTICLE_CODEX_BIN','ARTICLE_CLAUDE_BIN','ARTICLE_CODEX_EVENTS_FILE'}}
            env.update({'AGENT_RUNNER_BIN':str(fake),'WRITER_SHARED_RUNNER_STATE':str(root/'state')})
            result=subprocess.run([str(LEGACY_ENTRY),'judge','--prompt-file',str(prompt)],
                                  env=env,capture_output=True,text=True,check=False)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout),{'delegated':True})

    def test_production_repair_delegates_cage_session_and_durable_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); workspace=root/'workspace'; workspace.mkdir()
            args_file=root/'args.json'; fake=root/'agent-runner.py'
            fake.write_text("""#!/usr/bin/env python3
import json,os,pathlib,sys
a=sys.argv[1:]; pathlib.Path(os.environ['CAPTURE_ARGS']).write_text(json.dumps(a))
e=pathlib.Path(a[a.index('--evidence-dir')+1]); e.mkdir(parents=True)
(e/'attempt-01.stdout.log').write_text('{"type":"thread.started","thread_id":"thread-123"}\\n')
r=e/'result.json'; r.write_text('{"complete":true}')
(e/'summary.json').write_text(json.dumps({'result_path':str(r)}))
"""); fake.chmod(0o755)
            prompt=root/'prompt.txt'; prompt.write_text('repair this workspace')
            schema=root/'schema.json'; schema.write_text('{}')
            events,last=root/'events.jsonl',root/'last.json'
            env={key:value for key,value in os.environ.items()
                 if key not in {'ARTICLE_CODEX_BIN','ARTICLE_CLAUDE_BIN'}}
            env.update({'AGENT_RUNNER_BIN':str(fake),'WRITER_SHARED_RUNNER_STATE':str(root/'state'),
                        'ARTICLE_REPAIR_WORKSPACE':str(workspace),'ARTICLE_CODEX_EVENTS_FILE':str(events),
                        'ARTICLE_CODEX_LAST_MESSAGE_FILE':str(last),'ARTICLE_CODEX_OUTPUT_SCHEMA':str(schema),
                        'ARTICLE_CODEX_RESUME_SESSION_ID':'thread-123','CAPTURE_ARGS':str(args_file)})
            result=subprocess.run([str(LEGACY_ENTRY),'repair','--prompt-file',str(prompt)],
                                  env=env,capture_output=True,text=True,check=False)
            self.assertEqual(result.returncode,0,result.stderr)
            args=json.loads(args_file.read_text())
            self.assertIn('writer-repair-agent',args)
            self.assertEqual(args[args.index('--codex-resume-session-id')+1],'thread-123')
            self.assertIn('thread.started',events.read_text())
            self.assertEqual(json.loads(last.read_text()),{'complete':True})


if __name__ == "__main__":
    unittest.main()
