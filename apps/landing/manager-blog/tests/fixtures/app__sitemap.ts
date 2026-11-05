import type { MetadataRoute } from "next";
import {
  AFFIRMATION_HREFLANG_TRIPLES,
  alternatesFor,
} from "@/lib/affirmation-alternates";
import { loadAllBlogPosts, } from "@/lib/blog-posts";
import { BUSINESSES } from "@/lib/blog-business.mjs";
import { allEnAffirmationSlugs } from "@/lib/en-affirmation-problems";
import { allEsAffirmationSlugs } from "@/lib/es-affirmation-problems";
import { JA_AFFIRMATION_PROBLEMS } from "@/lib/ja-affirmation-problems";
import { allKokoroTypeIds } from "@/lib/kokoro-quiz";
import { LM_JA_GUIDES } from "@/lib/lm-ja-guides";

const BASE_URL = "https://aniccaai.com";

// Static top-level pages. Paths must exist (no 404s). No trailing-slash
// duplicates of redirect-only aliases.
const STATIC_PATHS = [
  "/blog",
  "/affirmation-app",
  "/best-affirmation-apps",
  "/ja/best-affirmation-apps",
  "/affirmation-app/ja",
  "/affirmation-app/ja/shindan",
  "/affirmation-app/en/quiz",
  "/affirmation-app/en/quiz/burnout",
  "/affirmation-app/en/quiz/comparison",
  "/affirmation-app/en/quiz/heartbreak",
  "/affirmation-app/en/quiz/money-worry",
  "/affirmation-app/en/quiz/morning",
  "/affirmation-app/en/quiz/night-anxiety",
  "/affirmation-app/en/quiz/self-blame",
  "/affirmation-app/en/quiz/self-esteem",
  "/letter",
  "/tegami",
  "/en",
  "/honne",
  "/honne/ja",
  "/pdf-insight",
  "/dais",
  "/breath-calm",
  "/calmcortisol",
  "/thankful",
  "/dailydharma",
  "/sleepreset",
  "/studio-cherie",
  "/ai-cafe-tokyo/",
  "/ai-grave/",
  "/lm",
  "/lm/ja",
  "/lm/ja/departure-calculator",
  "/lm/guide",
  "/tools/social-jet-lag-calculator",
  "/ai-monk-factory", // canonical has no trailing slash (the slash form 301s; GSC "Redirect error" 10/27–11/1)
];

function tripleLanguagesForEnSlug(enSlug: string) {
  const triple = AFFIRMATION_HREFLANG_TRIPLES.find((t) => t.en === enSlug);
  return triple ? alternatesFor(triple) : undefined;
}

export default function sitemap(): MetadataRoute.Sitemap {
  const staticEntries: MetadataRoute.Sitemap = STATIC_PATHS.map((p) => ({
    url: `${BASE_URL}${p}`,
  }));

  // 2026-10-27 indexing fix: GSC showed 518/527 "Discovered - not indexed".
  // Google crawls fewer URLs on a new low-authority domain, so the sitemap now
  // lists only hand-picked hubs and evergreen pages. Timestamped auto posts,
  // sticker posts and archive pagination stay live (and linked) but are not
  // advertised here. Cap blog entries at the 40 newest evergreen posts.
  const isEvergreen = (slug: string) =>
    !/\d{4}-\d{2}-\d{2}/.test(slug) && !/^line-sticker/.test(slug);
  const blogEntries: MetadataRoute.Sitemap = loadAllBlogPosts().filter((post) => isEvergreen(post.slug)).slice(0, 40).map((post) => ({
    url: `${BASE_URL}/blog/${post.slug}`,
    lastModified: post.date || undefined,
  }));

  // One hub per business (2026-10-18): each business's articles form their own cluster.
  const businessHubEntries: MetadataRoute.Sitemap = Object.keys(BUSINESSES).map((key) => ({
    url: `${BASE_URL}/blog/c/${key}`,
  }));

  // Hand-written Japanese Life Manager guides (separate from the Writer's /blog posts).
  const lmGuideEntries: MetadataRoute.Sitemap = LM_JA_GUIDES.map((g) => ({
    url: `${BASE_URL}/lm/guide/${g.slug}`,
    lastModified: g.date,
  }));

  const jaAffirmationEntries: MetadataRoute.Sitemap =
    JA_AFFIRMATION_PROBLEMS.map((problem) => {
      const triple = AFFIRMATION_HREFLANG_TRIPLES.find((t) => t.ja === problem.slug);
      const languages = triple ? alternatesFor(triple) : undefined;
      return {
        url: `${BASE_URL}/affirmation-app/ja/a/${problem.slug}`,
        ...(languages ? { alternates: { languages } } : {}),
      };
    });

  const enAffirmationEntries: MetadataRoute.Sitemap = allEnAffirmationSlugs().map(
    (slug) => {
      const languages = tripleLanguagesForEnSlug(slug);
      return {
        url: `${BASE_URL}/affirmation-app/a/${slug}`,
        ...(languages ? { alternates: { languages } } : {}),
      };
    },
  );

  const esAffirmationEntries: MetadataRoute.Sitemap = allEsAffirmationSlugs().map(
    (slug) => {
      const triple = AFFIRMATION_HREFLANG_TRIPLES.find((t) => t.es === slug);
      const languages = triple ? alternatesFor(triple) : undefined;
      return {
        url: `${BASE_URL}/affirmation-app/es/a/${slug}`,
        ...(languages ? { alternates: { languages } } : {}),
      };
    },
  );

  const kokoroTypeEntries: MetadataRoute.Sitemap = allKokoroTypeIds().map((type) => ({
    url: `${BASE_URL}/affirmation-app/ja/shindan/${type}`,
  }));

  void esAffirmationEntries;
  void kokoroTypeEntries;

  const all = [
    ...staticEntries,
    ...jaAffirmationEntries,
    ...enAffirmationEntries,

    ...lmGuideEntries,
    ...blogEntries,
    ...businessHubEntries,
    ...["/affirmation-app-faq/","/thankful-faq/","/honne-faq/","/guides/","/guides/best-free-affirmation-app-iphone/","/guides/affirmation-reminder-app/","/guides/simple-gratitude-journal-app/","/guides/gratitude-journal-prompts/","/guides/what-does-this-text-mean-app/","/guides/ai-reply-suggestions-text/","/guides/compare/affirmation-apps/","/guides/compare/gratitude-journal-apps/","/guides/compare/text-message-interpreter-apps/"].map((p)=>({url:`${BASE_URL}${p}`})),
  ];

  // Deduplicate by URL (defensive).
  const seen = new Set<string>();
  return all.filter((entry) => {
    if (seen.has(entry.url)) return false;
    seen.add(entry.url);
    return true;
  });
}
