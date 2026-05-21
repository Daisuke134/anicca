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
        // Default sans for places that opt out of serif.
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        inter: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        'noto-sans-jp': ['var(--font-noto-sans-jp)', 'system-ui', 'sans-serif'],
        // New: editorial serif default for body + headings.
        serif: ['var(--font-newsreader)', 'Iowan Old Style', 'Apple Garamond', 'Georgia', 'serif'],
        display: ['var(--font-newsreader)', 'Iowan Old Style', 'Georgia', 'serif'],
        // Soft expressive serif (used on the affirmation app landing).
        soft: ['var(--font-fraunces)', 'var(--font-newsreader)', 'Iowan Old Style', 'Georgia', 'serif'],
        'serif-jp': ['var(--font-noto-serif-jp)', 'Hiragino Mincho ProN', 'Yu Mincho', 'serif'],
        mono: ['var(--font-jetbrains)', 'SF Mono', 'Menlo', 'monospace'],
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
        ink: 'hsl(var(--ink))',
        'ink-soft': 'hsl(var(--ink-soft))',
        cream: 'hsl(var(--cream))',
        bone: 'hsl(var(--bone))',
        gold: 'hsl(var(--gold))',
        ember: 'hsl(var(--ember))',
        mist: 'hsl(var(--mist))',
      },
      container: {
        center: true,
        padding: '1rem',
        screens: {
          '2xl': '1200px',
        },
      },
    },
  },
  plugins: [animate],
}

export default config
