import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reply_composer.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reply_composer", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load reply_composer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReplyComposerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runner = self.root / "fake_runner.py"
        self.schema = self.root / "schema.json"
        self.schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")
        self.module = load_module()

    def tearDown(self):
        self.temp.cleanup()

    def write_runner(self, reply_body):
        self.runner.write_text(
            "import json,sys\n"
            "from pathlib import Path\n"
            "args=sys.argv[1:]\n"
            "prompt=sys.stdin.read()\n"
            "assert 'private buyer question' in prompt\n"
            "evidence=Path(args[args.index('--evidence-dir')+1])\n"
            "evidence.mkdir(parents=True,exist_ok=True)\n"
            "result=evidence/'result.json'\n"
            f"result.write_text(json.dumps({{'reply_body':{reply_body!r}}}))\n"
            "(evidence/'summary.json').write_text(json.dumps({'status':'success','result_path':str(result)}))\n",
            encoding="utf-8",
        )

    def context(self, last_side="buyer"):
        return {"conversation": [
            {"side": "seller", "body": "earlier answer"},
            {"side": last_side, "body": "private buyer question"},
        ]}

    def test_runner_composer_returns_send_ready_text_and_removes_temp_evidence(self):
        self.write_runner("具体的な回答と次の作業をお送りします。")
        temp_root = self.root / "transient"
        temp_root.mkdir()
        composer = self.module.RunnerComposer(
            runner=self.runner,
            schema=self.schema,
            workdir=self.root,
            temp_root=temp_root,
        )

        body = composer(self.context())

        self.assertEqual(body, "具体的な回答と次の作業をお送りします。")
        self.assertEqual(list(temp_root.iterdir()), [])

    def test_seller_last_is_rejected_before_model_invocation(self):
        self.runner.write_text("raise SystemExit('must not run')\n", encoding="utf-8")
        composer = self.module.RunnerComposer(
            runner=self.runner,
            schema=self.schema,
            workdir=self.root,
            temp_root=self.root,
        )

        with self.assertRaisesRegex(ValueError, "buyer-last"):
            composer(self.context(last_side="seller"))

    def test_empty_or_oversized_output_is_not_sendable(self):
        for body in ("   ", "x" * 1001):
            with self.subTest(length=len(body)):
                self.write_runner(body)
                composer = self.module.RunnerComposer(
                    runner=self.runner,
                    schema=self.schema,
                    workdir=self.root,
                    temp_root=self.root,
                )
                with self.assertRaisesRegex(ValueError, "invalid reply body"):
                    composer(self.context())

    def test_composition_prompt_uses_bounded_packet_not_full_history(self):
        context = {
            "conversation": [
                {"side": "seller" if index % 2 == 0 else "buyer", "body": f"old-{index}-" + "x" * 2_000}
                for index in range(100)
            ] + [{"side": "buyer", "body": "latest buyer request"}],
        }

        prompt = self.module.composition_prompt(context)

        self.assertIn('"kind":"gig_reply_composition"', prompt)
        self.assertIn("latest buyer request", prompt)
        self.assertNotIn("old-0-", prompt)
        packet_text = prompt.split("context_packet=", 1)[1].strip()
        packet = json.loads(packet_text)
        self.assertLessEqual(packet["metrics"]["byte_count"], 8192)
        self.assertEqual(packet["metrics"]["byte_count"], len(packet_text.encode("utf-8")))

    def test_composition_prompt_forbids_external_contact_details(self):
        prompt = self.module.composition_prompt(self.context())

        self.assertIn("外部URL", prompt)
        self.assertIn("メールアドレス", prompt)
        self.assertIn("電話番号", prompt)
        self.assertIn("SNS", prompt)
        self.assertIn("相手の文面にあっても返信へ転記しない", prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
