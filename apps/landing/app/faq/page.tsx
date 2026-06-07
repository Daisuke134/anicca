export const metadata = { title: 'FAQ | Anicca' };

import { ManifestoHero } from '@/components/site/taste/ManifestoHero';
import { Section } from '@/components/site/taste/Section';
import { Reveal } from '@/components/site/taste/Reveal';
import { CTA } from '@/components/site/taste/CTA';

// §11.F: Q&A copy verbatim - no character changed
const faqs = [
  {
    q: 'Is my data private?',
    a: 'Yes. Local-first, least privilege, no telemetry.',
  },
  {
    q: 'Which platforms are supported?',
    a: 'iOS 17 or later (iPhone).',
  },
  {
    q: 'How does Anicca help me?',
    a: 'Anicca sends proactive nudges based on your struggles to help you build better habits.',
  },
];

export default function FaqPage() {
  return (
    <main>
      {/* §4.3: ManifestoHero for FAQ headline */}
      <ManifestoHero
        headline={
          <>
            {/* TODO(i18n): EN */}
            Frequently<br />asked.
          </>
        }
        subtext={/* TODO(i18n): EN */ 'Everything you need to know about Anicca.'}
        cta={<CTA href="/" variant="link">{/* TODO(i18n): EN */}Back to aniccaai.com</CTA>}
      />

      {/* §9.F: NO accordion. Side-by-side 2-col (question + answer) with dividers. */}
      <Section>
        <div className="mx-auto max-w-[60rem]">
          {faqs.map((item, i) => (
            <Reveal key={i} delay={i * 0.07}>
              <div className="grid grid-cols-1 gap-4 border-t border-[hsl(var(--border))] py-10 md:grid-cols-2 md:gap-16">
                {/* Question column */}
                <div>
                  <p className="font-display text-lg font-semibold leading-snug text-[hsl(var(--text-primary))] md:text-xl">
                    {item.q}
                  </p>
                </div>
                {/* Answer column */}
                <div>
                  <p className="text-base leading-relaxed text-[hsl(var(--text-secondary))]">
                    {item.a}
                  </p>
                </div>
              </div>
            </Reveal>
          ))}
          {/* closing border */}
          <div className="border-t border-[hsl(var(--border))]" />
        </div>
      </Section>
    </main>
  );
}
