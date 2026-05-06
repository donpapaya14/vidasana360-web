// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import mdx from '@astrojs/mdx';
import vercel from '@astrojs/vercel';

export default defineConfig({
  site: 'https://vida-sana-360.com',
  output: 'static',
  trailingSlash: 'never',
  integrations: [
    sitemap({
      filter: (page) =>
        !page.includes('/aviso-legal') &&
        !page.includes('/politica-privacidad') &&
        !page.includes('/politica-cookies'),
      i18n: { defaultLocale: 'es', locales: { es: 'es-ES' } },
    }),
    mdx(),
  ],
  adapter: vercel({
    webAnalytics: { enabled: true },
  }),
  i18n: {
    defaultLocale: 'es',
    locales: ['es'],
  },
});
