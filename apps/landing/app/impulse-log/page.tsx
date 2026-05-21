import JsonLd from '@/components/JsonLd';

export const metadata = {
  title: 'ImpulseLog — Anger & ADHD Diary',
  description:
    'Log your emotional explosions in 30 seconds. Discover your ADHD/HSP triggers. Break the cycle of regret.',
};

const impulseLogLd = {
  '@context': 'https://schema.org',
  '@type': 'MobileApplication',
  name: 'ImpulseLog',
  url: 'https://aniccaai.com/impulse-log',
  operatingSystem: 'iOS',
  applicationCategory: 'HealthApplication',
  description:
    'ImpulseLog helps people with ADHD and HSP track anger, impulses, and emotional explosions in 30 seconds. Discover your triggers and break the cycle of regret.',
  publisher: { '@type': 'Organization', name: 'Anicca', url: 'https://aniccaai.com' },
};

export default function ImpulseLogLanding() {
  return (
    <main className="bg-[#1a1a2e] text-white min-h-screen">
      <JsonLd data={impulseLogLd} />
      {/* Hero */}
      <section className="container mx-auto max-w-2xl px-6 pt-24 pb-16 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-pink-500/30 bg-pink-500/10 px-4 py-1.5 text-sm text-pink-400 mb-8">
          <span>⚡</span>
          <span>Available on iOS</span>
        </div>

        <h1 className="text-5xl font-bold leading-tight mb-6">
          Emotional Explosion?<br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-pink-400 to-purple-400">
            Log it in 30 seconds.
          </span>
        </h1>

        <p className="text-xl text-gray-400 mb-10 leading-relaxed">
          ImpulseLog helps people with ADHD and HSP track anger, impulses, and
          emotional surges — and discover the hidden triggers behind them.
        </p>

        <a
          href="https://apps.apple.com/app/id6746798349"
          className="inline-flex items-center gap-3 rounded-2xl bg-white px-8 py-4 text-black font-semibold text-lg hover:bg-gray-100 transition-colors"
        >
          <svg viewBox="0 0 24 24" className="w-6 h-6 fill-current" aria-hidden="true">
            <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z" />
          </svg>
          Download on App Store
        </a>
      </section>

      {/* Features */}
      <section className="container mx-auto max-w-2xl px-6 py-16">
        <h2 className="text-3xl font-bold text-center mb-12">Break the Cycle</h2>
        <div className="grid gap-8 md:grid-cols-3">
          <div className="text-center">
            <div className="text-4xl mb-4">⚡</div>
            <h3 className="font-semibold text-lg mb-2">30-Second Log</h3>
            <p className="text-gray-400 text-sm">Capture emotional surges before they fade. Designed for impulsive moments.</p>
          </div>
          <div className="text-center">
            <div className="text-4xl mb-4">📊</div>
            <h3 className="font-semibold text-lg mb-2">Pattern Reports</h3>
            <p className="text-gray-400 text-sm">Weekly reports reveal your top triggers and most vulnerable times.</p>
          </div>
          <div className="text-center">
            <div className="text-4xl mb-4">🔒</div>
            <h3 className="font-semibold text-lg mb-2">100% Private</h3>
            <p className="text-gray-400 text-sm">All data stays on your device. No cloud sync, no sharing.</p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="container mx-auto max-w-2xl px-6 py-12 text-center border-t border-white/10">
        <p className="text-gray-500 text-sm mb-4">
          ImpulseLog by Anicca
        </p>
        <div className="flex justify-center gap-6 text-sm text-gray-500">
          <a href="/impulse-log/privacy/en" className="hover:text-white transition-colors">Privacy Policy</a>
          <a href="https://www.apple.com/legal/internet-services/itunes/dev/stdeula/" className="hover:text-white transition-colors">Terms of Use</a>
        </div>
      </footer>
    </main>
  );
}
