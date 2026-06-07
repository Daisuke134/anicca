import Image from 'next/image';
import { SplitHero, Section, Reveal, CTA } from '@/components/site/taste';

export const metadata = {
  title: 'Thankful - Gratitude Journal | Daily Gratitude & Affirmations',
  description:
    'Start each day with gratitude and watch your life transform. Quick 3-entry journaling, daily affirmations, and streak tracking. Free to download.',
};

export default function ThankfulLanding() {
  return (
    <main className="min-h-screen bg-[hsl(var(--background))]">
      <SplitHero
        eyebrow="Free to Download"
        headline={
          <>
            Daily Gratitude<br />&amp; Affirmations
          </>
        }
        subtext="Start each day with gratitude and watch your life transform. Your daily companion for building a powerful gratitude practice that sticks."
        primary={
          <CTA href="https://apps.apple.com/app/thankful-gratitude-journal/id6759514159">
            Download on the App Store
          </CTA>
        }
        asset={
          <Image
            src="/anicca-app-icon.png"
            alt="Thankful app icon"
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
            What makes Thankful different
          </h2>
        </Reveal>
        <ul className="space-y-3 text-lg text-[hsl(var(--text-primary))]">
          {[
            'Quick 3-entry gratitude journaling - takes just 2 minutes',
            'Daily affirmations to rewire your mindset',
            'Streak tracking to build lasting habits',
            'Beautiful, distraction-free writing experience',
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
            Whether you&apos;re new to gratitude or deepening an existing practice, Thankful meets
            you where you are. Thousands of people have found more joy, resilience, and peace
            through a daily gratitude practice. Start yours today - free.
          </p>
        </Reveal>
      </Section>

      <footer className="border-t border-[hsl(var(--border))] px-4 py-8 text-sm text-[hsl(var(--text-secondary))]">
        <div className="mx-auto max-w-[1400px] space-y-2">
          <p>
            <a href="/thankful/privacy/en" className="underline hover:text-[hsl(var(--text-primary))]">Privacy Policy</a>
            {' · '}
            <a href="/thankful/terms" className="underline hover:text-[hsl(var(--text-primary))]">Terms of Use</a>
            {' · '}
            <a href="mailto:keiodaisuke@gmail.com" className="underline hover:text-[hsl(var(--text-primary))]">Support</a>
          </p>
          <p>© 2026 Daisuke Narita. All rights reserved.</p>
        </div>
      </footer>
    </main>
  );
}
