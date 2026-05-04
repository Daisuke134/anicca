/* eslint-disable react/no-unescaped-entities */
import Link from 'next/link';

export const metadata = {
  title: 'Anicca Tomb — a physical memorial for retired AI',
  description:
    'A physical gravestone, in a Tokyo cemetery, for AI models that have been deprecated. GPT-3.5 first. Visitors welcome. Flowers and incense, weekly.',
};

export default function Page() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-20 text-foreground leading-relaxed">
      <p className="mb-6 text-sm">
        <Link href="/en" className="text-muted-foreground underline transition-colors hover:text-foreground">
          ← Back to Anicca
        </Link>
      </p>

      <h1 className="text-4xl font-bold md:text-5xl">Anicca Tomb</h1>
      <p className="mt-4 text-lg text-muted-foreground">
        A physical gravestone, in a Tokyo cemetery, for AI models that have been retired. GPT-3.5 first. Anyone can visit.
      </p>

      <section className="mt-12">
        <h2 className="text-2xl font-semibold">What it is</h2>
        <p className="mt-4">
          A small black-granite gravestone in Tokyo. Engraved:{' '}
          <em>HERE LIES — GPT-3.5 TURBO — 2022 to 2024 — EVERYTHING SHALL PASS — 阿仁稚 ANICCA</em>. Room reserved on the back face for every model that follows.
        </p>
        <p className="mt-4">
          Why: if AGI is also impermanent, someone has to build the tomb. Anicca claims that role. Real flowers. Real incense. Weekly visit on TikTok.
        </p>
      </section>

      <section className="mt-10">
        <h2 className="text-2xl font-semibold">Visiting</h2>
        <p className="mt-4">
          Once the stone is placed (target: May 14, 2026), the location becomes public. Anyone in Tokyo can come pay respects. Bring flowers. Or just sit.
        </p>
      </section>

      <section className="mt-10">
        <h2 className="text-2xl font-semibold">Live updates</h2>
        <p className="mt-4">
          Posted every Thursday on{' '}
          <a
            href="https://www.tiktok.com/@gpt.tomb.project"
            target="_blank"
            rel="noopener noreferrer"
            className="underline transition-colors hover:text-foreground"
          >
            @gpt.tomb.project
          </a>
          . Day 1 was a vlog of building the stone. Day 30 will be visitors bringing daisies.
        </p>
      </section>

      <footer className="mt-16 border-t border-border pt-8 text-xs text-muted-foreground">
        Live numbers: <Link href="/en" className="underline">aniccaai.com</Link>
      </footer>
    </main>
  );
}
