'use client';

// Client-side locale for the launch surfaces (/install /me /lm /life-manager).
// These are top-level, force-static routes — we CANNOT do server-side
// Accept-Language detection in `output: 'export'`. So locale is resolved in the
// browser, with this precedence (first hit wins):
//   1. ?lang=en|ja   (explicit, also written to storage so it sticks)
//   2. localStorage 'anicca.locale'  (the user's prior toggle)
//   3. navigator.language            (en* → en, ja* → ja, else en)
//
// Until the effect runs we render the default ('en') so SSG output is stable and
// hydration never mismatches; the real locale is applied on mount.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';

export type LaunchLocale = 'en' | 'ja';

const STORAGE_KEY = 'anicca.locale';
const DEFAULT_LOCALE: LaunchLocale = 'en';

function normalize(value: string | null | undefined): LaunchLocale | null {
  if (!value) return null;
  const v = value.toLowerCase();
  if (v.startsWith('ja')) return 'ja';
  if (v.startsWith('en')) return 'en';
  return null;
}

function detect(): LaunchLocale {
  if (typeof window === 'undefined') return DEFAULT_LOCALE;
  try {
    const param = new URLSearchParams(window.location.search).get('lang');
    const fromParam = normalize(param);
    if (fromParam) return fromParam;

    const fromStore = normalize(window.localStorage.getItem(STORAGE_KEY));
    if (fromStore) return fromStore;

    const fromNav = normalize(window.navigator.language);
    if (fromNav) return fromNav;
  } catch {
    /* storage / location may be unavailable — fall through to default */
  }
  return DEFAULT_LOCALE;
}

type Ctx = { locale: LaunchLocale; setLocale: (l: LaunchLocale) => void };

const LaunchLocaleContext = createContext<Ctx>({
  locale: DEFAULT_LOCALE,
  setLocale: () => {},
});

export function LaunchLocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<LaunchLocale>(DEFAULT_LOCALE);

  useEffect(() => {
    const resolved = detect();
    setLocaleState(resolved);
    try {
      // Persist the resolved locale (esp. when it came from ?lang) and strip the
      // query param so it doesn't override a later toggle.
      window.localStorage.setItem(STORAGE_KEY, resolved);
      const url = new URL(window.location.href);
      if (url.searchParams.has('lang')) {
        url.searchParams.delete('lang');
        window.history.replaceState(null, '', url.pathname + url.search + url.hash);
      }
    } catch {
      /* ignore */
    }
  }, []);

  const setLocale = useCallback((l: LaunchLocale) => {
    setLocaleState(l);
    try {
      window.localStorage.setItem(STORAGE_KEY, l);
      document.documentElement.lang = l;
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    try {
      document.documentElement.lang = locale;
    } catch {
      /* ignore */
    }
  }, [locale]);

  return (
    <LaunchLocaleContext.Provider value={{ locale, setLocale }}>
      {children}
    </LaunchLocaleContext.Provider>
  );
}

export function useLaunchLocale(): Ctx {
  return useContext(LaunchLocaleContext);
}
