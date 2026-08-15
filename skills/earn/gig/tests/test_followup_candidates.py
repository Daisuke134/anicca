from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


# 26 threads sit with our own message last and next_action=observe -- nobody ever acts on
# them. Measured 2026-08-06: 8 are under three days old, 9 between three and seven, 8
# between seven and fourteen.
#
# Yesware's 10M-thread study (https://www.yesware.com/blog/sales-follow-up-statistics/)
# finds the cadence that actually earns replies is roughly six touches across three weeks,
# that "waiting more than four days typically decreases reply", and that reply rates fall
# below 10% after the seventh touch. Coconala forbids sending follow-ups to "不特定多数"
# (https://coconala-support.zendesk.com/hc/ja/articles/10003722830105), which these are
# not -- every one is a thread the buyer opened -- but the spirit of that rule is why the
# per-thread cap here is three rather than six.


def load():
    spec = importlib.util.spec_from_file_location(
        "followup_candidates", SCRIPTS / "followup_candidates.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


NOW = 1786000000


def thread(thread_id="93000004", days_since=5.0, sent=0, outcome="silent"):
    return {
        "thread_id": thread_id,
        "last_seller_sent_at": NOW - int(days_since * 86400),
        "followups_sent": sent,
        "outcome": outcome,
    }


def test_a_thread_silent_long_enough_is_a_candidate() -> None:
    m = load()
    assert m.is_candidate(thread(days_since=5.0), now=NOW) is True


def test_a_thread_answered_yesterday_is_left_alone() -> None:
    # Under four days, following up measurably lowers the reply rate. Sending anyway would
    # trade a real chance of a reply for the feeling of having done something.
    m = load()
    assert m.is_candidate(thread(days_since=1.0), now=NOW) is False
    assert m.is_candidate(thread(days_since=2.9), now=NOW) is False


def test_a_thread_that_converted_is_never_followed_up() -> None:
    # They bought. Asking again would read as not noticing.
    m = load()
    assert m.is_candidate(thread(days_since=9.0, outcome="won"), now=NOW) is False


def test_the_third_followup_is_the_last() -> None:
    # Yesware's data allows six; the cap here is three because Coconala's 迷惑行為 rule
    # makes an over-eager loop an account risk, not merely an ineffective one.
    m = load()
    assert m.is_candidate(thread(days_since=9.0, sent=2), now=NOW) is True
    assert m.is_candidate(thread(days_since=9.0, sent=3), now=NOW) is False


def test_a_thread_with_no_send_time_is_not_guessed_at() -> None:
    m = load()
    assert m.is_candidate({"thread_id": "1", "outcome": "silent"}, now=NOW) is False
    assert m.is_candidate({"thread_id": "1", "last_seller_sent_at": None}, now=NOW) is False


def test_selection_orders_the_longest_silence_first() -> None:
    # The buyer who has waited longest is closest to being lost for good.
    m = load()
    rows = [
        thread("a", days_since=4.0),
        thread("b", days_since=12.0),
        thread("c", days_since=1.0),
        thread("d", days_since=8.0, outcome="won"),
    ]
    assert [row["thread_id"] for row in m.select(rows, now=NOW)] == ["b", "a"]


def test_selection_is_bounded_per_pass() -> None:
    # A backlog of 17 must not become 17 messages in one hour; that is the shape the
    # "不特定多数" rule exists to prevent, even inside threads we are allowed to answer.
    m = load()
    rows = [thread(str(n), days_since=10.0 + n) for n in range(10)]
    assert len(m.select(rows, now=NOW, limit=3)) == 3



def test_a_refused_thread_is_excluded_and_says_why():
    """The buyer who sent us to a competitor is never contacted again."""
    module = load()
    row = thread()
    row["conversation"] = [{"sender": "buyer", "text": "他の方探して下さい。"}]
    assert module.is_candidate(row, now=NOW) is False
    assert module.exclusion_reason(row, now=NOW) == "stopped:other_seller"


def test_a_buyer_still_deciding_is_kept():
    """検討します is the state a follow-up exists to serve, not a refusal."""
    module = load()
    row = thread()
    row["conversation"] = [{"sender": "buyer", "text": "社内で検討しますのでお待ちください"}]
    assert module.exclusion_reason(row, now=NOW) is None


def test_every_other_exclusion_names_itself():
    """An exclusion nobody can explain is indistinguishable from a bug eating buyers."""
    module = load()
    assert module.exclusion_reason({}, now=NOW) == "no_send_time"
    assert module.exclusion_reason(thread(days_since=0.1), now=NOW) == "too_soon"
    assert module.exclusion_reason(thread(outcome="won"), now=NOW) == "already_won"
    assert module.exclusion_reason(thread(sent=3), now=NOW) == "followup_limit"
