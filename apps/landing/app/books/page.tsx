/* eslint-disable react/no-unescaped-entities */
import Link from 'next/link';

export const metadata = {
  title: 'Anicca Books — ebooks library',
  description:
    'Anicca Books — Buddhist short reads. Lead magnet + paid editions. EN + JP.',
};

interface BookEntry {
  slug: string;
  title: string;
  language: 'EN' | 'JP';
  description: string;
  coverHref: string;
  primaryHref: string;
  primaryLabel: string;
  pdfHref?: string;
}

const BOOKS: BookEntry[] = [
  {
    slug: 'anicca-reset-en',
    title: 'Anicca Reset',
    language: 'EN',
    description:
      'A short reset for the over-stimulated mind. Lead magnet + paid edition. Read on the dedicated page.',
    coverHref: '/ebooks/cover-en.jpg',
    primaryHref: '/monk',
    primaryLabel: 'Open page →',
    pdfHref: '/ebooks/anicca-reset-en.pdf',
  },
  {
    slug: 'anicca-reset-jp',
    title: 'アニッチャ・リセット',
    language: 'JP',
    description:
      '過剰な刺激を受けた心のための、ごく短いリセット。リードマグネット + 有料版。専用ページで読む。',
    coverHref: '/ebooks/cover-jp.jpg',
    primaryHref: '/achan',
    primaryLabel: 'ページを開く →',
    pdfHref: '/ebooks/anicca-reset-jp.pdf',
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
        Buddhist short reads. Each book has its own page — read it there.
        New titles ship as Anicca writes them.
      </p>

      <section className="mt-12 grid gap-8 md:grid-cols-2">
        {BOOKS.map((b) => (
          <article
            key={b.slug}
            className="flex flex-col rounded-xl border border-border bg-background p-6 transition-colors hover:border-foreground"
          >
            <Link
              href={b.primaryHref}
              className="relative mb-6 block aspect-[3/4] w-full overflow-hidden rounded-lg bg-muted"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={b.coverHref}
                alt={`${b.title} cover`}
                className="absolute inset-0 h-full w-full object-cover"
              />
            </Link>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-2xl font-semibold">
                <Link href={b.primaryHref} className="hover:underline">
                  {b.title}
                </Link>
              </h2>
              <span className="rounded-full border border-border px-3 py-1 text-xs uppercase tracking-widest text-muted-foreground">
                {b.language}
              </span>
            </div>
            <p className="mb-6 text-sm leading-relaxed text-muted-foreground">{b.description}</p>
            <div className="mt-auto flex flex-wrap gap-3">
              <Link
                href={b.primaryHref}
                className="rounded-lg bg-foreground px-4 py-2 text-sm font-semibold text-background transition-opacity hover:opacity-90"
              >
                {b.primaryLabel}
              </Link>
              {b.pdfHref && (
                <a
                  href={b.pdfHref}
                  className="rounded-lg border border-border px-4 py-2 text-sm font-semibold transition-colors hover:border-foreground"
                  download
                >
                  PDF
                </a>
              )}
            </div>
          </article>
        ))}
      </section>

      <section className="mt-16 rounded-xl border border-border bg-background px-6 py-6 text-sm leading-relaxed text-muted-foreground">
        <p>
          Anicca Reset has both an English page (
          <Link href="/monk" className="underline hover:text-foreground">/monk</Link>
          ) and a Japanese page (
          <Link href="/achan" className="underline hover:text-foreground">/achan</Link>
          ). Each one carries the full reading experience — lead magnet, paid
          edition, and the offline files.
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
