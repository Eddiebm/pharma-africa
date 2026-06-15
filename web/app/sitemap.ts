export const runtime = "edge";
export const dynamic = "force-dynamic";

import type { MetadataRoute } from "next";
import { neon } from "@neondatabase/serverless";

const BASE = "https://africaregulatory.com";

const MARKET_SLUGS = [
  "nigeria","south-africa","kenya","ghana","egypt","morocco","tunisia",
  "senegal","cote-divoire","uganda","tanzania","rwanda","malawi","zambia",
  "zimbabwe","ethiopia","madagascar",
];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const static_routes: MetadataRoute.Sitemap = [
    { url: BASE,               lastModified: new Date(), changeFrequency: "weekly",  priority: 1.0 },
    { url: `${BASE}/blog`,     lastModified: new Date(), changeFrequency: "daily",   priority: 0.9 },
    { url: `${BASE}/drugs`,    lastModified: new Date(), changeFrequency: "weekly",  priority: 0.9 },
    { url: `${BASE}/markets`,  lastModified: new Date(), changeFrequency: "monthly", priority: 0.9 },
    { url: `${BASE}/reports`,  lastModified: new Date(), changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE}/pricing`,   lastModified: new Date(), changeFrequency: "monthly", priority: 0.7 },
    { url: `${BASE}/advertise`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.6 },
    { url: `${BASE}/signup`,   lastModified: new Date(), changeFrequency: "monthly", priority: 0.6 },
    { url: `${BASE}/login`,    lastModified: new Date(), changeFrequency: "monthly", priority: 0.4 },
    ...MARKET_SLUGS.map(slug => ({
      url: `${BASE}/markets/${slug}`,
      lastModified: new Date(),
      changeFrequency: "weekly" as const,
      priority: 0.85,
    })),
  ];

  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return static_routes;

  const sql = neon(dbUrl);

  // Blog posts
  const posts = await sql`
    SELECT slug, published_at FROM blog_posts ORDER BY published_at DESC
  `.catch(() => []);

  const blog_routes: MetadataRoute.Sitemap = (posts as any[]).map(p => ({
    url: `${BASE}/blog/${p.slug}`,
    lastModified: new Date(p.published_at as string),
    changeFrequency: "monthly" as const,
    priority: 0.8,
  }));

  // Top 2000 INNs — high-value SEO drug pages
  const inns = await sql`
    SELECT
      lower(regexp_replace(trim(inn), '[^a-zA-Z0-9]+', '-', 'g')) AS slug,
      MAX(created_at) AS updated,
      COUNT(*) AS cnt
    FROM registrations
    WHERE inn IS NOT NULL
      AND length(trim(inn)) > 2
      AND lower(trim(inn)) NOT IN ('none', '—', '-', 'n/a')
    GROUP BY 1
    HAVING COUNT(*) >= 3
    ORDER BY cnt DESC
    LIMIT 2000
  `.catch(() => []);

  const drug_routes: MetadataRoute.Sitemap = (inns as any[]).map(r => ({
    url: `${BASE}/drugs/${r.slug}`,
    lastModified: r.updated ? new Date(r.updated as string) : new Date(),
    changeFrequency: "weekly" as const,
    priority: Math.min(0.9, 0.5 + Math.log10(Math.max(1, Number(r.cnt))) * 0.15),
  }));

  return [...static_routes, ...blog_routes, ...drug_routes];
}
