export const metadata = {
  title: "Privacy Policy – BreathReset",
  description: "BreathReset Privacy Policy",
};

export default function BreathResetPrivacyEN() {
  return (
    <main className="max-w-2xl mx-auto px-6 py-16 text-gray-800">
      <h1 className="text-3xl font-bold mb-6">Privacy Policy</h1>
      <p className="text-sm text-gray-500 mb-8">Last updated: March 1, 2026</p>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">1. Information We Collect</h2>
        <p className="mb-3">BreathReset collects the following information to provide and improve our service:</p>
        <ul className="list-disc pl-6 space-y-2">
          <li><strong>Usage Data:</strong> Session counts, streak days, and preferred breathing techniques — stored locally on your device using UserDefaults.</li>
          <li><strong>Analytics:</strong> Anonymized event data (session started, paywall viewed, etc.) sent to Mixpanel for product improvement. Device ID is collected for analytics purposes only and is not linked to your identity.</li>
          <li><strong>Purchase Data:</strong> Subscription status managed by RevenueCat. We do not store payment details.</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">2. How We Use Information</h2>
        <ul className="list-disc pl-6 space-y-2">
          <li>To display your progress (streaks, session history)</li>
          <li>To send daily breathing reminders (optional push notifications)</li>
          <li>To manage your Premium subscription</li>
          <li>To improve the app based on aggregated usage patterns</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">3. Data Sharing</h2>
        <p>We do not sell your personal data. We share anonymized analytics with:</p>
        <ul className="list-disc pl-6 mt-3 space-y-2">
          <li><strong>Mixpanel</strong> — product analytics</li>
          <li><strong>RevenueCat</strong> — subscription management</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">4. Data Retention</h2>
        <p>Usage data is stored locally on your device. You can reset all data by uninstalling the app. Mixpanel retains anonymized event data for up to 5 years.</p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">5. Tracking</h2>
        <p>BreathReset does <strong>not</strong> track you across other apps or websites. We do not use IDFA or any cross-app tracking technology.</p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">6. Children</h2>
        <p>BreathReset is not directed to children under 13. We do not knowingly collect data from children.</p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">7. Contact</h2>
        <p>Questions? Email us at <a href="mailto:support@anicca.app" className="text-blue-600 underline">support@anicca.app</a></p>
      </section>
    </main>
  );
}
