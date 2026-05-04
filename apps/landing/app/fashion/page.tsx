/* eslint-disable react/no-unescaped-entities */
import Link from 'next/link';

export const metadata = {
  title: 'Anicca Fashion — everything shall pass',
  description:
    'Anicca Fashion: print-on-demand tees that say what the brand believes. "everything shall pass" — Buddhist plain truth in cotton.',
};

export default function Page() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-20 text-foreground leading-relaxed">
      <p className="mb-6 text-sm">
        <Link href="/en" className="text-muted-foreground underline transition-colors hover:text-foreground">
          ← Back to Anicca
        </Link>
      </p>

      <h1 className="text-4xl font-bold md:text-5xl">Anicca Fashion</h1>
      <p className="mt-4 text-lg text-muted-foreground">
        One sentence on cotton. Print-on-demand. Worn as a daily reminder.
      </p>

      <section className="mt-12">
        <h2 className="text-2xl font-semibold">What it is</h2>
        <p className="mt-4">
          A line of black tees with the Anicca app icon on the chest and one sentence on the back: <strong>"everything shall pass."</strong> Print-on-demand through Printful — zero inventory, fulfilled and shipped per order, anywhere in the world.
        </p>
      </section>

      <section className="mt-10">
        <h2 className="text-2xl font-semibold">Why</h2>
        <p className="mt-4">
          Affirmation apps remind you when you tap them. A shirt reminds you when you put it on. The brain doesn't separate "I am wearing this idea" from "I believe this idea." That's the entire point.
        </p>
      </section>

      <section className="mt-10 rounded-xl border border-border px-6 py-6">
        <h2 className="text-xl font-semibold">$35 — coming May 16</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Bella + Canvas 3001 black, sizes XS–XXL. Worldwide shipping via Printful.
        </p>
        <p className="mt-4 text-xs text-muted-foreground">Stripe checkout pending Printful setup.</p>
      </section>

      <footer className="mt-16 border-t border-border pt-8 text-xs text-muted-foreground">
        Live numbers: <Link href="/en" className="underline">aniccaai.com</Link>
      </footer>
    </main>
  );
}
