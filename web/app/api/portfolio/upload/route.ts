export const runtime = "edge";

import { neon } from "@neondatabase/serverless";
import { verifyToken } from "@/app/lib/auth";

export async function POST(req: Request) {
  const user = await verifyToken(req);
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return Response.json({ error: "Internal server error" }, { status: 500 });

  const text = await req.text();
  const lines = text.split("\n").map(l => l.trim()).filter(Boolean);
  if (lines.length < 2) return Response.json({ error: "CSV must have a header and at least one row" }, { status: 400 });

  const header = lines[0].toLowerCase().split(",").map(h => h.trim());
  const drugIdx = header.indexOf("drug_name");
  const innIdx = header.indexOf("inn");
  if (drugIdx === -1) return Response.json({ error: "CSV must have a drug_name column" }, { status: 400 });

  const sql = neon(dbUrl);
  const rows = lines.slice(1).map(line => {
    const cols = line.split(",").map(c => c.trim().replace(/^"|"$/g, ""));
    return { drug_name: cols[drugIdx] || "", inn: innIdx >= 0 ? (cols[innIdx] || null) : null };
  }).filter(r => r.drug_name);

  if (rows.length === 0) return Response.json({ error: "No valid rows found" }, { status: 400 });
  if (rows.length > 500) return Response.json({ error: "Maximum 500 drugs per upload" }, { status: 400 });

  // Clear existing portfolio for this user and replace
  await sql`DELETE FROM portfolios WHERE user_id = ${user.id}`;

  for (const row of rows) {
    await sql`
      INSERT INTO portfolios (user_id, drug_name, inn)
      VALUES (${user.id}, ${row.drug_name}, ${row.inn})
    `;
  }

  return Response.json({ ok: true, imported: rows.length });
}
