from __future__ import annotations

import html
import json
import subprocess
from pathlib import Path
from typing import Any


class MaterialError(ValueError):
    pass


def secure_material_paths(*paths: Path) -> None:
    for path in paths:
        path.chmod(0o600)


def validate_claims(profile: dict[str, Any], items: list[dict[str, Any]]) -> None:
    approved = {fact["id"] for fact in profile.get("facts", [])}
    for item in items:
        fact_ids = item.get("fact_ids")
        if not isinstance(fact_ids, list) or not fact_ids or not set(fact_ids) <= approved:
            raise MaterialError("every claim must reference approved fact IDs")
        text = str(item.get("text", ""))
        if "mufg" in {value.casefold() for value in fact_ids}:
            lowered = text.casefold()
            if "led the entire" in lowered or "single-handed" in lowered:
                raise MaterialError("MUFG ownership wording is not approved")


def render_resume_html(
    profile: dict[str, Any],
    sections: list[dict[str, Any]],
    *,
    links: list[tuple[str, str]],
    include_date_of_birth: bool = False,
    date_of_birth_label: str = "Date of birth",
    document_language: str = "en",
    display_name: str | None = None,
    base_display: str | None = None,
    headline: str = "Applied AI & Agent Engineer",
    summary: str = (
        "regulated enterprise deployment, research, and consumer AI products"
    ),
) -> str:
    all_items = [item for section in sections for item in section.get("items", [])]
    validate_claims(profile, all_items)
    name = html.escape(display_name or profile["candidate"]["name"])
    body: list[str] = []
    for section in sections:
        body.append(f"<section><h2>{html.escape(section['heading'])}</h2><ul>")
        for item in section.get("items", []):
            body.append(f"<li>{html.escape(item['text'])}</li>")
        body.append("</ul></section>")
    link_html = " · ".join(
        f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>'
        for label, url in links
    )
    candidate = profile["candidate"]
    contact_values = [
        candidate.get("application_email"),
        candidate.get("phone"),
        base_display or candidate.get("base"),
    ]
    if include_date_of_birth and candidate.get("date_of_birth"):
        contact_values.append(
            f"{date_of_birth_label}：{candidate['date_of_birth']}"
            if document_language == "ja"
            else f"{date_of_birth_label}: {candidate['date_of_birth']}"
        )
    contact_html = " · ".join(
        html.escape(str(value)) for value in contact_values if value
    )
    headline_html = html.escape(headline)
    summary_html = html.escape(summary)
    return f"""<!doctype html>
<html lang="{html.escape(document_language, quote=True)}"><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 12mm 14mm; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Yu Gothic",
       "Noto Sans CJK JP", "Helvetica Neue", Arial, sans-serif;
       color: #111827; font-size: 9.2pt; line-height: 1.28; }}
main {{ display: grid; grid-template-columns: 1fr; gap: 3px; }}
h1 {{ font-size: 22pt; margin: 0; }} h2 {{ font-size: 11pt; text-transform: uppercase;
letter-spacing: .08em; border-bottom: 1px solid #9ca3af; margin: 7px 0 3px; }}
p, ul {{ margin: 2px 0; }} ul {{ padding-left: 17px; }} li {{ margin: 1.5px 0; }}
a {{ color: #1d4ed8; text-decoration: none; }}
html[lang="ja"] body {{ font-size: 8.7pt; line-height: 1.25; }}
html[lang="ja"] h2 {{ text-transform: none; letter-spacing: .04em; }}
</style></head><body><main>
<header><h1>{name}</h1><p><strong>{headline_html}</strong> — {summary_html}</p>
<p>{contact_html}</p><p>{link_html}</p></header>
{''.join(body)}
</main></body></html>"""


def master_sections(profile: dict[str, Any]) -> list[dict[str, Any]]:
    facts = {fact["id"]: fact["claim"] for fact in profile["facts"]}
    groups = [
        (
            "Enterprise AI — MUIT / MUFG (2025–Present)",
            ["muit_agent_crm", "muit_genie_logs", "muit_rm_summary", "mufg"],
        ),
        (
            "Consumer AI Products",
            ["anicca_consumer", "life_manager"],
        ),
        (
            "Research & Leadership — NAIST / ATR (2024–2026)",
            ["naist", "atr_research", "agent_club", "iclr"],
        ),
        ("Earlier Growth Experience", ["a10_marketing"]),
        ("Education & Languages", ["education", "languages"]),
    ]
    return [
        {
            "heading": heading,
            "items": [
                {"text": facts[fact_id], "fact_ids": [fact_id]}
                for fact_id in fact_ids
                if fact_id in facts
            ],
        }
        for heading, fact_ids in groups
    ]


def business_sections(profile: dict[str, Any]) -> list[dict[str, Any]]:
    facts = {fact["id"]: fact["claim"] for fact in profile["facts"]}
    groups = [
        (
            "Regulated Enterprise AI Delivery — MUIT / MUFG (2025–Present)",
            [
                "muit_role_2025",
                "muit_agent_crm",
                "muit_genie_logs",
                "muit_rm_summary",
                "mufg",
            ],
        ),
        (
            "Product, Customer & Growth",
            ["anicca_consumer", "life_manager", "a10_marketing"],
        ),
        (
            "Technical Leadership & Communication",
            ["agent_club", "iclr"],
        ),
        (
            "Research & Education",
            ["naist", "atr_research", "education", "languages"],
        ),
    ]
    return [
        {
            "heading": heading,
            "items": [
                {"text": facts[fact_id], "fact_ids": [fact_id]}
                for fact_id in fact_ids
                if fact_id in facts
            ],
        }
        for heading, fact_ids in groups
    ]


JAPANESE_FACT_TEXT = {
    "muit_role_2025": (
        "三菱UFJインフォメーションテクノロジー（MUIT）で、2025年4月から"
        "応用AI・AIエージェント領域に従事。"
    ),
    "muit_agent_crm": "銀行のCRM環境へのAIエージェント導入に従事。",
    "muit_genie_logs": (
        "Databricks Genie Codeを用い、エージェント出力ログの詳細分析を自動化。"
    ),
    "muit_rm_summary": (
        "リレーションシップマネージャー向け企業情報要約エージェントの"
        "プロンプト調整を担当。"
    ),
    "mufg": (
        "金融機関として日本初となるAgentforce for Financial Servicesの"
        "MUFG本番導入に貢献し、厳格な銀行環境へエージェント業務を展開。"
    ),
    "anicca_consumer": (
        "Swift/iOSのコンシューマー向けプロダクトとグロース施策を構築し、"
        "Aniccaを月間経常収益100米ドルまで成長。"
    ),
    "life_manager": (
        "金融・身体・メンタルヘルスのワークフローを統合する"
        "コンシューマーAIエージェント「Life Manager」を開発。"
    ),
    "naist": (
        "奈良先端科学技術大学院大学の修士研究（2024年4月〜2026年4月）で、"
        "EEGと機械学習を用いたマインドワンダリング検出に従事。"
    ),
    "atr_research": "ATRでマインドワンダリング研究を実施し、研究成果を発表。",
    "agent_club": (
        "Claude Code、Codex、Cursor、AIエージェントの研究・業務活用を扱う"
        "週次勉強会とコミュニティを研究室・大学院内で設立。"
    ),
    "iclr": (
        "リオデジャネイロでICLR 2026に参加し、社内発表およびMUIT公式"
        "YouTubeレポートで最新論文の学びを共有。"
    ),
    "a10_marketing": (
        "A10 Labで2,000万円の広告予算を運用し、CPAを10%削減、"
        "有料獲得数の過去最高を達成。"
    ),
    "education": (
        "奈良先端科学技術大学院大学 修士課程、慶應義塾大学 法学部政治学科卒。"
    ),
    "languages": (
        "日本語ネイティブ。英語：TOEFL iBT 96、Duolingo English Test 140。"
        "スペイン語：DELE B1。"
    ),
}


def japanese_sections(profile: dict[str, Any]) -> list[dict[str, Any]]:
    approved = {fact["id"] for fact in profile["facts"]}
    groups = [
        (
            "職務経歴 — MUIT / MUFG（2025年4月〜現在）",
            [
                "muit_role_2025",
                "muit_agent_crm",
                "muit_genie_logs",
                "muit_rm_summary",
                "mufg",
            ],
        ),
        (
            "個人開発・コンシューマーAI",
            ["anicca_consumer", "life_manager"],
        ),
        (
            "研究・コミュニティ活動 — NAIST / ATR",
            ["naist", "atr_research", "agent_club", "iclr"],
        ),
        ("マーケティング経験", ["a10_marketing"]),
        ("学歴・語学", ["education", "languages"]),
    ]
    return [
        {
            "heading": heading,
            "items": [
                {"text": JAPANESE_FACT_TEXT[fact_id], "fact_ids": [fact_id]}
                for fact_id in fact_ids
                if fact_id in approved
            ],
        }
        for heading, fact_ids in groups
    ]


def _render_pdf(
    *,
    profile: dict[str, Any],
    output_dir: Path,
    filename_stem: str,
    sections: list[dict[str, Any]],
    links: list[tuple[str, str]],
    headline: str,
    summary: str,
    required_ats_text: tuple[str, ...],
    include_date_of_birth: bool = False,
    date_of_birth_label: str = "Date of birth",
    document_language: str = "en",
    display_name: str | None = None,
    base_display: str | None = None,
) -> tuple[Path, Path]:
    rendered = render_resume_html(
        profile,
        sections,
        links=links,
        include_date_of_birth=include_date_of_birth,
        date_of_birth_label=date_of_birth_label,
        document_language=document_language,
        display_name=display_name,
        base_display=base_display,
        headline=headline,
        summary=summary,
    )
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os_mode = output_dir.stat().st_mode & 0o777
    if os_mode != 0o700:
        output_dir.chmod(0o700)
    html_path = output_dir / f"{filename_stem}.html"
    pdf_path = output_dir / f"{filename_stem}.pdf"
    html_path.write_text(rendered, encoding="utf-8")
    subprocess.run(["weasyprint", str(html_path), str(pdf_path)], check=True)
    secure_material_paths(html_path, pdf_path)
    extracted = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    for required in required_ats_text:
        if required not in extracted:
            raise MaterialError(f"PDF missing required ATS text: {required}")
    secure_material_paths(html_path, pdf_path)
    return html_path, pdf_path


def _public_links() -> list[tuple[str, str]]:
    return [
        ("Portfolio", "https://aniccaai.com/dais"),
        ("ICLR 2026 report", "https://www.youtube.com/watch?v=biHAQ6aSQuc"),
        ("Life Manager", "https://aniccaai.com/life-manager"),
    ]


def render_master(profile_path: Path, output_dir: Path) -> tuple[Path, Path]:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    return _render_pdf(
        profile=profile,
        output_dir=output_dir,
        filename_stem="Daisuke_Narita_AI_Resume",
        sections=master_sections(profile),
        links=_public_links(),
        headline="Applied AI & Agent Engineer",
        summary="regulated enterprise deployment, research, and consumer AI products",
        required_ats_text=("Daisuke Narita", "MUIT", "NAIST", "Applied AI"),
    )


def render_business(profile_path: Path, output_dir: Path) -> tuple[Path, Path]:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    return _render_pdf(
        profile=profile,
        output_dir=output_dir,
        filename_stem="Daisuke_Narita_AI_Business_Resume",
        sections=business_sections(profile),
        links=_public_links(),
        headline="AI Product, Solutions & Customer Strategy",
        summary=(
            "regulated enterprise delivery, customer adoption, and consumer "
            "product growth"
        ),
        required_ats_text=(
            "Daisuke Narita",
            "MUIT",
            "AI Product",
            "Customer",
            "Anicca",
        ),
    )


def render_japanese(profile_path: Path, output_dir: Path) -> tuple[Path, Path]:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    candidate = profile["candidate"]
    name_ja = candidate.get("name_ja")
    display_name = (
        f"{name_ja} / {candidate['name']}" if name_ja else candidate["name"]
    )
    base_display = (
        "東京都、日本"
        if candidate.get("base") == "Tokyo, Japan"
        else candidate.get("base")
    )
    return _render_pdf(
        profile=profile,
        output_dir=output_dir,
        filename_stem="Daisuke_Narita_Japan_AI_Resume",
        sections=japanese_sections(profile),
        links=[
            ("ポートフォリオ", "https://aniccaai.com/dais"),
            (
                "ICLR 2026参加レポート",
                "https://www.youtube.com/watch?v=biHAQ6aSQuc",
            ),
            ("Life Manager", "https://aniccaai.com/life-manager"),
        ],
        headline="職務経歴書",
        summary=(
            "金融機関向けエンタープライズAIとコンシューマーAIプロダクトの実装経験"
        ),
        required_ats_text=(
            display_name,
            "職務経歴書",
            "MUIT",
            "AIエージェント",
            "NAIST",
        ),
        include_date_of_birth=True,
        date_of_birth_label="生年月日",
        document_language="ja",
        display_name=display_name,
        base_display=base_display,
    )
