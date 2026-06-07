export const metadata = { title: 'Privacy Policy | BreathStory - Guided Breathing Stories' };

export default function BreathStoryPrivacyEN() {
  return (
    <main className="container mx-auto max-w-3xl px-4 py-24">
      <h1 className="text-3xl font-bold text-foreground">Privacy Policy</h1>
      <p className="mt-6 text-muted-foreground">
        This policy describes how we handle user data, including personal information, in the BreathStory iOS app (the &quot;Service&quot;).
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">1. Business Information</h2>
      <p className="mt-3 text-muted-foreground">Daisuke Narita (Individual Business Owner) / keiodaisuke@gmail.com</p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">2. Scope of Application</h2>
      <p className="mt-3 text-muted-foreground">
        This policy applies to the Service and related support communications. It also applies to our website pages that link to this policy.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">3. Information We Collect</h2>
      <p className="mt-3 text-muted-foreground">
        BreathStory is designed with privacy first. We collect minimal data:
      </p>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>Subscription status information (managed via App Store / RevenueCat)</li>
        <li>In-app preferences stored locally on your device (streak count, onboarding completion)</li>
        <li>Support communications (e.g., emails you send to our support address)</li>
      </ul>
      <p className="mt-3 text-muted-foreground">
        We do <strong>not</strong> collect analytics events, crash reports, advertising identifiers (IDFA), or any personally identifiable information beyond what Apple provides for subscription management.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">4. Main Collection Methods</h2>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>Information received from Apple for subscription validation (managed via RevenueCat)</li>
        <li>Support inquiries sent to our support desk</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">5. Purpose of Use</h2>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>Manage subscriptions and unlock premium content</li>
        <li>Respond to support inquiries and send important notices</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">6. Third-Party Services</h2>
      <p className="mt-3 text-muted-foreground">
        We use the following vendors to operate the Service:
      </p>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>Apple (App Store billing and related platform services)</li>
        <li>RevenueCat (subscription/entitlement management - receives anonymized purchase receipt only)</li>
      </ul>
      <p className="mt-3 text-muted-foreground">
        We do NOT use analytics SDKs, advertising networks, crash reporting services, or tracking frameworks.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">7. Data Storage</h2>
      <p className="mt-3 text-muted-foreground">
        All user preferences (streak count, subscription status cache, onboarding state) are stored locally on your device using Apple&apos;s UserDefaults. This data is never transmitted to our servers. BreathStory has no backend server.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">8. Data We Do Not Collect</h2>
      <p className="mt-3 text-muted-foreground">
        BreathStory does not collect or access: HealthKit data, location data, camera or microphone data, contacts, photo library, advertising identifiers (IDFA), or any analytics/behavioral data.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">9. Retention Period and Deletion</h2>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>Local device data: Deleted when the app is removed from your device</li>
        <li>Support history: Stored for a reasonable period to maintain records</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">10. Security Measures</h2>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>All data stored locally on-device (no server transmission)</li>
        <li>Subscription validation uses RevenueCat&apos;s secure infrastructure</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">11. User Rights</h2>
      <p className="mt-3 text-muted-foreground">
        To remove all data: delete BreathStory from your device. For support-related data deletion, contact keiodaisuke@gmail.com. Requests will be handled within a reasonable period.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">12. Children</h2>
      <p className="mt-3 text-muted-foreground">
        BreathStory is rated 4+ and is suitable for all ages. We do not knowingly collect personal information from children under 13. Since we collect no personal data, COPPA requirements are inherently satisfied.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">13. Policy Updates</h2>
      <p className="mt-3 text-muted-foreground">
        We may update this policy as the Service evolves. Material changes will be communicated via this page. Continued use of the Service after changes constitutes acceptance.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">14. Contact</h2>
      <p className="mt-3 text-muted-foreground">
        For questions or concerns about this policy, contact: keiodaisuke@gmail.com
      </p>

      <p className="mt-10 text-sm text-muted-foreground">Last updated: March 2026</p>

      <div className="mt-8 border-t border-border pt-6 text-sm text-muted-foreground">
        <a href="/breathstory/privacy/ja" className="underline hover:text-foreground">日本語版プライバシーポリシー</a>
      </div>
    </main>
  );
}
