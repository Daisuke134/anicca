import JsonLd from '@/components/JsonLd';

export const metadata = { title: 'CalmCortisol — Stress Relief in 60 Seconds' };

const calmCortisolLd = {
  '@context': 'https://schema.org',
  '@type': 'MobileApplication',
  name: 'CalmCortisol',
  url: 'https://aniccaai.com/calmcortisol',
  operatingSystem: 'iOS',
  applicationCategory: 'HealthApplication',
  description:
    'AI-powered breathing sessions that reset your nervous system in 60 seconds. CalmCortisol detects when your cortisol is spiking and steps in before you spiral. Science-backed breathing techniques.',
  publisher: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
};

export default function CalmCortisolLanding() {
  return (
    <main className="container mx-auto max-w-3xl px-4 py-24 text-center">
      <JsonLd data={calmCortisolLd} />
      <h1 className="text-4xl font-bold text-foreground mb-6">CalmCortisol</h1>
      <p className="text-xl text-muted-foreground mb-8">
        Stressed? Anxious? Can&apos;t sleep?<br />
        AI-powered breathing sessions reset your nervous system in 60 seconds.
      </p>
      <p className="text-muted-foreground mb-4">
        CalmCortisol detects when your cortisol is spiking and steps in before you spiral.
        Science-backed breathing techniques. No meditation experience needed.
      </p>
      <p className="text-sm text-muted-foreground mt-12">
        Available on iOS — Coming Soon to App Store
      </p>
    </main>
  );
}
