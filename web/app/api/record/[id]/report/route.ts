export const runtime = "edge";

import { neon } from "@neondatabase/serverless";

const VALID_TYPES = ["wrong_status", "wrong_expiry", "wrong_holder", "not_found", "duplicate", "other"];

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return Response.json({ error: "Internal server error" }, { status: 500 });

  let body: { error_type?: string; notes?: string; reporter_email?: string };
  try { body = await req.json(); } catch { return Response.json({ error: "Invalid JSON" }, { status: 400 }); }

  const { error_type, notes, reporter_email } = body;
  if (!error_type || !VALID_TYPES.includes(error_type)) {
    return Response.json({ error: "Invalid error_type" }, { status: 400 });
  }

  const sql = neon(dbUrl);

  // Verify registration exists
  const [reg] = await sql`SELECT id FROM registrations WHERE id = ${id}`;
  if (!reg) return Response.json({ error: "Not found" }, { status: 404 });

  await sql`
    INSERT INTO error_reports (registration_id, error_type, notes, reporter_email)
    VALUES (${id}, ${error_type}, ${notes || null}, ${reporter_email || null})
  `;

  return Response.json({ ok: true });
}
