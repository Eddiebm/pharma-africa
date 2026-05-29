export const runtime = "edge";

import { neon } from "@neondatabase/serverless";
import { hashPassword, createToken, sessionCookieSet } from "@/app/lib/auth";

export async function POST(req: Request) {
  const url = process.env.DATABASE_URL;
  if (!url) return Response.json({ error: "Internal server error" }, { status: 500 });

  let body: { email?: string; password?: string; company_name?: string };
  try { body = await req.json(); } catch { return Response.json({ error: "Invalid JSON" }, { status: 400 }); }

  const { email, password, company_name } = body;
  if (!email || !password) return Response.json({ error: "Email and password required" }, { status: 400 });
  if (password.length < 8) return Response.json({ error: "Password must be at least 8 characters" }, { status: 400 });
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return Response.json({ error: "Invalid email" }, { status: 400 });

  const sql = neon(url);
  const existing = await sql`SELECT id FROM users WHERE email = ${email.toLowerCase().trim()}`;
  if (existing.length > 0) return Response.json({ error: "Email already registered" }, { status: 409 });

  const password_hash = await hashPassword(password);
  const [user] = await sql`
    INSERT INTO users (email, password_hash, company_name, plan)
    VALUES (${email.toLowerCase().trim()}, ${password_hash}, ${company_name || null}, 'free')
    RETURNING id, email, company_name, plan
  `;

  const token = await createToken({ id: user.id, email: user.email, company_name: user.company_name, plan: user.plan });
  return new Response(JSON.stringify({ ok: true, user: { id: user.id, email: user.email, plan: user.plan } }), {
    status: 201,
    headers: { "Content-Type": "application/json", "Set-Cookie": sessionCookieSet(token) },
  });
}
