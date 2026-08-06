from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any


PINNED_IMAGE = re.compile(r"^grafana/otel-lgtm@sha256:[a-f0-9]{64}$")


def docker_run_args(config: dict[str, Any]) -> list[str]:
    image = str(config.get("image") or "")
    name = str(config.get("container_name") or "")
    retention = str(config.get("retention") or "")
    if PINNED_IMAGE.fullmatch(image) is None:
        raise ValueError("observability image must be pinned by sha256 digest")
    if name != "anicca-job-hunter-observability" or retention != "30d":
        raise ValueError("observability service contract is invalid")
    volume = Path(str(config.get("volume") or "")).expanduser().resolve()
    volume.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(volume, 0o700)
    return [
        "docker", "run", "--detach", "--name", name, "--restart", "unless-stopped",
        "--publish", "127.0.0.1:4318:4318", "--publish", "127.0.0.1:3000:3000",
        "--volume", f"{volume}:/data", "--log-opt", "max-size=10m", "--log-opt",
        "max-file=3", "--env",
        "PROMETHEUS_EXTRA_ARGS=--storage.tsdb.retention.time=30d", "--env",
        "LOKI_EXTRA_ARGS=--limits.retention-period=30d", image,
    ]


def health_receipt(*, image_id: str, running: bool, otlp_healthy: bool,
                   grafana_healthy: bool) -> dict[str, Any]:
    healthy = running and otlp_healthy and grafana_healthy
    return {
        "version": 1,
        "status": "healthy" if healthy else "unhealthy",
        "image_id": image_id,
        "running": running,
        "otlp_healthy": otlp_healthy,
        "grafana_healthy": grafana_healthy,
        "listeners": ["127.0.0.1:3000", "127.0.0.1:4318"],
    }


def _probe(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("start", "health"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.command == "start":
        subprocess.run(docker_run_args(config), check=True, timeout=180)
    name = str(config["container_name"])
    inspected = subprocess.run(
        ["docker", "inspect", name, "--format", "{{.Image}} {{.State.Running}}"],
        check=False, capture_output=True, text=True, timeout=15,
    )
    fields = inspected.stdout.strip().split()
    receipt = health_receipt(
        image_id=fields[0] if fields else "",
        running=len(fields) == 2 and fields[1] == "true",
        otlp_healthy=_probe("http://127.0.0.1:4318/"),
        grafana_healthy=_probe("http://127.0.0.1:3000/api/health"),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "healthy" else 1


if __name__ == "__main__":
    raise SystemExit(main())
