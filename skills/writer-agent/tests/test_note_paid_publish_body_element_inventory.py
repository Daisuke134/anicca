"""The paid publish path must not send an element class note has never accepted.

MEASURED 2026-08-08 by authenticated read-only GETs of the rejected draft
`n47735d9811e8` and of the four paid articles note has actually accepted at
¥500 — `n190c1d92bf10`, `n7a0eac82f085`, `n84aed983c96c`, `n2fb2c506deda` —
splitting each on the `separator` note itself stores and inventorying both
halves:

    accepted paid halves : every <img> src is https://assets.st-note.com/...
    rejected paid half   : <img src="headline-image.png">
                           <img src="body-diagram.png">

and note's own stored render of that same draft deletes exactly those two
<img> elements while keeping the three note-hosted ones. That is the only
element class present in the rejected paid half and absent from all four
accepted paid halves.

The fixture below reproduces that measured shape byte-for-byte in miniature.
"""

import importlib.util
import sys
import types
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "note-publish" / "publish-paid.py"

# The exact element shapes read off note on 2026-08-08.
NOTE_HOSTED_FIGURE = (
    '<figure name="ea2cc4f0" id="ea2cc4f0">'
    '<img src="https://assets.st-note.com/img/1786034178-q2fGyu504zockXBxlLFJUsIP.png"'
    ' alt="" width="480" height="314" contenteditable="false" draggable="false">'
    "<figcaption></figcaption></figure>"
)
UNHOSTABLE_FIGURE = (
    '<figure name="6ac09900" id="6ac09900">'
    '<img src="body-diagram.png" alt="" width="620" height="457"'
    ' contenteditable="false" draggable="false">'
    "<figcaption>提案書の構成図</figcaption></figure>"
)
UNCAPTIONED_UNHOSTABLE_FIGURE = (
    '<figure name="f7aa6eac" id="f7aa6eac">'
    '<img src="headline-image.png" alt="" width="620" height="457"'
    ' contenteditable="false" draggable="false">'
    "<figcaption></figcaption></figure>"
)

BODY = "\n".join(
    [
        '<p name="p1" id="p1">無料パートの本文です。</p>',
        NOTE_HOSTED_FIGURE,
        '<p name="p2" id="p2">ここまでが無料。</p>',
        UNCAPTIONED_UNHOSTABLE_FIGURE,
        '<p name="p3" id="p3">有料パートの本文です。</p>',
        UNHOSTABLE_FIGURE,
        '<p name="p4" id="p4">終わり。</p>',
    ]
)


def _module():
    sys.path.insert(0, str(SCRIPT.parent))
    sys.modules.setdefault(
        "cloakbrowser", types.SimpleNamespace(launch_context=lambda **kwargs: None)
    )
    spec = importlib.util.spec_from_file_location("note_publish_paid_body", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload(module, **kwargs):
    return module.build_paid_publish_payload(
        {"id": 1, "body": BODY, "name": "t", "slug": "s"},
        price=500,
        after_chars=12,
        tags=[],
        **kwargs,
    )


def _images(html: str) -> list[str]:
    import re

    return [
        match.group(1)
        for match in re.finditer(r'<img\b[^>]*\bsrc="([^"]*)"', html)
    ]


def test_paid_publish_never_sends_an_image_note_cannot_host() -> None:
    module = _module()
    payload = _payload(module)
    whole = payload["free_body"] + payload["pay_body"]
    unhostable = [src for src in _images(whole) if not src.startswith("https://")]
    assert unhostable == [], f"paid publish still carries unhostable images: {unhostable}"


def test_degraded_figure_keeps_its_meaning_instead_of_vanishing() -> None:
    module = _module()
    payload = _payload(module)
    whole = payload["free_body"] + payload["pay_body"]
    assert "提案書の構成図" in whole


def test_degraded_figure_links_to_the_public_asset_when_the_run_staged_one() -> None:
    """note has accepted raw.githubusercontent.com anchors inside a paid half."""
    module = _module()
    staged = {
        "body-diagram.png": (
            "https://raw.githubusercontent.com/Daisuke134/zenn-articles/"
            "main/images/daily-2026-08-07/body-diagram.png"
        )
    }
    payload = _payload(module, resolve_asset_url=lambda src: staged.get(src, ""))
    whole = payload["free_body"] + payload["pay_body"]
    assert (
        '<a href="https://raw.githubusercontent.com/Daisuke134/zenn-articles/'
        'main/images/daily-2026-08-07/body-diagram.png" target="_blank"'
        ' rel="nofollow noopener">提案書の構成図</a>'
    ) in whole


def test_note_hosted_images_are_untouched() -> None:
    module = _module()
    payload = _payload(module)
    whole = payload["free_body"] + payload["pay_body"]
    assert (
        "https://assets.st-note.com/img/1786034178-q2fGyu504zockXBxlLFJUsIP.png" in whole
    )
    assert len(_images(whole)) == 1


def test_editor_only_attributes_are_stripped_from_images() -> None:
    """Second ranked candidate: present in zero accepted bodies, note deletes them itself."""
    module = _module()
    payload = _payload(module)
    whole = payload["free_body"] + payload["pay_body"]
    assert "contenteditable" not in whole
    assert "draggable" not in whole


def test_block_count_and_block_ids_survive_the_transform() -> None:
    """The boundary logic is untouched: same blocks, same ids, same order."""
    module = _module()

    def block_ids(html: str) -> list[str]:
        parsed = module.NoteBodyBlocks(html)
        parsed.feed(html)
        return [block["id"] for block in parsed.blocks]

    normalized, _ = module.normalize_note_publish_body(BODY)
    assert block_ids(normalized) == block_ids(BODY)


def test_normalization_report_names_what_it_degraded() -> None:
    module = _module()
    report: dict = {}
    _payload(module, normalization_report=report)
    assert report["changed"] is True
    assert sorted(report["images_degraded"]) == ["body-diagram.png", "headline-image.png"]
    # Only the surviving note-hosted <img> can still carry them; the two degraded
    # figures no longer have an <img> by the time the attribute pass runs.
    assert report["editor_only_attrs_stripped"] == 2


def test_a_clean_body_is_returned_byte_identical() -> None:
    module = _module()
    clean = '<p name="a" id="a">x</p>\n' + NOTE_HOSTED_FIGURE.replace(
        ' contenteditable="false" draggable="false"', ""
    )
    normalized, report = module.normalize_note_publish_body(clean)
    assert normalized == clean
    assert report["changed"] is False
