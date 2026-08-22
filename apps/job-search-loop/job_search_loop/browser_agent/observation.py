from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .contracts import ObservationV1, SessionHandleV1, VisibleControlV1
from .session import BrowserSession
from .direct_cdp import DirectCDPPage


class ObservationBuilder:
    """Build value-only observations; never retain provider element handles."""

    def __init__(self, session: BrowserSession, evidence_dir: Path) -> None:
        self._session = session
        self._evidence_dir = evidence_dir

    async def build(self, handle: SessionHandleV1) -> ObservationV1:
        page = self._session.page(handle)
        self._evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self._evidence_dir, 0o700)
        screenshot = await page.screenshot(full_page=True, type="jpeg", quality=65)
        screenshot_sha = hashlib.sha256(screenshot).hexdigest()
        screenshot_path = self._evidence_dir / f"{handle.row_run_id}-{screenshot_sha}.jpg"
        screenshot_path.write_bytes(screenshot)
        os.chmod(screenshot_path, 0o600)

        snapshot: dict[str, Any] = await page.evaluate(
            """() => {
              const visible = el => {
                const s = getComputedStyle(el), r = el.getBoundingClientRect();
                return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
              };
              const label = el => {
                const own = el.getAttribute('aria-label') || el.getAttribute('title') || '';
                const linked = el.labels && el.labels.length ? Array.from(el.labels).map(x => x.innerText).join(' ') : '';
                return (own || linked || el.getAttribute('placeholder') || el.innerText || '').trim();
              };
              const nodes = Array.from(document.querySelectorAll('input,button,select,textarea,a,[role]'))
                .filter(visible);
              const automationCounts = new Map();
              const idCounts = new Map();
              for (const el of nodes) {
                const automation = el.getAttribute('data-automation-id');
                const id = el.getAttribute('id');
                if (automation) automationCounts.set(automation, (automationCounts.get(automation) || 0) + 1);
                if (id) idCounts.set(id, (idCounts.get(id) || 0) + 1);
              }
              const stableId = (el, index) => {
                const automation = el.getAttribute('data-automation-id');
                if (automation && automationCounts.get(automation) === 1) return `automation:${automation}`;
                const id = el.getAttribute('id');
                if (id && idCounts.get(id) === 1) return `id:${id}`;
                // Adapted from career-ops' ref-tagged drive loop: every fresh
                // observation gives otherwise anonymous visible controls an
                // observation-local identity. The next observation replaces it.
                const ref = `e${index}`;
                el.setAttribute('data-anicca-ref', ref);
                return `ref:${ref}`;
              };
              const role = el => el.getAttribute('role') || ({
                A: 'link', BUTTON: 'button', SELECT: 'combobox',
                TEXTAREA: 'textbox'
              }[el.tagName] || (el.tagName === 'INPUT' ? (
                ['checkbox', 'radio', 'button', 'submit'].includes(el.type)
                  ? el.type.replace('submit', 'button') : 'textbox'
              ) : ''));
              const controls = nodes.map((el, index) => ({
                  tag: el.tagName.toLowerCase(), role: role(el),
                  control_type: el.getAttribute('type') || '', label: label(el),
                  disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
                  required: !!el.required || el.getAttribute('aria-required') === 'true',
                  filled: ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName)
                    ? String(el.value || '').trim().length > 0 : false,
                  stable_id: stableId(el, index),
                  checked: el.matches('input[type="checkbox"],input[type="radio"]')
                    ? !!el.checked
                    : (el.hasAttribute('aria-checked') ? el.getAttribute('aria-checked') === 'true' : null),
                  options: el.tagName === 'SELECT'
                    ? Array.from(el.options).map(option => option.textContent.trim()).filter(Boolean)
                    : []
                }));
              const validation = Array.from(document.querySelectorAll('[role="alert"],[aria-invalid="true"],.error'))
                .filter(visible).map(el => (el.innerText || el.getAttribute('aria-label') || '').trim()).filter(Boolean);
              const challengeProvider = el => {
                const haystack = `${el.getAttribute('src') || ''} ${el.getAttribute('title') || ''} ${el.getAttribute('name') || ''} ${el.className || ''}`.toLowerCase();
                if (haystack.includes('hcaptcha')) return 'hcaptcha';
                if (haystack.includes('recaptcha')) return 'recaptcha';
                if (haystack.includes('turnstile')) return 'turnstile';
                return '';
              };
              const challenges = Array.from(document.querySelectorAll('iframe,[data-sitekey]'))
                .filter(visible).map(challengeProvider).filter(Boolean);
              return { visible_text: document.body ? document.body.innerText : '', controls, validation,
                challenges: Array.from(new Set(challenges)) };
            }"""
        )
        controls = tuple(VisibleControlV1(**value) for value in snapshot["controls"])
        tabs = (
            (page.url,)
            if isinstance(page, DirectCDPPage)
            else tuple(
                candidate.url
                for context in page.context.browser.contexts
                for candidate in context.pages
            )
        )
        canonical = {
            "url": page.url,
            "title": await page.title(),
            "visible_text": snapshot["visible_text"],
            "controls": [asdict(value) for value in controls],
            "validation_text": snapshot["validation"],
            "visible_challenges": snapshot["challenges"],
            "tabs": tabs,
            "screenshot_sha256": screenshot_sha,
        }
        content_sha = hashlib.sha256(
            json.dumps(canonical, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return ObservationV1(
            1, canonical["url"], canonical["title"], canonical["visible_text"],
            controls, tuple(canonical["validation_text"]), tabs, screenshot_path,
            screenshot_sha, content_sha, tuple(canonical["visible_challenges"]),
        )
