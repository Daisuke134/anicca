"""PROP-G2-static (required:true, Tier 1 static-analysis) — INV-13 static half.

Spec: REQ-G2(a) — skill code MUST NOT contain a write to its own manifest.json.
"""
import pytest

from lib.manifest import skill_writes_own_manifest  # FAIL until 2b


# Python AST attack corpus — skill at /path/to/skill/run.py. skill_writes_own_manifest()
# is pure string/AST analysis (no filesystem access — see lib/manifest.py), so this can be
# any skill-shaped path; it does not need to resolve to a real directory.
SKILL_DIR = "__REPO_ROOT__/skills/example-skill"


def test_direct_literal_write_detected():
    src = (
        "with open('__REPO_ROOT__/skills/example-skill/manifest.json', 'w') as f:\n"
        "    f.write('{}')\n"
    )
    assert skill_writes_own_manifest(src, SKILL_DIR) is True


def test_relative_dunder_file_write_detected():
    src = (
        "from pathlib import Path\n"
        "(Path(__file__).parent / 'manifest.json').write_text('{}')\n"
    )
    assert skill_writes_own_manifest(src, SKILL_DIR) is True


def test_variable_path_concat_detected():
    src = (
        "manifest = SKILL_DIR + '/manifest.json'\n"
        "open(manifest, 'w').write(json.dumps(data))\n"
    )
    assert skill_writes_own_manifest(src, SKILL_DIR) is True


# ── negative: writes to OTHER files, or reads, are OK ────────────────
def test_writes_to_other_files_not_flagged():
    src = (
        "open('/tmp/log.txt', 'w').write('hello')\n"
        "open('events.jsonl', 'a').write(json.dumps(event))\n"
    )
    assert skill_writes_own_manifest(src, SKILL_DIR) is False


def test_reads_own_manifest_not_flagged():
    src = "manifest = json.load(open('manifest.json'))"
    assert skill_writes_own_manifest(src, SKILL_DIR) is False
