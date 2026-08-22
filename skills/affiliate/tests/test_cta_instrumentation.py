import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "cta_instrumentation.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("cta_instrumentation", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CtaInstrumentationTests(unittest.TestCase):
    def test_transforms_fixed_host_redirect_and_public_href_without_raw_receipt(self):
        library = '''const TOKEN = /^(ai|ho|ej|ee)_[a-z2-7]{20}$/;\nfunction destination(product, token, providerToken) {\n  if (product.kind === "app") {\n}\n    const product = match && products[match[1]];'''
        transformed = MODULE._transform_library(library)
        self.assertIn("AFFILIATE_CTA_V1", transformed)
        self.assertIn('kind: "affiliate"', transformed)
        self.assertIn("https://try.elevenlabs.io/${product.placementId}", transformed)
        page = '''function renderMarkdown(md: string): string {\n  const inline = (s: string) =>\n    s\n      .replace(/&/g, "&amp;")'''
        transformed_page = MODULE._transform_page(page)
        self.assertIn("trackedAffiliateHref", transformed_page)
        self.assertIn("/go/af_${placement}", transformed_page)

    def test_click_observation_joins_exact_placements_and_zero_is_non_money(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            MODULE.atomic_write(state / "cta-instrumentation.json", {
                "state": "LIVE", "commit": "a" * 40,
                "deployed_at": "2026-08-22T00:00:00+00:00",
            })
            responses = [
                io.BytesIO(b'[{"receipt_id":"one","clicked_at":"2026-08-22T01:00:00Z"}]'),
                io.BytesIO(b"[]"),
            ]
            with patch.object(MODULE, "_env", side_effect=["https://project.test", "key"]), \
                 patch.object(MODULE.urllib.request, "urlopen", side_effect=responses):
                result = MODULE.observe_clicks(state, [
                    {"placement_id": "alpha-en-1"}, {"placement_id": "beta-en-1"},
                ])
            self.assertEqual([row["count"] for row in result["placements"]], [1, 0])
            self.assertEqual(result["money_state"], "NON_MONEY")
            self.assertNotIn("key", json.dumps(result))

    def test_v2_scopes_tokens_and_keeps_app_token_requirement(self):
        wrapper = '''  if (!providerToken || !supabaseUrl || !serviceKey)\n    providerToken,'''
        library = '''const TOKEN = /af_([a-z0-9][a-z0-9-]{2,80})/;\n  if (!products || !providerToken || typeof persist !== "function")\n    if (!product)\n      return { statusCode: 404, headers: { "cache-control": "no-store" }, body: "Not Found" };'''
        self.assertIn("AFFILIATE_CTA_V2", MODULE._transform_v2_wrapper(wrapper))
        transformed = MODULE._transform_v2_library(library)
        self.assertIn("elevenlabs-discovered-", transformed)
        self.assertIn('product.kind === "app" && !providerToken', transformed)

    def test_v3_page_sends_only_reduced_source_from_exact_affiliate_article(self):
        page = '''import WriterUnlock from "../../../components/blog/WriterUnlock";
function renderMarkdown(md: string): string {
  const html = renderMarkdown(articleMarkdown);
    <main className="bg-cream">'''
        transformed = MODULE._transform_v3_page(page)
        self.assertIn("AFFILIATE_ENTRY_V1", transformed)
        self.assertIn("affiliatePlacement(articleMarkdown)", transformed)
        self.assertIn("<AffiliateEntryReceipt placementId={affiliatePlacementId}", transformed)

    def test_v3_client_never_sends_raw_referrer_query_cookie_ip_or_user_agent(self):
        client = MODULE.V3_NEW_FILES[
            "apps/landing/components/blog/AffiliateEntryReceipt.tsx"
        ]
        self.assertIn('? "X" : "UNKNOWN"', client)
        self.assertIn('referrerPolicy: "no-referrer"', client)
        self.assertIn('credentials: "omit"', client)
        for forbidden in ("document.referrer,", "location.search", "document.cookie", "userAgent"):
            self.assertNotIn(forbidden, client)

    def test_generated_v3_netlify_handler_executes_its_real_node_test(self):
        with tempfile.TemporaryDirectory() as root:
            landing = Path(root)
            for name, content in MODULE.V3_NEW_FILES.items():
                relative = name.removeprefix("apps/landing/")
                target = landing / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            result = subprocess.run(
                ["node", "--test", "netlify/functions/_lib/__tests__/marketing-entry.test.js"],
                cwd=landing, capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_entry_public_readback_requires_exact_post_only_contract(self):
        error = urllib.error.HTTPError(
            "https://aniccaai.com/.netlify/functions/marketing-entry",
            405, "Method Not Allowed", {"allow": "POST"}, None,
        )
        with patch.object(MODULE.urllib.request, "urlopen", side_effect=error):
            self.assertTrue(MODULE._entry_public_ready())
        missing = urllib.error.HTTPError("https://aniccaai.com", 404, "Not Found", {}, None)
        with patch.object(MODULE.urllib.request, "urlopen", side_effect=missing):
            self.assertFalse(MODULE._entry_public_ready())


if __name__ == "__main__":
    unittest.main()
