#!/usr/bin/env python3
"""Inspect or align one canonical Lancers storefront offer."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
DEFAULT_PRODUCT = HERE.parent / "products" / "monthly-sns-content-ops-v1.json"
ORIGIN = "https://www.lancers.jp"


class OfferError(RuntimeError): pass


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None: raise OfferError("runtime_unavailable")
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    return module


def _product(path: Path) -> tuple[dict[str, Any], Path]:
    try: value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError): raise OfferError("product_invalid") from None
    if not isinstance(value, dict): raise OfferError("product_invalid")
    strings = ("product_id", "listing_external_id", "title_stem", "subtitle", "category", "subcategory", "service_type", "industry", "description", "notice", "image_path")
    if any(not isinstance(value.get(key), str) or not value[key].strip() for key in strings): raise OfferError("product_invalid")
    if not re.fullmatch(r"[0-9]+", value["listing_external_id"]): raise OfferError("product_invalid")
    if not (1 <= len(value["title_stem"] + "ます") <= 40 and len(value["subtitle"]) <= 60 and len(value["description"]) <= 2000 and len(value["notice"]) <= 2000): raise OfferError("product_invalid")
    tags, plans = value.get("tags"), value.get("plans")
    if not isinstance(tags, list) or not 1 <= len(tags) <= 5 or len(set(tags)) != len(tags) or not all(isinstance(tag, str) and tag.strip() for tag in tags): raise OfferError("product_invalid")
    if not isinstance(plans, list) or len(plans) != 3: raise OfferError("product_invalid")
    superseded = value.get("superseded_listing_ids")
    if not isinstance(superseded, list) or len(superseded) != len(set(superseded)) or any(not isinstance(item, str) or re.fullmatch(r"[0-9]+", item) is None for item in superseded) or value["listing_external_id"] in superseded: raise OfferError("product_invalid")
    for plan in plans:
        if not isinstance(plan, dict) or not isinstance(plan.get("description"), str) or not 1 <= len(plan["description"]) <= 80 or plan.get("delivery_days") not in {1,2,3,4,5,6,7,10,14,21,30,45,60,75,90} or type(plan.get("price_jpy")) is not int or plan["price_jpy"] < 1000: raise OfferError("product_invalid")
    image = (path.parent / value["image_path"]).resolve()
    if not image.is_file() or image.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif"}: raise OfferError("product_invalid")
    value["public_title"] = value["title_stem"] + "ます"
    return value, image


def _text(page: Any, selector: str) -> str:
    locator = page.locator(selector)
    if locator.count() != 1: raise OfferError("public_readback_invalid")
    text = " ".join(str(locator.inner_text() or "").split())
    if not text: raise OfferError("public_readback_invalid")
    return text


def _public(page: Any, product: Mapping[str, Any]) -> dict[str, Any]:
    listing_id = product["listing_external_id"]; public_url = f"{ORIGIN}/menu/detail/{listing_id}"
    response = page.goto(public_url, wait_until="domcontentloaded", timeout=30_000)
    if response is None or response.status != 200 or page.url != public_url: raise OfferError("public_readback_invalid")
    canonical = page.locator('link[rel="canonical"]')
    og = page.locator('meta[property="og:url"]')
    if canonical.count() != 1 or canonical.get_attribute("href") != public_url or og.count() != 1 or og.get_attribute("content") != public_url: raise OfferError("canonical_mismatch")
    plans = []
    for section in page.locator("li.p-menu-browse-detail__sidebar-content.js-project-plan-tab-content").all():
        fields = [section.locator(selector) for selector in ("p.p-menu-browse-detail__sidebar-description", "div.p-menu-browse-detail__sidebar-header-price", "div.p-menu-browse-detail__sidebar-menu")]
        if [field.count() for field in fields] == [0, 0, 0]: continue
        if [field.count() for field in fields] != [1, 1, 1]: raise OfferError("public_readback_invalid")
        description = " ".join(fields[0].inner_text().split()); price = "".join(re.findall(r"[0-9]", fields[1].inner_text())); delivery = re.search(r"納期\s*([0-9]+)\s*日", fields[2].inner_text())
        if not description or not price or delivery is None: raise OfferError("public_readback_invalid")
        plans.append({"description": description, "price_jpy": int(price), "delivery_days": int(delivery.group(1))})
    routes = []
    for prefix in ("basicMain", "standardMain", "premiumMain"):
        for month in (1, 3, 6):
            field = page.locator(f"#{prefix}{month}")
            if field.count() != 1: raise OfferError("contract_route_invalid")
            route = field.get_attribute("value") or ""
            expected = r"/project_board/quote_request\?project_plan_menu_id=[0-9]+" if month == 1 else rf"/monthly_work_contracts/client/[^/]+/add\?project_plan_menu_id=[0-9]+&month={month}"
            if re.fullmatch(expected, route) is None: raise OfferError("contract_route_invalid")
            routes.append(route)
    image = page.locator(".p-menu-browse-detail__carousel-list img")
    has_image = image.count() >= 1 and all("photo-film" not in str(image.nth(index).get_attribute("src") or "") for index in range(image.count()))
    observed = {"title": _text(page, "h1"), "subtitle": _text(page, ".l-page-header__heading-description"), "description": _text(page, "#body + .p-project-plan-markdown"), "notice": _text(page, "#notice_for_sale + .c-text"), "plans": plans}
    expected = {"title": product["public_title"], "subtitle": product["subtitle"], "description": " ".join(product["description"].split()), "notice": " ".join(product["notice"].split()), "plans": [{key: plan[key] for key in ("description", "price_jpy", "delivery_days")} for plan in product["plans"]]}
    return {"ok": True, "logged_in": True, "listing_external_id": listing_id, "canonical_url": public_url, "aligned": observed == expected and has_image, "has_image": has_image, "prices_jpy": [plan["price_jpy"] for plan in plans], "delivery_days": [plan["delivery_days"] for plan in plans], "contract_routes": {"spot": 3, "three_month": 3, "six_month": 3}}


def _field(page: Any, selector: str) -> Any:
    field = page.locator(selector)
    if field.count() != 1: raise OfferError("form_changed")
    return field


def _setting_status(page: Any, listing_id: str) -> str:
    path = f"/myplan/{listing_id}/setting"
    try: page.goto(ORIGIN + path, wait_until="domcontentloaded", timeout=20_000)
    except Exception: raise OfferError("setting_readback_unavailable") from None
    if urlsplit(str(page.url)).path != path: raise OfferError("setting_route_invalid")
    fields = page.locator('[name="data[ProjectPlanStatusForm][status]"]')
    if fields.count() != 3: raise OfferError("setting_readback_invalid")
    checked = [fields.nth(index).get_attribute("value") for index in range(3) if fields.nth(index).is_checked()]
    if len(checked) != 1 or checked[0] not in {"active", "paused", "archived"}: raise OfferError("setting_readback_invalid")
    return str(checked[0])


def _reconcile_superseded(page: Any, listing_ids: Sequence[str]) -> dict[str, Any]:
    active = [listing_id for listing_id in listing_ids if _setting_status(page, listing_id) == "active"]
    if not active: return {"superseded_active_count": 0, "status_effect_count": 0}
    listing_id = active[0]
    _field(page, '[name="data[ProjectPlanStatusForm][status]"][value="paused"]').check()
    save = page.get_by_role("button", name="保存", exact=True)
    if save.count() != 1: raise OfferError("setting_form_changed")
    try: save.click(timeout=5_000, no_wait_after=True)
    except Exception: pass
    page.wait_for_timeout(1_000)
    if _setting_status(page, listing_id) != "paused": raise OfferError("setting_submission_uncertain")
    return {"superseded_active_count": len(active) - 1, "status_effect_count": 1, "paused_listing_id": listing_id}


def _write_receipt(state_path: Path, product: Mapping[str, Any]) -> None:
    path = state_path.with_name("listing.json"); path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    digest = hashlib.sha256(json.dumps(product, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    value = {"record_type": "listing_receipt", "schema_version": 1, "platform": "lancers", "product_id": product["product_id"], "product_version": product["product_version"], "listing_external_id": product["listing_external_id"], "public_url": f"{ORIGIN}/menu/detail/{product['listing_external_id']}", "status": "published", "content_sha256": digest, "idempotency_key": f"lancers:listing:{product['product_id']}:v{product['product_version']}", "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle: json.dump(value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":")); handle.write("\n")
        os.replace(temporary, path); path.chmod(0o600)
    finally:
        try: os.unlink(temporary)
        except FileNotFoundError: pass


def _step(page: Any, label: str) -> None:
    values = [item for item in page.get_by_text(label, exact=True).all() if item.is_visible()]
    chosen = next((item for item in values if "clickable" in str(item.get_attribute("class") or "")), values[0] if len(values) == 1 else None)
    if chosen is None: raise OfferError("form_changed")
    chosen.click()


def _apply(page: Any, product: Mapping[str, Any], image: Path) -> dict[str, Any]:
    before = _public(page, product)
    reconciliation = _reconcile_superseded(page, product["superseded_listing_ids"])
    if reconciliation["status_effect_count"]: return before | reconciliation | {"action": "paused_superseded"}
    if before["aligned"]: return before | {"action": "unchanged"}
    listing_id = product["listing_external_id"]; edit_url = f"{ORIGIN}/myplan/{listing_id}/edit"
    page.goto(edit_url, wait_until="domcontentloaded", timeout=30_000)
    if page.url != edit_url: raise OfferError("edit_route_invalid")
    page.wait_for_selector('[name="ProjectPlanForm.title"]', state="visible", timeout=5_000)
    _field(page, '[name="ProjectPlanForm.title"]').fill(product["title_stem"])
    _field(page, '[name="ProjectPlanForm.subtitle"]').fill(product["subtitle"])
    _field(page, '[name="___main_category_id"]').select_option(label=product["category"])
    page.wait_for_function("label => [...document.querySelectorAll('[name=\"ProjectPlanForm.project_category_id\"] option')].some(o => o.textContent.trim() === label)", arg=product["subcategory"], timeout=5_000)
    _field(page, '[name="ProjectPlanForm.project_category_id"]').select_option(label=product["subcategory"])
    page.wait_for_selector('[name="ProjectPlanCategoryForm.service_type[0]"]', state="attached", timeout=5_000)
    services = page.locator('[name="ProjectPlanCategoryForm.service_type[0]"]')
    matches = [field for field in services.all() if " ".join(field.evaluate("e => e.parentElement.parentElement.innerText").split()) == product["service_type"]]
    if len(matches) != 1 or re.fullmatch(r"[0-9]+", matches[0].get_attribute("value") or "") is None: raise OfferError("form_changed")
    service_id = matches[0].get_attribute("value")
    with page.expect_response(lambda response: urlsplit(response.url).path == f"/v1/project_store_api/project_category/{service_id}", timeout=10_000) as service_loaded:
        page.locator(f'label[for="{service_id}"]').click()
    if service_loaded.value.status != 200 or not matches[0].is_checked(): raise OfferError("form_changed")
    _field(page, '[name="ProjectPlanForm.industry_type_id"]').select_option(label=product["industry"])
    while page.locator('[aria-label="削除"]').count(): page.locator('[aria-label="削除"]').first.click()
    tag_field = _field(page, '[name="MultiSelectTagSearch_ProjectPlanTagForm"]')
    for tag in product["tags"]: tag_field.fill(tag); tag_field.press("Enter")
    _step(page, "料金表")
    for index, plan in enumerate(product["plans"]):
        prefix = f"ProjectPlanMenuForm[{index}]"
        _field(page, f'[name="{prefix}.description"]').fill(plan["description"])
        _field(page, f'[name="{prefix}.delivery_time"]').select_option(str(plan["delivery_days"]))
        _field(page, f'[name="{prefix}.price"]').fill(str(plan["price_jpy"]))
    _step(page, "業務内容"); _field(page, "textarea:not([name])").fill(product["description"])
    _step(page, "確認事項"); _field(page, '[name="ProjectPlanForm.notice_for_sale"]').fill(product["notice"])
    _step(page, "画像ほか")
    upload = page.locator('input[type="file"][accept*="image/"]')
    if upload.count() != 1: raise OfferError("form_changed")
    with page.expect_response(lambda response: urlsplit(response.url).path == "/v1/project_store_api/project_blob/add", timeout=20_000) as uploaded:
        upload.set_input_files(str(image))
    if uploaded.value.status != 200: raise OfferError("image_upload_failed")
    page.wait_for_selector('img[src*="img2.lancers.jp/projectblob/"]', state="visible", timeout=5_000)
    save = page.get_by_role("button", name="保存する", exact=True)
    if save.count() != 1: raise OfferError("form_changed")
    save.click(); page.wait_for_url(f"**/myplan/{listing_id}/edit/complete", timeout=30_000)
    try: return _public(page, product) | {"action": "updated"}
    except OfferError: raise OfferError("publication_uncertain") from None


def run(apply: bool, product_path: Path, state_path: Path) -> dict[str, Any]:
    tick = browser = page = None; logged_in = False; result: dict[str, Any] = {"ok": False, "error": "offer_unavailable"}
    try:
        product, image = _product(product_path); tick = _load("lancers_storefront_offer_tick", HERE / "application_tick.py")
        with tick.account_lock(state_path.with_name("work-sync.json")):
            browser = tick._default_browser_factory(tick.CDP_URL); page = tick._new_owned_page(browser)
            if not tick._production_account_ready(page): raise OfferError("account_unavailable")
            logged_in = True; result = _apply(page, product, image) if apply else _public(page, product) | {"action": "inspect"}
            if apply and result.get("ok") is True and result.get("aligned") is True: _write_receipt(Path(state_path), product)
    except OfferError as error: result = {"ok": False, "logged_in": logged_in, "error": str(error)}
    except Exception as error: result = {"ok": False, "logged_in": logged_in, "error": "account_lock_busy" if "LockBusy" in type(error).__name__ else "offer_unavailable"}
    finally:
        try:
            closed = page is None or bool(tick._close_owned_page(page))
            if browser is not None: tick._stop_playwright_runtime(getattr(browser, "_anicca_playwright_runtime", None))
        except Exception: closed = False
        if not closed: result = {"ok": False, "logged_in": logged_in, "error": "cleanup_failed"}
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(); mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect", action="store_true"); mode.add_argument("--apply", action="store_true")
    parser.add_argument("--product", type=Path, default=DEFAULT_PRODUCT); parser.add_argument("--state-path", type=Path, default=Path.home() / ".local/state/anicca/lancers/application.json")
    args = parser.parse_args(argv); result = run(args.apply, args.product, args.state_path)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))); return 0 if result.get("ok") is True else 1


if __name__ == "__main__": raise SystemExit(main())
