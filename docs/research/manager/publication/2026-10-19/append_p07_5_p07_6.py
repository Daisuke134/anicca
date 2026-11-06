"""Append source-grounded EN/JA P07-5/6 Manager articles to canonical blog.

Uses the *existing* manager-blog package contract and manifest, rather than
creating a parallel publishing system. Re-runnable, no duplicate articles.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PACKAGE = ROOT / "docs/research/manager/publication/2026-10-19"
MANIFEST = PACKAGE / "manifest.json"
ARTICLES = (
    # Language, source basename, URL slug, page title, description, citation count, editorial order
    ("ja", "2026-11-05-vipassana-insight-behavior-model-ja.md",
     "manager-vipassana-behavior-model-ja",
     "ヴィパッサナーの無常・苦・無我を、行動AIは理解できるのか",
     "MN10・SN22.59・SN12.2と7T脳科学の限界を解説。悟り診断ではなく実際の行動を測る。",
     7, 160),
    ("en", "2026-11-05-vipassana-insight-behavior-model-en.md",
     "manager-vipassana-behavior-model-en",
     "Can a Behavioral Foundation Model Understand Vipassana Insight?",
     "Primary Buddhist texts, contemplative neuroscience and why an AI should not classify enlightenment.",
     7, 90),
    ("ja", "2026-11-05-measure-benefit-and-harm-p07-6-ja.md",
     "manager-measure-welfare-and-harm-ja",
     "行動AIの最重要ベンチマークは、現実に役立ったか、害を生まなかったか",
     "WHO-5等の尺度、瞑想の有害事象、RCTの評価を再利用し、Managerの安全基盤へ接続する。",
     8, 161),
    ("en", "2026-11-05-measure-benefit-and-harm-p07-6-en.md",
     "manager-measure-welfare-and-harm-en",
     "The Real Benchmark of Behavior-Change AI Is Human Benefit—and Harm",
     "Measuring human outcomes, validated-scale rights, meditation harms and causal assignment.",
     8, 91),
)


def run():
    if not MANIFEST.is_file():
        raise RuntimeError("canonical blog manifest not found")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(manifest.get("articles"), list) or len(manifest["articles"]) < 80:
        raise RuntimeError("canonical publishing history missing; never replace with new manifest")
    seen = {a["slug"]: a for a in manifest["articles"]}
    for lang, basename, slug, title, desc, citations, order in ARTICLES:
        source_path = Path("docs/research/manager/articles") / basename
        source = ROOT / source_path
        raw = source.read_bytes()
        markdown = raw.decode("utf-8")
        if len(markdown) < 1000:
            raise RuntimeError(f"truncated article {slug}")
        if markdown.count("https://") < 3:
            raise RuntimeError(f"missing source links for {slug}")
        sha = hashlib.sha256(raw).hexdigest()
        relative = f"{lang}/{slug}.md"
        target = PACKAGE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        entry = {
            "source": source_path.as_posix(),
            "source_sha256": sha,
            "slug": slug,
            "language": lang,
            "title": title,
            "package_path": relative,
            "canonical_url": f"https://aniccaai.com/blog/{slug}",
            "date": "2026-11-05",
            "project": "Manager",
            "lang": lang,
            "n_papers_cited": citations,
            "word_count": len(markdown.split()),
            "character_count": len(markdown),
            "markdown": markdown,
            "sha256": sha,
            "description": desc,
            "series_order": order,
        }
        if slug in seen:
            old = seen[slug]
            if old != entry:
                raise RuntimeError(f"published metadata drift for {slug}; explicit review needed")
        else:
            manifest["articles"].append(entry)
        print("CANONICAL_BLOG_ARTICLE", slug, sha, len(raw))
    expected_slugs = {a[2] for a in ARTICLES}
    if len(expected_slugs) != len(ARTICLES):
        raise AssertionError("duplicate new article")
    if not expected_slugs.issubset({a["slug"] for a in manifest["articles"]}):
        raise AssertionError("article missing after append")
    if len(manifest["articles"]) != 84 or len(manifest["media"]) != 50:
        raise RuntimeError(
            f"Unexpected manifest 84/50 versus {len(manifest['articles'])}/{len(manifest['media'])}"
        )
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("CANONICAL_BLOG_PACKAGED", len(manifest["articles"]), len(manifest["media"]))


if __name__ == "__main__":
    run()
