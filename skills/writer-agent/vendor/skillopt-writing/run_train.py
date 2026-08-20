#!/usr/bin/env python3
"""Registration wrapper for the SkillOpt feasibility probe.

Why this file exists: `scripts/train.py` (both the /tmp/SkillOpt checkout
and the copy installed into ~/.venvs/skillopt) discovers benchmarks through
one hardcoded function, `_register_builtins()`, which populates a plain
`_ENV_REGISTRY` dict -- there is no plugin/entry-point/env-var discovery
mechanism (checked directly in the installed source; see FEASIBILITY.md).
The guide's own Step 5 says to edit `scripts/train.py` to register a new
benchmark, but Task B's brief is explicit: do not modify anything inside
/tmp/SkillOpt, and (by the same logic) not the installed copy either --
this is a probe of the tool AS SHIPPED, not a patched fork of it.

This wrapper achieves registration without either edit: it puts this
directory on sys.path (so `import writing` resolves to ./writing/), then
monkeypatches `scripts.train._ENV_REGISTRY["writing"]` at runtime, BEFORE
calling the real `main()`. This is a real, if unusual, finding in its own
right -- it is the only way to add a benchmark to this CLI without either
forking the upstream file or shipping a fork of the installed package.
"""
from __future__ import annotations

import sys
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(VENDOR_DIR))

import scripts.train as _train  # noqa: E402  (import after sys.path mutation, required)
from writing.adapter import WritingAdapter  # noqa: E402

_train._ENV_REGISTRY["writing"] = WritingAdapter

if __name__ == "__main__":
    sys.exit(_train.main())
