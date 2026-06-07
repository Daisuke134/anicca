import React from 'react';

type SectionProps = {
  children: React.ReactNode;
  className?: string;
  id?: string;
};

// §3.E max-w container, §7 DENSITY 3 => py-24 (mobile py-16). 1テーマ前提(§4.11).
export function Section({ children, className = '', id }: SectionProps) {
  return (
    <section id={id} className={`w-full px-4 py-16 md:py-24 ${className}`}>
      <div className="mx-auto max-w-[1400px]">{children}</div>
    </section>
  );
}
