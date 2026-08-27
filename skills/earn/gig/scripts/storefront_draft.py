#!/usr/bin/env python3
"""Prepare and verify one evidence-qualified Coconala Storefront draft."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import struct
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def load_contract(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("storefront_draft_contract_invalid") from error
    fields = value.get("public_fields")
    category = value.get("category")
    gate = value.get("publication_gate")
    category_specific = value.get("category_specific")
    subscription = value.get("subscription")
    paid_options = value.get("paid_options")
    if (
        value.get("version") != 1 or value.get("platform") != "coconala"
        or not str(value.get("draft_service_id") or "").isdigit()
        or value.get("draft_url") != f"https://coconala.com/mypage/services/{value.get('draft_service_id')}"
        or value.get("expected_public_url") != f"https://coconala.com/services/{value.get('draft_service_id')}"
        or not isinstance(fields, dict) or not isinstance(category, dict) or not isinstance(gate, dict)
        # Some official categories stop at two levels, so a type is optional but never partial.
        or any(not isinstance(category.get(level), dict) for level in ("master", "sub"))
        or (category.get("type") is not None and not isinstance(category.get("type"), dict))
        or any(not str(level.get("value") or "").isdigit()
               for level in category.values() if isinstance(level, dict))
        or fields.get("expected_title") != f"{fields.get('overview_input')}ます"
        or not (15 <= len(str(fields.get("catchphrase") or "")) <= 30)
        or not str(fields.get("head") or "") or len(str(fields["head"])) > 1000
        or not str(fields.get("body") or "") or len(str(fields["body"])) > 500
        or type(fields.get("display_price_jpy")) is not int or fields["display_price_jpy"] <= 0
        or not str(fields.get("price_option_value") or "").isdigit()
        or int(fields["price_option_value"]) != int(fields["display_price_jpy"] * 1.1)
        or type(fields.get("delivery_days")) is not int or not 1 <= fields["delivery_days"] <= 99
        or type(fields.get("order_limit")) is not int or not 1 <= fields["order_limit"] <= 20
        or not isinstance(category_specific, dict)
        or any(not isinstance(category_specific.get(key), list) or not category_specific[key]
               for key in ("features", "industries", "languages"))
        or any(not all(str(item).isdigit() for item in category_specific[key])
               for key in ("features", "industries", "languages"))
        or category_specific.get("provision_format") not in {"1", "2", "3"}
        or not str(category_specific.get("fix_limit") or "").lstrip("-").isdigit()
        or not str(category_specific.get("unit_price_jpy_per_character") or "").isdigit()
        or not isinstance(subscription, dict) or subscription.get("enabled") is not True
        or subscription.get("discount_ratio") not in {"5", "10", "15", "20"}
        or not isinstance(paid_options, list) or len(paid_options) != 1
        or not isinstance(paid_options[0], dict) or not str(paid_options[0].get("title") or "").strip()
        or type(paid_options[0].get("price_jpy")) is not int or paid_options[0]["price_jpy"] < 500
        or paid_options[0].get("opened") != "1"
        or not all(gate.get(key) is True for key in (
            "requires_distinct_catalog_outcome", "requires_owned_capability",
            "requires_available_capacity", "requires_hero_image",
            "requires_no_conflicting_service_experiment",
        ))
    ):
        raise RuntimeError("storefront_draft_contract_invalid")
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    try:
        gig_root = path.resolve().parents[3]
        image_contract_path = (path.parent / str(value.get("hero_image_contract") or "")).resolve()
        image_contract_path.relative_to(gig_root)
        image = json.loads(image_contract_path.read_text(encoding="utf-8"))
        asset_path = (image_contract_path.parent / str(image.get("asset") or "")).resolve()
        asset_path.relative_to(image_contract_path.parent.resolve())
        data = asset_path.read_bytes()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("storefront_draft_image_contract_invalid") from error
    if (
        image.get("version") != 1 or image.get("service_id") != value.get("draft_service_id")
        or image.get("field") != "image" or image.get("mime_type") != "image/png"
        or len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n"
        or struct.unpack(">II", data[16:24]) != (1220, 1016)
        or (image.get("width"), image.get("height")) != (1220, 1016)
        or hashlib.sha256(data).hexdigest() != image.get("asset_sha256")
        or not isinstance(image.get("claims"), list) or not image["claims"]
    ):
        raise RuntimeError("storefront_draft_image_contract_invalid")
    return {
        **value,
        "contract_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "hero_image": {**image, "asset_path": str(asset_path)},
    }


async def _call(ws: Any, method: str, params: dict[str, Any], cid: int) -> dict[str, Any]:
    await ws.send(json.dumps({"id": cid, "method": method, "params": params}))
    while True:
        response = json.loads(await ws.recv())
        if response.get("id") == cid:
            return response


async def _evaluate(ws: Any, expression: str, cid: int) -> tuple[Any, int]:
    response = await _call(ws, "Runtime.evaluate", {
        "expression": expression, "returnByValue": True, "awaitPromise": True,
    }, cid)
    result = response.get("result", {}).get("result", {})
    if result.get("subtype") == "error" or "exceptionDetails" in response.get("result", {}):
        raise RuntimeError("storefront_draft_browser_evaluation_failed")
    return result.get("value"), cid + 1


async def _wait_for_option(
    ws: Any, field_name: str, option_value: str, cid: int, timeout_seconds: float = 12.0,
) -> int:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    selector = f'[name="{field_name}"]'
    while asyncio.get_running_loop().time() < deadline:
        found, cid = await _evaluate(ws, (
            "(()=>{const s=document.querySelector(" + json.dumps(selector) + ");"
            f"return !!s&&[...s.options].some(o=>o.value==={json.dumps(option_value)})}})()"
        ), cid)
        if found is True:
            return cid
        await asyncio.sleep(0.25)
    raise RuntimeError(f"storefront_draft_category_option_missing:{field_name}")


def _expected_values(contract: dict[str, Any]) -> dict[str, str]:
    fields, category = contract["public_fields"], contract["category"]
    return {
        "data[Service][master_category]": category["master"]["value"],
        "data[Service][master_sub_category]": category["sub"]["value"],
        **({"data[Service][master_category_type_id]": category["type"]["value"]}
           if isinstance(category.get("type"), dict) else {}),
        "data[Service][overview]": fields["overview_input"],
        "data[Service][catchphrase]": fields["catchphrase"],
        "data[Service][head]": fields["head"],
        "data[Service][price]": fields["price_option_value"],
        "data[Service][delivery_time]": str(fields["delivery_days"]),
        "data[Service][order_limit]": str(fields["order_limit"]),
        "data[Service][body]": fields["body"],
    }


def _field_detail(rows: list[dict[str, Any]], name: str) -> str:
    row = next((r for r in rows if r.get("name") == name), None)
    if not isinstance(row, dict):
        return ""
    marks = "".join(m for m, on in (("D", row.get("disabled")), ("R", row.get("readonly"))) if on)
    options = row.get("options")
    tail = f"opts={','.join(str(o) for o in options[:8])}" if isinstance(options, list) else ""
    return f"[{row.get('tag') or '?'}/{row.get('type') or ''}{marks}{'/' + tail if tail else ''}]"


def _snapshot_mismatches(snapshot: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    if snapshot.get("url") != contract["draft_url"] or snapshot.get("action") != contract["draft_url"]:
        return ["draft_url"]
    rows = [row for row in snapshot.get("fields") or [] if isinstance(row, dict)]
    values = {str(row.get("name") or ""): str(row.get("value") or "") for row in rows}
    # A control the category greys out cannot hold a value for anyone, so it carries nothing
    # to verify. Only controls the form actually lets us set are held to the contract.
    settable = {str(row.get("name") or "") for row in rows
                if not row.get("disabled") and not row.get("readonly")}
    checked = lambda name: {
        str(row.get("value") or "") for row in rows
        if row.get("name") == name and row.get("checked") is True
    }
    category_specific = contract["category_specific"]
    option = contract["paid_options"][0]
    price = next((row for row in snapshot.get("price_options") or []
                  if str(row.get("value") or "") == _expected_values(contract)["data[Service][price]"]), None)
    display = f"{contract['public_fields']['display_price_jpy']}円"

    mismatches = [name for name, value in _expected_values(contract).items() if values.get(name) != value]
    if not isinstance(price, dict) or str(price.get("text") or "").replace(",", "") != display:
        mismatches.append("price_option_text")
    # Feature, industry and language facets, per-character pricing, revision limits and
    # subscription belong to the writing category. Another official category simply does not
    # render them, so there is nothing to verify rather than a fault.
    for name, actual, wanted in (
        ("data[facets][163][]", checked("data[facets][163][]"), set(category_specific["features"])),
        ("data[facets][164][]", checked("data[facets][164][]"), set(category_specific["industries"])),
        ("data[facets][165][]", checked("data[facets][165][]"), set(category_specific["languages"])),
        ("data[Service][provision_format]", checked("data[Service][provision_format]"),
         {category_specific["provision_format"]}),
        ("data[Service][can_subscribe]", checked("data[Service][can_subscribe]"), {"1"}),
        ("data[Service][fix_limit]", values.get("data[Service][fix_limit]"), category_specific["fix_limit"]),
        ("data[Service][unit_price]", values.get("data[Service][unit_price]"),
         category_specific["unit_price_jpy_per_character"]),
        ("data[ServiceSubscription][discount_ratio]", values.get("data[ServiceSubscription][discount_ratio]"),
         contract["subscription"]["discount_ratio"]),
    ):
        if name in settable and actual != wanted:
            mismatches.append(f"{name}{_field_detail(rows, name)}={actual!r}!={wanted!r}")
    for name, wanted in (
        ("data[Option][0][title]", option["title"]),
        ("data[Option][0][price]", str(option["price_jpy"])),
        ("data[Option][0][opened]", option["opened"]),
    ):
        if values.get(name) != wanted:
            mismatches.append(name)
    return mismatches


def _snapshot_matches(snapshot: dict[str, Any], contract: dict[str, Any]) -> bool:
    return not _snapshot_mismatches(snapshot, contract)


def _snapshot_image_count(snapshot: dict[str, Any]) -> int:
    images = snapshot.get("images")
    if not isinstance(images, list):
        return -1
    return len(images)


def _snapshot_image_identity(snapshot: dict[str, Any]) -> str:
    identities = set()
    for image in snapshot.get("images") or []:
        if not isinstance(image, dict):
            continue
        text = f"{image.get('src') or ''} {image.get('style') or ''}"
        match = re.search(r"service_images/(?:original/|[^/]+/)([A-Za-z0-9-]+\.(?:png|jpe?g|webp))", text)
        if match:
            identities.add(match.group(1))
    if len(identities) != 1:
        raise RuntimeError("storefront_draft_image_identity_invalid")
    return identities.pop()


DRAFT_SNAPSHOT_EXPRESSION = (
    "JSON.stringify((()=>{const f=document.forms[0],p=f?.querySelector('[name=\"data[Service][price]\"]');"
    "return{url:location.href,action:f?.action||'',fields:f?[...f.elements].filter(e=>e.name).map(e=>({name:e.name,value:e.value,checked:!!e.checked,"
    "tag:e.tagName,type:e.type||'',disabled:!!e.disabled,readonly:!!e.readOnly,"
    "options:e.tagName==='SELECT'?[...e.options].map(o=>o.value):null})):[],"
    "price_options:p?[...p.options].map(o=>({value:o.value,text:o.text})):[],"
    "images:[...document.querySelectorAll('.js_image-thumbnail')].map(e=>({style:e.getAttribute('style')||'',src:e.getAttribute('src')||''}))"
    ".filter(e=>e.style||e.src)}})())"
)


async def _prepare(ws_url: str, contract: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    import websockets

    expected = _expected_values(contract)
    async with websockets.connect(ws_url, ping_interval=None, open_timeout=10, max_size=40 * 1024 * 1024) as ws:
        cid = 1
        await _call(ws, "Page.enable", {}, cid); cid += 1
        cid = await _wait_for_option(
            ws, "data[Service][master_category]", contract["category"]["master"]["value"], cid,
        )
        hydration_deadline = asyncio.get_running_loop().time() + 6
        before = {}
        while asyncio.get_running_loop().time() < hydration_deadline:
            before_raw, cid = await _evaluate(ws, DRAFT_SNAPSHOT_EXPRESSION, cid)
            before = json.loads(str(before_raw or "{}"))
            if _snapshot_matches(before, contract) and _snapshot_image_count(before) == 1:
                return before, False
            await asyncio.sleep(0.25)
        before_image_count = _snapshot_image_count(before)
        if before_image_count > 1:
            raise RuntimeError("storefront_draft_image_count_invalid")
        if _snapshot_matches(before, contract) and before_image_count == 1:
            return before, False
        if not _snapshot_matches(before, contract):
            for name in ("master_category", "master_sub_category", "master_category_type_id"):
                if name == "master_category_type_id" and not isinstance(
                        contract["category"].get("type"), dict):
                    continue  # Coconala offers only two levels in some categories.
                value = contract["category"][{"master_category": "master", "master_sub_category": "sub",
                                              "master_category_type_id": "type"}[name]]["value"]
                field_name = f"data[Service][{name}]"
                cid = await _wait_for_option(ws, field_name, value, cid)
                result, cid = await _evaluate(ws, (
                    "(()=>{const s=document.querySelector(" + json.dumps(f'[name="{field_name}"]') + ");"
                    f"if(!s||![...s.options].some(o=>o.value==={json.dumps(value)}))return false;"
                    f"s.value={json.dumps(value)};s.dispatchEvent(new Event('input',{{bubbles:true}}));"
                    "s.dispatchEvent(new Event('change',{bubbles:true}));return true})()"
                ), cid)
                if result is not True:
                    raise RuntimeError(f"storefront_draft_category_option_missing:{name}")
                await asyncio.sleep(0.75)
            text_values = {name: value for name, value in expected.items()
                           if name not in {"data[Service][master_category]", "data[Service][master_sub_category]",
                                           "data[Service][master_category_type_id]", "data[Service][price]"}}
            result, cid = await _evaluate(ws, (
                "(()=>{const values=" + json.dumps(text_values, ensure_ascii=False) + ";"
                "for(const [name,value] of Object.entries(values)){const e=document.querySelector(`[name=\"${name}\"]`);"
                "if(!e)return JSON.stringify({ok:false,missing:name});e.value=value;e.dispatchEvent(new Event('input',{bubbles:true}));"
                "e.dispatchEvent(new Event('change',{bubbles:true}))}return JSON.stringify({ok:true})})()"
            ), cid)
            if json.loads(str(result or "{}" )).get("ok") is not True:
                raise RuntimeError("storefront_draft_text_field_missing")
            price_value = expected["data[Service][price]"]
            result, cid = await _evaluate(ws, (
                "(()=>{const s=document.querySelector('[name=\"data[Service][price]\"]');"
                f"const o=[...s.options].find(x=>x.value==={json.dumps(price_value)});"
                f"if(!o||o.text.replace(/,/g,'')!=={json.dumps(str(contract['public_fields']['display_price_jpy']) + '円')})return false;"
                f"s.value={json.dumps(price_value)};s.dispatchEvent(new Event('change',{{bubbles:true}}));return true}})()"
            ), cid)
            if result is not True:
                raise RuntimeError("storefront_draft_price_contract_mismatch")
            await asyncio.sleep(0.5)
        category_specific = contract["category_specific"]
        checkbox_values = {
            "data[facets][163][]": category_specific["features"],
            "data[facets][164][]": category_specific["industries"],
            "data[facets][165][]": category_specific["languages"],
        }
        configured, cid = await _evaluate(ws, (
            "(()=>{const sets=" + json.dumps(checkbox_values) + ";"
            "for(const [name,wanted] of Object.entries(sets)){const els=[...document.getElementsByName(name)];"
            "for(const e of els){e.checked=wanted.includes(e.value);"
            "e.dispatchEvent(new Event('change',{bubbles:true}))}}"
            "const radio=[...document.getElementsByName('data[Service][provision_format]')]"
            f".find(e=>e.value==={json.dumps(category_specific['provision_format'])});"
            "const live=s=>{const e=document.querySelector(s);return e&&!e.disabled&&!e.readOnly?e:null};"
            "const fix=live('[name=\"data[Service][fix_limit]\"]');"
            "const unit=live('[name=\"data[Service][unit_price]\"]');"
            "const subscribe=live('[name=\"data[Service][can_subscribe]\"][type=checkbox]');"
            "const discount=live('[name=\"data[ServiceSubscription][discount_ratio]\"]');"
            "if(radio){radio.checked=true;radio.dispatchEvent(new Event('change',{bubbles:true}))}"
            f"if(fix){{fix.value={json.dumps(category_specific['fix_limit'])};fix.dispatchEvent(new Event('change',{{bubbles:true}}))}}"
            f"if(unit){{unit.value={json.dumps(category_specific['unit_price_jpy_per_character'])};unit.dispatchEvent(new Event('input',{{bubbles:true}}))}}"
            "if(subscribe){subscribe.checked=true;subscribe.dispatchEvent(new Event('change',{bubbles:true}))}"
            f"if(discount){{discount.value={json.dumps(contract['subscription']['discount_ratio'])};discount.dispatchEvent(new Event('change',{{bubbles:true}}))}}"
            "return true})()"
        ), cid)
        # Each control is set only where the category renders it. A form that omits one has
        # nothing to set; readback still fails closed on anything present and left wrong.
        if configured is not True:
            raise RuntimeError("storefront_draft_category_specific_missing")
        option = contract["paid_options"][0]
        has_option, cid = await _evaluate(
            ws, "!!document.querySelector('[name=\"data[Option][0][title]\"]')", cid,
        )
        if has_option is not True:
            added, cid = await _evaluate(ws, (
                "(()=>{const b=document.querySelector('.js_add-option-button');if(!b)return false;b.click();return true})()"
            ), cid)
            if added is not True:
                raise RuntimeError("storefront_draft_paid_option_add_missing")
            await asyncio.sleep(0.5)
        option_set, cid = await _evaluate(ws, (
            "(()=>{const title=document.querySelector('[name=\"data[Option][0][title]\"]');"
            "const price=document.querySelector('[name=\"data[Option][0][price]\"]');"
            "const opened=document.querySelector('[name=\"data[Option][0][opened]\"]');"
            "if(!title||!price||!opened)return false;"
            f"title.value={json.dumps(option['title'], ensure_ascii=False)};title.dispatchEvent(new Event('input',{{bubbles:true}}));"
            f"price.value={json.dumps(str(option['price_jpy']))};price.dispatchEvent(new Event('change',{{bubbles:true}}));"
            f"opened.value={json.dumps(option['opened'])};opened.dispatchEvent(new Event('change',{{bubbles:true}}));return true}})()"
        ), cid)
        if option_set is not True:
            raise RuntimeError("storefront_draft_paid_option_missing")
        if before_image_count == 0:
            clicked, cid = await _evaluate(ws, (
                "(()=>{const b=document.querySelector('.js_upload-select');if(!b)return false;b.click();return true})()"
            ), cid)
            if clicked is not True:
                raise RuntimeError("storefront_draft_image_add_missing")
            await asyncio.sleep(0.5)
            document = await _call(ws, "DOM.getDocument", {"depth": -1, "pierce": True}, cid); cid += 1
            queried = await _call(ws, "DOM.querySelector", {
                "nodeId": document["result"]["root"]["nodeId"], "selector": "input.js_upload-button",
            }, cid); cid += 1
            node_id = int(queried.get("result", {}).get("nodeId") or 0)
            if node_id <= 0:
                raise RuntimeError("storefront_draft_image_input_missing")
            await _call(ws, "DOM.setFileInputFiles", {
                "nodeId": node_id, "files": [contract["hero_image"]["asset_path"]],
            }, cid); cid += 1
            deadline = asyncio.get_running_loop().time() + 12
            while asyncio.get_running_loop().time() < deadline:
                preview, cid = await _evaluate(
                    ws, "!!document.querySelector('.js_image-thumbnail[style*=\"blob:\"]')", cid,
                )
                if preview is True:
                    break
                await asyncio.sleep(0.25)
            else:
                raise RuntimeError("storefront_draft_image_preview_missing")
        submitted, cid = await _evaluate(ws, (
            "(()=>{const b=[...document.querySelectorAll('button[type=submit][data-mode=\"draft\"]')]"
            ".find(e=>(e.innerText||'').trim()==='下書きで保存');const f=b?.form;"
            "const mode=f?.querySelector('[name=\"mode\"]');if(!b||!f||!mode)return false;"
            "mode.value='draft';f.requestSubmit(b);return true})()"
        ), cid)
        if submitted is not True:
            raise RuntimeError("storefront_draft_save_control_missing")
        await asyncio.sleep(3)
        return before, True


async def _readback(ws_url: str, contract: dict[str, Any]) -> dict[str, Any]:
    import websockets

    async with websockets.connect(ws_url, ping_interval=None, open_timeout=10, max_size=40 * 1024 * 1024) as ws:
        cid = 1
        await _call(ws, "Page.enable", {}, cid); cid += 1
        for field_name, value in (
            ("data[Service][master_category]", contract["category"]["master"]["value"]),
            ("data[Service][master_sub_category]", contract["category"]["sub"]["value"]),
            *(( ("data[Service][master_category_type_id]", contract["category"]["type"]["value"]), )
              if isinstance(contract["category"].get("type"), dict) else ()),
        ):
            cid = await _wait_for_option(ws, field_name, value, cid)
        deadline = asyncio.get_running_loop().time() + 15
        mismatches: list[str] = ["snapshot_unread"]
        while asyncio.get_running_loop().time() < deadline:
            raw, cid = await _evaluate(ws, DRAFT_SNAPSHOT_EXPRESSION, cid)
            snapshot = json.loads(str(raw or "{}"))
            images = _snapshot_image_count(snapshot)
            mismatches = _snapshot_mismatches(snapshot, contract) + ([] if images == 1 else [f"images={images}"])
            if not mismatches:
                return snapshot
            await asyncio.sleep(0.25)
    raise RuntimeError("storefront_draft_readback_mismatch:" + ",".join(mismatches[:6]))


def prepare_draft(contract: dict[str, Any], default_tab_script: Path, evidence_dir: Path) -> dict[str, Any]:
    snapshot = None
    changed = False
    last_error = None
    for attempt in range(3):
        opened = subprocess.run(
            [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
             "--background", "open", contract["draft_url"]], capture_output=True, text=True,
            check=False, timeout=30,
        )
        tab = None
        try:
            tab = json.loads(opened.stdout)
            if opened.returncode != 0 or tab.get("ok") is not True:
                raise RuntimeError("storefront_draft_tab_open_failed")
            snapshot, changed = asyncio.run(_prepare(str(tab["ws"]), contract))
            break
        except RuntimeError as error:
            last_error = error
            retryable = str(error).startswith("storefront_draft_category_option_missing")
            if not retryable or attempt >= 2:
                raise
        finally:
            if isinstance(tab, dict) and tab.get("target_id"):
                subprocess.run(
                    [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
                     "close", str(tab["target_id"])], capture_output=True, text=True,
                    check=False, timeout=30,
                )
        time.sleep(2)
    if snapshot is None:
        raise last_error or RuntimeError("storefront_draft_readback_missing")
    if changed:
        opened = subprocess.run(
            [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
             "--background", "open", contract["draft_url"]], capture_output=True, text=True,
            check=False, timeout=30,
        )
        tab = None
        try:
            tab = json.loads(opened.stdout)
            if opened.returncode != 0 or tab.get("ok") is not True:
                raise RuntimeError("storefront_draft_readback_tab_open_failed")
            snapshot = asyncio.run(_readback(str(tab["ws"]), contract))
        finally:
            if isinstance(tab, dict) and tab.get("target_id"):
                subprocess.run(
                    [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
                     "close", str(tab["target_id"])], capture_output=True, text=True,
                    check=False, timeout=30,
                )
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / "new-listing-draft-readback.json"
    evidence_path.write_text(json.dumps(snapshot, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "version": 1, "candidate_key": contract["candidate_key"],
        "contract_sha256": contract["contract_sha256"], "draft_service_id": contract["draft_service_id"],
        "status": "prepared", "effect": int(changed), "readback": 1, "public_effect": 0,
        "image_count": _snapshot_image_count(snapshot),
        "asset_sha256": contract["hero_image"]["asset_sha256"],
        "evidence_path": str(evidence_path),
    }


async def _submit_public(ws_url: str, contract: dict[str, Any], evidence_dir: Path) -> tuple[str, str]:
    import websockets

    async with websockets.connect(ws_url, ping_interval=None, open_timeout=10, max_size=40 * 1024 * 1024) as ws:
        cid = 1
        await _call(ws, "Page.enable", {}, cid); cid += 1
        cid = await _wait_for_option(
            ws, "data[Service][master_category]", contract["category"]["master"]["value"], cid,
        )
        deadline = asyncio.get_running_loop().time() + 12
        while asyncio.get_running_loop().time() < deadline:
            raw, cid = await _evaluate(ws, DRAFT_SNAPSHOT_EXPRESSION, cid)
            snapshot = json.loads(str(raw or "{}"))
            if _snapshot_matches(snapshot, contract) and _snapshot_image_count(snapshot) == 1:
                image_identity = _snapshot_image_identity(snapshot)
                break
            await asyncio.sleep(0.25)
        else:
            raise RuntimeError("storefront_publish_precondition_mismatch")
        submitted, cid = await _evaluate(ws, (
            "(()=>{const b=[...document.querySelectorAll('button[type=submit][data-mode=\"open\"]')]"
            ".find(e=>(e.innerText||'').trim()==='公開する');const f=b?.form;"
            "const mode=f?.querySelector('[name=\"mode\"]');if(!b||!f||!mode)return false;"
            "mode.value='open';f.requestSubmit(b);return true})()"
        ), cid)
        if submitted is not True:
            raise RuntimeError("storefront_publish_control_missing")
        await asyncio.sleep(5)
        # Whatever the site says after 公開する is the only account of what publishing did:
        # a review queue, a validation error or a live listing all look the same from outside.
        raw, cid = await _evaluate(ws, (
            "JSON.stringify({url:location.href,title:document.title,"
            "errors:[...document.querySelectorAll('[class*=error],[class*=alert],.c-alert')]"
            ".map(e=>(e.innerText||'').trim()).filter(Boolean).slice(0,10),"
            "body:document.body?document.body.innerText.slice(0,4000):''})"
        ), cid)
        evidence_dir.mkdir(parents=True, exist_ok=True)
        answer = json.loads(str(raw or "{}"))
        (evidence_dir / "new-listing-publish-submit.json").write_text(
            json.dumps(answer, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        return image_identity, str(answer.get("url") or "")


async def _public_readback(
    ws_url: str, contract: dict[str, Any], image_identity: str,
) -> dict[str, Any]:
    import websockets

    async with websockets.connect(ws_url, ping_interval=None, open_timeout=10, max_size=40 * 1024 * 1024) as ws:
        cid = 1
        deadline = asyncio.get_running_loop().time() + 15
        missing: list[str] = ["page_unread"]
        while asyncio.get_running_loop().time() < deadline:
            raw, cid = await _evaluate(ws, (
                "JSON.stringify({url:location.href,title:document.title,"
                "body:document.body?document.body.innerText.slice(0,120000):'',"
                "images:[...document.images].map(e=>e.currentSrc||e.src).filter(Boolean)})"
            ), cid)
            snapshot = json.loads(str(raw or "{}"))
            body = str(snapshot.get("body") or "")
            images = [str(value) for value in snapshot.get("images") or []]
            public = contract["public_fields"]
            missing = [
                name for name, ok in (
                    ("url", snapshot.get("url") == contract["expected_public_url"]),
                    ("title", public["expected_title"] in body),
                    ("catchphrase", public["catchphrase"] in body),
                    ("head", public["head"] in body),
                    ("body", public["body"] in body),
                    # The public page renders the amount and its unit as separate nodes, so the
                    # text can carry a newline between them where the seller form does not.
                    ("price", re.search(rf"{public['display_price_jpy']:,}\s*円", body) is not None),
                    # A two-level category carries no type, so only the levels it has are checked.
                    ("category", all(
                        level["label"] in body for level in contract["category"].values()
                        if isinstance(level, dict)
                    )),
                    ("image", any(image_identity in value for value in images)),
                ) if not ok
            ]
            if not missing:
                return snapshot
            await asyncio.sleep(0.5)
    raise RuntimeError("storefront_publish_public_readback_mismatch:" + ",".join(missing))


def publish_draft(contract: dict[str, Any], default_tab_script: Path, evidence_dir: Path) -> dict[str, Any]:
    opened = subprocess.run(
        [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
         "--background", "open", contract["draft_url"]], capture_output=True, text=True,
        check=False, timeout=30,
    )
    tab = None
    try:
        tab = json.loads(opened.stdout)
        if opened.returncode != 0 or tab.get("ok") is not True:
            raise RuntimeError("storefront_publish_tab_open_failed")
        image_identity, submit_url = asyncio.run(_submit_public(str(tab["ws"]), contract, evidence_dir))
    finally:
        if isinstance(tab, dict) and tab.get("target_id"):
            subprocess.run(
                [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
                 "close", str(tab["target_id"])], capture_output=True, text=True,
                check=False, timeout=30,
            )
    public_opened = subprocess.run(
        [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
         "--background", "open", contract["expected_public_url"]], capture_output=True, text=True,
        check=False, timeout=30,
    )
    public_tab = None
    try:
        public_tab = json.loads(public_opened.stdout)
        if public_opened.returncode != 0 or public_tab.get("ok") is not True:
            raise RuntimeError("storefront_publish_readback_tab_open_failed")
        snapshot = asyncio.run(_public_readback(str(public_tab["ws"]), contract, image_identity))
        verification_error = None
    except RuntimeError as error:
        # The site answers an accepted publication on its own confirmation page. Once that has
        # happened the listing is live whatever the public page later fails to match, and a
        # listing that is not written down is one the next wake would publish all over again.
        accepted = str(submit_url).startswith(
            f"https://coconala.com/services/new_open/{contract['draft_service_id']}"
        )
        if not accepted:
            raise
        snapshot, verification_error = {"unverified": str(error)}, str(error)
    finally:
        if isinstance(public_tab, dict) and public_tab.get("target_id"):
            subprocess.run(
                [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
                 "close", str(public_tab["target_id"])], capture_output=True, text=True,
                check=False, timeout=30,
            )
    evidence_path = evidence_dir / "new-listing-public-readback.json"
    evidence_path.write_text(json.dumps(snapshot, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "version": 1, "candidate_key": contract["candidate_key"],
        "contract_sha256": contract["contract_sha256"], "draft_service_id": contract["draft_service_id"],
        "status": "published", "effect": 1, "readback": int(verification_error is None), "image_count": 1,
        "public_effect": 1, "public_url": contract["expected_public_url"],
        "public_image_identity": image_identity, "public_readback_error": verification_error,
        "asset_sha256": contract["hero_image"]["asset_sha256"], "evidence_path": str(evidence_path),
    }


def readback_published_draft(
    contract: dict[str, Any], default_tab_script: Path, evidence_dir: Path,
    known_image_identity: str | None = None,
) -> dict[str, Any]:
    image_identity = known_image_identity
    last_error = None
    for attempt in range(3) if image_identity is None else ():
        draft_opened = subprocess.run(
            [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
             "--background", "open", contract["draft_url"]], capture_output=True, text=True,
            check=False, timeout=30,
        )
        draft_tab = None
        try:
            draft_tab = json.loads(draft_opened.stdout)
            if draft_opened.returncode != 0 or draft_tab.get("ok") is not True:
                raise RuntimeError("storefront_published_draft_tab_open_failed")
            draft_snapshot = asyncio.run(_readback(str(draft_tab["ws"]), contract))
            image_identity = _snapshot_image_identity(draft_snapshot)
            break
        except RuntimeError as error:
            last_error = error
            retryable = (
                str(error).startswith("storefront_draft_category_option_missing")
                or str(error).startswith("storefront_draft_readback_mismatch")
            )
            if not retryable or attempt >= 2:
                raise
        finally:
            if isinstance(draft_tab, dict) and draft_tab.get("target_id"):
                subprocess.run(
                    [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
                     "close", str(draft_tab["target_id"])], capture_output=True, text=True,
                    check=False, timeout=30,
                )
        time.sleep(2)
    if image_identity is None:
        raise last_error or RuntimeError("storefront_published_draft_readback_missing")
    public_opened = subprocess.run(
        [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
         "--background", "open", contract["expected_public_url"]], capture_output=True, text=True,
        check=False, timeout=30,
    )
    public_tab = None
    try:
        public_tab = json.loads(public_opened.stdout)
        if public_opened.returncode != 0 or public_tab.get("ok") is not True:
            raise RuntimeError("storefront_published_readback_tab_open_failed")
        snapshot = asyncio.run(_public_readback(str(public_tab["ws"]), contract, image_identity))
    finally:
        if isinstance(public_tab, dict) and public_tab.get("target_id"):
            subprocess.run(
                [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
                 "close", str(public_tab["target_id"])], capture_output=True, text=True,
                check=False, timeout=30,
            )
    evidence_path = evidence_dir / "new-listing-public-readback.json"
    evidence_path.write_text(json.dumps(snapshot, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "version": 1, "candidate_key": contract["candidate_key"],
        "contract_sha256": contract["contract_sha256"], "draft_service_id": contract["draft_service_id"],
        "status": "already_public", "effect": 0, "readback": 1, "image_count": 1,
        "public_effect": 0, "public_url": contract["expected_public_url"],
        "public_image_identity": image_identity,
        "asset_sha256": contract["hero_image"]["asset_sha256"], "evidence_path": str(evidence_path),
        "publication_guard": "already_public",
    }


async def _blank_draft_ids(ws_url: str) -> tuple[list[str], list[dict[str, Any]]]:
    import websockets

    # Every draft card is recorded, not just the untouched ones, because an attempt that fails
    # after filling leaves a draft behind and nothing yet knows what can be done with it.
    expression = r"""JSON.stringify((()=>{const cards=[...document.querySelectorAll('.serviceListContentBox')];
      const rows=cards.map(card=>({text:(card.innerText||'').trim(),
      ids:[...card.querySelectorAll('a[href*="/mypage/services/"]')]
      .map(a=>(a.href.match(/\/mypage\/services\/(\d+)/)||[])[1]).filter(Boolean),
      controls:[...card.querySelectorAll('a,button')].map(e=>({tag:e.tagName,
      label:(e.innerText||'').trim().slice(0,24),href:e.getAttribute('href')||'',
      cls:(e.className||'').toString().slice(0,80)}))}));
      return{ready:document.readyState,cards:cards.length,
      add_control:!!document.querySelector('a[href="/services/add"],a[href*="/services/add"]'),
      drafts:rows.filter(row=>row.text.includes('下書き中')).map(row=>({ids:row.ids,
      titled:!row.text.includes('サービスタイトル未設定'),controls:row.controls})),
      ids:rows.filter(row=>row.text.includes('下書き中')&&row.text.includes('サービスタイトル未設定'))
      .flatMap(row=>row.ids)}})())"""
    async with websockets.connect(ws_url, ping_interval=None, open_timeout=10,
                                  max_size=40 * 1024 * 1024) as ws:
        cid = 1
        deadline = asyncio.get_running_loop().time() + 15
        while asyncio.get_running_loop().time() < deadline:
            raw, cid = await _evaluate(ws, expression, cid)
            observed = json.loads(str(raw or "{}"))
            if (int(observed.get("cards") or 0) > 0
                    or (observed.get("ready") == "complete" and observed.get("add_control") is True)):
                values = observed.get("ids") or []
                drafts = [row for row in observed.get("drafts") or [] if isinstance(row, dict)]
                break
            await asyncio.sleep(0.25)
        else:
            raise RuntimeError("storefront_create_inventory_not_hydrated")
    return sorted({str(value) for value in values if str(value).isdigit()}), drafts


async def _submit_blank_draft(ws_url: str) -> str:
    import websockets

    async with websockets.connect(ws_url, ping_interval=None, open_timeout=10,
                                  max_size=40 * 1024 * 1024) as ws:
        cid = 1
        deadline = asyncio.get_running_loop().time() + 15
        while asyncio.get_running_loop().time() < deadline:
            selected, cid = await _evaluate(ws, """(()=>{const r=document.querySelector(
              'input[name="service-type"][value="0"]');if(!r)return false;r.click();
              r.dispatchEvent(new Event('change',{bubbles:true}));return true})()""", cid)
            if selected is True:
                break
            await asyncio.sleep(0.25)
        else:
            raise RuntimeError("storefront_create_service_type_missing")
        await asyncio.sleep(0.5)
        submitted, cid = await _evaluate(ws, """(()=>{const f=document.querySelector(
          'form[action$="/services/add"]');const b=f?.querySelector('button[type=submit]');
          if(!f||!b)return false;f.requestSubmit(b);return true})()""", cid)
        if submitted is not True:
            raise RuntimeError("storefront_create_submit_missing")
        deadline = asyncio.get_running_loop().time() + 15
        while asyncio.get_running_loop().time() < deadline:
            url, cid = await _evaluate(ws, "location.href", cid)
            match = re.fullmatch(r"https://coconala\.com/mypage/services/(\d+)", str(url or ""))
            if match:
                return match.group(1)
            await asyncio.sleep(0.25)
    raise RuntimeError("storefront_create_draft_id_missing")


def _preferred_recoverable_draft(
    preferred_ids: list[str], draft_cards: list[dict[str, Any]],
) -> str | None:
    available = {
        str(value) for row in draft_cards if isinstance(row, dict)
        for value in row.get("ids") or [] if str(value).isdigit()
    }
    return next((str(value) for value in preferred_ids if str(value) in available), None)


def _preferred_ledger_draft(preferred_ids: list[str]) -> str | None:
    return next((str(value) for value in preferred_ids if str(value).isdigit()), None)


def create_or_claim_blank_draft(
    default_tab_script: Path, preferred_draft_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Claim one recoverable blank draft, creating it only when none exists."""
    ledger_draft = _preferred_ledger_draft(preferred_draft_ids or [])
    if ledger_draft is not None:
        return {"draft_service_id": ledger_draft, "effect": 0, "recovered": True,
                "abandoned_drafts": []}
    list_opened = subprocess.run(
        [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
         "--background", "open", "https://coconala.com/mypage/services_lists"],
        capture_output=True, text=True, check=False, timeout=30,
    )
    list_tab = None
    try:
        list_tab = json.loads(list_opened.stdout)
        if list_opened.returncode != 0 or list_tab.get("ok") is not True:
            raise RuntimeError("storefront_create_inventory_tab_open_failed")
        blank_ids, draft_cards = asyncio.run(_blank_draft_ids(str(list_tab["ws"])))
    finally:
        if isinstance(list_tab, dict) and list_tab.get("target_id"):
            subprocess.run(
                [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
                 "close", str(list_tab["target_id"])], capture_output=True, text=True,
                check=False, timeout=30,
            )
    abandoned = [row for row in draft_cards if row.get("titled") is True]
    preferred = _preferred_recoverable_draft(preferred_draft_ids or [], draft_cards)
    if preferred is not None:
        return {"draft_service_id": preferred, "effect": 0, "recovered": True,
                "abandoned_drafts": [row for row in abandoned if preferred not in row.get("ids", [])]}
    if len(blank_ids) > 1:
        raise RuntimeError("storefront_create_multiple_blank_drafts")
    if blank_ids:
        return {"draft_service_id": blank_ids[0], "effect": 0, "recovered": True,
                "abandoned_drafts": abandoned}

    add_opened = subprocess.run(
        [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
         "--background", "open", "https://coconala.com/services/add"],
        capture_output=True, text=True, check=False, timeout=30,
    )
    add_tab = None
    try:
        add_tab = json.loads(add_opened.stdout)
        if add_opened.returncode != 0 or add_tab.get("ok") is not True:
            raise RuntimeError("storefront_create_tab_open_failed")
        draft_id = asyncio.run(_submit_blank_draft(str(add_tab["ws"])))
    finally:
        if isinstance(add_tab, dict) and add_tab.get("target_id"):
            subprocess.run(
                [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
                 "close", str(add_tab["target_id"])], capture_output=True, text=True,
                check=False, timeout=30,
            )
    return {"draft_service_id": draft_id, "effect": 1, "recovered": False,
            "abandoned_drafts": abandoned}


async def _read_category_children_async(
    ws_url: str, master_value: str, sub_value: str | None = None,
) -> dict[str, Any]:
    import websockets

    async with websockets.connect(ws_url, ping_interval=None, open_timeout=10,
                                  max_size=40 * 1024 * 1024) as ws:
        cid = 1
        await _call(ws, "Page.enable", {}, cid); cid += 1
        # Selecting a category only changes the live form; nothing is submitted or saved.
        # The draft form hydrates its category list after load, so wait for the option to exist
        # rather than calling a page that is still rendering unselectable.
        cid = await _wait_for_option(ws, "data[Service][master_category]", master_value, cid)
        applied, cid = await _evaluate(ws, (
            "(()=>{const s=document.querySelector('[name=\"data[Service][master_category]\"]');"
            f"if(!s||![...s.options].some(o=>o.value==={json.dumps(master_value)}))return false;"
            f"s.value={json.dumps(master_value)};"
            "s.dispatchEvent(new Event('change',{bubbles:true}));return true})()"
        ), cid)
        if applied is not True:
            raise RuntimeError("storefront_category_master_not_selectable")
        if sub_value:
            # Category type only appears once its sub category is chosen, so the levels are
            # read in the order the form itself fills them.
            cid = await _wait_for_option(ws, "data[Service][master_sub_category]", sub_value, cid)
            applied_sub, cid = await _evaluate(ws, (
                "(()=>{const s=document.querySelector('[name=\"data[Service][master_sub_category]\"]');"
                f"if(!s||![...s.options].some(o=>o.value==={json.dumps(sub_value)}))return false;"
                f"s.value={json.dumps(sub_value)};"
                "s.dispatchEvent(new Event('change',{bubbles:true}));return true})()"
            ), cid)
            if applied_sub is not True:
                raise RuntimeError("storefront_category_sub_not_selectable")
        wanted = ("data[Service][master_category_type_id]" if sub_value
                  else "data[Service][master_sub_category]")
        deadline = asyncio.get_running_loop().time() + 12
        while asyncio.get_running_loop().time() < deadline:
            raw, cid = await _evaluate(ws, (
                "JSON.stringify(Object.fromEntries(['data[Service][master_sub_category]',"
                "'data[Service][master_category_type_id]'].map(n=>{const s=document.querySelector"
                "('[name=\"'+n+'\"]');return [n, s?[...s.options].filter(o=>o.value)"
                ".map(o=>({value:o.value,label:(o.textContent||'').trim()})):[]]})))"
            ), cid)
            children = json.loads(str(raw or "{}"))
            if children.get(wanted):
                return children
            selects, cid = await _evaluate(ws, (
                "JSON.stringify([...document.querySelectorAll('select')].map(s=>"
                "s.name+':'+s.options.length+(s.disabled?'D':'')))"
            ), cid)
            await asyncio.sleep(0.25)
    # A type list that never arrives is reported as its own case: the sub list being ready is
    # not evidence that the category has no third level, only that this one is still empty.
    # Every select on the form is named, because the field carrying the type is a guess until
    # the page says otherwise.
    if sub_value:
        raise RuntimeError(f"storefront_category_type_absent:{sub_value}:{selects}")
    raise RuntimeError("storefront_category_children_not_loaded")


def read_category_children(
    default_tab_script: Path, draft_service_id: str, master_value: str,
    sub_value: str | None = None,
) -> dict[str, Any]:
    """Read the sub and type options an official category offers, without saving anything."""
    opened = subprocess.run(
        [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
         "--background", "open", f"https://coconala.com/mypage/services/{draft_service_id}"],
        capture_output=True, text=True, check=False, timeout=30,
    )
    tab = None
    try:
        tab = json.loads(opened.stdout)
        if opened.returncode != 0 or tab.get("ok") is not True:
            raise RuntimeError("storefront_category_tab_open_failed")
        return asyncio.run(_read_category_children_async(str(tab["ws"]), master_value, sub_value))
    finally:
        if isinstance(tab, dict) and tab.get("target_id"):
                subprocess.run(
                    [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
                     "close", str(tab["target_id"])], capture_output=True, text=True,
                    check=False, timeout=30,
                )


async def _read_category_form_async(ws_url: str, category: dict[str, dict[str, str]]) -> dict[str, Any]:
    import websockets

    async with websockets.connect(ws_url, ping_interval=None, open_timeout=10,
                                  max_size=40 * 1024 * 1024) as ws:
        cid = 1
        await _call(ws, "Page.enable", {}, cid); cid += 1
        for key, field in (
            ("master", "data[Service][master_category]"),
            ("sub", "data[Service][master_sub_category]"),
            ("type", "data[Service][master_category_type_id]"),
        ):
            row = category.get(key)
            if not isinstance(row, dict):
                continue
            value = str(row.get("value") or "")
            cid = await _wait_for_option(ws, field, value, cid)
            changed, cid = await _evaluate(ws, (
                "(()=>{const s=document.querySelector(" + json.dumps(f'[name="{field}"]') + ");"
                f"if(!s||![...s.options].some(o=>o.value==={json.dumps(value)}))return false;"
                f"s.value={json.dumps(value)};s.dispatchEvent(new Event('input',{{bubbles:true}}));"
                "s.dispatchEvent(new Event('change',{bubbles:true}));return true})()"
            ), cid)
            if changed is not True:
                raise RuntimeError(f"storefront_bootstrap_category_not_selectable:{key}")
            await asyncio.sleep(0.75)
        has_option, cid = await _evaluate(
            ws, "!!document.querySelector('[name=\"data[Option][0][title]\"]')", cid,
        )
        if has_option is not True:
            await _evaluate(ws, (
                "(()=>{const b=document.querySelector('.js_add-option-button');"
                "if(!b)return false;b.click();return true})()"
            ), cid)
            await asyncio.sleep(0.5)
        raw, cid = await _evaluate(ws, DRAFT_SNAPSHOT_EXPRESSION, cid)
        snapshot = json.loads(str(raw or "{}"))
        if snapshot.get("url") is None or not isinstance(snapshot.get("fields"), list):
            raise RuntimeError("storefront_bootstrap_form_unavailable")
        return snapshot


def read_category_form(
    default_tab_script: Path, draft_service_id: str, category: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Read official category-specific form choices without saving the draft."""
    opened = subprocess.run(
        [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
         "--background", "open", f"https://coconala.com/mypage/services/{draft_service_id}"],
        capture_output=True, text=True, check=False, timeout=30,
    )
    tab = None
    try:
        tab = json.loads(opened.stdout)
        if opened.returncode != 0 or tab.get("ok") is not True:
            raise RuntimeError("storefront_bootstrap_form_tab_open_failed")
        return asyncio.run(_read_category_form_async(str(tab["ws"]), category))
    finally:
        if isinstance(tab, dict) and tab.get("target_id"):
            subprocess.run(
                [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
                 "close", str(tab["target_id"])], capture_output=True, text=True,
                check=False, timeout=30,
            )
