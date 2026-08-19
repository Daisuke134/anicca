"""Buyer-visible copy must never name a tool the platform withdrew a listing for."""

import json
import sys
from pathlib import Path

GIG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GIG / "scripts"))

import storefront_direct  # noqa: E402


def test_the_terms_from_the_takedown_notice_are_detected():
    assert storefront_direct._prohibited_copy_terms(
        "原稿はWordまたはGoogleドキュメントで納品します") == ["Googleドキュメント"]
    assert storefront_direct._prohibited_copy_terms(
        "スプレッドシートを共有してください") == ["スプレッドシート"]


def test_ordinary_copy_is_left_alone():
    assert storefront_direct._prohibited_copy_terms(
        "Excelファイルの転記手順を整理します", "Word形式で納品します") == []


def test_every_field_of_the_copy_is_searched():
    assert storefront_direct._prohibited_copy_terms(
        "整理し", "見出しを整えます", "本文", "Dropboxで受け渡し") == ["Dropbox"]


def test_a_mutation_that_writes_a_prohibited_tool_is_rejected():
    contract = {"proposed_value": "納品はGoogleドライブ経由です"}
    prohibited = storefront_direct._prohibited_copy_terms(
        json.dumps(contract["proposed_value"], ensure_ascii=False))
    assert prohibited == ["Googleドライブ"]
