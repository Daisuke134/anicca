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
            item_links = " · ".join(
                f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>'
                for label, url in item.get("links", [])
            )
            suffix = f"<br><span class=\"item-links\">{item_links}</span>" if item_links else ""
            body.append(f"<li>{html.escape(item['text'])}{suffix}</li>")
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
a {{ color: #1d4ed8; text-decoration: none; }} .item-links {{ font-size: 8pt; }}
html[lang="ja"] body {{ font-size: 8.7pt; line-height: 1.25; }}
html[lang="ja"] h2 {{ text-transform: none; letter-spacing: .04em; }}
</style></head><body><main>
<header><h1>{name}</h1><p><strong>{headline_html}</strong> — {summary_html}</p>
<p>{contact_html}</p><p>{link_html}</p></header>
{''.join(body)}
</main></body></html>"""


def master_sections(profile: dict[str, Any]) -> list[dict[str, Any]]:
    sections = [
        {"heading": "Professional Experience", "items": [
            {"text": "Mitsubishi UFJ Information Technology, Ltd. (MUIT) — Applied AI / AI Agent Engineering | Tokyo, Japan | Apr 2025–Present", "fact_ids": ["muit_role_2025"]},
            {"text": "Enterprise CRM AI Agent Deployment — Contributed through MUIT to Japan's first production deployment by a financial institution of Salesforce Agentforce—a platform for building and operating AI agents—integrating agent capabilities into MUFG Bank's internal CRM system used by sales professionals.", "fact_ids": ["muit_agent_crm", "mufg"]},
            {"text": "Built an observability workflow in Databricks to analyze the AI agents' inputs, outputs, and responses to sales professionals. Used Genie Code to investigate behavior, identify response-quality issues, and support improvements in agent effectiveness.", "fact_ids": ["muit_genie_logs"]},
            {"text": "Supported prompt tuning and context engineering for the deployed AI agents, including agents that generate company-information summaries for relationship managers.", "fact_ids": ["muit_rm_summary"]},
            {"text": "ICLR 2026 Research Communication — Represented MUIT at ICLR 2026 in Rio de Janeiro; synthesized frontier-AI research for an internal executive briefing and presented key findings through MUIT's official two-part conference report.", "fact_ids": ["iclr"], "links": [("ICLR 2026 Conference Report", "https://www.youtube.com/watch?v=biHAQ6aSQuc")]},
            {"text": "A10 Lab Inc. — Marketing Intern | Jan 2021–Jan 2022 — Managed a JPY 20M campaign budget, reduced CPA by 10%, and achieved record paid acquisition.", "fact_ids": ["a10_marketing"]},
        ]},
        {"heading": "Education & Research", "items": [
            {"text": "Nara Institute of Science and Technology (NAIST) | Apr 2024–Apr 2026 — Master's research applying EEG and machine learning to mind-wandering detection; conducted and presented research at Advanced Telecommunications Research Institute International (ATR).", "fact_ids": ["naist", "atr_research"]},
            {"text": "Founded a weekly community focused on applying Claude Code, Codex, Cursor, and AI-agent workflows to research and daily work.", "fact_ids": ["agent_club"]},
            {"text": "Keio University — B.A. in Political Science | 2020–2024.", "fact_ids": ["education"]},
        ]},
        {"heading": "Selected Independent Projects", "items": [
            {"text": "Life Manager — Autonomous Personal Operations Agent — Built an open-source agent system designed to run locally and coordinate calendar, commute, phone, Telegram, and everyday life workflows, with persistent scheduling and verified handling of external actions.", "fact_ids": ["life_manager"], "links": [("Web", "https://aniccaai.com/life-manager"), ("GitHub", "https://github.com/Daisuke134/life-manager")]},
            {"text": "Anicca — Mobile Affirmation App — Built and shipped a mobile affirmation app with 45+ ratings and a 4.5/5 rating.", "fact_ids": ["anicca_consumer"], "links": [("Product", "https://aniccaai.com/affirmation-app"), ("App Store", "https://apps.apple.com/jp/app/id6755129214")]},
        ]},
        {"heading": "Skills & Languages", "items": [
            {"text": "AI agents, Salesforce Agentforce, prompt tuning, context engineering, Databricks, Genie Code, AI observability, machine learning, CRM workflows, Swift, iOS development.", "fact_ids": ["muit_agent_crm", "muit_genie_logs", "muit_rm_summary", "anicca_consumer", "naist"]},
            {"text": "Japanese: Native | English: TOEFL iBT 96, Duolingo English Test 140 | Spanish: DELE B1.", "fact_ids": ["languages"]},
        ]},
    ]
    approved = {fact["id"] for fact in profile.get("facts", [])}
    return [
        {
            "heading": section["heading"],
            "items": [
                item
                for item in section["items"]
                if set(item["fact_ids"]) <= approved
            ],
        }
        for section in sections
    ]


def business_sections(profile: dict[str, Any]) -> list[dict[str, Any]]:
    sections = master_sections(profile)
    return [sections[0], sections[2], sections[1], sections[3]]


JAPANESE_FACT_TEXT = {
    "muit_role_2025": (
        "三菱UFJインフォメーションテクノロジー（MUIT）で、2025年4月から"
        "応用AI・AIエージェント領域に従事。"
    ),
    "muit_agent_crm": (
        "AIエージェントを構築・運用するSalesforceのプラットフォーム"
        "「Agentforce」を、三菱UFJ銀行の営業担当者が利用する社内CRMへ"
        "導入するプロジェクトに、MUITの担当者として参画。"
    ),
    "muit_genie_logs": (
        "AIエージェントへの入力、生成された回答、営業担当者への回答内容を"
        "分析する基盤をDatabricks上で構築。Genie Codeを活用して挙動や"
        "回答品質の問題を調査し、エージェントの有効性改善を支援。"
    ),
    "muit_rm_summary": (
        "企業情報を営業担当者向けに要約する機能を含むAIエージェントについて、"
        "プロンプト調整とコンテキストエンジニアリングを支援。"
    ),
    "mufg": (
        "金融機関として国内初となるAgentforce for Financial Servicesの"
        "本番導入に、MUITの担当者として貢献。"
    ),
    "anicca_consumer": (
        "モバイル向けアファメーションアプリAniccaを開発・公開。"
        "45件以上の評価を獲得し、評価4.5/5。"
    ),
    "life_manager": (
        "カレンダー、移動、電話、Telegramなど日常生活に関わる作業を連携する"
        "オープンソースのAIエージェント「Life Manager」を開発。"
        "ローカル環境を中心に継続的に動作し、外部操作の結果確認に対応。"
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
        "MUITの業務としてリオデジャネイロで開催されたICLR 2026に参加。"
        "最先端AI研究を整理して経営層向けに社内報告し、MUIT公式の"
        "カンファレンスレポートを通じて社外にも発信。"
    ),
    "a10_marketing": (
        "A10 Labで2021年1月から2022年1月までマーケティングインターン。"
        "2,000万円の広告予算を運用し、CPAを10%削減、"
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
            "職務経歴 — 三菱UFJインフォメーションテクノロジー株式会社（MUIT）｜2025年4月〜現在",
            [
                "muit_role_2025",
                "muit_agent_crm",
                "muit_genie_logs",
                "muit_rm_summary",
                "mufg",
            ],
        ),
        ("ICLR 2026の調査・社内外発信", ["iclr"]),
        (
            "研究・学歴 — NAIST / ATR / 慶應義塾大学",
            ["naist", "atr_research", "agent_club", "education"],
        ),
        (
            "個人開発",
            ["life_manager", "anicca_consumer"],
        ),
        ("マーケティング経験", ["a10_marketing"]),
        ("語学", ["languages"]),
    ]
    link_map = {
        "life_manager": [("Web", "https://aniccaai.com/life-manager"), ("GitHub", "https://github.com/Daisuke134/life-manager")],
        "anicca_consumer": [("Product", "https://aniccaai.com/affirmation-app"), ("App Store", "https://apps.apple.com/jp/app/id6755129214")],
        "iclr": [("ICLR 2026参加レポート", "https://www.youtube.com/watch?v=biHAQ6aSQuc")],
    }
    result = []
    for heading, fact_ids in groups:
        items = []
        for fact_id in fact_ids:
            if fact_id not in approved:
                continue
            item = {"text": JAPANESE_FACT_TEXT[fact_id], "fact_ids": [fact_id]}
            if fact_id in link_map:
                item["links"] = link_map[fact_id]
            items.append(item)
        result.append({"heading": heading, "items": items})
    return result


def japanese_rirekisho_sections(profile: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"heading": "学歴", "items": [
            {"text": "2020年　慶應義塾大学 法学部政治学科 入学", "fact_ids": ["education"]},
            {"text": "2024年　慶應義塾大学 法学部政治学科 卒業", "fact_ids": ["education"]},
            {"text": "2024年4月〜2026年4月　奈良先端科学技術大学院大学 修士課程", "fact_ids": ["naist"]},
        ]},
        {"heading": "職歴・実務経験", "items": [
            {"text": "2021年1月〜2022年1月　株式会社A10 Lab　マーケティングインターン", "fact_ids": ["a10_marketing"]},
            {"text": "2025年4月　三菱UFJインフォメーションテクノロジー株式会社 入社　応用AI・AIエージェント関連業務に従事（現在に至る）", "fact_ids": ["muit_role_2025"]},
        ]},
        {"heading": "研究活動", "items": [
            {"text": "奈良先端科学技術大学院大学にて、EEGと機械学習を用いたマインドワンダリング検出を研究。株式会社国際電気通信基礎技術研究所（ATR）にて研究を実施し、研究成果を発表。", "fact_ids": ["naist", "atr_research"]},
        ]},
        {"heading": "語学", "items": [
            {"text": "日本語：ネイティブ　英語：TOEFL iBT 96、Duolingo English Test 140　スペイン語：DELE B1", "fact_ids": ["languages"]},
        ]},
        {"heading": "本人希望欄", "items": [
            {"text": "貴社規定に従います。", "fact_ids": ["muit_role_2025"]},
        ]},
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
        ("GitHub", "https://github.com/Daisuke134"),
        ("ICLR 2026 Conference Report", "https://www.youtube.com/watch?v=biHAQ6aSQuc"),
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
        summary=("AI agent deployment and observability in MUFG Bank's internal CRM, "
                 "AI research, and product engineering"),
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
            "banking AI delivery, customer workflows, and product growth"
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
            (
                "ICLR 2026参加レポート",
                "https://www.youtube.com/watch?v=biHAQ6aSQuc",
            ),
            ("GitHub", "https://github.com/Daisuke134"),
        ],
        headline="職務経歴書",
        summary=(
            "三菱UFJ銀行の社内CRMへのAIエージェント導入・改善、AI研究、プロダクト開発"
        ),
        required_ats_text=(
            display_name,
            "職務経歴書",
            "MUIT",
            "AIエージェント",
            "NAIST",
        ),
        include_date_of_birth=False,
        document_language="ja",
        display_name=display_name,
        base_display=base_display,
    )


def render_japanese_rirekisho(
    profile_path: Path, output_dir: Path
) -> tuple[Path, Path]:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    candidate = profile["candidate"]
    name_ja = candidate.get("name_ja") or candidate["name"]
    return _render_pdf(
        profile=profile,
        output_dir=output_dir,
        filename_stem="Daisuke_Narita_Japanese_Rirekisho",
        sections=japanese_rirekisho_sections(profile),
        links=[],
        headline="履歴書",
        summary="学歴・職歴・研究活動・語学",
        required_ats_text=(
            name_ja,
            "履歴書",
            "慶應義塾大学",
            "三菱UFJインフォメーションテクノロジー株式会社",
        ),
        include_date_of_birth=True,
        date_of_birth_label="生年月日",
        document_language="ja",
        display_name=name_ja,
        base_display="東京都、日本",
    )
