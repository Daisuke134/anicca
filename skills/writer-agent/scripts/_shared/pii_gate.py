#!/usr/bin/env python3
"""One-line fail-closed PII gate for the Python publishers in this pipeline.

The bash publishers call scripts/pii-gate.py (a process); the Python publishers call
`gate_files(...)` / `gate_text(...)` from here. Both funnel into the same
pii_scan.enforce(), so there is exactly one place where "is this safe to make public" is
decided, and exactly one blocklist source.

Every failure mode -- a finding, an unconfigured blocklist, an unreadable artifact, an
undecodable byte, a bug inside the scanner -- raises SystemExit with a non-empty message and a
non-zero status. There is deliberately no return value and no exception a caller can mistake for
"clean": the only way past these functions is a clean scan.

Messages carry rule ids and redacted spans only, never a matched literal.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Mapping

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

try:
    import pii_scan
except Exception as error:  # noqa: BLE001 -- an unimportable gate must block, never wave through
    raise SystemExit(
        f"REFUSED: PII gate is unavailable (rules=pii.gate.internal-error "
        f"reason={type(error).__name__}); refusing to publish"
    ) from error

# The frozen artifacts every managed destination is derived from.
RUN_ARTIFACTS = ("article-ja.md", "article-en.md", "x-post-ja.txt")

# Which frozen artifact each destination actually makes public. Gating a pair against the WHOLE
# run would refuse a clean payload because a *different* language was dirty -- measured on run
# 20260729-173948, where x-post-ja.txt was clean while both articles carried an operator handle.
# Blocking that x-post would have cost a publish and prevented no leak.
# An unknown/absent pair falls back to the whole run, so the default stays fail-closed.
PAIR_ARTIFACTS = {
    "note/ja": ("article-ja.md",),
    "zenn-article/ja": ("article-ja.md",),
    "substack/ja": ("article-ja.md",),
    "x-article/ja": ("article-ja.md",),
    "devto/en": ("article-en.md",),
    "substack/en": ("article-en.md",),
    "x-article/en": ("article-en.md",),
    "x-post/ja": ("x-post-ja.txt",),
}


def gate_text(stage: str, sources: Mapping[str, str], *, context: Mapping[str, object] | None = None) -> None:
    """Refuse unless every labelled string is clean."""
    try:
        pii_scan.enforce(stage, dict(sources), context=dict(context or {"caller": stage}))
    except pii_scan.PIIViolation as violation:
        raise SystemExit(
            f"REFUSED: PII gate BLOCK at {stage} "
            f"rules={','.join(violation.rule_ids)} "
            f"findings={' '.join(pii_scan.summarize(violation.findings))}"
        ) from violation
    except pii_scan.PIIConfigError as error:
        raise SystemExit(
            f"REFUSED: PII gate CONFIG-FAIL at {stage} "
            f"rules=pii.config.blocklist-missing reason={error}"
        ) from error
    except SystemExit:
        raise
    except BaseException as error:  # noqa: BLE001 -- fail closed on ANY unexpected failure
        raise SystemExit(
            f"REFUSED: PII gate ERROR at {stage} rules=pii.gate.internal-error "
            f"reason={type(error).__name__}: {error}"
        ) from error


def gate_files(stage: str, paths: Iterable[object], *, context: Mapping[str, object] | None = None) -> None:
    """Refuse unless every named file exists, decodes, and is clean."""
    sources: dict[str, str] = {}
    try:
        candidates = [Path(str(item)) for item in paths]
        if not candidates:
            raise ValueError("PII gate was given no artifact to scan")
        for path in candidates:
            # errors default to strict: undecodable bytes refuse instead of scanning a
            # silently mangled copy of what is about to be published.
            sources[str(path)] = path.read_text(encoding="utf-8")
    except SystemExit:
        raise
    except BaseException as error:  # noqa: BLE001 -- unreadable artifact == do not publish
        raise SystemExit(
            f"REFUSED: PII gate ERROR at {stage} rules=pii.gate.internal-error "
            f"reason={type(error).__name__}: {error}"
        ) from error
    gate_text(stage, sources, context=context)


def gate_run_dir(
    stage: str,
    run_dir: object,
    *,
    extra: Iterable[object] = (),
    pair: str = "",
) -> None:
    """Refuse unless the frozen artifacts this publish will expose (plus `extra`) are clean.

    `pair` narrows the scan to that destination's own payload (see PAIR_ARTIFACTS). An unknown or
    empty pair scans the whole run. An absent run directory, or a run directory holding none of
    the expected artifacts, is itself a refusal: a managed publisher that cannot find the bytes it
    is about to republish must not republish them.
    """
    base = Path(str(run_dir))
    wanted = PAIR_ARTIFACTS.get(str(pair).strip(), RUN_ARTIFACTS)
    present = [base / name for name in wanted if (base / name).is_file()]
    targets = [*present, *[Path(str(item)) for item in extra]]
    if not targets:
        raise SystemExit(
            f"REFUSED: PII gate ERROR at {stage} rules=pii.gate.internal-error "
            f"reason=no frozen artifact for pair={pair or '<all>'} found under {base}"
        )
    gate_files(
        stage, targets, context={"caller": stage, "run_dir": str(base), "pair": str(pair)}
    )


def gate_pair(stage: str, run_dir: object, pair: str, *, extra: Iterable[object] = ()) -> None:
    """gate_run_dir narrowed to one destination's payload. Unknown pair => scan everything."""
    gate_run_dir(stage, run_dir, extra=extra, pair=pair)
