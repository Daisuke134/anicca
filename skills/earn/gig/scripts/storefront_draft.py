#!/usr/bin/env python3
"""Prepare and verify one evidence-qualified Coconala Storefront draft."""

from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
import sys
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
    if (
        value.get("version") != 1 or value.get("platform") != "coconala"
        or not str(value.get("draft_service_id") or "").isdigit()
        or value.get("draft_url") != f"https://coconala.com/mypage/services/{value.get('draft_service_id')}"
        or value.get("expected_public_url") != f"https://coconala.com/services/{value.get('draft_service_id')}"
        or not isinstance(fields, dict) or not isinstance(category, dict) or not isinstance(gate, dict)
        or any(not isinstance(category.get(level), dict) for level in ("master", "sub", "type"))
        or any(not str(category[level].get("value") or "").isdigit() for level in ("master", "sub", "type"))
        or fields.get("expected_title") != f"{fields.get('overview_input')}ます"
        or not (15 <= len(str(fields.get("catchphrase") or "")) <= 30)
        or not str(fields.get("head") or "") or len(str(fields["head"])) > 1000
        or not str(fields.get("body") or "") or len(str(fields["body"])) > 500
        or type(fields.get("display_price_jpy")) is not int or fields["display_price_jpy"] <= 0
        or not str(fields.get("price_option_value") or "").isdigit()
        or int(fields["price_option_value"]) != int(fields["display_price_jpy"] * 1.1)
        or type(fields.get("delivery_days")) is not int or not 1 <= fields["delivery_days"] <= 99
        or type(fields.get("order_limit")) is not int or not 1 <= fields["order_limit"] <= 20
        or not all(gate.get(key) is True for key in (
            "requires_distinct_catalog_outcome", "requires_owned_capability",
            "requires_available_capacity", "requires_hero_image",
            "requires_no_active_storefront_experiment",
        ))
    ):
        raise RuntimeError("storefront_draft_contract_invalid")
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {**value, "contract_sha256": hashlib.sha256(canonical.encode()).hexdigest()}


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
        "data[Service][master_category_type_id]": category["type"]["value"],
        "data[Service][overview]": fields["overview_input"],
        "data[Service][catchphrase]": fields["catchphrase"],
        "data[Service][head]": fields["head"],
        "data[Service][price]": fields["price_option_value"],
        "data[Service][delivery_time]": str(fields["delivery_days"]),
        "data[Service][order_limit]": str(fields["order_limit"]),
        "data[Service][body]": fields["body"],
    }


def _snapshot_matches(snapshot: dict[str, Any], contract: dict[str, Any]) -> bool:
    if snapshot.get("url") != contract["draft_url"] or snapshot.get("action") != contract["draft_url"]:
        return False
    values = {str(row.get("name") or ""): str(row.get("value") or "")
              for row in snapshot.get("fields") or [] if isinstance(row, dict)}
    expected = _expected_values(contract)
    if any(values.get(name) != value for name, value in expected.items()):
        return False
    price = next((row for row in snapshot.get("price_options") or []
                  if str(row.get("value") or "") == expected["data[Service][price]"]), None)
    return isinstance(price, dict) and str(price.get("text") or "").replace(",", "") == (
        f"{contract['public_fields']['display_price_jpy']}円"
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
        before_raw, cid = await _evaluate(ws, (
            "JSON.stringify((()=>{const f=document.forms[0],p=f?.querySelector('[name=\"data[Service][price]\"]');"
            "return{url:location.href,action:f?.action||'',fields:f?[...f.elements].filter(e=>e.name).map(e=>({name:e.name,value:e.value,checked:!!e.checked})):[],"
            "price_options:p?[...p.options].map(o=>({value:o.value,text:o.text})):[]}})())"
        ), cid)
        before = json.loads(str(before_raw or "{}"))
        if _snapshot_matches(before, contract):
            return before, False
        for name in ("master_category", "master_sub_category", "master_category_type_id"):
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
        result, cid = await _evaluate(ws, (
            "(()=>{const b=[...document.querySelectorAll('button[type=submit][data-mode=\"draft\"]')]"
            ".find(e=>(e.innerText||'').trim()==='下書きで保存');"
            "if(!b)return false;b.click();return true})()"
        ), cid)
        if result is not True:
            raise RuntimeError("storefront_draft_save_control_missing")
        deadline = asyncio.get_running_loop().time() + 15
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.25)
            after_raw, cid = await _evaluate(ws, (
                "JSON.stringify((()=>{const f=document.forms[0],p=f?.querySelector('[name=\"data[Service][price]\"]');"
                "return{url:location.href,action:f?.action||'',fields:f?[...f.elements].filter(e=>e.name).map(e=>({name:e.name,value:e.value,checked:!!e.checked})):[],"
                "price_options:p?[...p.options].map(o=>({value:o.value,text:o.text})):[]}})())"
            ), cid)
            after = json.loads(str(after_raw or "{}"))
            if _snapshot_matches(after, contract):
                return after, True
        raise RuntimeError("storefront_draft_readback_mismatch")


def prepare_draft(contract: dict[str, Any], default_tab_script: Path, evidence_dir: Path) -> dict[str, Any]:
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
    finally:
        if isinstance(tab, dict) and tab.get("target_id"):
            subprocess.run(
                [sys.executable, str(default_tab_script), "--owner", "gig-storefront-direct",
                 "close", str(tab["target_id"])], capture_output=True, text=True, check=False, timeout=30,
            )
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / "new-listing-draft-readback.json"
    evidence_path.write_text(json.dumps(snapshot, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "version": 1, "candidate_key": contract["candidate_key"],
        "contract_sha256": contract["contract_sha256"], "draft_service_id": contract["draft_service_id"],
        "status": "prepared", "effect": int(changed), "readback": 1, "public_effect": 0,
        "evidence_path": str(evidence_path),
    }
