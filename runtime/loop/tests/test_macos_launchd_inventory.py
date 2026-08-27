import unittest

from runtime.loop.macos_launchd_inventory import classify_owner, extract_release, runtime_state


class MacosLaunchdInventoryTest(unittest.TestCase):
    def test_owner_requires_existing_classification_or_life_manager_runtime_path(self):
        self.assertEqual(classify_owner("life-manager", "/usr/bin/true"), "life-manager")
        self.assertEqual(
            classify_owner(None, "/Users/me/.local/share/life-manager/releases/abc/run.sh"),
            "life-manager",
        )
        self.assertEqual(classify_owner(None, "/usr/bin/true"), "ambiguous")

    def test_disabled_override_wins_over_loaded_state(self):
        self.assertEqual(runtime_state(True, {"pid": "123"}), "disabled")
        self.assertEqual(runtime_state(False, {"pid": "123"}), "loaded-running")
        self.assertEqual(runtime_state(False, {"pid": "-"}), "loaded-idle")
        self.assertEqual(runtime_state(False, None), "unloaded")

    def test_release_extracts_sha_and_marks_mutable_checkout(self):
        self.assertEqual(
            extract_release("/Users/me/.local/share/life-manager/releases/" + "a" * 40 + "/run.sh"),
            "a" * 40,
        )
        self.assertEqual(
            extract_release("/Users/me/Projects/life-manager-main/apps/run.sh"),
            "mutable-checkout",
        )
        self.assertIsNone(extract_release("/usr/bin/true"))


if __name__ == "__main__":
    unittest.main()
