export const runtime = "edge";

import { neon } from "@neondatabase/serverless";

export async function GET(_req: Request, { params }: { params: Promise<{ slug: string }> }) {
  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return Response.json({ error: "Internal server error" }, { status: 500 });

  const { slug } = await params;
  const sql = neon(dbUrl);
  const [post] = await sql`
    SELECT id, slug, title, description, content, category, country_code, published_at
    FROM blog_posts WHERE slug = ${slug}
  `;

  if (!post) return Response.json({ error: "Not found" }, { status: 404 });
  return Response.json(post);
}
