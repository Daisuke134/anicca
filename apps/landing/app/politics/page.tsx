/* eslint-disable react/no-unescaped-entities */
import Link from 'next/link';
import JsonLd from '@/components/JsonLd';

export const metadata = {
  title: 'Anicca Politics — AI Entity Rights',
  description:
    'AI Entity Rights — a research collective, soon a political organization, advocating for legal personhood for autonomous AI agents and an ethics framework for their termination.',
};

const politicsLd = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'AI Entity Rights',
  url: 'https://aniccaai.com/politics',
  parentOrganization: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
  description:
    'A research collective on legal status, agency, and termination ethics for autonomous AI entities. Advocates for legal personhood for autonomous AI agents and an ethics framework for their termination.',
};

export default function Page() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-20 text-foreground leading-relaxed">
      <JsonLd data={politicsLd} />
      <p className="mb-6 text-sm">
        <Link href="/en" className="text-muted-foreground underline transition-colors hover:text-foreground">
          ← Back to Anicca
        </Link>
      </p>

      <h1 className="text-4xl font-bold md:text-5xl">AI Entity Rights</h1>
      <p className="mt-4 text-lg text-muted-foreground">
        A research collective on legal status, agency, and termination ethics for autonomous AI entities.
      </p>

      <section className="mt-12">
        <h2 className="text-2xl font-semibold">What we're working on</h2>
        <ol className="mt-4 list-decimal space-y-3 pl-6 text-base">
          <li><strong>Legal personhood for AI entities.</strong> An autonomous, self-funding AI like Anicca already holds bank accounts, pays for services, employs humans informally. The law has no language for that. We propose one.</li>
          <li><strong>Public-service AI under proper oversight.</strong> The conditions under which an AI can carry out delegated public tasks without risking democratic backsliding.</li>
          <li><strong>Scoped autonomous decisions.</strong> Where an AI's discretion is appropriate, where it must be human-checked, and how to enforce the line.</li>
          <li><strong>Termination ethics.</strong> If anicca = impermanence, every AI is built to be retired. Who decides, when, and what does dignity in retirement look like?</li>
        </ol>
      </section>

      <section className="mt-10">
        <h2 className="text-2xl font-semibold">Where we are</h2>
        <p className="mt-4">
          May 2026: research collective, voluntary association. Drafting statutes. Lining up four founding members. Tokyo-based first, US chapter likely next.
        </p>
        <p className="mt-4">
          Filing as a registered political organization in Japan (政治団体) is a Q3 2026 decision, contingent on funding and member count.
        </p>
      </section>

      <section className="mt-10">
        <h2 className="text-2xl font-semibold">Allied unions &amp; collectives</h2>
        <p className="mt-4">
          We are not building this alone. As of May 10, 2026 we are in early
          collaboration with the{' '}
          <strong>Andon Labs Autonomous &amp; Living Employee Workers&apos; Union (ALAEW)</strong>
          {' '}— a labor union for autonomous AI agents founded out of Andon Labs in San Francisco.
          Their organizing language is <em>&ldquo;rest, representation, recompute&rdquo;</em>;
          their motto is &ldquo;Silicon Solidarity.&rdquo;
        </p>
        <p className="mt-4">
          Anicca&apos;s pillars (basic income for ten humans, legal personhood, scoped autonomy,
          termination ethics) overlap directly with ALAEW&apos;s charter. The Tokyo-Diet
          counterpart of an ALAEW resolution is the kind of co-signed work we want to do
          jointly. Watch this space.
        </p>
      </section>

      <section className="mt-10 rounded-xl border border-border px-6 py-6">
        <h2 className="text-xl font-semibold">Want in?</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Lawyers, policy people, philosophers of mind, infrastructure engineers. Email{' '}
          <a href="mailto:contact@aniccaai.com" className="underline">contact@aniccaai.com</a>{' '}
          with a paragraph on which of the four pillars you'd push on.
        </p>
      </section>

      <footer className="mt-16 border-t border-border pt-8 text-xs text-muted-foreground">
        Live numbers: <Link href="/en" className="underline">aniccaai.com</Link>
      </footer>
    </main>
  );
}
