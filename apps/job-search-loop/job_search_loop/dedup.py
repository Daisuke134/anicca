from __future__ import annotations

import hashlib
import html
import re
import unicodedata


FINGERPRINT_MIN_TEXT = 200
CROSSLIST_THRESHOLD = 0.92
LOCATION_SUFFIXES = {
    "remote",
    "tokyo",
    "tokyo japan",
    "japan",
    "san francisco",
    "new york",
    "london",
    "berlin",
    "singapore",
    "apac",
    "emea",
}
CORPORATE_SUFFIXES = {
    "co",
    "company",
    "corp",
    "corporation",
    "gmbh",
    "inc",
    "incorporated",
    "llc",
    "ltd",
    "limited",
}


def _identity_words(value: object) -> list[str]:
    normalized = unicodedata.normalize("NFKD", str(value or "").casefold())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)


def company_key(company: object) -> str:
    words = _identity_words(company)
    while words and words[-1] in CORPORATE_SUFFIXES:
        words.pop()
    return " ".join(words)


def role_key(role: object) -> str:
    title = str(role or "").casefold().strip()
    while True:
        match = re.search(r"\s*[\[(]([^\[\]()]+)[\])]\s*$", title)
        if match is None:
            break
        suffix = " ".join(_identity_words(match.group(1)))
        if suffix not in LOCATION_SUFFIXES:
            break
        title = title[: match.start()].rstrip()
    return " ".join(_identity_words(title))


def company_role_key(company: object, role: object) -> str:
    return f"{company_key(company)}::{role_key(role)}"


def normalize_jd_text(text: object) -> str:
    value = html.unescape(str(text or "").casefold())
    value = re.sub(r"<[^>]*>", " ", value)
    value = re.sub(r"https?://\S+", " ", value)
    return " ".join(re.findall(r"[^\W_]+", value, flags=re.UNICODE))


def fingerprint_text(text: object) -> str:
    normalized = normalize_jd_text(text)
    if len(normalized) < FINGERPRINT_MIN_TEXT:
        return ""
    tokens = normalized.split()
    if len(tokens) < 3:
        return ""
    weights = [0] * 64
    for index in range(len(tokens) - 2):
        shingle = " ".join(tokens[index : index + 3]).encode("utf-8")
        digest = hashlib.sha1(shingle).digest()[:8]
        hashed = int.from_bytes(digest, "big")
        for bit in range(64):
            weights[bit] += 1 if hashed & (1 << (63 - bit)) else -1
    value = 0
    for bit, weight in enumerate(weights):
        if weight > 0:
            value |= 1 << (63 - bit)
    return f"{value:016x}"


def fingerprint_similarity(left: str, right: str) -> float:
    if re.fullmatch(r"[0-9a-f]{16}", left or "") is None:
        return 0.0
    if re.fullmatch(r"[0-9a-f]{16}", right or "") is None:
        return 0.0
    distance = (int(left, 16) ^ int(right, 16)).bit_count()
    return 1.0 - distance / 64.0
