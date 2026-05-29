export const runtime = "edge";

import { neon } from "@neondatabase/serverless";
import { verifyPassword, createToken, sessionCookieSet } from "@/app/lib/auth";

export async function POST(req: Request) {
  const url = process.env.DATABASE_URL;
  if (!url) return Response.json({ error: "Internal server error" }, { status: 500 });

  let body: { email?: string; password?: string };
  try { body = await req.json(); } catch { return Response.json({ error: "Invalid JSON" }, { status: 400 }); }

  const { email, password } = body;
  if (!email || !password) return Response.json({ error: "Email and password required" }, { status: 400 });

  const sql = neon(url);
  const [user] = await sql`
    SELECT id, email, password_hash, company_name, plan
    FROM users WHERE email = ${email.toLowerCase().trim()}
  `;

  if (!user || !(await verifyPassword(password, user.password_hash))) {
    return Response.json({ error: "Invalid email or password" }, { status: 401 });
  }

  const token = await createToken({ id: user.id, email: user.email, company_name: user.company_name, plan: user.plan });
  return new Response(JSON.stringify({ ok: true, user: { id: user.id, email: user.email, plan: user.plan } }), {
    headers: { "Content-Type": "application/json", "Set-Cookie": sessionCookieSet(token) },
  });
}
