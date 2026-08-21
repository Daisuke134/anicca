import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "publication_resume.py"
SPEC = importlib.util.spec_from_file_location("publication_resume", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_substack_identities_are_resolved_separately() -> None:
    identities = MODULE.configured_destination_identities(
        {
            "SUBSTACK_PUBLICATION_JA": "aniccabuddha.substack.com",
            "SUBSTACK_PUBLICATION_EN": "anicca-global.substack.com",
        }
    )

    assert identities["substack/ja"] == "aniccabuddha.substack.com"
    assert identities["substack/en"] == "anicca-global.substack.com"
    MODULE.validate_destination_identities(identities)


def test_substack_identity_conflation_fails_closed() -> None:
    with pytest.raises(MODULE.InvariantError, match="distinct"):
        MODULE.configured_destination_identities(
            {
                "SUBSTACK_PUBLICATION_JA": "aniccabuddha.substack.com",
                "SUBSTACK_PUBLICATION_EN": "aniccabuddha.substack.com",
            }
        )

    with pytest.raises(MODULE.InvariantError, match="required"):
        MODULE.configured_destination_identities(
            {"SUBSTACK_PUBLICATION_JA": "aniccabuddha.substack.com"}
        )


def test_headline_and_body_media_must_have_distinct_bytes(tmp_path: Path) -> None:
    run = tmp_path / "runs" / "daily-2026-08-21"
    gates = run / "gates"
    gates.mkdir(parents=True)
    ledger = tmp_path / "articles.jsonl"
    state = gates / "publication-state.json"
    draft = (
        "---\ntitle: Article\ntags: [writer]\n---\n\n"
        "# Article\n\n"
        "<!-- canonical-media:start -->\n"
        "![](headline-image.png)\n\n"
        "```mermaid\nflowchart LR\nA-->B\n```\n"
        "![](body-diagram.png)\n"
        "<!-- canonical-media:end -->\n"
    )
    ja = run / "article-ja.md"
    en = run / "article-en.md"
    ja.write_text(draft, encoding="utf-8")
    en.write_text(draft, encoding="utf-8")
    headline = run / "headline-image.png"
    body = run / "body-diagram.png"
    headline.write_bytes(b"same-bytes")
    body.write_bytes(b"same-bytes")
    store = MODULE.PublicationStore(state, ledger)
    with pytest.raises(MODULE.InvariantError, match="duplicate media bytes"):
        store._validate_layout(
            run.name,
            run,
            {"ja": ja, "en": en},
            None,
            headline,
            [body],
            require_state=False,
        )
