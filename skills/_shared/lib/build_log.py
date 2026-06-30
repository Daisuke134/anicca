"""build_log — append-only narrative memory per slot (sprint-2).

PROP-M1 (append-only), helper symbols for parse + format.
"""
from __future__ import annotations

import re
from pathlib import Path


def format_log_section(
    *, pass_id: str, ts: int, budget: str,
    picked: str, outcome: str, next_candidate: str,
) -> str:
    """REQ-M1 schema (FIND-018 fix): '## <ISO8601Z> — pass <pass_id>' header."""
    import datetime as _dt
    iso = _dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%dT%H:%MZ")
    return (
        f"## {iso} — pass {pass_id}\n"
        f"budget: {budget}\n"
        f"picked: {picked}\n"
        f"outcome: {outcome}\n"
        f"next-candidate: {next_candidate}\n\n"
    )


_PASS_ID_RE = re.compile(r"^## (\S+) — pass (\S+)")
_FIELD_RE = re.compile(r"^(\w[\w\-]*): (.+)$")


def parse_log_section(section: str) -> dict:
    """Reverse format_log_section. Returns {pass_id, ts_iso, budget, picked, outcome, next_candidate}.
    FIND-018 fix: matches '## <ISO8601Z> — pass <pass_id>' header schema.
    """
    out: dict = {}
    for line in section.splitlines():
        m = _PASS_ID_RE.match(line)
        if m:
            out["ts_iso"] = m.group(1)
            out["pass_id"] = m.group(2)
            # also expose unix ts when parsable
            try:
                import datetime as _dt
                out["ts"] = int(_dt.datetime.strptime(
                    m.group(1), "%Y-%m-%dT%H:%MZ"
                ).replace(tzinfo=_dt.timezone.utc).timestamp())
            except Exception:
                pass
            continue
        m = _FIELD_RE.match(line)
        if m:
            k = m.group(1).replace("-", "_")
            out[k] = m.group(2)
    return out


def append_pass(
    path: Path, *,
    pass_id: str, ts: int, budget: str,
    picked: str, outcome: str, next_candidate: str,
) -> None:
    """Append a pass section to build_log.md. NEVER overwrites existing content."""
    path = Path(path)
    section = format_log_section(
        pass_id=pass_id, ts=ts, budget=budget,
        picked=picked, outcome=outcome, next_candidate=next_candidate,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(section)
