import type { Config } from 'tailwindcss'
import animate from 'tailwindcss-animate'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        serif: ['var(--font-serif)', 'ui-serif', 'Georgia', 'serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'SFMono-Regular', 'monospace'],
        // Backwards-compat alias — older components reference font-inter.
        inter: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        'noto-sans-jp': ['var(--font-noto-sans-jp)', 'system-ui', 'sans-serif'],
        'noto-serif-jp': ['var(--font-noto-serif-jp)', 'ui-serif', 'serif'],
      },
      fontSize: {
        // Type scale — 1.250 (major third), restrained.
        xs:    ['0.75rem',  { lineHeight: '1.5' }],
        sm:    ['0.875rem', { lineHeight: '1.55' }],
        base:  ['1rem',     { lineHeight: '1.65' }],
        lg:    ['1.125rem', { lineHeight: '1.6' }],
        xl:    ['1.25rem',  { lineHeight: '1.5' }],
        '2xl': ['1.5rem',   { lineHeight: '1.35' }],
        '3xl': ['1.875rem', { lineHeight: '1.25' }],
        '4xl': ['2.5rem',   { lineHeight: '1.1', letterSpacing: '-0.02em' }],
        '5xl': ['3.5rem',   { lineHeight: '1.05', letterSpacing: '-0.025em' }],
        '6xl': ['4.5rem',   { lineHeight: '1.0',  letterSpacing: '-0.03em' }],
        '7xl': ['6rem',     { lineHeight: '0.95', letterSpacing: '-0.035em' }],
        '8xl': ['8rem',     { lineHeight: '0.92', letterSpacing: '-0.04em' }],
      },
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: {
          DEFAULT: 'hsl(var(--background))',
          alt: 'hsl(var(--background-alt))',
        },
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        gold: 'hsl(var(--gold))',
        amber: 'hsl(var(--amber))',
      },
      container: {
        center: true,
        padding: '1.5rem',
        screens: {
          '2xl': '1200px',
        },
      },
      maxWidth: {
        prose: '36rem',
        narrow: '40rem',
        content: '64rem',
        wide: '75rem',
      },
      letterSpacing: {
        tightest: '-0.04em',
      },
      keyframes: {
        'fade-up': {
          '0%':   { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        'fade-up': 'fade-up 600ms cubic-bezier(0.16, 1, 0.3, 1) both',
        'fade-in': 'fade-in 800ms ease-out both',
      },
    },
  },
  plugins: [animate],
}

export default config
