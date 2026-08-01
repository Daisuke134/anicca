import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "capafy_ig_session_verify.py"


class CdpHandler(BaseHTTPRequestHandler):
    tabs = [{"url": "https://www.instagram.com/capafy.skills25042/"}]

    def do_GET(self):
        body = json.dumps(self.tabs).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


def run_verify(tmp_path, tabs, credential_username="capafy.skills25042"):
    CdpHandler.tabs = tabs
    server = ThreadingHTTPServer(("127.0.0.1", 0), CdpHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        accounts = tmp_path / "accounts.json"
        credential = tmp_path / "credential.json"
        accounts.write_text(
            json.dumps(
                [
                    {
                        "handle": "capafy.skills25042",
                        "status": "warming",
                        "session_owner": "browser",
                        "port": port,
                    }
                ]
            ),
            encoding="utf-8",
        )
        credential.write_text(
            json.dumps({"username": credential_username, "pw": "fixture"}),
            encoding="utf-8",
        )
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--accounts",
                str(accounts),
                "--credential",
                str(credential),
                "--handle",
                "capafy.skills25042",
                "--port",
                str(port),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        server.shutdown()
        thread.join()


def test_profile_tab_and_matching_browser_owned_row_are_verified(tmp_path):
    result = run_verify(
        tmp_path, [{"url": "https://www.instagram.com/capafy.skills25042/"}]
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["verified"] is True


def test_login_or_challenge_tab_is_not_an_established_session(tmp_path):
    for url in (
        "https://www.instagram.com/accounts/login/",
        "https://www.instagram.com/challenge/ABC/",
    ):
        result = run_verify(tmp_path, [{"url": url}])
        assert result.returncode != 0


def test_credential_must_belong_to_the_new_handle(tmp_path):
    result = run_verify(
        tmp_path,
        [{"url": "https://www.instagram.com/capafy.skills25042/"}],
        credential_username="capafy.someone-else",
    )
    assert result.returncode != 0
