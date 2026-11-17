# Batch 1/6 — proxy Manager mount, 2026-11-17

Source branch: codex/proxy-manager-mount (anicca). Canonical API files imported
from claude/manager-api-callable-2026-11-17, with no changes to that implementation.
Proxy commit: a95cb5f02 on codex/proxy-manager-mount.
Proxy checkout: /home/hatch/workspace/anicca-products-proxy-manager-mount.
No push, deployment, paid API call, or APNs sender change.

Verification:
- /tmp/manager-mount-venv/bin/python -m pytest models/manager/product/tests -q
  — 2 passed; full output: contract.txt.
- /tmp/manager-mount-venv/bin/python models/manager/product/tests/e2e_mount.py
  /home/hatch/workspace/anicca-products-proxy-manager-mount
  — real local Python + Express router boot, curl health 200, decision 503
  explicitly labelled prior, upstream stopped 503; transcript: e2e.txt.
- git diff --check in both checkouts passed.
- Contract success fixture exercises the unchanged Swift snake_case response,
  backend/policy labels, candidate probability, time window, replay, observation
  acknowledgement, deletion. Generated text is a test fixture, not real inference.

Scope/limits: The production route module was booted in an isolated Express host,
not the full production server (which starts database migrations and jobs).
No production readback or deployment is claimed. Configure the private product
service and proxy variables described in ../README.md when integrating.
The default prior deliberately cannot generate a displayable decision.
The assignment's suggestion that explicit prior labelling might be accepted by
the app differs from the actual Swift validator: it accepts only manager-v1 plus
manager-generated-v1. The client was not loosened; prior returns non-2xx.

Procedure: read using-superpowers (dispatched-task exclusion applies) and
verification-before-completion; source identity checked, user assignment override
followed. Astra Advisor unavailable in this harness. Existing requireAuth reused.
Local dependencies were installed outside Git; temporary local servers terminated.
