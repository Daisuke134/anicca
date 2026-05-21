import JsonLd from '@/components/JsonLd';

export const metadata = {
  title: 'Thankful - Gratitude Journal | Daily Gratitude & Affirmations',
  description: 'Start each day with gratitude and watch your life transform. Quick 3-entry journaling, daily affirmations, and streak tracking. Free to download.',
};

const thankfulLd = {
  '@context': 'https://schema.org',
  '@type': 'MobileApplication',
  name: 'Thankful',
  url: 'https://aniccaai.com/thankful',
  operatingSystem: 'iOS',
  applicationCategory: 'LifestyleApplication',
  description:
    'A daily gratitude journal app. Quick 3-entry journaling that takes 2 minutes, daily affirmations to rewire your mindset, streak tracking, and a distraction-free writing experience. Free to download.',
  publisher: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
};

export default function ThankfulLanding() {
  return (
    <main className="container mx-auto max-w-3xl px-4 py-24">
      <JsonLd data={thankfulLd} />
      <h1 className="text-4xl font-bold text-foreground">Thankful</h1>
      <p className="mt-4 text-xl text-muted-foreground">Daily Gratitude & Affirmations</p>

      <p className="mt-8 text-lg text-foreground">
        Start each day with gratitude and watch your life transform. Thankful is your daily companion for building a powerful gratitude practice that sticks.
      </p>

      <h2 className="mt-12 text-2xl font-semibold text-foreground">What makes Thankful different</h2>
      <ul className="mt-4 list-disc pl-6 text-foreground space-y-3 text-lg">
        <li>Quick 3-entry gratitude journaling — takes just 2 minutes</li>
        <li>Daily affirmations to rewire your mindset</li>
        <li>Streak tracking to build lasting habits</li>
        <li>Beautiful, distraction-free writing experience</li>
      </ul>

      <p className="mt-10 text-lg text-muted-foreground">
        Whether you&apos;re new to gratitude or deepening an existing practice, Thankful meets you where you are. Thousands of people have found more joy, resilience, and peace through a daily gratitude practice. Start yours today — free.
      </p>

      <div className="mt-12">
        <a
          href="https://apps.apple.com/app/thankful-gratitude-journal/id6759514159"
          className="inline-block rounded-xl bg-foreground px-8 py-4 text-background font-semibold text-lg hover:opacity-90 transition-opacity"
        >
          Download on the App Store
        </a>
      </div>

      <div className="mt-16 border-t border-border pt-8 text-sm text-muted-foreground space-y-2">
        <p>
          <a href="/thankful/privacy/en" className="underline hover:text-foreground">Privacy Policy</a>
          {' · '}
          <a href="/thankful/terms" className="underline hover:text-foreground">Terms of Use</a>
          {' · '}
          <a href="mailto:contact@aniccaai.com" className="underline hover:text-foreground">Support</a>
        </p>
        <p>© 2026 Anicca. All rights reserved.</p>
      </div>
    </main>
  );
}
