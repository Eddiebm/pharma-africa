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

  // Welcome email — fire and forget, never block signup
  const resendKey = process.env.RESEND_API_KEY;
  if (resendKey) {
    fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { "Authorization": `Bearer ${resendKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        from: "AfricaRegulatory <hello@africaregulatory.com>",
        to: [user.email as string],
        subject: "Welcome to AfricaRegulatory",
        html: `<!DOCTYPE html>
<html>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f9fafb;margin:0;padding:32px 16px;">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
    <div style="background:#1d4ed8;padding:24px 32px;">
      <div style="color:#fff;font-size:18px;font-weight:700;">AfricaRegulatory</div>
      <div style="color:#93c5fd;font-size:12px;margin-top:2px;">African Pharmaceutical Regulatory Intelligence</div>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#111827;margin:0 0 12px;font-size:20px;">You're in.</h2>
      <p style="color:#374151;font-size:15px;line-height:1.6;margin:0 0 20px;">
        You now have access to 96,000+ drug registrations across 16 African markets — searchable, filterable, and updated continuously.
      </p>
      <p style="color:#374151;font-size:15px;line-height:1.6;margin:0 0 28px;">
        Start by searching your portfolio, or upgrade to Pro to get expiry alerts 90 days before registrations lapse.
      </p>
      <div style="text-align:center;margin-bottom:28px;">
        <a href="https://africaregulatory.com/search"
           style="display:inline-block;background:#1d4ed8;color:#fff;padding:13px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;">
          Search the database →
        </a>
      </div>
      <p style="color:#9ca3af;font-size:12px;margin:0;padding-top:20px;border-top:1px solid #f3f4f6;">
        AfricaRegulatory · <a href="https://africaregulatory.com" style="color:#1d4ed8;text-decoration:none;">africaregulatory.com</a>
      </p>
    </div>
  </div>
</body>
</html>`,
      }),
    }).catch(() => { /* never surface email errors to the user */ });
  }

  return new Response(JSON.stringify({ ok: true, user: { id: user.id, email: user.email, plan: user.plan } }), {
    status: 201,
    headers: { "Content-Type": "application/json", "Set-Cookie": sessionCookieSet(token) },
  });
}
