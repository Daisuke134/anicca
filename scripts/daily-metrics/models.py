"""Data models for daily metrics."""

from dataclasses import dataclass, asdict
from typing import Optional
import json


@dataclass(frozen=True)
class AppStoreMetrics:
    """Metrics from App Store Connect API."""
    total_downloads_7d: int = 0
    downloads_by_country: tuple[tuple[str, int], ...] = ()
    impressions: int = 0
    page_views: int = 0
    cvr_page_to_download: float = 0.0

    def country_dict(self) -> dict[str, int]:
        return dict(self.downloads_by_country)


@dataclass(frozen=True)
class RevenueCatMetrics:
    """Metrics from RevenueCat API v2."""
    mrr: float = 0.0
    active_subscriptions: int = 0
    active_trials: int = 0
    trial_to_paid_count: int = 0
    trial_expired_count: int = 0
    monthly_churn_rate: float = 0.0


@dataclass(frozen=True)
class MixpanelMetrics:
    """7-day unique-user funnel counts from Mixpanel."""
    onboarding_started: Optional[int] = None
    onboarding_welcome_completed: Optional[int] = None
    onboarding_struggles_completed: Optional[int] = None
    onboarding_struggle_depth_completed: Optional[int] = None
    onboarding_goals_completed: Optional[int] = None
    onboarding_insight_completed: Optional[int] = None
    onboarding_valueprop_completed: Optional[int] = None
    onboarding_notifications_completed: Optional[int] = None
    onboarding_completed: Optional[int] = None
    paywall_primer_viewed: Optional[int] = None
    paywall_plan_selection_viewed: Optional[int] = None
    onboarding_paywall_purchased: Optional[int] = None
    trial_started: Optional[int] = None
    onboarding_paywall_dismissed_free: Optional[int] = None


@dataclass(frozen=True)
class DataQuality:
    """Per-source health status for daily report."""
    asc: str = "missing"
    rc: str = "missing"
    mp: str = "missing"


@dataclass(frozen=True)
class DailyMetrics:
    """Combined daily metrics."""
    date: str
    app_store: Optional[AppStoreMetrics] = None
    revenuecat: Optional[RevenueCatMetrics] = None
    mixpanel: Optional[MixpanelMetrics] = None
    data_quality: DataQuality = DataQuality()
    errors: tuple[str, ...] = ()

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)


@dataclass(frozen=True)
class DayOverDay:
    """Day-over-day comparison."""
    current: float
    previous: float

    @property
    def diff(self) -> float:
        return self.current - self.previous

    @property
    def diff_str(self) -> str:
        if self.diff > 0:
            return f"+{self.diff:.2f}".rstrip("0").rstrip(".")
        elif self.diff < 0:
            return f"{self.diff:.2f}".rstrip("0").rstrip(".")
        return "0"


@dataclass(frozen=True)
class AlertCondition:
    """Alert when metric is below threshold."""
    metric_name: str
    current_value: float
    threshold: float
    unit: str = ""

    @property
    def is_triggered(self) -> bool:
        return self.current_value < self.threshold

    @property
    def message(self) -> str:
        return f"{self.metric_name} {self.current_value}{self.unit} → 目標{self.threshold}{self.unit}に未達"
