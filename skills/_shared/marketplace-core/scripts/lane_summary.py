"""The per-wake lane summary every marketplace lane sends, in one shape.

Lancers renders this inside its own reporter, so CrowdWorks reporting only its successes meant Dais
could not tell "nothing was eligible" from "the lane is broken" — both were silence. This is the
second consumer, so the shape lives here rather than being copied a second time.

Rendered form, matching what Lancers already sends:

    [CrowdWorks][応募] ⚠️ proposal_form_changedで完了できませんでした
    確認: 公開案件226件 / 既応募13件 / 対象外112件 / 予算不足7件 / 応募候補1件 / 公式確認1件。
    応募実績: 今日11件 / 累計13件（公式proposal receipt）。
    次: 5分後のwakeで新着案件の確認と応募を続けます。
"""

from typing import Mapping, Optional, Sequence

_ICON_OK = "✅"
_ICON_APPLIED = "📨"
_ICON_FAIL = "⚠️"


def _count(value: object) -> str:
    return f"{value}件" if isinstance(value, int) and not isinstance(value, bool) else "取得できませんでした"


def render_lane_summary(
    *,
    platform_display_name: str,
    lane: str,
    headline: str,
    icon: str,
    counts: Sequence[tuple[str, object]],
    today_verified: object,
    total_verified: object,
    next_action: str,
) -> str:
    """One wake, one sentence per fact. Counts are (label, value) in display order."""
    checked = " / ".join(f"{label}{_count(value)}" for label, value in counts)
    return "\n".join((
        f"[{platform_display_name}][{lane}] {icon} {headline}",
        f"確認: {checked}。",
        f"応募実績: 今日{_count(today_verified)} / 累計{_count(total_verified)}（公式proposal receipt）。",
        f"次: {next_action}",
    ))


def summarise_apply_wake(
    *,
    platform_display_name: str,
    status: Mapping[str, object],
    today_verified: int,
    total_verified: int,
    next_action: str = "5分後のwakeで新着案件の確認と応募を続けます。",
) -> Optional[str]:
    """Render one apply wake from the owner's own status payload.

    Returns None when the wake carries nothing a reader could act on.
    """
    if not isinstance(status, Mapping): return None
    inspected = status.get("inspected_jobs") if isinstance(status.get("inspected_jobs"), Mapping) else {}
    state = str(status.get("status") or "")
    ok = status.get("ok") is True
    submitted = bool(status.get("submitted"))
    if not ok:
        icon, headline = _ICON_FAIL, f"{state or 'unknown'}で完了できませんでした"
    elif submitted:
        icon, headline = _ICON_APPLIED, "応募を送信し、公式ページで確認しました"
    else:
        icon, headline = _ICON_OK, "応募できる新しい案件はありませんでした"
    counts: list[tuple[str, object]] = [
        ("公開案件", inspected.get("inspected")),
        ("募集終了・実績なし発注者", inspected.get("closed_or_unverified")),
        ("内容不一致", inspected.get("off_topic")),
        ("対象外カテゴリ", inspected.get("wrong_category")),
        ("予算不足", inspected.get("budget")),
        ("取り込み", status.get("imported_applications")),
    ]
    return render_lane_summary(
        platform_display_name=platform_display_name,
        lane="応募",
        headline=headline,
        icon=icon,
        counts=[(label, value) for label, value in counts if value is not None],
        today_verified=today_verified,
        total_verified=total_verified,
        next_action=next_action,
    )


__all__ = ["render_lane_summary", "summarise_apply_wake"]
