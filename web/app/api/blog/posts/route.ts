export const runtime = "edge";

import { neon } from "@neondatabase/serverless";

export async function GET(req: Request) {
  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return Response.json({ error: "Internal server error" }, { status: 500 });

  const { searchParams } = new URL(req.url);
  const category = searchParams.get("category") || "";
  const limit = Math.min(50, parseInt(searchParams.get("limit") || "20"));
  const offset = Math.max(0, parseInt(searchParams.get("offset") || "0"));

  const sql = neon(dbUrl);
  const posts = await sql`
    SELECT id, slug, title, description, category, country_code, published_at
    FROM blog_posts
    WHERE (${category} = '' OR category = ${category})
    ORDER BY published_at DESC
    LIMIT ${limit} OFFSET ${offset}
  `;

  const [{ total }] = await sql`
    SELECT COUNT(*)::int AS total FROM blog_posts
    WHERE (${category} = '' OR category = ${category})
  `;

  return Response.json({ posts, total });
}
