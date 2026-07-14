#!/usr/bin/env bash
# run.sh — the loop's run-skill.mjs::resolveSkillPath always looks for run.sh regardless of the
# registry `entrypoint` field (documented in registry.json, ubi slot riskNote). Without this shim
# every `report` wake failed "report skill not found" (observed live 2026-07-14, founder loop).
exec "$(cd "$(dirname "$0")" && pwd)/anicca-report.sh" "$@"
