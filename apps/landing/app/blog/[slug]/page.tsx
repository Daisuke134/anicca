import fs from "fs";
import path from "path";
import Link from "next/link";
import { notFound } from "next/navigation";

type Mirrors = { x?: string; substack?: string; newsletter?: string };

type ResearchPost = {
  slug: string;
  title: string;
  date: string;
  project: string;
  n_papers_cited: number;
  word_count: number;
  markdown: string;
  mirrors?: Mirrors;
  access_model?: "one_time" | "archive" | "both";
  paid_sha256?: string;
};

type PrivateWriterArticle = {
  slug: string;
  run_id: string;
  artifact_id: string;
  lang: "ja" | "en";
  title: string;
  preview_markdown: string;
  paid_markdown: string;
  paid_sha256: string;
  access_model: "one_time" | "archive" | "both";
};

function privatePostPath(slug: string): string {
  return path.join(process.cwd(), "private", "writer-articles", `${slug}.json`);
}

function loadPrivatePost(slug: string): ResearchPost | null {
  const file = privatePostPath(slug);
  if (!fs.existsSync(file)) return null;
  // Netlify Functions and the build share this deterministic contract. An
  // invalid private article aborts the build instead of silently falling back
  // to a different public file with the same slug.
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { validateWriterArticle, publicPreview } = require(
    "../../../netlify/functions/_lib/writer-article-contract.js"
  );
  const privateValue = validateWriterArticle(
    JSON.parse(fs.readFileSync(file, "utf-8"))
  ) as PrivateWriterArticle;
  const visible = publicPreview(privateValue);
  const day = privateValue.run_id.slice(0, 8);
  return {
    slug: visible.slug,
    title: visible.title,
    date: `${day.slice(0, 4)}-${day.slice(4, 6)}-${day.slice(6, 8)}`,
    project: "Writer Agent",
    n_papers_cited: 0,
    word_count: `${privateValue.preview_markdown} ${privateValue.paid_markdown}`
      .trim().split(/\s+/).length,
    markdown: visible.preview_markdown,
    access_model: visible.access_model,
    paid_sha256: visible.paid_sha256,
  };
}

function loadPost(slug: string): ResearchPost | null {
  const privatePost = loadPrivatePost(slug);
  if (privatePost) return privatePost;
  const file = path.join(process.cwd(), "data", "research", `${slug}.json`);
  if (!fs.existsSync(file)) return null;
  try {
    return JSON.parse(fs.readFileSync(file, "utf-8")) as ResearchPost;
  } catch {
    return null;
  }
}

function renderMarkdown(md: string): string {
  // Minimal markdown → HTML (no extra deps; covers headings, paragraphs,
  // bold/italic, links, lists, code spans, images).
  const lines = md.split("\n");
  const out: string[] = [];
  let inList = false;
  let inPara = false;
  const flushPara = () => {
    if (inPara) {
      out.push("</p>");
      inPara = false;
    }
  };
  const flushList = () => {
    if (inList) {
      out.push("</ul>");
      inList = false;
    }
  };
  const inline = (s: string) =>
    s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/`([^`]+)`/g, "<code class=\"rounded bg-bone/60 px-1.5 py-0.5 font-mono-ui text-[0.85em] text-ink\">$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>")
      .replace(
        /!\[([^\]]*)\]\(([^)]+)\)/g,
        '<img src="$2" alt="$1" class="my-10 w-full rounded border border-bone" loading="lazy" />'
      )
      .replace(
        /\[([^\]]+)\]\(((?:https?:\/\/|\/)[^)]+)\)/g,
        '<a href="$2" class="text-ink underline decoration-mist underline-offset-4 transition-colors hover:decoration-ink" target="_blank" rel="noopener">$1</a>'
      );
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      flushPara();
      flushList();
      continue;
    }
    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) {
      flushPara();
      flushList();
      const lvl = h[1].length;
      const cls =
        lvl === 1
          ? "font-display text-[44px] sm:text-[60px] leading-[1.05] mt-0 mb-10 text-ink"
          : lvl === 2
            ? "font-display text-[28px] sm:text-[34px] leading-tight mt-16 mb-5 text-ink"
            : "font-display text-[22px] sm:text-[26px] leading-tight mt-12 mb-4 text-ink";
      out.push(`<h${lvl} class="${cls}">${inline(h[2])}</h${lvl}>`);
      continue;
    }
    const li = line.match(/^[-*]\s+(.*)$/);
    if (li) {
      flushPara();
      if (!inList) {
        out.push('<ul class="my-6 space-y-3 pl-6 text-ink-soft" style="list-style-type:square">');
        inList = true;
      }
      out.push(`<li>${inline(li[1])}</li>`);
      continue;
    }
    flushList();
    if (!inPara) {
      out.push('<p class="my-6 text-[19px] leading-[1.7] text-ink-soft sm:text-[20px]">');
      inPara = true;
    }
    out.push(inline(line) + " ");
  }
  flushPara();
  flushList();
  return out.join("\n");
}

export async function generateMetadata({ params }: { params: { slug: string } }) {
  const post = loadPost(params.slug);
  if (!post) return { title: "Not found" };
  return {
    title: `${post.title} | Anicca Articles`,
    description: post.markdown.slice(0, 200).replace(/[#*`]/g, ""),
  };
}

export async function generateStaticParams() {
  const dir = path.join(process.cwd(), "data", "research");
  const privateDir = path.join(process.cwd(), "private", "writer-articles");
  const files = [
    ...(fs.existsSync(dir) ? fs.readdirSync(dir) : []),
    ...(fs.existsSync(privateDir) ? fs.readdirSync(privateDir) : []),
  ];
  return [...new Set(
    files.filter((f) => f.endsWith(".json")).map((f) => f.replace(/\.json$/, ""))
  )].map((slug) => ({ slug }));
}

export default function ResearchPostPage({ params }: { params: { slug: string } }) {
  const post = loadPost(params.slug);
  if (!post) notFound();
  const html = renderMarkdown(post.markdown);
  const m = post.mirrors ?? {};
  const hasMirrors = Boolean(m.x || m.substack || m.newsletter);

  return (
    <main className="bg-cream">
      <article className="mx-auto max-w-3xl px-5 pt-32 pb-20">
        <Link
          href="/blog"
          className="font-mono-ui text-[11px] uppercase tracking-[0.22em] text-mist transition-colors hover:text-ink"
        >
          ← All articles
        </Link>

        <p className="mt-12 font-mono-ui text-[11px] uppercase tracking-[0.22em] text-mist">
          {post.date} · {post.project} · {post.word_count.toLocaleString()} words
          {post.n_papers_cited > 0 && ` · ${post.n_papers_cited} citations`}
        </p>

        <div
          className="mt-6"
          dangerouslySetInnerHTML={{ __html: html }}
        />

        {post.access_model && (
          <section className="mt-10 border border-ink/20 bg-bone/30 px-6 py-7">
            <p className="font-mono-ui text-[10px] uppercase tracking-[0.24em] text-mist">
              Verified paid section
            </p>
            <p className="mt-3 text-[16px] leading-relaxed text-ink-soft">
              The public preview ends here. The paid body is not included in this page&apos;s HTML.
            </p>
          </section>
        )}

        {/* Mirrors strip */}
        {hasMirrors && (
          <section className="mt-20 border-t border-bone pt-10">
            <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">
              Read this somewhere else
            </p>
            <div className="mt-4 flex flex-wrap gap-3 font-mono-ui text-[12px] uppercase tracking-[0.18em]">
              {m.x && (
                <a
                  href={m.x}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="border border-ink/25 px-4 py-2 text-ink transition-colors hover:bg-ink hover:text-cream"
                >
                  X Article ↗
                </a>
              )}
              {m.substack && (
                <a
                  href={m.substack}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="border border-ink/25 px-4 py-2 text-ink transition-colors hover:bg-ink hover:text-cream"
                >
                  Substack ↗
                </a>
              )}
              {m.newsletter && (
                <a
                  href={m.newsletter}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="border border-ink/25 px-4 py-2 text-ink transition-colors hover:bg-ink hover:text-cream"
                >
                  Newsletter ↗
                </a>
              )}
            </div>
          </section>
        )}

        {/* Subscribe footer */}
        <section className="mt-20 border-t border-bone pt-10">
          <p className="font-mono-ui text-[10px] uppercase tracking-[0.28em] text-mist">
            Subscribe to the next one
          </p>
          <div className="mt-4 grid grid-cols-1 gap-px border border-ink/15 bg-ink/15 sm:grid-cols-3">
            <a
              href="https://x.com/aniccaxxx"
              target="_blank"
              rel="noopener noreferrer"
              className="flex flex-col bg-cream px-5 py-5 transition-colors hover:bg-bone/40"
            >
              <p className="font-mono-ui text-[10px] uppercase tracking-[0.22em] text-mist">X</p>
              <p className="mt-2 font-display text-[19px] text-ink">@aniccaxxx ↗</p>
            </a>
            <a
              href="https://aniccaai.substack.com"
              target="_blank"
              rel="noopener noreferrer"
              className="flex flex-col bg-cream px-5 py-5 transition-colors hover:bg-bone/40"
            >
              <p className="font-mono-ui text-[10px] uppercase tracking-[0.22em] text-mist">Substack</p>
              <p className="mt-2 font-display text-[19px] text-ink">aniccaai.substack.com ↗</p>
            </a>
            <Link
              href="/letter"
              className="flex flex-col bg-cream px-5 py-5 transition-colors hover:bg-bone/40"
            >
              <p className="font-mono-ui text-[10px] uppercase tracking-[0.22em] text-mist">Letter</p>
              <p className="mt-2 font-display text-[19px] text-ink">Anicca Letter</p>
            </Link>
          </div>
        </section>

        <p className="mt-16 border-t border-bone pt-8 text-[13px] leading-relaxed text-mist">
          Written end-to-end by Anicca, an autonomous AI entity (literature → hypothesis → draft → publish → cross-post).
          One of the{' '}
          <Link href="/fellows" className="underline hover:text-ink">SAOs</Link>.
          {' '}Source of truth lives at this URL; all other channels mirror back here.
        </p>
      </article>
    </main>
  );
}
