#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
DISTRIBUTOR = ROOT / "lm-distribution" / "distribute.py"


def executable(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


class LifeManagerTikTokAccountRouteTests(unittest.TestCase):
    def test_default_daily_route_publishes_to_the_retired_video_loops_account(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video = root / "creative.mp4"
            video.write_bytes(b"account-route-video")
            caption = root / "caption.txt"
            caption.write_text("Life Manager account route", encoding="utf-8")
            approvals = root / "approvals.jsonl"
            approvals.write_text(
                json.dumps(
                    {
                        "creative_id": "A01",
                        "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                        "caption_sha256": hashlib.sha256(caption.read_bytes()).hexdigest(),
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            calls = root / "calls.jsonl"
            instagram = executable(
                root / "instagram.py",
                "#!/usr/bin/env python3\n"
                "import json\n"
                "print(json.dumps({'outcome':'published','post_url':'https://www.instagram.com/reel/IGACCOUNT/'}))\n",
            )
            tiktok = executable(
                root / "tiktok.py",
                "#!/usr/bin/env python3\n"
                "import json,os,sys\n"
                "open(os.environ['CALLS'],'a').write(json.dumps(sys.argv[1:])+'\\n')\n"
                "print(json.dumps({'state':'PUBLISHED','post_url':'https://www.tiktok.com/@anicca.comedy/video/123','post_id':'post-1'}))\n",
            )
            env = dict(os.environ, CALLS=str(calls))
            env.pop("LM_TIKTOK_INTEGRATION", None)

            result = subprocess.run(
                [
                    str(DISTRIBUTOR),
                    "--creative-id",
                    "A01",
                    "--video",
                    str(video),
                    "--caption-file",
                    str(caption),
                    "--ledger",
                    str(root / "ledger.jsonl"),
                    "--instagram-adapter",
                    str(instagram),
                    "--tiktok-adapter",
                    str(tiktok),
                    "--instagram-accounts",
                    str(root / "accounts.json"),
                    "--approvals",
                    str(approvals),
                ],
                text=True,
                capture_output=True,
                env=env,
                timeout=30,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            argv = json.loads(calls.read_text(encoding="utf-8").strip())
            integration_position = argv.index("--integration") + 1
            self.assertEqual(
                argv[integration_position],
                "cmpc6cr6g00d8lg0yfythzz9f",
            )


if __name__ == "__main__":
    unittest.main()
