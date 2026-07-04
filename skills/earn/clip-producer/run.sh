#!/usr/bin/env bash
# earn/clip-producer — ON-DEMAND wrapper around ../clip/producer.sh, registered as its own
# run_skill SLOT so a self-funded automaton (ClawRouter/genesis) can DECIDE for itself to
# produce a fresh clip when it notices `earn/clip` reporting queued_clip=none, instead of
# only waiting for the daily launchd cron (ai.anicca.clip-producer / -clawrouter, AM3:17/3:47).
#
# Why this is safe to slot-ify (unlike ig-account-create): producer.sh is a fully
# DETERMINISTIC pipeline (sliced yt-dlp DL -> whisper -> highlight pick -> 9:16 crop ->
# caption burn -> verify_clip gate) with NO visual/CDP judgment step -- no screenshots, no
# clickxy, nothing that requires an agentic vision loop. A single bash entrypoint is
# sufficient; genuinely different from ig-account-create (spec 2026-07-04-openclaw-claude-p
# -merge-design.md §8).
#
# 2026-07-04 タスク#2 follow-up: real-world observation showed ClawRouter picks earn/clip on
# its own (no human/dev intervention) but only ever gets "queued_clip=none" because nothing
# it can run_skill() actually produces content on demand. This slot closes that gap WITHOUT
# me (Claude Code) ever running producer.sh by hand -- the automaton picks this slot itself.
set -uo pipefail
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")/../clip" && pwd)/producer.sh" "$@"
