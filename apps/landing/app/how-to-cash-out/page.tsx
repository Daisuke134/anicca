import fs from 'fs';
import path from 'path';
import LaunchFrame from '@/components/site/LaunchFrame';
import CashOutBody from './CashOutBody';

// /how-to-cash-out (spec31 §E / spec30 §12). Server reads the two trusted markdown
// files at build time, renders to HTML, and hands both to the client body which
// shows the locale-matched one via the LaunchLocale toggle. Static export safe.

export const dynamic = 'force-static';

export const metadata = {
  title: 'How to cash out — Anicca',
  description:
    'How money moves between you and your Anicca. US: direct USDC on Base. Japan: Binance + PayPay + Solana. Honest about which paths are truly no-human-in-loop.',
};

function inline(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(
      /`([^`]+)`/g,
      '<code class="rounded bg-[hsl(var(--surface-elevated))] px-1.5 py-0.5 font-mono text-[0.85em] text-[hsl(var(--text-primary))]">$1</code>',
    )
    .replace(/\*\*([^*]+)\*\*/g, '<strong class="text-[hsl(var(--text-primary))]">$1</strong>')
    .replace(
      /\[([^\]]+)\]\(((?:https?:\/\/|\/)[^)]+)\)/g,
      '<a href="$2" class="underline underline-offset-4 hover:text-[hsl(var(--text-primary))]" target="_blank" rel="noopener noreferrer">$1</a>',
    );
}

// Minimal markdown → HTML for our own trusted content files (headings, paragraphs,
// ordered + unordered lists, bold, links, code). Mirrors blog/[slug] approach.
function renderMarkdown(md: string): string {
  const lines = md.split('\n');
  const out: string[] = [];
  let listType: 'ol' | 'ul' | null = null;
  let inPara = false;
  const flushPara = () => {
    if (inPara) {
      out.push('</p>');
      inPara = false;
    }
  };
  const flushList = () => {
    if (listType) {
      out.push(listType === 'ol' ? '</ol>' : '</ul>');
      listType = null;
    }
  };
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      flushPara();
      flushList();
      continue;
    }
    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) {
      flushPara();
      flushList();
      const lvl = h[1].length;
      const cls =
        lvl === 1
          ? 'font-display text-[34px] sm:text-[46px] leading-tight mt-0 mb-8 text-[hsl(var(--text-primary))]'
          : lvl === 2
            ? 'font-display text-[24px] sm:text-[30px] leading-tight mt-14 mb-4 text-[hsl(var(--text-primary))]'
            : 'font-display text-[18px] sm:text-[20px] leading-tight mt-10 mb-3 text-[hsl(var(--text-primary))]';
      out.push(`<h${lvl} class="${cls}">${inline(h[2])}</h${lvl}>`);
      continue;
    }
    const ol = line.match(/^\d+\.\s+(.*)$/);
    if (ol) {
      flushPara();
      if (listType !== 'ol') {
        flushList();
        out.push('<ol class="my-5 list-decimal space-y-2 pl-6 text-[15px] leading-relaxed text-[hsl(var(--text-secondary))]">');
        listType = 'ol';
      }
      out.push(`<li>${inline(ol[1])}</li>`);
      continue;
    }
    const ul = line.match(/^[-*]\s+(.*)$/);
    if (ul) {
      flushPara();
      if (listType !== 'ul') {
        flushList();
        out.push('<ul class="my-5 list-disc space-y-2 pl-6 text-[15px] leading-relaxed text-[hsl(var(--text-secondary))]">');
        listType = 'ul';
      }
      out.push(`<li>${inline(ul[1])}</li>`);
      continue;
    }
    flushList();
    if (!inPara) {
      out.push('<p class="my-5 text-[16px] leading-relaxed text-[hsl(var(--text-secondary))]">');
      inPara = true;
    }
    out.push(inline(line) + ' ');
  }
  flushPara();
  flushList();
  return out.join('\n');
}

function load(locale: 'en' | 'ja'): string {
  const file = path.join(process.cwd(), 'content', `how-to-cash-out.${locale}.md`);
  if (!fs.existsSync(file)) return '';
  return renderMarkdown(fs.readFileSync(file, 'utf-8'));
}

export default function Page() {
  const htmlEn = load('en');
  const htmlJa = load('ja');
  return (
    <LaunchFrame>
      <CashOutBody htmlEn={htmlEn} htmlJa={htmlJa} />
    </LaunchFrame>
  );
}
