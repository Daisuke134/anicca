import JsonLd from '@/components/JsonLd';

export const metadata = {
  title: 'BreathCalm - Reset Anxiety in 6 Minutes',
  description: '9D binaural breathwork that actually works. 4-7-8, Box, Coherent breathing + SOS emergency mode. Reset anxiety in just 6 minutes.',
};

const breathCalmLd = {
  '@context': 'https://schema.org',
  '@type': 'MobileApplication',
  name: 'BreathCalm',
  url: 'https://aniccaai.com/breath-calm',
  operatingSystem: 'iOS',
  applicationCategory: 'HealthApplication',
  description:
    '9D binaural breathwork that resets anxiety in 6 minutes. Includes 4-7-8, Box, Coherent, SOS emergency mode, and Japanese Walking techniques. Mood score tracking before/after each session and streak tracker.',
  publisher: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
};

export default function BreathCalmLanding() {
  return (
    <main className="container mx-auto max-w-3xl px-4 py-24">
      <JsonLd data={breathCalmLd} />
      <h1 className="text-4xl font-bold text-foreground">BreathCalm</h1>
      <p className="mt-4 text-xl text-muted-foreground">Reset Anxiety in 6 Minutes</p>

      <p className="mt-8 text-lg text-foreground">
        9D binaural breathwork that actually works. Whether you&apos;re overwhelmed, anxious, or just need to reset — BreathCalm guides you through science-backed breathing techniques in minutes.
      </p>

      <h2 className="mt-12 text-2xl font-semibold text-foreground">What makes BreathCalm different</h2>
      <ul className="mt-4 list-disc pl-6 text-foreground space-y-3 text-lg">
        <li>9D Binaural Beats — immersive audio synchronized with every breath</li>
        <li>SOS Emergency Mode — instant calm in 3 minutes when anxiety spikes</li>
        <li>5 expert techniques — 4-7-8, Box, Coherent, SOS, Japanese Walking</li>
        <li>Mood score tracking before and after each session</li>
        <li>Streak tracker to build a daily breathing habit</li>
      </ul>

      <p className="mt-10 text-lg text-muted-foreground">
        Anxiety doesn&apos;t have to win. A single 6-minute breathing session can lower your heart rate, calm your nervous system, and help you think clearly again. Start free today.
      </p>

      <div className="mt-12">
        <a
          href="https://aniccaai.com/app"
          className="inline-block rounded-xl bg-foreground px-8 py-4 text-background font-semibold text-lg hover:opacity-90 transition-opacity"
        >
          Download on the App Store
        </a>
      </div>

      <div className="mt-16 border-t border-border pt-8 text-sm text-muted-foreground space-y-2">
        <p>
          <a href="/breath-calm/privacy/en" className="underline hover:text-foreground">Privacy Policy</a>
          {' · '}
          <a href="/breath-calm/terms" className="underline hover:text-foreground">Terms of Use</a>
          {' · '}
          <a href="mailto:contact@aniccaai.com" className="underline hover:text-foreground">Support</a>
        </p>
        <p>© 2026 Daisuke Narita. All rights reserved.</p>
      </div>
    </main>
  );
}
