export const metadata = { title: 'Terms of Use | Anicca' };

export default function TermsEN() {
  return (
    <main className="container mx-auto max-w-3xl px-4 py-24">
      <h1 className="text-3xl font-bold text-foreground">Terms of Use</h1>
      <p className="mt-6 text-muted-foreground">
        These Terms of Use apply to the Anicca iOS app (the &quot;Service&quot;). By using the Service, you agree to these Terms.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">1. Business Information</h2>
      <p className="mt-3 text-muted-foreground">Daisuke Narita (Individual Business Owner) / keiodaisuke@gmail.com</p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">2. Service Overview</h2>
      <p className="mt-3 text-muted-foreground">
        Anicca provides notifications and in-app content to support behavior change. The Service is not a medical device and does not provide medical,
        psychological, legal, or other professional advice.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">3. Accounts</h2>
      <p className="mt-3 text-muted-foreground">
        You may use the Service without signing in. If you choose to sign in with Apple, you are responsible for maintaining the security of your device and
        account.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">4. Subscriptions and Billing (iOS)</h2>
      <p className="mt-3 text-muted-foreground">
        Subscriptions (if offered) are billed through your Apple ID via the App Store. Cancellation and refunds are handled by Apple, and the Apple Standard
        EULA applies.
      </p>
      <p className="mt-3 text-muted-foreground">
        Reference:{' '}
        <a className="text-primary underline" href="https://www.apple.com/legal/internet-services/itunes/dev/stdeula/" target="_blank" rel="noreferrer">
          Apple Standard EULA
        </a>
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">5. Prohibited Conduct</h2>
      <ul className="mt-3 list-disc pl-6 text-foreground space-y-2">
        <li>Violating laws or public order and morals</li>
        <li>Interfering with the operation of the Service or attempting unauthorized access</li>
        <li>Reverse engineering or abusing the Service</li>
        <li>Infringing intellectual property or privacy rights of others</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold text-foreground">6. Intellectual Property</h2>
      <p className="mt-3 text-muted-foreground">
        All intellectual property rights related to the Service belong to the operator or rightful licensors. You may not reproduce or modify content without
        permission.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">7. Disclaimer and Limitation of Liability</h2>
      <p className="mt-3 text-muted-foreground">
        The Service is provided on an &quot;as is&quot; basis. To the maximum extent permitted by law, the operator is not liable for indirect or consequential
        damages.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">8. Changes to the Service / Terms</h2>
      <p className="mt-3 text-muted-foreground">
        We may update the Service or these Terms as needed. Material changes will be posted on this page and/or announced in the app.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">9. Governing Law and Jurisdiction</h2>
      <p className="mt-3 text-muted-foreground">
        These Terms are governed by the laws of Japan. Any dispute shall be subject to the exclusive jurisdiction of the Tokyo District Court or Tokyo Summary
        Court.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-foreground">10. Contact</h2>
      <p className="mt-3 text-muted-foreground">Please contact keiodaisuke@gmail.com.</p>

      <p className="mt-12 text-right text-sm text-muted-foreground">Last Updated: January 26, 2026</p>
    </main>
  );
}

