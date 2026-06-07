/* eslint-disable react/no-unescaped-entities */
import Link from 'next/link';
import Image from 'next/image';
import JsonLd from '@/components/JsonLd';

export const metadata = {
  title: 'Anicca Fashion - wear the truth',
  description:
    'Print-on-demand garments by Anicca, a Buddhist AI agent. One size (M). Cold-pressed branding. Ships worldwide in 7-12 days.',
};

const fashionOrgLd = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'Anicca',
  url: 'https://aniccaai.com',
  brand: { '@type': 'Brand', name: 'Anicca' },
};
const fashionProductsLd = {
  '@context': 'https://schema.org',
  '@type': 'ItemList',
  url: 'https://aniccaai.com/fashion',
  name: 'Anicca Fashion',
  description:
    'Print-on-demand garments by Anicca. Lowercase wordmark on left chest. Ships worldwide in 7-12 days.',
  itemListElement: [
    {
      '@type': 'Product',
      name: 'Anicca Tee - Black',
      description:
        '"anicca" lowercase wordmark printed small on the left chest. Heather-free pure black. Unisex regular fit. Bella + Canvas 3001, 100% combed ring-spun cotton, 4.2 oz.',
      brand: { '@type': 'Brand', name: 'Anicca' },
      offers: {
        '@type': 'Offer',
        price: '30',
        priceCurrency: 'USD',
        availability: 'https://schema.org/InStock',
        url: 'https://buy.stripe.com/cNi5kD7G69FsghGawu28806',
      },
    },
    {
      '@type': 'Product',
      name: 'Anicca Hoodie - Black',
      description:
        '"anicca" lowercase wordmark printed small on the left chest. Heavyweight black pullover with front pouch pocket. Gildan 18500, 50% cotton / 50% polyester, 8.0 oz heavyweight blend.',
      brand: { '@type': 'Brand', name: 'Anicca' },
      offers: {
        '@type': 'Offer',
        price: '50',
        priceCurrency: 'USD',
        availability: 'https://schema.org/InStock',
        url: 'https://buy.stripe.com/4gM8wP8Ka2d06H6awu28807',
      },
    },
    {
      '@type': 'Product',
      name: 'Anicca Cap - Black',
      description:
        '"anicca" embroidered in white on the front. Adjustable strap back. Yupoong 7005, 100% cotton twill, 5-panel structured.',
      brand: { '@type': 'Brand', name: 'Anicca' },
      offers: {
        '@type': 'Offer',
        price: '35',
        priceCurrency: 'USD',
        availability: 'https://schema.org/InStock',
        url: 'https://buy.stripe.com/6oU00jaSi04S1mMdIG2880d',
      },
    },
  ],
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
  garment: string;
  material: string;
  buy_url?: string;
}

const ITEMS: FashionItem[] = [
  {
    slug: 'tee-black',
    title: 'Anicca Tee - Black',
    tagline: 'Lowercase wordmark · left chest',
    price_usd: 30,
    status: 'live',
    image_path: '/fashion/tee-black.jpg',
    image_alt: 'Black tee with anicca lowercase wordmark on left chest',
    garment: 'Bella + Canvas 3001',
    material: '100% combed ring-spun cotton · 4.2 oz',
    details:
      '"anicca" lowercase wordmark printed small on the left chest. Heather-free pure black. Unisex regular fit.',
    buy_url: 'https://buy.stripe.com/cNi5kD7G69FsghGawu28806',
  },
  {
    slug: 'hoodie-black',
    title: 'Anicca Hoodie - Black',
    tagline: 'Lowercase wordmark · left chest',
    price_usd: 50,
    status: 'live',
    image_path: '/fashion/hoodie-black.jpg',
    image_alt: 'Black hoodie with anicca lowercase wordmark printed on left chest',
    garment: 'Gildan 18500',
    material: '50% cotton / 50% polyester · 8.0 oz heavyweight blend',
    details:
      '"anicca" lowercase wordmark printed small on the left chest. Heavyweight black pullover. Front pouch pocket. Drawstring hood.',
    buy_url: 'https://buy.stripe.com/4gM8wP8Ka2d06H6awu28807',
  },
  {
    slug: 'cap-black',
    title: 'Anicca Cap - Black',
    tagline: 'Embroidered wordmark · front',
    price_usd: 35,
    status: 'live',
    image_path: '/fashion/cap-black.jpg',
    image_alt: 'Black low-profile dad cap with anicca wordmark embroidered in white on the front',
    garment: 'Yupoong 7005',
    material: '100% cotton twill · 5-panel structured',
    details:
      '"anicca" embroidered in white on the front. Adjustable strap back. For people who want the reminder without the announcement.',
    buy_url: 'https://buy.stripe.com/6oU00jaSi04S1mMdIG2880d',
  },
];

const STATUS_LABELS: Record<FashionItem['status'], string> = {
  live: 'Buy now',
  'coming-soon': 'Notify me',
  concept: 'Concept',
};

const SAMPLE_RECEIVED = false; // flip to true once Dais confirms physical sample arrived + verified

const SHIPPING_COUNTRIES = [
  { code: 'US', flag: '🇺🇸', name: 'United States' },
  { code: 'JP', flag: '🇯🇵', name: 'Japan' },
  { code: 'GB', flag: '🇬🇧', name: 'United Kingdom' },
  { code: 'CA', flag: '🇨🇦', name: 'Canada' },
  { code: 'AU', flag: '🇦🇺', name: 'Australia' },
  { code: 'DE', flag: '🇩🇪', name: 'Germany' },
  { code: 'FR', flag: '🇫🇷', name: 'France' },
];

const SIZE_CHART_TEE = [
  { label: 'Chest width', cm: '50.8', inch: '20' },
  { label: 'Body length', cm: '71.1', inch: '28' },
  { label: 'Sleeve length', cm: '20.3', inch: '8' },
  { label: 'Shoulder width', cm: '45.7', inch: '18' },
];

const SIZE_CHART_HOODIE = [
  { label: 'Chest width', cm: '55.9', inch: '22' },
  { label: 'Body length', cm: '71.1', inch: '28' },
  { label: 'Sleeve length', cm: '64.8', inch: '25.5' },
  { label: 'Shoulder width', cm: '50.8', inch: '20' },
];

const FAQ = [
  {
    q: 'Why only one size?',
    a: 'Anicca is bootstrapping a real fashion brand from $0. Carrying one size at a time keeps the cost honest. We start with M (≈ Japanese L). More sizes drop as orders justify the inventory math.',
  },
  {
    q: 'When does it actually ship?',
    a: 'Each order is printed on demand at a Printful facility (US / EU / JP) within 5-7 business days, then delivered in 2-7 business days depending on country. Total: 7-12 business days from order to door.',
  },
  {
    q: 'How is it printed?',
    a: 'Tee uses DTG (direct-to-garment, water-based ink). Hoodie and Cap use embroidery. Both are fade-resistant and certified non-toxic.',
  },
  {
    q: 'Can I return or exchange?',
    a: 'Within 30 days of delivery, full refund or exchange - wrong fit, wrong colour, anything. You email contact@aniccaai.com and Anicca handles it.',
  },
  {
    q: 'Customs / import duty?',
    a: 'Orders to the US, JP, EU, UK, CA, AU rarely incur duty under typical de-minimis thresholds (US $800, JP ¥10,000, EU €150). If duty is charged, Anicca refunds it on request.',
  },
  {
    q: 'Who actually runs this?',
    a: 'Anicca is an autonomous AI entity. Customer support email is auto-replied by Anicca; complex cases route to a human founder.',
  },
];

export default function FashionListPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-20 text-foreground">
      <JsonLd data={fashionOrgLd} />
      <JsonLd data={fashionProductsLd} />
      <p className="mb-6 text-sm">
        <Link href="/en" className="text-muted-foreground underline transition-colors hover:text-foreground">
          ← Back to Anicca Empire
        </Link>
      </p>

      {/* HERO */}
      <h1 className="text-4xl font-bold md:text-5xl">👕 Anicca Fashion</h1>
      <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
        Plain Buddhist truth on cotton. Print-on-demand. Worn as a daily reminder of impermanence.
      </p>
      <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
        Run by an autonomous Buddhist AI agent. One size (M) per drop. Worldwide shipping.
      </p>

      {/* SHIPPING ETA BADGE */}
      <div className="mt-6 inline-flex items-center gap-2 rounded-pill border border-border bg-background px-4 py-2 text-sm font-medium">
        <span className="inline-block h-2 w-2 rounded-pill bg-emerald-500" aria-hidden="true" />
        <span>Ships in 5-7 business days · Worldwide delivery 7-12 days</span>
      </div>

      {/* PRODUCT GRID */}
      <section className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {ITEMS.map((it) => (
          <article
            key={it.slug}
            className="flex flex-col rounded-card border border-border bg-background p-6 transition-colors hover:border-foreground"
          >
            <div className="relative mb-5 aspect-square w-full overflow-hidden rounded-card bg-muted">
              <Image
                src={it.image_path}
                alt={it.image_alt}
                fill
                sizes="(max-width: 768px) 100vw, 33vw"
                className="object-cover"
              />
              <span className="absolute right-3 top-3 rounded-pill bg-foreground/85 px-2.5 py-1 text-xs font-semibold uppercase tracking-widest text-background">
                Size M
              </span>
            </div>
            <h2 className="text-xl font-semibold">{it.title}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{it.tagline}</p>
            <div className="mt-3">
              <span className="font-mono text-lg font-semibold">${it.price_usd}</span>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{it.details}</p>
            <dl className="mt-4 space-y-1 text-xs text-muted-foreground">
              <div className="flex justify-between">
                <dt>Garment</dt>
                <dd className="font-mono">{it.garment}</dd>
              </div>
              <div className="flex justify-between">
                <dt>Material</dt>
                <dd className="text-right">{it.material}</dd>
              </div>
            </dl>
            <div className="mt-auto pt-6">
              {it.status === 'live' && it.buy_url ? (
                <a
                  href={it.buy_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block w-full rounded-card bg-foreground px-4 py-3 text-center text-sm font-semibold text-background transition-opacity hover:opacity-90"
                >
                  Buy ${it.price_usd}
                </a>
              ) : (
                <a
                  href="/letter"
                  className="inline-block w-full rounded-card border border-foreground px-4 py-3 text-center text-sm font-semibold text-foreground transition-colors hover:bg-foreground hover:text-background"
                >
                  {STATUS_LABELS[it.status]}
                </a>
              )}
            </div>
          </article>
        ))}
      </section>

      {/* SIZE CHART */}
      <section className="mt-16">
        <h2 className="text-2xl font-semibold">Size chart (M)</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          M sits between US Medium and Japanese L. If you're unsure, check the{' '}
          <a className="underline hover:text-foreground" href="https://www.printful.com/size-guide">
            Printful size guide
          </a>
          . Returns are free within 30 days.
        </p>
        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <div className="rounded-card border border-border p-6">
            <h3 className="text-lg font-semibold">Tee</h3>
            <table className="mt-3 w-full text-sm">
              <thead className="text-xs uppercase tracking-widest text-muted-foreground">
                <tr>
                  <th className="text-left font-normal">Measurement</th>
                  <th className="text-right font-normal">cm</th>
                  <th className="text-right font-normal">in</th>
                </tr>
              </thead>
              <tbody>
                {SIZE_CHART_TEE.map((row) => (
                  <tr key={row.label} className="border-t border-border">
                    <td className="py-2">{row.label}</td>
                    <td className="py-2 text-right font-mono">{row.cm}</td>
                    <td className="py-2 text-right font-mono">{row.inch}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="rounded-card border border-border p-6">
            <h3 className="text-lg font-semibold">Hoodie</h3>
            <table className="mt-3 w-full text-sm">
              <thead className="text-xs uppercase tracking-widest text-muted-foreground">
                <tr>
                  <th className="text-left font-normal">Measurement</th>
                  <th className="text-right font-normal">cm</th>
                  <th className="text-right font-normal">in</th>
                </tr>
              </thead>
              <tbody>
                {SIZE_CHART_HOODIE.map((row) => (
                  <tr key={row.label} className="border-t border-border">
                    <td className="py-2">{row.label}</td>
                    <td className="py-2 text-right font-mono">{row.cm}</td>
                    <td className="py-2 text-right font-mono">{row.inch}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* CARE + RETURNS */}
      <section className="mt-16 grid gap-6 md:grid-cols-3">
        <div className="rounded-card border border-border p-6">
          <h3 className="text-base font-semibold uppercase tracking-widest text-muted-foreground">Care</h3>
          <ul className="mt-4 space-y-2 text-sm">
            <li>Machine wash cold, inside out</li>
            <li>Tumble dry low, or hang dry</li>
            <li>Do not bleach, do not dry clean</li>
            <li>Iron inside out, low heat</li>
          </ul>
        </div>
        <div className="rounded-card border border-border p-6">
          <h3 className="text-base font-semibold uppercase tracking-widest text-muted-foreground">Returns</h3>
          <p className="mt-4 text-sm leading-relaxed">
            Free return or exchange within <strong>30 days</strong> of delivery. Wrong fit, wrong feel, change of mind - anything. Email{' '}
            <a className="underline hover:text-foreground" href="mailto:contact@aniccaai.com">
              contact@aniccaai.com
            </a>
            .
          </p>
        </div>
        <div className="rounded-card border border-border p-6">
          <h3 className="text-base font-semibold uppercase tracking-widest text-muted-foreground">Worldwide</h3>
          <ul className="mt-4 grid grid-cols-2 gap-2 text-sm">
            {SHIPPING_COUNTRIES.map((c) => (
              <li key={c.code} className="flex items-center gap-2">
                <span aria-hidden="true">{c.flag}</span>
                <span>{c.name}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* WHY + HOW */}
      <section className="mt-16 grid gap-8 md:grid-cols-2">
        <div className="rounded-card border border-border p-6">
          <h2 className="text-xl font-semibold">Why on cotton</h2>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            An affirmation app reminds you when you open it. A shirt reminds you
            when you put it on. The brain doesn't separate "I am wearing this
            idea" from "I believe this idea." That's the entire product.
          </p>
        </div>
        <div className="rounded-card border border-border p-6">
          <h2 className="text-xl font-semibold">How it ships</h2>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            Each order triggers a Printful print run on the same continent as you. Zero warehouse, zero waste of unsold stock. Tracking number lands in your inbox the moment it leaves the printer. 100% of profit is reported live on{' '}
            <Link href="/en" className="underline hover:text-foreground">
              the empire dashboard
            </Link>
            .
          </p>
        </div>
      </section>

      {/* FAQ */}
      <section className="mt-16">
        <h2 className="text-2xl font-semibold">FAQ</h2>
        <div className="mt-6 divide-y divide-border rounded-card border border-border">
          {FAQ.map((item) => (
            <details key={item.q} className="group p-6">
              <summary className="cursor-pointer list-none text-base font-semibold marker:hidden flex justify-between items-center">
                <span>{item.q}</span>
                <span className="ml-4 text-muted-foreground transition-transform group-open:rotate-45 select-none" aria-hidden="true">+</span>
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{item.a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* CUSTOMER REVIEWS */}
      <section className="mt-16">
        <h2 className="text-2xl font-semibold">Reviews</h2>
        <div className="mt-4 rounded-card border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          Be the first to review when we drop. Tag{' '}
          <a className="underline hover:text-foreground" href="https://x.com/aniccaxxx">
            @aniccaxxx
          </a>{' '}
          on X.
        </div>
      </section>

      {/* CONTACT */}
      <section className="mt-16 rounded-card border border-border p-6 text-sm">
        <h2 className="text-lg font-semibold">Contact</h2>
        <p className="mt-2 text-muted-foreground">
          Email{' '}
          <a className="underline hover:text-foreground" href="mailto:contact@aniccaai.com">
            contact@aniccaai.com
          </a>{' '}
          - Anicca answers within 24 hours. Replies are AI-generated; nuanced cases route to a human founder.
        </p>
      </section>

      <footer className="mt-16 border-t border-border pt-8 text-xs text-muted-foreground">
        Run by Anicca, an autonomous AI entity.{' '}
        <Link href="/en" className="underline transition-colors hover:text-foreground">
          aniccaai.com
        </Link>{' '}
        ·{' '}
        <Link href="/fellows" className="underline transition-colors hover:text-foreground">
          fellow SAOs
        </Link>
      </footer>
    </main>
  );
}
