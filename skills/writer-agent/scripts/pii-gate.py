#!/usr/bin/env python3
"""Fail-closed publish-time PII gate CLI. Exit 0 = clean, ANY non-zero exit = do not publish.

This pipeline is bash-heavy, so the scanner (scripts/_shared/pii_scan.py) is exposed as a tiny
process boundary every publish script can call before it makes an artifact public:

    python3 scripts/pii-gate.py --stage <who-is-publishing> FILE [FILE...]
    python3 scripts/pii-gate.py --stage <who> --run-dir "$ARTICLE_RUN_DIR"   # the frozen exact8 set

Contract, and the whole point of the file -- there is NO path where a problem produces exit 0:

    exit 0  every scanned surface is clean
    exit 3  at least one PII finding                 (rule ids on stderr)
    exit 4  blocklist missing / unreadable / empty   (WRITER_PII_BLOCKLIST unset, etc.)
    exit 5  anything else at all -- unreadable file, undecodable bytes, import failure, a bug in
            the scanner, an unexpected exception. Refusing is the default, not the exception.
    exit 2  bad CLI usage (argparse) -- also non-zero, also not a publish.

stderr is machine-readable and NEVER contains a matched literal:

    PII-GATE BLOCK stage=<stage> rules=<rule.id,rule.id> findings=<rule.id@<offset>(Ab***yz) ...>
    PII-GATE CONFIG-FAIL stage=<stage> rules=pii.config.blocklist-missing reason=<...>
    PII-GATE ERROR stage=<stage> rules=pii.gate.internal-error reason=<exception class>

`--run-dir` scans the three immutable artifacts every managed destination is derived from
(article-ja.md, article-en.md, x-post-ja.txt) plus any --file given, so a caller that only knows
the run directory still gates the exact bytes that are about to go out.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE / "_shared") not in sys.path:
    sys.path.insert(0, str(HERE / "_shared"))

# A failure to even import the scanner must refuse, never fall through to "no findings".
try:
    import pii_scan
    import pii_gate as pii_gate_shared
except Exception as error:  # noqa: BLE001 -- fail closed on ANY import problem
    print(
        "PII-GATE ERROR stage=<import> rules=pii.gate.internal-error "
        f"reason={type(error).__name__}",
        file=sys.stderr,
    )
    raise SystemExit(5) from error

EXIT_CLEAN = 0
EXIT_BLOCKED = 3
EXIT_CONFIG = 4
EXIT_ERROR = 5

# The frozen artifacts every managed destination republishes. Missing ones are skipped (a run may
# legitimately have only one language staged); an unreadable one is an error, not a skip.
RUN_ARTIFACTS = pii_gate_shared.RUN_ARTIFACTS
PAIR_ARTIFACTS = pii_gate_shared.PAIR_ARTIFACTS


def collect(args: argparse.Namespace) -> dict[str, str]:
    """Return {label: text} for everything to scan. Raises on any unreadable surface."""
    sources: dict[str, str] = {}
    paths: list[Path] = [Path(item) for item in args.files]
    if args.run_dir:
        run_dir = Path(args.run_dir)
        # A pair scans only its own payload; an unknown/absent pair scans everything.
        for name in PAIR_ARTIFACTS.get(args.pair.strip(), RUN_ARTIFACTS):
            candidate = run_dir / name
            if candidate.is_file():
                paths.append(candidate)
    if not paths:
        raise ValueError("pii-gate was given nothing to scan")
    for path in paths:
        # errors="strict": undecodable bytes are a refusal, not a silently truncated scan.
        sources[str(path)] = path.read_text(encoding="utf-8")
    return sources


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="files to scan before they become public")
    parser.add_argument("--run-dir", default="", help="also scan this run's frozen artifacts")
    parser.add_argument(
        "--pair", default="",
        help="narrow --run-dir to this destination's payload (unknown pair => scan all)",
    )
    parser.add_argument("--stage", default="publish", help="who is about to publish")
    parser.add_argument("--text", default=None, help="scan this literal string instead of a file")
    args = parser.parse_args()

    try:
        sources = {"--text": args.text} if args.text is not None else collect(args)
        pii_scan.enforce(args.stage, sources, context={"caller": args.stage})
    except pii_scan.PIIViolation as violation:
        print(
            f"PII-GATE BLOCK stage={args.stage} "
            f"rules={','.join(violation.rule_ids)} "
            f"findings={' '.join(pii_scan.summarize(violation.findings))}",
            file=sys.stderr,
        )
        return EXIT_BLOCKED
    except pii_scan.PIIConfigError as error:
        print(
            f"PII-GATE CONFIG-FAIL stage={args.stage} "
            f"rules=pii.config.blocklist-missing reason={error}",
            file=sys.stderr,
        )
        return EXIT_CONFIG
    except Exception as error:  # noqa: BLE001 -- fail closed on ANY unexpected failure
        print(
            f"PII-GATE ERROR stage={args.stage} rules=pii.gate.internal-error "
            f"reason={type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return EXIT_ERROR

    print(f"PII-GATE PASS stage={args.stage} scanned={len(sources)}")
    return EXIT_CLEAN


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as error:  # noqa: BLE001 -- even a KeyboardInterrupt must not publish
        print(
            f"PII-GATE ERROR stage=<toplevel> rules=pii.gate.internal-error "
            f"reason={type(error).__name__}",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_ERROR) from error
