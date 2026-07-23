#!/usr/bin/env python3
"""Own the shared headed CloakBrowser context for the lifetime of the process."""

from __future__ import annotations

import argparse
import signal
import time

from cloakbrowser import launch_persistent_context


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()

    context = launch_persistent_context(
        args.profile,
        headless=False,
        humanize=True,
        args=[
            f"--remote-debugging-port={args.port}",
            "--remote-debugging-address=127.0.0.1",
            "--remote-allow-origins=*",
        ],
    )
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(f"daily-driver persistent context alive on 127.0.0.1:{args.port}", flush=True)
    try:
        while not stopping:
            time.sleep(1)
    finally:
        context.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
