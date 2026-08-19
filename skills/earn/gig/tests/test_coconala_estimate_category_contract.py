import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "coconala_estimate_browser.py"
SPEC = importlib.util.spec_from_file_location("coconala_estimate_browser", MODULE_PATH)
assert SPEC and SPEC.loader
browser = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(browser)


class CategoryTypeContractTests(unittest.TestCase):
    def test_required_shape_proves_visible_row_in_both_paths(self):
        required = (
            "state.row_present&&!state.control_disabled&&!state.row_hidden"
            "&&state.enabled_option_count>0"
        )

        self.assertIn("row_present:!!row", browser.CATEGORY_TYPE_CONTRACT_JS)
        self.assertIn(required, browser.select_sub_expression("Web制作"))
        self.assertIn(required, browser.fill_expression({
            "master_category_label": "Web",
            "sub_category_label": "Web制作",
            "category_type_label": "サイト修正",
            "title": "title",
            "content": "content",
            "price_jpy": 10000,
            "purchase_plan": "single",
        }, "2026-08-20"))

    def test_optional_and_exact_label_guards_remain_fail_closed(self):
        optional = (
            "state.control_disabled&&state.row_hidden"
            "&&state.enabled_option_count===0"
        )
        exact_one = (
            "filter(o=>(o.textContent||\"\").trim()===label&&!o.disabled&&o.value);"
            "if(options.length!==1)"
        )

        select_sub = browser.select_sub_expression("Web制作")
        fill = browser.fill_expression({
            "master_category_label": "Web",
            "sub_category_label": "Web制作",
            "category_type_label": "サイト修正",
            "title": "title",
            "content": "content",
            "price_jpy": 10000,
            "purchase_plan": "single",
        }, "2026-08-20")

        self.assertIn(optional, select_sub)
        self.assertIn(optional, fill)
        self.assertIn(exact_one, select_sub)
        self.assertIn("return options.length===1?options[0]:null", fill)


if __name__ == "__main__":
    unittest.main()
