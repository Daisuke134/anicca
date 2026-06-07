export const metadata = { title: 'Privacy Policy | ImpulseLog' };

export default function ImpulseLogPrivacyEN() {
  return (
    <main className="container mx-auto max-w-3xl px-4 py-24">
      <h1 className="text-3xl font-bold text-foreground">Privacy Policy - ImpulseLog</h1>
      <p className="mt-4 text-sm text-muted-foreground">Last updated: February 26, 2026</p>

      <p className="mt-6 text-muted-foreground">
        This policy describes how ImpulseLog (the &quot;App&quot;) handles user data.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">1. Business Information</h2>
      <p className="mt-3 text-muted-foreground">Daisuke Narita (Individual Business Owner) / keiodaisuke@gmail.com</p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">2. Information We Collect</h2>
      <ul className="mt-3 list-disc pl-6 text-muted-foreground space-y-2">
        <li>Device identifiers - used for analytics and fraud prevention</li>
        <li>App usage events - e.g., logs created, paywall interactions</li>
        <li>Subscription status - managed via App Store / RevenueCat</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">3. Information We Do NOT Collect</h2>
      <ul className="mt-3 list-disc pl-6 text-muted-foreground space-y-2">
        <li>Your emotion log content or personal notes (stored locally on device only)</li>
        <li>Health data or biometric data</li>
        <li>Location data</li>
        <li>Contact lists, photos, or microphone recordings</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">4. Third-Party Services</h2>
      <ul className="mt-3 list-disc pl-6 text-muted-foreground space-y-2">
        <li><strong>RevenueCat</strong> - Subscription management (purchase history)</li>
        <li><strong>Mixpanel</strong> - Anonymous usage analytics</li>
        <li><strong>Apple App Store</strong> - Payment processing</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">5. Data Retention</h2>
      <p className="mt-3 text-muted-foreground">
        Analytics data is retained for up to 12 months. Your emotion logs are stored locally
        on your device and never transmitted to our servers. You may request deletion of
        analytics data by contacting us.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">6. Contact</h2>
      <p className="mt-3 text-muted-foreground">
        Email: keiodaisuke@gmail.com
      </p>
    </main>
  );
}
