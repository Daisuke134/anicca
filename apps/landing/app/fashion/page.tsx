/* eslint-disable react/no-unescaped-entities */
import Link from 'next/link';
import Image from 'next/image';

export const metadata = {
  title: 'Anicca Fashion — wear the truth',
  description:
    'Anicca Fashion — print-on-demand garments that say what the brand believes. Buddhist plain truth in cotton.',
};

interface FashionItem {
  slug: string;
  title: string;
  tagline: string;
  price_usd: number;
  status: 'live' | 'coming-soon' | 'concept';
  image_path: string;
  image_alt: string;
  details: string;
  buy_url?: string;
}

const ITEMS: FashionItem[] = [
  {
    slug: 'tee-black',
    title: 'Anicca Logo Tee — Black',
    tagline: 'Anicca app icon · 100% cotton',
    price_usd: 30,
    status: 'live',
    image_path: '/fashion/tee-black.jpg',
    image_alt: 'Black tee with Anicca app icon on chest',
    details:
      'Bella + Canvas 3001 black, sizes XS–XXL. Anicca app icon centered on the chest. Print-on-demand worldwide shipping in 7–12 days.',
    buy_url: 'https://buy.stripe.com/5kQ14n4tU6tgc1qcEC28803',
  },
  {
    slug: 'hoodie-black',
    title: 'Sabbe Sankhara — Hoodie',
    tagline: 'Pali first line of the Anicca sutta',
    price_usd: 50,
    status: 'live',
    image_path: '/fashion/hoodie-black.jpg',
    image_alt: 'Black hoodie with Pali script on left chest',
    details:
      'Heavyweight black pullover. "sabbe sankhāra dukkhā" embroidered on left chest in Pali. For the days you need to remember why everything feels heavy.',
    buy_url: 'https://buy.stripe.com/7sYbJ11hIaJw6H6bAy28804',
  },
  {
    slug: 'cap-black',
    title: 'Impermanence Cap',
    tagline: 'low-profile · subtle',
    price_usd: 25,
    status: 'live',
    image_path: '/fashion/cap-black.jpg',
    image_alt: 'Black low-profile cap with embroidered "anicca" wordmark',
    details:
      'Low-profile dad cap. "anicca" embroidered in lowercase on the front. For people who want the reminder without the announcement.',
    buy_url: 'https://buy.stripe.com/bJe00je4ueZMfdCbAy28805',
  },
];

const STATUS_LABELS: Record<FashionItem['status'], string> = {
  live: 'Buy now',
  'coming-soon': 'Coming soon',
  concept: 'Concept',
};

export default function FashionListPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-20 text-foreground">
      <p className="mb-6 text-sm">
        <Link href="/en" className="text-muted-foreground underline transition-colors hover:text-foreground">
          ← Back to Anicca Empire
        </Link>
      </p>

      <h1 className="text-4xl font-bold md:text-5xl">👕 Anicca Fashion</h1>
      <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
        Buddhist plain truth in cotton. Print-on-demand. Worn as a daily reminder.
      </p>

      <section className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {ITEMS.map((it) => (
          <article
            key={it.slug}
            className="flex flex-col rounded-xl border border-border bg-background p-6 transition-colors hover:border-foreground"
          >
            <div className="relative mb-5 aspect-square w-full overflow-hidden rounded-lg bg-muted">
              <Image
                src={it.image_path}
                alt={it.image_alt}
                fill
                sizes="(max-width: 768px) 100vw, 33vw"
                className="object-cover"
              />
            </div>
            <h2 className="text-xl font-semibold">{it.title}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{it.tagline}</p>
            <div className="mt-3 flex items-center justify-between">
              <span className="font-mono text-lg font-semibold">${it.price_usd}</span>
              <span className="rounded-full border border-border px-3 py-1 text-xs uppercase tracking-widest text-muted-foreground">
                {STATUS_LABELS[it.status]}
              </span>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{it.details}</p>
            <div className="mt-6">
              {it.status === 'live' && it.buy_url ? (
                <a
                  href={it.buy_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block w-full rounded-lg bg-foreground px-4 py-3 text-center text-sm font-semibold text-background transition-opacity hover:opacity-90"
                >
                  Buy ${it.price_usd}
                </a>
              ) : (
                <button
                  type="button"
                  disabled
                  className="inline-block w-full cursor-not-allowed rounded-lg border border-border px-4 py-3 text-center text-sm font-semibold text-muted-foreground"
                >
                  {STATUS_LABELS[it.status]}
                </button>
              )}
            </div>
          </article>
        ))}
      </section>

      <section className="mt-16 grid gap-8 md:grid-cols-2">
        <div className="rounded-xl border border-border p-6">
          <h2 className="text-xl font-semibold">Why on cotton</h2>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            Affirmation apps remind you when you tap them. A shirt reminds you
            when you put it on. The brain doesn't separate "I am wearing this
            idea" from "I believe this idea." That's the entire point.
          </p>
        </div>
        <div className="rounded-xl border border-border p-6">
          <h2 className="text-xl font-semibold">How it ships</h2>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            Each order triggers a Printful print run. Zero warehouse. Worldwide
            shipping in 7–12 days. 100% of profit is reported live on the
            empire dashboard.
          </p>
        </div>
      </section>

      <footer className="mt-16 border-t border-border pt-8 text-xs text-muted-foreground">
        Live numbers:{' '}
        <Link href="/en" className="underline transition-colors hover:text-foreground">
          aniccaai.com
        </Link>{' '}
        · github.com/Daisuke134/anicca
      </footer>
    </main>
  );
}
