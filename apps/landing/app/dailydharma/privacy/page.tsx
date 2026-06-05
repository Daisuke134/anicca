export const metadata = { title: 'Privacy Policy | Daily Dharma' };

export default function DailyDharmaPrivacy() {
  return (
    <main className="container mx-auto max-w-3xl px-4 py-24">
      <h1 className="text-3xl font-bold text-foreground">Privacy Policy</h1>
      <p className="mt-2 text-muted-foreground">Daily Dharma - Buddhist Wisdom App</p>

      <p className="mt-6 text-muted-foreground">
        This policy describes how Daily Dharma (&quot;the App&quot;) handles user data.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">1. Information We Collect</h2>
      <p className="mt-3 text-muted-foreground">
        Daily Dharma is designed with privacy in mind. We collect minimal data:
      </p>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li><strong>App Preferences</strong>: Your settings (dark mode, notification frequency) are stored locally on your device only.</li>
        <li><strong>Bookmarks</strong>: Your bookmarked verses are stored locally on your device only.</li>
        <li><strong>Purchase Information</strong>: If you subscribe to Premium, purchase data is processed by RevenueCat and Apple. We do not store payment details.</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">2. Information We Do NOT Collect</h2>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>Personal identification information (name, email, phone number)</li>
        <li>Location data</li>
        <li>Usage analytics or tracking data</li>
        <li>Device identifiers for advertising purposes</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">3. Third-Party Services</h2>
      <p className="mt-3 text-muted-foreground">
        The App uses the following third-party services:
      </p>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li><strong>RevenueCat</strong>: For subscription management. RevenueCat processes purchase transactions through Apple&apos;s App Store. See <a href="https://www.revenuecat.com/privacy" className="underline">RevenueCat Privacy Policy</a>.</li>
        <li><strong>Apple App Store</strong>: For app distribution and in-app purchases. See <a href="https://www.apple.com/legal/privacy/" className="underline">Apple Privacy Policy</a>.</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">4. Local Notifications</h2>
      <p className="mt-3 text-muted-foreground">
        The App sends local notifications (&quot;Stay Present&quot; reminders and morning verses) based on your settings. These notifications are scheduled entirely on your device and do not transmit any data to external servers.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">5. Data Storage</h2>
      <p className="mt-3 text-muted-foreground">
        All your preferences and bookmarks are stored locally on your device using AsyncStorage. We do not have access to this data, and it is not transmitted to any server.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">6. Children&apos;s Privacy</h2>
      <p className="mt-3 text-muted-foreground">
        The App does not knowingly collect any personal information from children under 13 years of age. The App contains no objectionable content and is suitable for all ages.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">7. Changes to This Policy</h2>
      <p className="mt-3 text-muted-foreground">
        We may update this Privacy Policy from time to time. Any changes will be posted on this page with an updated revision date.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">8. Contact</h2>
      <p className="mt-3 text-muted-foreground">
        If you have any questions about this Privacy Policy, please contact us at: <a href="mailto:keiodaisuke@gmail.com" className="underline">keiodaisuke@gmail.com</a>
      </p>

      <p className="mt-12 text-right text-sm text-muted-foreground">Last Updated: January 13, 2026</p>
    </main>
  );
}
