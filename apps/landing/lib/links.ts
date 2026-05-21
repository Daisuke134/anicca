export const links = {
  en: {
    appStore: 'https://aniccaai.com/app',
    tiktok: 'https://www.tiktok.com/@anicca.ai',
    instagram: 'https://www.instagram.com/anicca.ai',
    youtube: 'https://www.youtube.com/@anicca-ai',
    x: 'https://x.com/aniccaen',
  },
  ja: {
    appStore: 'https://aniccaai.com/app',
    tiktok: 'https://www.tiktok.com/@anicca.japan',
    instagram: 'https://www.instagram.com/anicca.japan',
    youtube: 'https://www.youtube.com/@anicca-jp',
    x: 'https://x.com/aniccaxxx',
  },
} as const;

export type Locale = keyof typeof links;
