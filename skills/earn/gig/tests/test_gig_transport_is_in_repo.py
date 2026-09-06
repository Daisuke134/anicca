"""Reply, Paid and Storefront must send through the in-repo client, like Lancers and CrowdWorks.

Measured 2026-09-07, one hour of production sends:

    Lancers     37 delivered / 0 failed   (shared client)
    CrowdWorks   4 delivered / 0 failed   (shared client)
    Coconala    20 delivered / 13 failed  (openclaw CLI, TimeoutExpired)

Same account, same Telegram, same minutes. The difference was the transport. A CLI is also
unusable in a clone of this repository, which forfeits the OSS goal.

The class keeps its old name as an alias because the four call sites that construct it live in the
Paid and Storefront owners' files; renaming would have forced edits there.

Run: python3 -m pytest skills/earn/gig/tests/test_gig_transport_is_in_repo.py
"""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import telegram_report  # noqa: E402

SOURCE = (SCRIPTS / "telegram_report.py").read_text(encoding="utf-8")


class _Sent:
    def __init__(self, provider_id, error=None):
        self.started, self.provider_id, self.error = True, provider_id, error


def test_the_transport_no_longer_execs_a_cli(tmp_path):
    transport = telegram_report.GigTelegramTransport(
        target="chat", receipt_dir=tmp_path,
        sender=lambda message, chat_id, env_file=None: _Sent("62999"),
    )
    assert transport.send_report("hello", event_key="k") == "62999"


def test_an_unacknowledged_send_is_never_counted_as_sent(tmp_path):
    transport = telegram_report.GigTelegramTransport(
        target="chat", receipt_dir=tmp_path,
        sender=lambda message, chat_id, env_file=None: _Sent(None, "receipt_missing"),
    )
    try:
        transport.send_report("hello", event_key="k")
    except RuntimeError:
        return
    raise AssertionError("a missing provider id must raise so the caller records delivery_unknown")


def test_the_old_name_still_constructs_for_the_other_owners_files():
    """paid_direct, ask_buyer_pass, checkpoint_via_tg and retainer_lane all build this by name."""
    assert telegram_report.OpenClawTelegramTransport is telegram_report.GigTelegramTransport


def test_an_executable_argument_is_accepted_and_ignored(tmp_path):
    """Those same call sites still pass executable=; they must keep working untouched."""
    transport = telegram_report.GigTelegramTransport(
        target="chat", executable=Path("/opt/homebrew/bin/anything"), receipt_dir=tmp_path,
        sender=lambda message, chat_id, env_file=None: _Sent("1"),
    )
    assert transport.send_report("hello", event_key="k") == "1"


def test_no_cli_path_survives_in_the_send_path():
    """Scoped to send_report: the class docstring keeps the history on purpose."""
    cls = SOURCE.split("class GigTelegramTransport:", 1)[1].split("\nOpenClawTelegramTransport", 1)[0]
    send = cls.split("def send_report(", 1)[1]
    assert "/opt/homebrew" not in send
    assert '"message", "send"' not in send
    assert "send_via_shared_client" in cls


def test_the_command_line_no_longer_takes_a_binary_path():
    assert '--openclaw' not in SOURCE
