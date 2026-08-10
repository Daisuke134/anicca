import importlib.util, json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "agent_runner.py"
class NumericTruthTest(unittest.TestCase):
    def test_provider_usage_distinguishes_absent_and_invalid_optional_numbers(self):
        sys.path.insert(0, str(ROOT)); self.addCleanup(lambda: sys.path.remove(str(ROOT)))
        spec = importlib.util.spec_from_file_location("agent_runner_usage", RUNNER); module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        token_fields = ("input_tokens", "cached_input_tokens", "cache_creation_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens")
        cases = [("codex", {"input_tokens": 10, "output_tokens": 20}, {"cached_input_tokens": ("cached_input_tokens", 0), "reasoning_output_tokens": ("reasoning_output_tokens", 0)}), ("claude", {"input_tokens": 10, "output_tokens": 20}, {"cache_creation_input_tokens": ("cache_creation_input_tokens", 0), "cache_read_input_tokens": ("cached_input_tokens", 0), "reasoning_output_tokens": ("reasoning_output_tokens", 0)}), ("openclaw", {"input": 10, "output": 20}, {"cacheRead": ("cached_input_tokens", 0), "cacheWrite": ("cache_creation_input_tokens", 0), "total": ("total_tokens", 30)})]
        missing = object()
        def extract(provider, payload, cost=missing):
            if provider == "codex": body = {"type": "turn.completed", "usage": payload}
            elif provider == "claude":
                body = {"usage": payload}
                if cost is not missing: body["total_cost_usd"] = cost
            else: body = {"result": {"meta": {"agentMeta": {"lastCallUsage": payload}}}}
            return module.extract_provider_usage(provider, json.dumps(body))
        for provider, payload, optionals in cases:
            for field, (normalized, default) in optionals.items():
                with self.subTest(provider=provider, field=field):
                    absent = extract(provider, payload); self.assertEqual(absent["measurement"], "provider_reported"); self.assertEqual(absent[normalized], default)
                    for value in (True, None, -1, 1.5, "bad"):
                        invalid = extract(provider, {**payload, field: value}); self.assertEqual(invalid["measurement"], "unavailable"); self.assertTrue(all(invalid[name] is None for name in token_fields))
        base = {"input_tokens": 10, "output_tokens": 20}; absent = extract("claude", base); self.assertEqual((absent["provider_cost_usd"], absent["cost_basis"]), (None, "unavailable")); self.assertEqual(extract("claude", base, 1.25)["provider_cost_usd"], 1.25)
        for cost in (True, -1, float("inf"), 10**1000, "bad"):
            with self.subTest(cost=cost):
                invalid = extract("claude", base, cost); self.assertEqual((invalid["measurement"], invalid["provider_cost_usd"], invalid["cost_basis"]), ("provider_reported", None, "unavailable"))
        self.assertEqual(extract("openclaw", {"input": 10, "output": 20, "total": 0})["total_tokens"], 0)
