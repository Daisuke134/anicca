from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


BUSINESS_ROLE_FAMILIES = frozenset(
    {
        "product",
        "program",
        "solutions",
        "gtm",
        "partnerships",
        "customer_success",
        "technical_account",
        "sales_engineering",
        "business_development",
    }
)

JAPANESE_PATTERN = re.compile(r"[ぁ-んァ-ヶ一-龯々]")
ASCII_LETTER_PATTERN = re.compile(r"[A-Za-z]")


def detect_posting_language(posting_text: str) -> str:
    japanese_count = len(JAPANESE_PATTERN.findall(posting_text))
    ascii_count = len(ASCII_LETTER_PATTERN.findall(posting_text))
    comparable_count = japanese_count + ascii_count
    if (
        japanese_count >= 8
        and comparable_count > 0
        and japanese_count / comparable_count >= 0.18
    ):
        return "ja"
    return "en"


def _normalized_role_family(role_family: str) -> str:
    return re.sub(r"[\s-]+", "_", role_family.strip().casefold())


def select_resume(
    *,
    posting_text: str,
    role_family: str,
    materials_root: Path,
    posting_language: str | None = None,
) -> dict[str, str]:
    language = posting_language or detect_posting_language(posting_text)
    if language not in {"ja", "en"}:
        raise ValueError("posting_language must be ja or en")

    if language == "ja":
        variant = "japanese"
        relative_path = Path("japan") / "Daisuke_Narita_Japan_AI_Resume.pdf"
    elif _normalized_role_family(role_family) in BUSINESS_ROLE_FAMILIES:
        variant = "technical_business"
        relative_path = (
            Path("business") / "Daisuke_Narita_AI_Business_Resume.pdf"
        )
    else:
        variant = "engineering"
        relative_path = Path("master") / "Daisuke_Narita_AI_Resume.pdf"

    resume_path = (Path(materials_root).expanduser() / relative_path).resolve()
    if not resume_path.is_file():
        raise FileNotFoundError(f"selected resume does not exist: {resume_path}")
    digest = hashlib.sha256(resume_path.read_bytes()).hexdigest()
    return {
        "posting_language": language,
        "resume_variant": variant,
        "resume_path": str(resume_path),
        "resume_sha256": digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role-family", required=True)
    parser.add_argument("--materials-root", required=True, type=Path)
    parser.add_argument("--posting-language", choices=("ja", "en"))
    parser.add_argument("--posting-text-file", type=Path)
    arguments = parser.parse_args()
    posting_text = (
        arguments.posting_text_file.read_text(encoding="utf-8")
        if arguments.posting_text_file
        else sys.stdin.read()
    )
    print(
        json.dumps(
            select_resume(
                posting_text=posting_text,
                role_family=arguments.role_family,
                materials_root=arguments.materials_root,
                posting_language=arguments.posting_language,
            ),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
