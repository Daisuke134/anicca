"""Structural checks only; these are NOT an iOS hit-testing or E2E pass."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import json

APP = Path(__file__).resolve().parents[2]


class OnboardingShipGateContracts(unittest.TestCase):
    def test_gate_is_in_compiled_target_and_active_test_plan(self):
        project = (APP / 'aniccaios.xcodeproj/project.pbxproj').read_text()
        self.assertEqual(project.count('A1911001C0FFEE0000000001 /* OnboardingTapE2ETests.swift */'), 3)
        self.assertEqual(project.count('A1911001C0FFEE0000000002 /* OnboardingTapE2ETests.swift in Sources */'), 2)
        plan = json.loads((APP / 'aniccaios/OnboardingTap.xctestplan').read_text())
        self.assertEqual(['aniccaiosUITests'], [x['target']['name'] for x in plan['testTargets']])
        scheme = ET.parse(APP / 'aniccaios.xcodeproj/xcshareddata/xcschemes/aniccaios.xcscheme')
        self.assertIn('container:aniccaios/OnboardingTap.xctestplan',
                      [node.attrib['reference'] for node in scheme.findall('.//TestPlanReference')])
        self.assertIn('-testPlan OnboardingTap', (APP / 'scripts/onboarding-ship-gate.sh').read_text())

    def test_flow_uses_coordinates_without_long_press_or_retries(self):
        test = (APP / 'aniccaiosUITests/OnboardingTapE2ETests.swift').read_text()
        self.assertEqual(len(re.findall(r'func testFullOnboarding\w+\(', test)), 3)
        self.assertIn('coordinate(withNormalizedOffset:', test)
        for forbidden in ['press(forDuration:', 'sleep(', '--screenshot-', 'for _ in', 'while ', 'try?']:
            self.assertNotIn(forbidden, test)
        self.assertIn('continueAfterFailure = false', test)
        # The shipped adaptive journey, including every conditional deep-dive type.
        for marker in ['welcome-cta', 'goal-continue', 'focus_categories', 'name-continue',
                       'birth_context', 'mood_baseline', 'struggles-next', 'stress_trigger',
                       'anxiety_target', 'self_criticism', 'avoidance_task', 'sleep_reason',
                       'bedtime', 'wake_time', 'depth-continue', 'belief_themes', 'micro-save',
                       'tone', 'life_context', 'routine_anchors', 'prior_attempts',
                       'prior_helpfulness', 'start_reason', 'quiet_hours', 'theme-continue',
                       'icon-continue', 'widget-interested', 'first-continue', 'reminder-continue',
                       'notifications-allow', 'paywall-plan-cta', 'paywall-close-button', 'feed-scroll']:
            self.assertIn(marker, test)

    def test_primary_shape_is_inside_label_after_sizing(self):
        source = (APP / 'aniccaios/DesignSystem/Components/PrimaryButton.swift').read_text()
        label = source.split('} label: {', 1)[1].split('\n        }', 1)[0]
        self.assertIn('.contentShape(Rectangle())', label)
        self.assertLess(label.index('.frame(minHeight:'), label.index('.contentShape(Rectangle())'))

    def test_background_cannot_receive_input(self):
        source = (APP / 'aniccaios/DesignSystem/AppBackground.swift').read_text()
        self.assertIn('.allowsHitTesting(false)', source)

    def test_versions_are_consistent_across_targets(self):
        project = (APP / 'aniccaios.xcodeproj/project.pbxproj').read_text()
        self.assertEqual(set(re.findall(r'MARKETING_VERSION = ([^;]+);', project)), {'1.10.1'})
        self.assertEqual(set(re.findall(r'CURRENT_PROJECT_VERSION = ([^;]+);', project)), {'836'})

    def test_result_gate_rejects_missing_skipped_failed_or_empty_runs(self):
        verifier = APP / 'scripts/verify-onboarding-result.py'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'summary.json'
            good = dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0, expectedFailures=0)
            cases = [(good, 0), ({}, 1),
                     (dict(good, totalTestCount=0, passedTests=0), 1),
                     (dict(good, passedTests=0, skippedTests=1), 1),
                     (dict(good, failedTests=1), 1),
                     (dict(good, expectedFailures=1), 1)]
            for summary, expected in cases:
                with self.subTest(summary=summary):
                    path.write_text(json.dumps(summary))
                    result = subprocess.run([sys.executable, str(verifier), str(path)],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, expected, result.stderr)



if __name__ == '__main__':
    unittest.main()
