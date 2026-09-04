"""Sanity check for catalog.json: parses, every entry keeps required keys,
every newly added price carries an evidence reference. Run: python3 test_catalog.py"""
import json
import os

PATH = os.path.join(os.path.dirname(__file__), "catalog.json")
REQUIRED_KEYS = {
    "id", "title_ja", "family", "value_prop", "tiers", "deliverables",
    "required_inputs", "faq", "evidence", "platform_overrides",
}


def check_evidence(obj, ctx):
    ev = obj.get("evidence")
    assert ev and ev.get("competitor_refs"), f"{ctx}: missing evidence.competitor_refs"
    for ref in ev["competitor_refs"]:
        assert ref.get("path") and ref.get("note"), f"{ctx}: evidence ref missing path/note"


def main():
    with open(PATH, encoding="utf-8") as f:
        data = json.load(f)

    listings = data["listings"]
    assert len(listings) == 20, f"expected 20 listings, got {len(listings)}"

    for listing in listings:
        lid = listing["id"]
        missing = REQUIRED_KEYS - listing.keys()
        assert not missing, f"{lid}: missing required keys {missing}"

        assert "image_guidance" in listing, f"{lid}: missing image_guidance"
        ig = listing["image_guidance"]
        assert ig.get("cover") and ig.get("gallery"), f"{lid}: image_guidance incomplete"
        check_evidence(ig, f"{lid}.image_guidance")

        if "monthly_plan" in listing:
            mp = listing["monthly_plan"]
            assert isinstance(mp.get("price_jpy"), int) and mp["price_jpy"] > 0, f"{lid}: bad monthly_plan price"
            check_evidence(mp, f"{lid}.monthly_plan")

        if "paid_addons" in listing:
            assert listing["paid_addons"], f"{lid}: paid_addons present but empty"
            for addon in listing["paid_addons"]:
                assert isinstance(addon.get("price_jpy"), int) and addon["price_jpy"] > 0, f"{lid}: bad addon price"
                check_evidence(addon, f"{lid}.paid_addons[{addon.get('name')}]")

    print(f"OK: {len(listings)} listings parsed; required keys present; "
          f"all monthly_plan/paid_addons/image_guidance entries carry evidence.")


if __name__ == "__main__":
    main()
