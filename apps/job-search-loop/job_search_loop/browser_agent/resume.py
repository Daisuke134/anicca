from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from .contracts import ObservationV1, ResumeVerificationV1, SessionHandleV1
from .session import BrowserSession
from .direct_cdp import DirectCDPPage


class ResumeVerifier:
    """Verify an uploaded resume and parsed fields without returning field values."""

    def __init__(self, session: BrowserSession) -> None:
        self._session = session

    async def verify(
        self,
        handle: SessionHandleV1,
        observation: ObservationV1,
        resume_path: Path,
        expected_fields: Mapping[str, str],
    ) -> ResumeVerificationV1:
        if not resume_path.is_file():
            raise ValueError("routed resume does not exist")
        page = self._session.page(handle)
        resume_sha = hashlib.sha256(resume_path.read_bytes()).hexdigest()
        filename_visible = await page.evaluate(
            """expected => {
              const bodyHasName = (document.body?.innerText || '').includes(expected);
              const inputHasName = Array.from(document.querySelectorAll('input[type="file"]'))
                .some(input => Array.from(input.files || []).some(file => file.name === expected));
              return bodyHasName || inputHasName;
            }""",
            resume_path.name,
        )

        checked: list[str] = []
        mismatched: list[str] = []
        if isinstance(page, DirectCDPPage):
            values = await page.evaluate(
                """labels => {
                  const controls = Array.from(document.querySelectorAll('input,textarea,select'));
                  const label = el => {
                    const own = el.getAttribute('aria-label') || '';
                    const linked = el.labels && el.labels.length
                      ? Array.from(el.labels).map(x => x.innerText).join(' ') : '';
                    return (own || linked || '').trim();
                  };
                  return Object.fromEntries(labels.map(expected => {
                    const matches = controls.filter(el => label(el) === expected)
                      .filter(el => { const s=getComputedStyle(el),r=el.getBoundingClientRect(); return s.visibility!=='hidden'&&s.display!=='none'&&r.width>0&&r.height>0; });
                    return [expected, matches.length === 1 ? String(matches[0].value || '') : null];
                  }));
                }""",
                list(expected_fields),
            )
            for label, expected in expected_fields.items():
                actual = values.get(label) if isinstance(values, dict) else None
                if actual is None:
                    mismatched.append(label)
                    continue
                checked.append(label)
                if " ".join(str(actual).split()).casefold() != " ".join(expected.split()).casefold():
                    mismatched.append(label)
            safe = {
                "observation_sha256": observation.content_sha256,
                "resume_sha256": resume_sha,
                "filename_visible": bool(filename_visible),
                "checked_labels": tuple(checked),
                "mismatched_labels": tuple(mismatched),
            }
            receipt_sha = hashlib.sha256(
                json.dumps(safe, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
            return ResumeVerificationV1(1, receipt_sha256=receipt_sha, **safe)
        for label, expected in expected_fields.items():
            locator = page.get_by_label(label, exact=True)
            visible = [
                locator.nth(index)
                for index in range(await locator.count())
                if await locator.nth(index).is_visible()
            ]
            if len(visible) != 1:
                mismatched.append(label)
                continue
            checked.append(label)
            actual = await visible[0].input_value()
            if " ".join(actual.split()).casefold() != " ".join(expected.split()).casefold():
                mismatched.append(label)

        safe = {
            "observation_sha256": observation.content_sha256,
            "resume_sha256": resume_sha,
            "filename_visible": bool(filename_visible),
            "checked_labels": tuple(checked),
            "mismatched_labels": tuple(mismatched),
        }
        receipt_sha = hashlib.sha256(
            json.dumps(safe, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return ResumeVerificationV1(1, receipt_sha256=receipt_sha, **safe)
