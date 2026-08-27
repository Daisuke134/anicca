#!/usr/bin/env python3
"""Fail-closed admission contract for one source-grounded X original."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

VALUE_TYPES = {
    "procedure", "decision_criterion", "failure_condition", "comparison_method",
}
SOURCE_KINDS = {
    "official_documentation", "official_announcement", "primary_research",
    "first_party_article", "public_source_post",
}
URL = re.compile(r"https?://\S+")
ALLOWED_DOMAINS = (
    "xiaohongshu.com", "douyin.com", "kuaishou.com", "bilibili.com",
    "weibo.com", "tieba.baidu.com", "zhihu.com",
)


def canonical_domain(hostname: str | None) -> str | None:
    host = (hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return next((domain for domain in ALLOWED_DOMAINS
                 if host == domain or host.endswith(f".{domain}")), None)


def content_url_allowed(value: str) -> bool:
    parsed = urlparse(value)
    domain = canonical_domain(parsed.hostname)
    host, path = (parsed.hostname or "").lower(), parsed.path
    rules = {
        "xiaohongshu.com": host in {"xiaohongshu.com", "www.xiaohongshu.com"} and path.startswith("/explore/"),
        "douyin.com": host in {"douyin.com", "www.douyin.com"} and path.startswith("/video/"),
        "kuaishou.com": host in {"kuaishou.com", "www.kuaishou.com"} and path.startswith("/short-video/"),
        "bilibili.com": host in {"bilibili.com", "www.bilibili.com"} and path.startswith("/video/"),
        "weibo.com": host in {"weibo.com", "www.weibo.com"} and len(path.strip("/").split("/")) >= 2,
        "tieba.baidu.com": host == "tieba.baidu.com" and path.startswith("/p/"),
        "zhihu.com": ((host in {"zhihu.com", "www.zhihu.com"} and path.startswith("/question/"))
                      or (host == "zhuanlan.zhihu.com" and path.startswith("/p/"))),
    }
    return bool(rules.get(domain))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"invalid JSON receipt: {path.name}") from error
    if not isinstance(value, dict):
        raise ValueError(f"receipt is not an object: {path.name}")
    return value


def normalized(value: str) -> str:
    return " ".join(value.translate(str.maketrans({
        "‘": "'", "’": "'", "“": '"', "”": '"',
    })).split())


def weighted_length(value: str) -> int:
    def chars(text: str) -> int:
        return sum(
            2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
            for char in text
        )

    total = start = 0
    for match in URL.finditer(value):
        total += chars(value[start:match.start()]) + 23
        start = match.end()
    return total + chars(value[start:])


def posted_text_hashes(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    hashes = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        claimed = row.get("text_sha256") if isinstance(row, dict) else None
        if isinstance(claimed, str) and re.fullmatch(r"[0-9a-f]{64}", claimed):
            hashes.add(claimed)
        text = row.get("text") if isinstance(row, dict) else None
        if isinstance(text, str) and text:
            hashes.add(hashlib.sha256(text.encode()).hexdigest())
            lines = text.rstrip().splitlines()
            if lines and re.fullmatch(r"https?://\S+", lines[-1]):
                body = "\n".join(lines[:-1]).rstrip()
                if body:
                    hashes.add(hashlib.sha256(body.encode()).hexdigest())
    return hashes


def posted_source_urls(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    urls = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        source_url = row.get("source_url") if isinstance(row, dict) else None
        if isinstance(source_url, str) and source_url:
            urls.add(source_url)
    return urls


def admit(source_path: Path, draft_path: Path, critic_path: Path, posted_path: Path) -> dict:
    source, draft, critic = map(read_object, (source_path, draft_path, critic_path))
    source_sha, draft_sha = sha256_file(source_path), sha256_file(draft_path)
    source_url = source.get("url")
    parsed = urlparse(source_url) if isinstance(source_url, str) else None
    source_domain = canonical_domain(parsed.hostname if parsed else None)
    source_text = source.get("text")
    if not all((
        parsed and parsed.scheme == "https" and source_domain and content_url_allowed(source_url),
        source.get("source_domain") == source_domain,
        source.get("source_language") == "zh",
        source.get("source_kind") in SOURCE_KINDS,
        isinstance(source.get("title"), str) and source["title"].strip(),
        isinstance(source_text, str) and source_text.strip(),
        isinstance(source.get("observed_at"), str) and source["observed_at"],
    )):
        raise ValueError("source receipt is not admissible")

    text = draft.get("text")
    evidence = draft.get("evidence_quote")
    evidence_translation = draft.get("evidence_translation")
    reader_value = draft.get("reader_value")
    draft_values = draft.get("value_types")
    if not all((
        isinstance(text, str) and text == text.strip() and 40 <= len(text) <= 240,
        not URL.search(text or ""),
        draft.get("source_url") == source_url,
        isinstance(evidence, str) and len(normalized(evidence)) >= 8,
        normalized(evidence) in normalized(source_text),
        isinstance(evidence_translation, str) and len(normalized(evidence_translation)) >= 8,
        isinstance(reader_value, str) and reader_value.strip(),
        isinstance(draft_values, list),
        len(set(draft_values) & VALUE_TYPES) >= 2,
        weighted_length(f"{text}\n{source_url}") <= 280,
    )):
        raise ValueError("draft lacks grounded concrete value")

    critic_values = critic.get("value_types")
    if not all((
        critic.get("source_sha256") == source_sha,
        critic.get("draft_sha256") == draft_sha,
        critic.get("supported") is True,
        critic.get("useful") is True,
        critic.get("novel") is True,
        critic.get("spam_risk") == "low",
        critic.get("unsupported_claims") == [],
        critic.get("near_duplicate_post_ids") == [],
        isinstance(critic_values, list),
        len(set(critic_values) & VALUE_TYPES) >= 2,
        isinstance(critic.get("reason"), str) and critic["reason"].strip(),
    )):
        raise ValueError("critic did not admit the original")

    text_sha = hashlib.sha256(text.encode()).hexdigest()
    if text_sha in posted_text_hashes(posted_path):
        raise ValueError("exact original duplicate")
    if source_url in posted_source_urls(posted_path):
        raise ValueError("source URL duplicate")
    core = {
        "schema_version": 1,
        "receipt_type": "X_TWEETER_ORIGINAL_PAYLOAD",
        "state": "READY_TO_PUBLISH",
        "text": text,
        "text_sha256": text_sha,
        "source_url": source_url,
        "source_domain": source_domain,
        "source_sha256": source_sha,
        "draft_sha256": draft_sha,
        "critic_sha256": sha256_file(critic_path),
        "evidence_quote": evidence,
        "evidence_translation": evidence_translation,
        "reader_value": reader_value,
        "value_types": sorted(set(draft_values) & VALUE_TYPES),
        "weighted_length_with_source": weighted_length(f"{text}\n{source_url}"),
    }
    return {
        **core,
        "payload_id": hashlib.sha256(json.dumps(
            core, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--critic", type=Path, required=True)
    parser.add_argument("--posted", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(admit(
        args.source, args.draft, args.critic, args.posted
    ), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
