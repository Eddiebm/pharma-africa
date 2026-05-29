export const runtime = "edge";

import { neon } from "@neondatabase/serverless";
import { verifyToken } from "@/app/lib/auth";

export async function PUT(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const user = await verifyToken(req);
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return Response.json({ error: "Internal server error" }, { status: 500 });

  const { id } = await params;
  let body: { country_codes?: string[]; expiry_days_threshold?: number; active?: boolean };
  try { body = await req.json(); } catch { return Response.json({ error: "Invalid JSON" }, { status: 400 }); }

  const sql = neon(dbUrl);
  const [sub] = await sql`
    UPDATE alert_subscriptions
    SET country_codes = COALESCE(${body.country_codes ?? null}, country_codes),
        expiry_days_threshold = COALESCE(${body.expiry_days_threshold ?? null}, expiry_days_threshold),
        active = COALESCE(${body.active ?? null}, active)
    WHERE id = ${id} AND user_id = ${user.id}
    RETURNING *
  `;
  if (!sub) return Response.json({ error: "Not found" }, { status: 404 });
  return Response.json({ subscription: sub });
}

export async function DELETE(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const user = await verifyToken(req);
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return Response.json({ error: "Internal server error" }, { status: 500 });

  const { id } = await params;
  const sql = neon(dbUrl);
  await sql`DELETE FROM alert_subscriptions WHERE id = ${id} AND user_id = ${user.id}`;
  return Response.json({ ok: true });
}
