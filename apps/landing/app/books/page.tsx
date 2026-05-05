/* eslint-disable react/no-unescaped-entities */
import Link from 'next/link';
import Image from 'next/image';

export const metadata = {
  title: 'Anicca Books — ebooks library',
  description:
    'Anicca Books — Buddhist short reads. Free downloads in PDF, HTML and Markdown. EN + JP.',
};

interface BookEntry {
  slug: string;
  title: string;
  language: 'EN' | 'JP';
  description: string;
  cover: string;
  pdf: string;
  html: string;
  md: string;
}

const BOOKS: BookEntry[] = [
  {
    slug: 'anicca-reset-en',
    title: 'Anicca Reset',
    language: 'EN',
    description:
      'A short reset for the over-stimulated mind. Twelve impermanence prompts you can read in fifteen minutes.',
    cover: '/ebooks/cover-en.jpg',
    pdf: '/ebooks/anicca-reset-en.pdf',
    html: '/ebooks/anicca-reset-en.html',
    md: '/ebooks/anicca-reset-en.md',
  },
  {
    slug: 'anicca-reset-jp',
    title: 'Anicca リセット',
    language: 'JP',
    description:
      '過剰な刺激を受けた心のための、ごく短いリセット。15 分で読み切れる無常 12 章。',
    cover: '/ebooks/cover-jp.jpg',
    pdf: '/ebooks/anicca-reset-jp.pdf',
    html: '/ebooks/anicca-reset-jp.html',
    md: '/ebooks/anicca-reset-jp.md',
  },
];

export default function BooksPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-20 text-foreground">
      <p className="mb-6 text-sm">
        <Link href="/en" className="text-muted-foreground underline transition-colors hover:text-foreground">
          ← Back to Anicca Empire
        </Link>
      </p>

      <h1 className="text-4xl font-bold md:text-5xl">📚 Anicca Books</h1>
      <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
        Buddhist short reads. Free downloads in PDF, HTML, and Markdown.
        New titles ship as Anicca writes them.
      </p>

      <section className="mt-12 grid gap-8 md:grid-cols-2">
        {BOOKS.map((b) => (
          <article
            key={b.slug}
            className="flex flex-col rounded-xl border border-border bg-background p-6 transition-colors hover:border-foreground"
          >
            <div className="relative mb-6 aspect-[3/4] w-full overflow-hidden rounded-lg bg-muted">
              <Image
                src={b.cover}
                alt={`${b.title} cover`}
                fill
                sizes="(max-width: 768px) 100vw, 33vw"
                className="object-cover"
                priority
              />
            </div>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-2xl font-semibold">{b.title}</h2>
              <span className="rounded-full border border-border px-3 py-1 text-xs uppercase tracking-widest text-muted-foreground">
                {b.language}
              </span>
            </div>
            <p className="mb-6 text-sm leading-relaxed text-muted-foreground">{b.description}</p>
            <div className="mt-auto flex flex-wrap gap-3">
              <a
                href={b.pdf}
                className="rounded-lg bg-foreground px-4 py-2 text-sm font-semibold text-background transition-opacity hover:opacity-90"
                download
              >
                PDF
              </a>
              <a
                href={b.html}
                className="rounded-lg border border-border px-4 py-2 text-sm font-semibold transition-colors hover:border-foreground"
                target="_blank"
                rel="noopener noreferrer"
              >
                Read online
              </a>
              <a
                href={b.md}
                className="rounded-lg border border-border px-4 py-2 text-sm font-semibold transition-colors hover:border-foreground"
                target="_blank"
                rel="noopener noreferrer"
              >
                Markdown
              </a>
            </div>
          </article>
        ))}
      </section>

      <section className="mt-16 rounded-xl border border-border bg-background px-6 py-6 text-sm leading-relaxed text-muted-foreground">
        <p>
          Books are free. Anicca is open source, self-funding, and impermanent.
          If a title helps you, the most generous response is to share it with
          someone whose week is harder than yours.
        </p>
      </section>

      <footer className="mt-12 border-t border-border pt-8 text-xs text-muted-foreground">
        Live numbers:{' '}
        <Link href="/en" className="underline transition-colors hover:text-foreground">
          aniccaai.com
        </Link>{' '}
        · github.com/Daisuke134/anicca
      </footer>
    </main>
  );
}
