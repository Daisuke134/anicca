#!/usr/bin/env python3
"""Attach to daily-driver, open the Corgi draft, dump editor DOM info."""
import json, time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    # Look for an existing X.com editor tab
    target = None
    for page in ctx.pages:
        try:
            if "x.com" in page.url and "compose" in page.url:
                target = page
                break
        except Exception:
            pass
    if target is None:
        target = ctx.new_page()
        target.goto("https://x.com/compose/articles", wait_until="domcontentloaded")
        time.sleep(4)
        try:
            target.locator('a:has-text("Write")').first.click(timeout=3000)
        except Exception:
            target.goto("https://x.com/compose/articles/new", wait_until="domcontentloaded")
        time.sleep(5)

    print(f"URL: {target.url}")
    info = target.evaluate("""
    () => {
        const eds = Array.from(document.querySelectorAll('[contenteditable="true"]'));
        return eds.map((e, i) => ({
            idx: i,
            tag: e.tagName,
            role: e.getAttribute('role'),
            ariaLabel: e.getAttribute('aria-label'),
            ariaPlaceholder: e.getAttribute('aria-placeholder'),
            dataPlaceholder: e.getAttribute('data-placeholder'),
            dataTestid: e.getAttribute('data-testid'),
            placeholder: e.getAttribute('placeholder'),
            textPreview: (e.textContent || '').slice(0, 80),
            class: (e.className || '').slice(0, 120),
            rect: (() => {
                const r = e.getBoundingClientRect();
                return {x: r.x, y: r.y, w: r.width, h: r.height};
            })(),
            parentTag: e.parentElement ? e.parentElement.tagName : null,
            parentRole: e.parentElement ? e.parentElement.getAttribute('role') : null,
            parentAriaLabel: e.parentElement ? e.parentElement.getAttribute('aria-label') : null,
        }));
    }
    """)
    print("contenteditable elements:")
    for it in info:
        print(json.dumps(it, ensure_ascii=False, indent=2))

    # Now find anything that could be the title field
    print("\n--- TITLE candidates ---")
    titles = target.evaluate("""
    () => {
        // Look for elements that have "Add a title" placeholder text or label
        const all = Array.from(document.querySelectorAll('*'));
        const out = [];
        for (const el of all) {
            const text = (el.textContent || '').trim();
            const ph = el.getAttribute('placeholder') || '';
            const ariaLabel = el.getAttribute('aria-label') || '';
            const dataPh = el.getAttribute('data-placeholder') || '';
            const ariaPh = el.getAttribute('aria-placeholder') || '';
            const matches = (
                (text === 'Add a title') ||
                ph.includes('title') || ph.includes('Title') ||
                ariaLabel.includes('title') || ariaLabel.includes('Title') ||
                dataPh.includes('title') || dataPh.includes('Title') ||
                ariaPh.includes('title') || ariaPh.includes('Title')
            );
            if (!matches) continue;
            const r = el.getBoundingClientRect();
            if (r.width === 0 || r.height === 0) continue;
            out.push({
                tag: el.tagName,
                role: el.getAttribute('role'),
                ariaLabel,
                ariaPh,
                dataPh,
                ph,
                dataTestid: el.getAttribute('data-testid'),
                text: text.slice(0, 60),
                isInput: el.tagName === 'INPUT' || el.tagName === 'TEXTAREA',
                contentEditable: el.getAttribute('contenteditable'),
                rect: {x: r.x, y: r.y, w: r.width, h: r.height},
            });
            if (out.length > 12) break;
        }
        return out;
    }
    """)
    for t in titles:
        print(json.dumps(t, ensure_ascii=False, indent=2))

    # Also list all inputs in the editor area
    print("\n--- inputs/textareas/headings near top ---")
    near_top = target.evaluate("""
    () => {
        const els = Array.from(document.querySelectorAll('input, textarea, h1, h2, [role="heading"], [role="textbox"]'));
        return els
            .filter(e => {
                const r = e.getBoundingClientRect();
                return r.width > 0 && r.height > 0 && r.y < 800;
            })
            .slice(0, 15)
            .map(e => ({
                tag: e.tagName,
                role: e.getAttribute('role'),
                type: e.getAttribute('type'),
                name: e.getAttribute('name'),
                ph: e.getAttribute('placeholder'),
                ariaLabel: e.getAttribute('aria-label'),
                ariaPh: e.getAttribute('aria-placeholder'),
                dataPh: e.getAttribute('data-placeholder'),
                dataTestid: e.getAttribute('data-testid'),
                text: (e.textContent || '').slice(0, 60),
                rect: (() => {const r = e.getBoundingClientRect(); return {x: r.x, y: r.y, w: r.width, h: r.height};})(),
            }));
    }
    """)
    for t in near_top:
        print(json.dumps(t, ensure_ascii=False, indent=2))
