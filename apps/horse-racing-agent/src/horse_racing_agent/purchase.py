from collections.abc import Mapping


class PurchaseExecutor:
    def execute(
        self,
        request: Mapping[str, object],
        *,
        caller_enabled: bool = False,
        config: Mapping[str, object] | None = None,
        receipt: Mapping[str, object] | None = None,
        side_effects: Mapping[str, object] | None = None,
    ) -> dict[str, str]:
        return {"status": "blocked", "reason": "purchase_disabled"}
