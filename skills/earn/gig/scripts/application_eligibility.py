#!/usr/bin/env python3
"""Deterministic pre-submit capability and buyer/seller role checks."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


SYNCHRONOUS_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "video_meeting",
        re.compile(
            r"(?:Google\s*Meet|Zoom|Microsoft\s*Teams|Webex|"
            r"ビデオ(?:通話|会議|面談)|オンライン(?:面談|ヒアリング|面接)|"
            r"Web(?:面談|会議|面接))",
            re.IGNORECASE,
        ),
    ),
    (
        "scheduled_interview",
        re.compile(
            r"(?:クライアント|採用|オンライン)?面談.{0,45}"
            r"(?:日時|日程|時刻|対応(?:は)?可能|ご対応|候補日)|"
            r"(?:日時|日程|時刻|候補日).{0,45}(?:面談|面接|ヒアリング)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "live_participation",
        re.compile(
            r"(?:オンライン)?(?:ヒアリング|インタビュー|面接).{0,35}"
            r"(?:参加|ご協力|お話|実施)|"
            r"(?:参加|ご協力).{0,35}(?:ヒアリング|インタビュー|面接)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "phone_or_voice",
        re.compile(
            r"(?:電話|通話|音声通話|本人音声|音声収録|ナレーション収録)",
            re.IGNORECASE,
        ),
    ),
    (
        "live_or_face",
        re.compile(
            r"(?:ライブ講義|生配信への出演|顔出し|顔を出して|対面(?:作業|面談|打合せ|打ち合わせ))",
            re.IGNORECASE,
        ),
    ),
)

PARTICIPANT_BUYER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?:ヒアリング|インタビュー|アンケート|モニター)"
        r".{0,40}(?:ご協力|参加|回答(?:して|いただ|ください)|お話を伺)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"(?:ご協力|参加|回答(?:して|いただ|ください)).{0,40}"
        r"(?:ヒアリング|インタビュー|アンケート|モニター)",
        re.IGNORECASE | re.DOTALL,
    ),
)

SERVICE_PROVIDER_PROPOSAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:支援|サポート).{0,20}(?:提案|提供|いたします|します)"),
    re.compile(r"(?:納品|お渡し|作成|制作|構築|改善案)"),
)

ASYNCHRONOUS_NEGATION = re.compile(
    r"(?:チャット|トークルーム|テキスト).{0,25}"
    r"(?:非同期|隙間時間|完結)|"
    r"(?:非同期|隙間時間).{0,25}(?:チャット|テキスト)",
    re.IGNORECASE | re.DOTALL,
)

SYNC_SIGNAL_WORD = re.compile(
    r"(?:Google\s*Meet|Zoom|Microsoft\s*Teams|Webex|電話|通話|"
    r"面談|面接|ヒアリング|インタビュー|ライブ講義|顔出し|対面)",
    re.IGNORECASE,
)

OPTIONAL_OR_ABSENT = re.compile(
    r"(?:ありません|不要|必要(?:は)?ありません|必須ではありません|"
    r"必須ではない|任意|求めません|できなくても(?:可|可能)|歓迎条件)",
    re.IGNORECASE,
)


def _normalize(value: str | None) -> str:
    return unicodedata.normalize("NFKC", value or "").strip()


def _matching_signals(
    text: str,
    patterns: tuple[tuple[str, re.Pattern[str]], ...],
) -> list[str]:
    return [name for name, pattern in patterns if pattern.search(text)]


def _required_synchronous_text(text: str) -> str:
    segments = re.split(r"(?<=[。\n！？])|(?=ただし|一方で)", text)
    return "\n".join(
        segment
        for segment in segments
        if not (
            SYNC_SIGNAL_WORD.search(segment)
            and OPTIONAL_OR_ABSENT.search(segment)
        )
    )


def evaluate_application(
    brief_text: str,
    proposal_text: str,
    *,
    form_text: str = "",
) -> dict[str, Any]:
    """Return a stable fail-closed verdict for explicit unsupported work."""
    brief = _normalize(brief_text)
    proposal = _normalize(proposal_text)
    form = _normalize(form_text)
    combined = "\n".join(part for part in (brief, form) if part)

    synchronous_signals = _matching_signals(
        _required_synchronous_text(combined),
        SYNCHRONOUS_PATTERNS,
    )
    buyer_expects_participant = any(
        pattern.search(brief) for pattern in PARTICIPANT_BUYER_PATTERNS
    )
    proposal_sells_service = any(
        pattern.search(proposal)
        for pattern in SERVICE_PROVIDER_PROPOSAL_PATTERNS
    )

    reason_codes: list[str] = []
    if synchronous_signals:
        reason_codes.append("synchronous_live_presence_required")
    if buyer_expects_participant and proposal_sells_service:
        reason_codes.append(
            "buyer_participant_seller_provider_role_mismatch"
        )

    return {
        "version": 1,
        "allowed": not reason_codes,
        "reason_codes": reason_codes,
        "signals": {
            "synchronous": synchronous_signals,
            "buyer_expects_participant": buyer_expects_participant,
            "proposal_sells_service": proposal_sells_service,
            "asynchronous_text_explicit": (
                ASYNCHRONOUS_NEGATION.search(combined) is not None
            ),
        },
    }
