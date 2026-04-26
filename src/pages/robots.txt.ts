import type { APIContext } from 'astro';

export function GET(context: APIContext) {
  const siteUrl = context.site?.toString().replace(/\/$/, '') ?? '';
  const body = `User-agent: *
Allow: /
Disallow: /api/

Sitemap: ${siteUrl}/sitemap-index.xml
`;

  return new Response(body, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}
