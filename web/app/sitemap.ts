export const runtime = "edge";
export const dynamic = "force-dynamic";

import type { MetadataRoute } from "next";
import { neon } from "@neondatabase/serverless";

const BASE = "https://africaregulatory.com";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const MARKET_SLUGS = [
    "nigeria","south-africa","kenya","ghana","egypt","morocco","tunisia",
    "senegal","cote-divoire","uganda","tanzania","rwanda","malawi","zambia","zimbabwe","ethiopia",
  ];

  const static_routes: MetadataRoute.Sitemap = [
    { url: BASE,                  lastModified: new Date(), changeFrequency: "weekly",  priority: 1.0 },
    { url: `${BASE}/blog`,        lastModified: new Date(), changeFrequency: "daily",   priority: 0.9 },
    { url: `${BASE}/markets`,     lastModified: new Date(), changeFrequency: "monthly", priority: 0.9 },
    { url: `${BASE}/reports`,     lastModified: new Date(), changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE}/pricing`,     lastModified: new Date(), changeFrequency: "monthly", priority: 0.7 },
    { url: `${BASE}/signup`,      lastModified: new Date(), changeFrequency: "monthly", priority: 0.6 },
    { url: `${BASE}/login`,       lastModified: new Date(), changeFrequency: "monthly", priority: 0.4 },
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
  const posts = await sql`
    SELECT slug, published_at FROM blog_posts ORDER BY published_at DESC
  `;

  const blog_routes: MetadataRoute.Sitemap = posts.map(p => ({
    url: `${BASE}/blog/${p.slug}`,
    lastModified: new Date(p.published_at as string),
    changeFrequency: "monthly" as const,
    priority: 0.8,
  }));

  return [...static_routes, ...blog_routes];
}
