from horse_racing_agent.purchase import PurchaseExecutor


class FailIfCalled:
    def __init__(self, label):
        self.label = label
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError(f"forbidden side effect called: {self.label}")


def test_live_request_is_blocked_without_side_effects():
    side_effects = {
        name: FailIfCalled(name)
        for name in ("credential_reader", "network_transport", "dom_adapter", "wallet_bank")
    }
    result = PurchaseExecutor().execute(
        {"action": "LIVE", "stake": 100},
        caller_enabled=True,
        config={"purchase_enabled": True},
        receipt={"official": True},
        side_effects=side_effects,
    )

    assert result == {"status": "blocked", "reason": "purchase_disabled"}
    assert all(effect.calls == 0 for effect in side_effects.values())


def test_every_live_request_is_fail_closed():
    result = PurchaseExecutor().execute(
        {"action": "LIVE", "provider": "arbitrary", "stake": 100},
        caller_enabled=False,
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "purchase_disabled"
