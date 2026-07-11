import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.erc20 import ERC20_TRANSFER_TOPIC0, parse_erc20_transfer_amount  # noqa: E402

USDC_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
RECIPIENT = "0x3EcCAD24794ca298D25378E9902A251322ea8749"
OTHER_ADDRESS = "0x9999999999999999999999999999999999999999"


def _topic(addr: str) -> str:
    return "0x" + addr.lower().replace("0x", "").rjust(64, "0")


def _transfer_log(*, token_address=USDC_BASE, to_address=RECIPIENT, amount_units=2_900_000, from_address="0x1111111111111111111111111111111111111111"):
    return {
        "address": token_address,
        "topics": [ERC20_TRANSFER_TOPIC0, _topic(from_address), _topic(to_address)],
        "data": hex(amount_units),
    }


# --- FIND-004: tx-specific Transfer log parsing (pure function) ---


def test_parse_erc20_transfer_amount_matches_correct_log():
    logs = [_transfer_log(amount_units=2_900_000)]
    amount = parse_erc20_transfer_amount(logs=logs, token_address=USDC_BASE, to_address=RECIPIENT)
    assert amount == 2_900_000


def test_parse_erc20_transfer_amount_case_insensitive_addresses():
    logs = [_transfer_log(token_address=USDC_BASE.upper(), to_address=RECIPIENT.upper())]
    amount = parse_erc20_transfer_amount(logs=logs, token_address=USDC_BASE, to_address=RECIPIENT)
    assert amount == 2_900_000


def test_parse_erc20_transfer_amount_no_logs_returns_none():
    assert parse_erc20_transfer_amount(logs=[], token_address=USDC_BASE, to_address=RECIPIENT) is None


def test_parse_erc20_transfer_amount_wrong_token_ignored():
    logs = [_transfer_log(token_address=OTHER_ADDRESS)]
    assert parse_erc20_transfer_amount(logs=logs, token_address=USDC_BASE, to_address=RECIPIENT) is None


def test_parse_erc20_transfer_amount_wrong_recipient_ignored():
    logs = [_transfer_log(to_address=OTHER_ADDRESS)]
    assert parse_erc20_transfer_amount(logs=logs, token_address=USDC_BASE, to_address=RECIPIENT) is None


def test_parse_erc20_transfer_amount_wrong_event_topic_ignored():
    log = _transfer_log()
    log["topics"][0] = "0x" + "00" * 32  # not the Transfer event topic
    assert parse_erc20_transfer_amount(logs=[log], token_address=USDC_BASE, to_address=RECIPIENT) is None


def test_parse_erc20_transfer_amount_malformed_log_shapes_ignored_not_crashed():
    logs = [
        None,
        {"address": USDC_BASE},  # no topics at all
        {"address": USDC_BASE, "topics": [ERC20_TRANSFER_TOPIC0, _topic(RECIPIENT)]},  # only 2 topics
        {"address": USDC_BASE, "topics": [ERC20_TRANSFER_TOPIC0, _topic("0x1"), _topic(RECIPIENT)], "data": None},
        _transfer_log(amount_units=500_000),  # the one real match, after the junk
    ]
    amount = parse_erc20_transfer_amount(logs=logs, token_address=USDC_BASE, to_address=RECIPIENT)
    assert amount == 500_000


def test_parse_erc20_transfer_amount_picks_first_matching_log():
    logs = [_transfer_log(amount_units=1_000_000), _transfer_log(amount_units=9_000_000)]
    amount = parse_erc20_transfer_amount(logs=logs, token_address=USDC_BASE, to_address=RECIPIENT)
    assert amount == 1_000_000
