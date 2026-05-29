export const runtime = "edge";

import { neon } from "@neondatabase/serverless";
import { verifyToken } from "@/app/lib/auth";

export async function GET(req: Request) {
  const user = await verifyToken(req);
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return Response.json({ error: "Internal server error" }, { status: 500 });

  const sql = neon(dbUrl);
  const rows = await sql`SELECT * FROM alert_subscriptions WHERE user_id = ${user.id} ORDER BY created_at DESC`;
  return Response.json({ subscriptions: rows });
}

export async function POST(req: Request) {
  const user = await verifyToken(req);
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });
  if (user.plan === "free") return Response.json({ error: "Alerts require a Pro plan" }, { status: 403 });

  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return Response.json({ error: "Internal server error" }, { status: 500 });

  let body: { country_codes?: string[]; expiry_days_threshold?: number };
  try { body = await req.json(); } catch { return Response.json({ error: "Invalid JSON" }, { status: 400 }); }

  const { country_codes = [], expiry_days_threshold = 90 } = body;
  if (!Array.isArray(country_codes) || country_codes.length === 0) {
    return Response.json({ error: "At least one country required" }, { status: 400 });
  }

  const sql = neon(dbUrl);
  const [sub] = await sql`
    INSERT INTO alert_subscriptions (user_id, country_codes, expiry_days_threshold, active)
    VALUES (${user.id}, ${country_codes}, ${expiry_days_threshold}, true)
    RETURNING *
  `;
  return Response.json({ subscription: sub }, { status: 201 });
}
