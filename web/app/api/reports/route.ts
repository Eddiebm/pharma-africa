export const runtime = "edge";

import { neon } from "@neondatabase/serverless";

export async function GET(req: Request) {
  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return Response.json({ error: "Internal server error" }, { status: 500 });

  const { searchParams } = new URL(req.url);
  const limit = Math.min(24, parseInt(searchParams.get("limit") || "12"));

  const sql = neon(dbUrl);
  const reports = await sql`
    SELECT id, slug, title, description, pdf_path, period_start, period_end, published_at
    FROM monthly_reports
    ORDER BY period_start DESC
    LIMIT ${limit}
  `;

  return Response.json({ reports });
}
