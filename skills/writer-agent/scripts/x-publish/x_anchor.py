"""Pure helpers for placing immutable X Article body images."""

from __future__ import annotations

import re


def rendered_anchor(anchor: str) -> str:
    """Return text that X's editor renders as one searchable text node."""
    link = re.search(r"\[([^\]]+)\]\([^)]+\)", anchor)
    if link is not None and link.group(1).strip():
        suffix = anchor[link.end() :].lstrip(" \t-—–:：")
        return suffix.strip() or link.group(1).strip()
    value = re.sub(r"^(?:#{1,6}|[-*+])\s+", "", anchor)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    truncated_link = re.match(r"^\[([^\]]+)\]\(", value)
    if truncated_link is not None:
        return truncated_link.group(1).strip()
    return value.strip()


def _candidates(anchor: str) -> list[str]:
    values = [anchor, rendered_anchor(anchor)]
    link = re.search(r"\[([^\]]+)\]\([^)]+\)", anchor)
    if link is not None:
        values.append(link.group(1).strip())
    result: list[str] = []
    for value in values:
        value = value.strip()
        if value and value not in result:
            result.append(value)
        if len(value) > 20 and value[:20] not in result:
            result.append(value[:20])
    return result


def find_block_end(html: str, anchor: str, position: int) -> int:
    """Find the end of the reader-visible block containing ``anchor``."""
    candidates = _candidates(anchor)
    index = -1
    for candidate in candidates:
        index = html.find(candidate, position)
        if index != -1:
            break
    if index == -1:
        flat_html = re.sub(r"\s+", " ", html)
        for candidate in candidates:
            flat_index = flat_html.find(re.sub(r"\s+", " ", candidate))
            if flat_index != -1:
                index = html.find(candidate[: min(20, len(candidate))], position)
                if index != -1:
                    break
    if index == -1:
        raise ValueError(f"ANCHOR NOT FOUND: {anchor[:80]}")
    closing = re.search(
        r"</(?:p|h[1-6]|li|blockquote)>",
        html[index:],
        re.IGNORECASE,
    )
    if closing is None:
        return len(html)
    end = index + closing.end()
    if closing.group(0).lower() == "</li>":
        parent = re.match(r"\s*</(?:ul|ol)>", html[end:], re.IGNORECASE)
        if parent is not None:
            end += parent.end()
    return end


def build_chunks(html: str, content_images: list[dict]) -> list[tuple[str, str]]:
    """Split HTML into text/image chunks without silently dropping images."""
    chunks: list[tuple[str, str]] = []
    position = 0
    for image in sorted(content_images, key=lambda item: item["block_index"]):
        anchor = str(image.get("after_text") or "")
        end = find_block_end(html, anchor, position)
        chunks.extend((("html", html[position:end]), ("img", str(image["path"]))))
        position = end
    chunks.append(("html", html[position:]))
    return chunks
