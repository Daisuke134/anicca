import importlib.util
from pathlib import Path


MODULE = Path(__file__).parents[1] / "scripts" / "x-publish" / "x_anchor.py"
CHUNKED = MODULE.with_name("x_chunked.py")
SPEC = importlib.util.spec_from_file_location("x_anchor", MODULE)
assert SPEC and SPEC.loader
x_anchor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(x_anchor)


def test_markdown_link_anchor_matches_html_list_item_and_keeps_image():
    html = (
        '<p>前半</p>'
        '<ul><li><a href="https://x.com/example">X上の長文記事の事例</a>'
        ' — 短文、無料資料、手順付きコンテンツをつなぐ需要</li></ul>'
        '<p>後半</p>'
    )
    chunks = x_anchor.build_chunks(
        html,
        [{
            "block_index": 1,
            "path": "/tmp/body.png",
            "after_text": "- [X上の長文記事の事例](https://x.com/example) — 短文、無料資料、手順付きコ",
        }],
    )
    assert [kind for kind, _ in chunks] == ["html", "img", "html"]
    assert chunks[0][1].endswith("</li></ul>")
    assert chunks[1][1] == "/tmp/body.png"


def test_missing_anchor_fails_closed():
    try:
        x_anchor.build_chunks(
            "<p>本文</p>",
            [{"block_index": 1, "path": "/tmp/body.png", "after_text": "存在しない"}],
        )
    except ValueError as error:
        assert str(error).startswith("ANCHOR NOT FOUND:")
    else:
        raise AssertionError("missing image anchor must not be silently dropped")


def test_browser_chunker_fails_closed_on_media_loss():
    source = CHUNKED.read_text(encoding="utf-8")
    assert '[data-testid="empty_state_button_text"]' in source
    assert 'if i in (6, 15, 24): open_editor()' in source
    assert 'raise SystemExit(f"IMAGE MISSING: {v}")' in source
    assert 'raise SystemExit(f"IMG PASTE FAILED after retries: {v}")' in source
    assert "IMAGE COUNT MISMATCH" in source
