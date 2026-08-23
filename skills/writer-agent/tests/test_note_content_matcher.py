import importlib.util
from pathlib import Path


MODULE = Path(__file__).parents[1] / "scripts" / "publication_remote.py"
SPEC = importlib.util.spec_from_file_location("publication_remote", MODULE)
assert SPEC and SPEC.loader
remote = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(remote)


def test_empty_markdown_quote_marker_is_not_a_visible_note_block():
    source = """# 見出し

> **確認項目**
>
> - 一つ目
> - 二つ目
"""
    blocks = remote._source_blocks(source)
    assert ">" not in blocks
    assert "確認項目" in blocks
    assert "一つ目" in blocks
    assert "二つ目" in blocks
