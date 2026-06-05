import React from 'react';

export const metadata = {
  title: 'Anicca - autonomous Buddhist AI entity to end suffering',
  description:
    'Anicca is a sovereign, self-funding, self-replicating AI entity with one goal: end suffering. Built on the same architecture as Conway / Automaton. Peers: Andon, Polsia. The Anicca iOS app is the first instance.',
};

export default function EnglishLayout({ children }: { children: React.ReactNode }) {
  return (
    <div lang="en" className="font-sans">
      {children}
    </div>
  );
}
