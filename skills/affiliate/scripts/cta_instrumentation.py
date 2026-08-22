#!/usr/bin/env python3
"""Install the owned, fail-closed Affiliate CTA redirect through the publication owner."""

import hashlib
import html
import json
import os
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from job_journal import reconcile_effect, start_effect, verify_effect
from provider_cli import atomic_write


FILES = {
    "apps/landing/netlify/functions/_lib/marketing-go.js": "e88450e39aa9e4a98cb5e48926f66011729fb5c5ffe431eb297af38ee7b086cc",
    "apps/landing/netlify/functions/_lib/__tests__/marketing-go.test.js": "5205c356d62217e88299569828236c41746313e4a0f59ff59d8e268db96d3f1e",
    "apps/landing/app/blog/[slug]/page.tsx": "11286f2056a2958c4504809537c23c947f822e2c0c445a0cc5da8708e8b45abe",
}
MARKER = "AFFILIATE_CTA_V1"


class InstrumentationError(RuntimeError):
    pass


def _git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode:
        raise InstrumentationError("git command failed")
    return result.stdout.strip()


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _transform_library(text):
    text = text.replace(
        'const TOKEN = /^(ai|ho|ej|ee)_[a-z2-7]{20}$/;',
        'const TOKEN = /^(?:(ai|ho|ej|ee)_[a-z2-7]{20}|af_([a-z0-9][a-z0-9-]{2,80}))$/; // AFFILIATE_CTA_V1',
    )
    text = text.replace(
        'function destination(product, token, providerToken) {\n  if (product.kind === "app") {',
        'function destination(product, token, providerToken) {\n  if (product.kind === "affiliate") return `https://try.elevenlabs.io/${product.placementId}`;\n  if (product.kind === "app") {',
    )
    text = text.replace(
        '    const product = match && products[match[1]];',
        '    const product = match && (match[2]\n      ? { productId: match[2], kind: "affiliate", placementId: match[2] }\n      : products[match[1]]);',
    )
    return text


def _transform_page(text):
    anchor = 'function renderMarkdown(md: string): string {'
    helper = '''// AFFILIATE_CTA_V1: fixed-host redirect; no arbitrary destination input.\nfunction trackedAffiliateHref(href: string): string {\n  try {\n    const url = new URL(href);\n    const placement = url.pathname.replace(/^\\/+|\\/+$/g, "");\n    if (url.protocol === "https:" && url.hostname === "try.elevenlabs.io" &&\n        !url.search && !url.hash && /^[a-z0-9][a-z0-9-]{2,80}$/.test(placement))\n      return `/go/af_${placement}`;\n  } catch {}\n  return href;\n}\n\n'''
    text = text.replace(anchor, helper + anchor)
    text = text.replace(
        '  const inline = (s: string) =>\n    s\n      .replace(/&/g, "&amp;")',
        '  const inline = (s: string) =>\n    s\n      .replace(/https:\\/\\/try\\.elevenlabs\\.io\\/[a-z0-9][a-z0-9-]{2,80}/g, trackedAffiliateHref)\n      .replace(/&/g, "&amp;")',
    )
    return text


def _transform_test(text):
    return text + '''
// AFFILIATE_CTA_V1
test("affiliate tokens persist exact placement before fixed-host redirect", async () => {
  const writes = [];
  const handler = makeMarketingGoHandler({
    products, providerToken: "123456", receiptId: () => "click-affiliate",
    persist: async (_key, value) => writes.push(value),
  });
  const placement = "elevenlabs-discovered-voice-changer-en-1";
  const response = await handler(event(`af_${placement}`));
  assert.equal(response.statusCode, 302);
  assert.equal(response.headers.location, `https://try.elevenlabs.io/${placement}`);
  assert.equal(writes[0].product_id, placement);
  assert.equal(JSON.stringify(writes[0]).includes("try.elevenlabs.io"), false);
});
'''


def _env(name):
    value = os.environ.get(name, "").strip()
    if value:
        return value
    for path in (Path("~/.config/anicca/affiliate.env"), Path("~/.openclaw/.env")):
        path = path.expanduser()
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith(f"{name}=") and line.split("=", 1)[1].strip():
                return line.split("=", 1)[1].strip().strip("\"'")
    raise InstrumentationError(f"{name} is unavailable")


def observe_clicks(state, placements):
    instrumentation = json.loads((state / "cta-instrumentation.json").read_text())
    if instrumentation.get("state") != "LIVE":
        return {"state": "WAITING_FOR_INSTRUMENTATION", "changed": False}
    base = _env("SUPABASE_URL").rstrip("/")
    key = _env("SUPABASE_SERVICE_ROLE_KEY")
    rows = []
    for placement in placements:
        placement_id = placement["placement_id"]
        query = urllib.parse.urlencode({
            "select": "receipt_id,clicked_at", "product_id": f"eq.{placement_id}",
            "clicked_at": f"gte.{instrumentation['deployed_at']}", "order": "clicked_at.asc",
        })
        request = urllib.request.Request(
            f"{base}/rest/v1/marketing_click_receipts?{query}",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            receipts = json.load(response)
        rows.append({
            "placement_id": placement_id, "count": len(receipts), "state": "OBSERVED",
            "first_clicked_at": receipts[0].get("clicked_at") if receipts else None,
            "last_clicked_at": receipts[-1].get("clicked_at") if receipts else None,
        })
    core = {
        "schema_version": 1, "receipt_type": "AFFILIATE_CTA_CLICK_OBSERVATION",
        "instrumentation_commit": instrumentation.get("commit"),
        "interval_start": instrumentation.get("deployed_at"),
        "placements": rows, "money_state": "NON_MONEY",
    }
    receipt_sha256 = hashlib.sha256(json.dumps(
        core, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    receipt = {**core, "receipt_sha256": receipt_sha256}
    latest = state / "cta-click-observations" / "latest.json"
    changed = not latest.is_file() or json.loads(latest.read_text()).get("receipt_sha256") != receipt_sha256
    atomic_write(latest, receipt)
    if changed:
        with (state / "cta-click-observations.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n")
    return {**receipt, "state": "OBSERVED", "changed": changed}


def _public_ready(owned_url, placement_id):
    try:
        with urllib.request.urlopen(owned_url, timeout=20) as response:
            body = html.unescape(response.read().decode("utf-8", errors="replace"))
    except Exception:
        return False
    return f"/go/af_{placement_id}" in body


def advance(state, landing_root, placement_id, owned_url):
    receipt_path = state / "cta-instrumentation.json"
    prior = json.loads(receipt_path.read_text()) if receipt_path.is_file() else {}
    if prior.get("state") in {"DELIVERED", "LIVE"} and _public_ready(owned_url, placement_id):
        receipt = {**prior, "state": "LIVE", "observed_at": datetime.now(timezone.utc).isoformat()}
        atomic_write(receipt_path, receipt)
        return {**receipt, "changed": prior.get("state") != "LIVE"}
    root = landing_root.resolve()
    if _git(root, "rev-parse", "--show-toplevel") != str(root):
        raise InstrumentationError("publication worktree mismatch")
    paths = {name: root / name for name in FILES}
    if not all(MARKER in path.read_text(encoding="utf-8") for path in paths.values()):
        if _git(root, "status", "--porcelain"):
            raise InstrumentationError("publication worktree is dirty")
        for name, path in paths.items():
            if _sha(path) != FILES[name]:
                raise InstrumentationError("publication source hash drift")
        paths[next(name for name in paths if name.endswith("marketing-go.js") and "__tests__" not in name)].write_text(
            _transform_library(paths[next(name for name in paths if name.endswith("marketing-go.js") and "__tests__" not in name)].read_text()), encoding="utf-8"
        )
        test_name = next(name for name in paths if "__tests__" in name)
        paths[test_name].write_text(_transform_test(paths[test_name].read_text()), encoding="utf-8")
        page_name = next(name for name in paths if name.endswith("page.tsx"))
        paths[page_name].write_text(_transform_page(paths[page_name].read_text()), encoding="utf-8")
        completed = subprocess.run(
            ["node", "--test", "netlify/functions/_lib/__tests__/marketing-go.test.js"],
            cwd=root / "apps/landing", capture_output=True, check=False, timeout=60,
        )
        if completed.returncode:
            raise InstrumentationError("marketing-go test failed")
        _git(root, "add", "--", *paths)
        _git(root, "commit", "-m", "feat(marketing): receipt affiliate CTA redirects")
    commit = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "ls-remote", "origin", "refs/heads/main")
    remote_head = remote.split()[0] if remote else None
    if remote_head != commit:
        job = start_effect(state, "AFFILIATE_CTA_DEPLOY", "aniccaai.com", {"commit": commit}, {"head": remote_head}, 600)
        _git(root, "push", "origin", "HEAD:refs/heads/main")
        verify_effect(state, job["job_id"], {"state": "DELIVERED", "head": commit})
    else:
        reconcile_effect(state, "AFFILIATE_CTA_DEPLOY", "aniccaai.com", {"state": "DELIVERED", "head": commit})
    receipt = {
        "schema_version": 1, "receipt_type": "AFFILIATE_CTA_INSTRUMENTATION",
        "state": "DELIVERED", "commit": commit, "placement_id": placement_id,
        "owned_url": owned_url,
        "tracking_url_state": "NOT_PERSISTED", "deployed_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write(receipt_path, receipt)
    return {**receipt, "changed": True}
