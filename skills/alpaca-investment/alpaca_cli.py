"""Pinned, paper-only Alpaca CLI observation boundary."""

from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any


CLI_VERSION = "0.0.14"
PAPER_ENDPOINT = "https://paper-api.alpaca.markets/v2"
MAX_CREDENTIAL_BYTES = 1_048_576
MAX_OUTPUT_BYTES = 64 * 1024


def _credentials(path: Path) -> dict[str, str]:
    parent, info = path.parent, path.lstat()
    if path.is_symlink() or parent.is_symlink():
        raise ValueError("credential_path_invalid")
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError("credential_path_invalid")
    if stat.S_IMODE(info.st_mode) != 0o600 or stat.S_IMODE(parent.stat().st_mode) != 0o700:
        raise ValueError("credential_permissions_invalid")
    if info.st_size > MAX_CREDENTIAL_BYTES:
        raise ValueError("credential_file_too_large")
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = [row for row in document.get("credentials", [])
            if isinstance(row, dict) and row.get("service") == "app.alpaca.markets"]
    if len(rows) != 1:
        raise ValueError("alpaca_credential_record_invalid")
    row = rows[0]
    if row.get("paper_endpoint") != PAPER_ENDPOINT:
        raise ValueError("live_endpoint_forbidden")
    values = {key: row.get(key) for key in ("api_key", "api_secret")}
    if any(not isinstance(value, str) or not value or len(value) > 8192
           for value in values.values()):
        raise ValueError("alpaca_paper_credentials_unavailable")
    return values  # type: ignore[return-value]


def _run(cli: Path, args: list[str], env: dict[str, str]) -> Any:
    result = subprocess.run(
        [str(cli), *args], env=env, stdin=subprocess.DEVNULL,
        capture_output=True, timeout=30, check=False,
    )
    if result.returncode != 0:
        raise ValueError("alpaca_cli_failed")
    if len(result.stdout) > MAX_OUTPUT_BYTES:
        raise ValueError("alpaca_cli_output_too_large")
    try:
        return json.loads(result.stdout.decode("utf-8").strip())
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("alpaca_cli_json_invalid") from error


def observe(*, credentials_path: Path, cli_path: Path, symbol: str = "SPY") -> dict[str, Any]:
    if symbol != "SPY":
        raise ValueError("unsupported_observation_symbol")
    if not cli_path.is_file() or not os.access(cli_path, os.X_OK):
        raise ValueError("alpaca_cli_unavailable")
    private = _credentials(credentials_path)
    env = {
        **os.environ,
        "ALPACA_API_KEY": private["api_key"],
        "ALPACA_SECRET_KEY": private["api_secret"],
        "ALPACA_LIVE_TRADE": "false",
    }
    version = subprocess.run(
        [str(cli_path), "version"], env=env, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, timeout=10, check=False,
    )
    if version.returncode != 0 or version.stdout.strip() != CLI_VERSION:
        raise ValueError("alpaca_cli_version_unpinned")

    account = _run(cli_path, [
        "account", "get", "--quiet", "--jq",
        "{status:.status,cash:.cash,equity:.equity,last_equity:.last_equity,options_level:.options_trading_level}",
    ], env)
    clock = _run(cli_path, [
        "clock", "get", "--quiet", "--jq",
        "{is_open:.is_open,observed_at:.timestamp,next_open:.next_open,next_close:.next_close}",
    ], env)
    positions = _run(cli_path, [
        "position", "list", "--quiet", "--jq",
        "[.[]|{symbol,qty,side,market_value,unrealized_pl}]",
    ], env)
    orders = _run(cli_path, [
        "order", "list", "--quiet", "--status", "all", "--limit", "500", "--jq", "length",
    ], env)
    activities = _run(cli_path, [
        "account", "activity", "list", "--quiet", "--jq", "length",
    ], env)
    trade = _run(cli_path, [
        "data", "latest-trade", "--symbol", symbol, "--quiet", "--jq",
        "{symbol:.symbol,price:.trade.p,timestamp:.trade.t}",
    ], env)
    options = _run(cli_path, [
        "data", "option", "chain", "--underlying-symbol", symbol, "--limit", "100", "--quiet", "--jq",
        "(.snapshots|length)",
    ], env)
    if not isinstance(account, dict) or not isinstance(clock, dict):
        raise ValueError("alpaca_cli_shape_invalid")
    if not isinstance(positions, list) or not isinstance(orders, int):
        raise ValueError("alpaca_cli_shape_invalid")
    if not isinstance(activities, int) or not isinstance(trade, dict) or not isinstance(options, int):
        raise ValueError("alpaca_cli_shape_invalid")
    return {
        "account": account,
        "activities_count": activities,
        "cli_version": CLI_VERSION,
        "clock": clock,
        "observed_symbol": symbol,
        "open_and_closed_orders_count": orders,
        "option_contracts_count": options,
        "paper": True,
        "positions": positions,
        "trade": trade,
    }
