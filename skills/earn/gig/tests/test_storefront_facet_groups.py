"""Facet groups are category-specific: a development category renders different group ids
and options than the writing category the pipeline used to assume everywhere (163/164/165).
This covers the pure grouping step that turns the live form's own per-checkbox rows into one
entry per facet group, using the exact 基本対応範囲(80)/言語(81) shape observed on Coconala's
アプリ開発・制作 subcategory.

Run: python3 -m pytest skills/earn/gig/tests/test_storefront_facet_groups.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import storefront_draft as sdraft


def _row(name, value, label, group_label, required, max_select=None):
    return {"name": name, "value": value, "label": label, "group_label": group_label,
            "required": required, "max_select": max_select}


def test_facet_rows_group_by_id_never_assuming_another_category_s_ids():
    rows = [
        _row("data[facets][80][]", "53", "要件定義", "基本対応範囲", True),
        _row("data[facets][80][]", "54", "設計", "基本対応範囲", True),
        _row("data[facets][81][]", "377", "Java", "言語", True, 3),
        _row("data[facets][81][]", "388", "React Native", "言語", True, 3),
        # A duplicate row (e.g. a re-read) must not double the option list.
        _row("data[facets][80][]", "53", "要件定義", "基本対応範囲", True),
        {"name": "data[Service][overview]", "value": "x"},  # non-facet fields are ignored
    ]

    groups = sdraft._facet_groups_from_rows(rows)

    assert set(groups) == {"80", "81"}
    assert groups["80"]["group_label"] == "基本対応範囲"
    assert groups["80"]["required"] is True
    assert groups["80"]["max_select"] is None
    assert groups["80"]["options"] == [
        {"value": "53", "label": "要件定義"}, {"value": "54", "label": "設計"},
    ]
    assert groups["81"]["max_select"] == 3
    assert groups["81"]["options"] == [
        {"value": "377", "label": "Java"}, {"value": "388", "label": "React Native"},
    ]
    # The old bootstrap writing category's own ids never leak in from elsewhere.
    assert "163" not in groups and "164" not in groups and "165" not in groups


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
