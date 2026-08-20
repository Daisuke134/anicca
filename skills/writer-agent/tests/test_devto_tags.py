import importlib.util
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "scripts"
    / "devto-publish"
    / "devto.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("devto_publish", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DevtoTagNormalizationTest(unittest.TestCase):
    def test_platform_tags_are_ascii_alphanumeric(self):
        module = load_module()

        self.assertEqual(
            module._tags("ai, llm, evaluation, machine-learning"),
            ["ai", "llm", "evaluation", "machinelearning"],
        )


if __name__ == "__main__":
    unittest.main()
