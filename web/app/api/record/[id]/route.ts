export const runtime = "edge";

import { neon } from "@neondatabase/serverless";
import { verifyToken } from "@/app/lib/auth";

export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const user = await verifyToken(req);
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return Response.json({ error: "Internal server error" }, { status: 500 });

  const { id } = await params;
  const sql = neon(dbUrl);
  const [record] = await sql`
    SELECT id, inn, brand_name, country_code, registration_no, holder, local_agent,
           status, expiry_date, dosage_forms, source_url, source_type, last_verified, created_at
    FROM registrations WHERE id = ${id}
  `;

  if (!record) return Response.json({ error: "Not found" }, { status: 404 });

  // WHO prequalification check
  const whoRows = await sql`
    SELECT inn, product_name, manufacturer, dosage_form, strength, who_ref
    FROM who_prequalified WHERE LOWER(inn) = LOWER(${record.inn || ""})
    LIMIT 5
  `;

  return Response.json({ record, who_prequalified: whoRows });
}
