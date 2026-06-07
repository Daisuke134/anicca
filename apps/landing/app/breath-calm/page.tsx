import Image from 'next/image';
import { SplitHero, Section, Reveal, CTA } from '@/components/site/taste';

export const metadata = {
  title: 'BreathCalm - Reset Anxiety in 6 Minutes',
  description:
    '9D binaural breathwork that actually works. 4-7-8, Box, Coherent breathing + SOS emergency mode. Reset anxiety in just 6 minutes.',
};

export default function BreathCalmLanding() {
  return (
    <main className="min-h-screen bg-[hsl(var(--background))]">
      <SplitHero
        eyebrow="Available on iOS"
        headline={
          <>
            Reset Anxiety<br />in 6 Minutes
          </>
        }
        subtext="9D binaural breathwork that actually works. 4-7-8, Box, Coherent breathing plus SOS emergency mode."
        primary={
          <CTA href="https://aniccaai.com/app">
            Download on the App Store
          </CTA>
        }
        asset={
          <Image
            src="/anicca-app-icon.png"
            alt="BreathCalm app icon"
            width={400}
            height={400}
            className="w-full h-auto object-cover"
            priority
          />
        }
      />

      <Section>
        <Reveal>
          <h2 className="text-2xl font-semibold text-[hsl(var(--text-primary))] mb-8">
            What makes BreathCalm different
          </h2>
        </Reveal>
        <ul className="space-y-3 text-lg text-[hsl(var(--text-primary))]">
          {[
            '9D Binaural Beats - immersive audio synchronized with every breath',
            'SOS Emergency Mode - instant calm in 3 minutes when anxiety spikes',
            '5 expert techniques - 4-7-8, Box, Coherent, SOS, Japanese Walking',
            'Mood score tracking before and after each session',
            'Streak tracker to build a daily breathing habit',
          ].map((item, i) => (
            <Reveal key={i} delay={i * 0.06}>
              <li className="list-disc ml-6">{item}</li>
            </Reveal>
          ))}
        </ul>
      </Section>

      <Section>
        <Reveal>
          <p className="text-lg text-[hsl(var(--text-secondary))] max-w-2xl">
            Anxiety doesn&apos;t have to win. A single 6-minute breathing session can lower
            your heart rate, calm your nervous system, and help you think clearly again.
            Start free today.
          </p>
        </Reveal>
      </Section>

      <footer className="border-t border-[hsl(var(--border))] px-4 py-8 text-sm text-[hsl(var(--text-secondary))]">
        <div className="mx-auto max-w-[1400px] space-y-2">
          <p>
            <a href="/breath-calm/privacy/en" className="underline hover:text-[hsl(var(--text-primary))]">Privacy Policy</a>
            {' · '}
            <a href="/breath-calm/terms" className="underline hover:text-[hsl(var(--text-primary))]">Terms of Use</a>
            {' · '}
            <a href="mailto:keiodaisuke@gmail.com" className="underline hover:text-[hsl(var(--text-primary))]">Support</a>
          </p>
          <p>© 2026 Daisuke Narita. All rights reserved.</p>
        </div>
      </footer>
    </main>
  );
}
