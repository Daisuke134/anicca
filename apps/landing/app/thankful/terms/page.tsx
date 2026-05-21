'use client';

import { useEffect } from 'react';

export default function ThankfulTerms() {
  useEffect(() => {
    window.location.href = 'https://www.apple.com/legal/internet-services/itunes/dev/stdeula/';
  }, []);

  return (
    <main className="container mx-auto max-w-3xl px-4 py-24">
      <p className="text-muted-foreground">Redirecting to Terms of Use...</p>
    </main>
  );
}
