import { ManifestoHero, Section, Reveal } from '@/components/site/taste';

export const metadata = { title: 'CalmCortisol - Stress Relief in 60 Seconds' };

export default function CalmCortisolLanding() {
  return (
    <main className="min-h-screen bg-[hsl(var(--background))]">
      <ManifestoHero
        headline={
          <>
            Stressed? Anxious?<br />Can&apos;t sleep?
          </>
        }
        subtext="AI-powered breathing sessions reset your nervous system in 60 seconds."
      />

      <Section>
        <Reveal>
          <p className="text-base text-[hsl(var(--text-secondary))] max-w-2xl">
            CalmCortisol detects when your cortisol is spiking and steps in before you spiral.
            Science-backed breathing techniques. No meditation experience needed.
          </p>
        </Reveal>
        <Reveal delay={0.1}>
          <p className="text-sm text-[hsl(var(--text-secondary))] mt-12">
            Available on iOS - Coming Soon to App Store
          </p>
        </Reveal>
      </Section>
    </main>
  );
}
