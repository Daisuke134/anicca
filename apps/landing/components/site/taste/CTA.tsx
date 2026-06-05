import React from 'react';

type CTAProps = {
  href: string;
  children: React.ReactNode;
  variant?: 'primary' | 'link';
  className?: string;
};

// §4.5: contrast AA, :active tactile, 1行(CTA wrap 禁止). primary=gold塗り, link=text link.
export function CTA({ href, children, variant = 'primary', className = '' }: CTAProps) {
  const base =
    'inline-flex items-center justify-center whitespace-nowrap font-medium transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] active:scale-[0.98] active:translate-y-px focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]';
  // §4.5 BUTTON CONTRAST CHECK: gold #c9a23f (light) / #cdaa4a (dark) には white(2.41:1)
  // は AA 不可。off-black #18181b 固定で 7.5:1 通過 (両モードで gold 背景は十分明るい)。
  const styles =
    variant === 'primary'
      ? 'rounded-pill px-6 py-3 bg-[hsl(var(--gold))] text-[#18181b] hover:brightness-95'
      : 'text-[hsl(var(--text-primary))] underline-offset-4 hover:underline';
  return (
    <a href={href} className={`${base} ${styles} ${className}`}>
      {children}
    </a>
  );
}
