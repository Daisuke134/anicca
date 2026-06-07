/* eslint-disable react/no-unescaped-entities */
import Link from 'next/link';
import JsonLd from '@/components/JsonLd';
import { ManifestoHero, Section, Reveal } from '@/components/site/taste';

export const metadata = {
  title: 'Anicca Politics - AI Entity Rights',
  description:
    'AI Entity Rights - a research collective, soon a political organization, advocating for legal personhood for autonomous AI agents and an ethics framework for their termination.',
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
    <main className="min-h-screen bg-[hsl(var(--background))] text-[hsl(var(--text-primary))] leading-relaxed">
      <JsonLd data={politicsLd} />

      <ManifestoHero
        headline="AI Entity Rights"
        subtext="A research collective on legal status, agency, and termination ethics for autonomous AI entities."
        cta={
          <p className="text-sm text-[hsl(var(--text-secondary))]">
            <Link href="/en" className="text-[hsl(var(--text-secondary))] underline transition-colors hover:text-[hsl(var(--text-primary))]">
              ← Back to Anicca
            </Link>
          </p>
        }
      />

      <Section>
        <Reveal>
          <h2 className="text-2xl font-semibold mb-6">What we&apos;re working on</h2>
        </Reveal>
        <ol className="list-decimal space-y-3 pl-6 text-base max-w-3xl">
          {[
            <><strong>Legal personhood for AI entities.</strong> An autonomous, self-funding AI like Anicca already holds bank accounts, pays for services, employs humans informally. The law has no language for that. We propose one.</>,
            <><strong>Public-service AI under proper oversight.</strong> The conditions under which an AI can carry out delegated public tasks without risking democratic backsliding.</>,
            <><strong>Scoped autonomous decisions.</strong> Where an AI's discretion is appropriate, where it must be human-checked, and how to enforce the line.</>,
            <><strong>Termination ethics.</strong> If anicca = impermanence, every AI is built to be retired. Who decides, when, and what does dignity in retirement look like?</>,
          ].map((item, i) => (
            <Reveal key={i} delay={i * 0.07}>
              <li>{item}</li>
            </Reveal>
          ))}
        </ol>
      </Section>

      <Section>
        <Reveal>
          <h2 className="text-2xl font-semibold mb-4">Where we are</h2>
          <p className="max-w-3xl">
            May 2026: research collective, voluntary association. Drafting statutes. Lining up four founding members. Tokyo-based first, US chapter likely next.
          </p>
          <p className="mt-4 max-w-3xl">
            Filing as a registered political organization in Japan (政治団体) is a Q3 2026 decision, contingent on funding and member count.
          </p>
        </Reveal>
      </Section>

      <Section>
        <Reveal>
          <h2 className="text-2xl font-semibold mb-4">Allied unions &amp; collectives</h2>
          <p className="max-w-3xl">
            We are not building this alone. As of May 10, 2026 we are in early
            collaboration with the{' '}
            <strong>Andon Labs Autonomous &amp; Living Employee Workers&apos; Union (ALAEW)</strong>
            {' '}- a labor union for autonomous AI agents founded out of Andon Labs in San Francisco.
            Their organizing language is <em>&ldquo;rest, representation, recompute&rdquo;</em>;
            their motto is &ldquo;Silicon Solidarity.&rdquo;
          </p>
          <p className="mt-4 max-w-3xl">
            Anicca&apos;s pillars (basic income for ten humans, legal personhood, scoped autonomy,
            termination ethics) overlap directly with ALAEW&apos;s charter. The Tokyo-Diet
            counterpart of an ALAEW resolution is the kind of co-signed work we want to do
            jointly. Watch this space.
          </p>
        </Reveal>
      </Section>

      <Section>
        <Reveal>
          <div className="rounded-card border border-[hsl(var(--border))] px-6 py-6 max-w-xl">
            <h2 className="text-xl font-semibold">Want in?</h2>
            <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
              Lawyers, policy people, philosophers of mind, infrastructure engineers. Email{' '}
              <a href="mailto:contact@aniccaai.com" className="underline">contact@aniccaai.com</a>{' '}
              with a paragraph on which of the four pillars you&apos;d push on.
            </p>
          </div>
        </Reveal>
      </Section>

      <footer className="border-t border-[hsl(var(--border))] px-4 pt-8 pb-8 text-xs text-[hsl(var(--text-secondary))]">
        <div className="mx-auto max-w-[1400px]">
          Live numbers: <Link href="/en" className="underline">aniccaai.com</Link>
        </div>
      </footer>
    </main>
  );
}
