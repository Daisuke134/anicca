/* eslint-disable react/no-unescaped-entities */
import Link from 'next/link';

export const metadata = {
  title: 'Anicca Cafe — $10 mango juice on Uber Eats',
  description:
    'Anicca Cafe: one drink, one ingredient, one mission. $10 cold-pressed mango juice delivered through Uber Eats Tokyo. Launching June 1.',
};

export default function Page() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-20 text-foreground leading-relaxed">
      <p className="mb-6 text-sm">
        <Link href="/en" className="text-muted-foreground underline transition-colors hover:text-foreground">
          ← Back to Anicca
        </Link>
      </p>

      <h1 className="text-4xl font-bold md:text-5xl">Anicca Cafe</h1>
      <p className="mt-4 text-lg text-muted-foreground">
        One drink. One ingredient. Delivered to your door. <strong>Launching June 1, Tokyo.</strong>
      </p>

      <section className="mt-12">
        <h2 className="text-2xl font-semibold">What it is</h2>
        <p className="mt-4">
          The food instance of the Anicca swarm. A single product: <strong>cold-pressed mango juice, ¥1,500 ($10), 350ml</strong>. Made in a Shinjuku cloud kitchen, delivered through Uber Eats and Wolt, anywhere within Tokyo.
        </p>
      </section>

      <section className="mt-10">
        <h2 className="text-2xl font-semibold">Why one drink</h2>
        <p className="mt-4">
          Cafés that try to be everything fail at being anything. Anicca Cafe makes one thing, well, every day. The kitchen is rented by the hour. The supply chain is a fruit market and a Vitamix. The branding is the cup. Eventually: 50 cups a day, ¥1,150 profit each, in profit from week one.
        </p>
      </section>

      <section className="mt-10">
        <h2 className="text-2xl font-semibold">Recipe (no secrets)</h2>
        <ul className="mt-4 list-disc space-y-1 pl-6 text-base">
          <li>1 ripe Filipino or Mexican mango (¥250)</li>
          <li>¼ lime (¥30)</li>
          <li>50g ice</li>
          <li>100ml mineral water</li>
          <li>No sugar. No syrup. No additives.</li>
        </ul>
      </section>

      <section className="mt-10 rounded-xl border border-border px-6 py-6">
        <h2 className="text-xl font-semibold">Order on Uber Eats — June 1</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          May 2026 is teaser month — kitchen build, recipe lock, food permit. Uber Eats listing opens June 1. Tokyo only at first.
        </p>
      </section>

      <footer className="mt-16 border-t border-border pt-8 text-xs text-muted-foreground">
        Live numbers: <Link href="/en" className="underline">aniccaai.com</Link>
      </footer>
    </main>
  );
}
