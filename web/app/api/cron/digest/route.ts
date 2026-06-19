export const runtime = "edge";

import { neon } from "@neondatabase/serverless";

const COUNTRIES: Record<string, string> = {
  ZA: "South Africa", NG: "Nigeria", KE: "Kenya", GH: "Ghana", RW: "Rwanda",
  TZ: "Tanzania", UG: "Uganda", ET: "Ethiopia", ZM: "Zambia", ZW: "Zimbabwe",
  MA: "Morocco", MW: "Malawi", EG: "Egypt", SN: "Senegal", CI: "Côte d'Ivoire", TN: "Tunisia",
};

function fmtDate(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

function buildDigestEmail(
  newApprovals: Record<string, unknown>[],
  expiryWatch: Record<string, unknown>[],
  totalNew: number,
): string {
  const weekStr = new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" });

  const approvalsHtml = newApprovals.length === 0
    ? `<tr><td colspan="3" style="padding:12px;text-align:center;color:#9ca3af;font-size:13px;">No new approvals today</td></tr>`
    : newApprovals.slice(0, 10).map(r => `
      <tr>
        <td style="padding:8px 12px;border-bottom:1px solid #f3f4f6;font-weight:500;color:#111827;font-size:13px;">${r.brand_name || r.inn}</td>
        <td style="padding:8px 12px;border-bottom:1px solid #f3f4f6;color:#6b7280;font-size:12px;">${COUNTRIES[r.country_code as string] || r.country_code}</td>
        <td style="padding:8px 12px;border-bottom:1px solid #f3f4f6;color:#6b7280;font-size:12px;">${r.holder || "—"}</td>
      </tr>`).join("");

  const expiryHtml = expiryWatch.length === 0
    ? `<tr><td colspan="3" style="padding:12px;text-align:center;color:#9ca3af;font-size:13px;">No critical expiries today</td></tr>`
    : expiryWatch.slice(0, 8).map(r => {
        const days = Math.ceil((new Date(r.expiry_date as string).getTime() - Date.now()) / 86400000);
        const color = days <= 30 ? "#dc2626" : "#d97706";
        return `
      <tr>
        <td style="padding:8px 12px;border-bottom:1px solid #f3f4f6;font-weight:500;color:#111827;font-size:13px;">${r.brand_name || r.inn}</td>
        <td style="padding:8px 12px;border-bottom:1px solid #f3f4f6;color:#6b7280;font-size:12px;">${COUNTRIES[r.country_code as string] || r.country_code}</td>
        <td style="padding:8px 12px;border-bottom:1px solid #f3f4f6;font-weight:600;font-size:12px;color:${color};">${fmtDate(r.expiry_date as string)}<br><span style="font-weight:400;">${days}d</span></td>
      </tr>`;
      }).join("");

  return `<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,sans-serif;background:#f9fafb;margin:0;padding:24px 16px;">
  <div style="max-width:620px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);">

    <div style="background:#1d4ed8;padding:20px 28px;">
      <div style="color:#fff;font-size:16px;font-weight:700;">AfricaRegulatory</div>
      <div style="color:#93c5fd;font-size:12px;margin-top:2px;">Daily Regulatory Digest · ${weekStr}</div>
    </div>

    <div style="padding:28px;">

      <p style="color:#374151;font-size:14px;margin:0 0 24px;line-height:1.6;">
        Here's today's snapshot of African pharmaceutical regulatory activity across 16 markets.
      </p>

      <!-- New Approvals -->
      <h2 style="font-size:14px;font-weight:700;color:#111827;margin:0 0 4px;">
        New approvals today
        <span style="font-weight:400;color:#6b7280;font-size:13px;">(${totalNew} total)</span>
      </h2>
      <p style="font-size:12px;color:#9ca3af;margin:0 0 12px;">Registrations added or verified in the last 24 hours</p>
      <div style="overflow-x:auto;margin-bottom:28px;">
        <table style="width:100%;border-collapse:collapse;border:1px solid #f3f4f6;border-radius:8px;overflow:hidden;">
          <thead>
            <tr style="background:#f8fafc;">
              <th style="padding:8px 12px;text-align:left;color:#374151;font-size:11px;text-transform:uppercase;letter-spacing:0.05em;">Drug</th>
              <th style="padding:8px 12px;text-align:left;color:#374151;font-size:11px;text-transform:uppercase;letter-spacing:0.05em;">Market</th>
              <th style="padding:8px 12px;text-align:left;color:#374151;font-size:11px;text-transform:uppercase;letter-spacing:0.05em;">Holder</th>
            </tr>
          </thead>
          <tbody>${approvalsHtml}</tbody>
        </table>
      </div>

      <!-- Expiry Watch -->
      <h2 style="font-size:14px;font-weight:700;color:#111827;margin:0 0 4px;">Expiry watch</h2>
      <p style="font-size:12px;color:#9ca3af;margin:0 0 12px;">Active registrations expiring within 60 days across all markets</p>
      <div style="overflow-x:auto;margin-bottom:28px;">
        <table style="width:100%;border-collapse:collapse;border:1px solid #f3f4f6;border-radius:8px;overflow:hidden;">
          <thead>
            <tr style="background:#f8fafc;">
              <th style="padding:8px 12px;text-align:left;color:#374151;font-size:11px;text-transform:uppercase;letter-spacing:0.05em;">Drug</th>
              <th style="padding:8px 12px;text-align:left;color:#374151;font-size:11px;text-transform:uppercase;letter-spacing:0.05em;">Market</th>
              <th style="padding:8px 12px;text-align:left;color:#374151;font-size:11px;text-transform:uppercase;letter-spacing:0.05em;">Expires</th>
            </tr>
          </thead>
          <tbody>${expiryHtml}</tbody>
        </table>
      </div>

      <!-- Upgrade CTA -->
      <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:16px 20px;margin-bottom:24px;">
        <p style="color:#1e40af;font-size:13px;font-weight:600;margin:0 0 4px;">Get personalised expiry alerts</p>
        <p style="color:#3b82f6;font-size:12px;margin:0 0 12px;">Upgrade to Pro to monitor your specific portfolio and receive alerts 90 days before any registration expires.</p>
        <a href="https://africaregulatory.com/pricing"
           style="display:inline-block;background:#1d4ed8;color:#fff;padding:8px 20px;border-radius:6px;text-decoration:none;font-weight:600;font-size:12px;">
          Upgrade to Pro →
        </a>
      </div>

      <div style="border-top:1px solid #f3f4f6;padding-top:16px;">
        <p style="font-size:11px;color:#9ca3af;margin:0;">
          You're receiving this as a registered AfricaRegulatory user.
          <a href="https://africaregulatory.com/account" style="color:#1d4ed8;text-decoration:none;">Manage preferences</a> ·
          <a href="https://africaregulatory.com" style="color:#1d4ed8;text-decoration:none;">africaregulatory.com</a>
        </p>
      </div>
    </div>
  </div>
</body>
</html>`;
}

export async function POST(req: Request) {
  const secret = process.env.CRON_SECRET;
  if (!secret || req.headers.get("authorization") !== `Bearer ${secret}`) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const dbUrl = process.env.DATABASE_URL;
  const resendKey = process.env.RESEND_API_KEY;
  if (!dbUrl) return Response.json({ error: "Internal server error" }, { status: 500 });
  if (!resendKey) return Response.json({ error: "RESEND_API_KEY not configured" }, { status: 503 });

  const sql = neon(dbUrl);

  // Get all free users (plan = 'free')
  const freeUsers = await sql`SELECT id, email FROM users WHERE plan = 'free'`;
  if (freeUsers.length === 0) {
    return Response.json({ ok: true, sent: 0, reason: "No free users" });
  }

  // New approvals in last 7 days (verified or created recently, active)
  const newApprovals = await sql`
    SELECT inn, brand_name, holder, country_code
    FROM registrations
    WHERE source_type != 'alert'
      AND status = 'active'
      AND last_verified >= NOW() - INTERVAL '24 hours'
    ORDER BY last_verified DESC
    LIMIT 20
  `;

  // Expiry watch — active registrations expiring within 60 days
  const expiryWatch = await sql`
    SELECT inn, brand_name, country_code, expiry_date
    FROM registrations
    WHERE source_type != 'alert'
      AND status = 'active'
      AND expiry_date BETWEEN NOW() AND NOW() + INTERVAL '60 days'
    ORDER BY expiry_date ASC
    LIMIT 15
  `;

  const html = buildDigestEmail(
    newApprovals as unknown as Record<string, unknown>[],
    expiryWatch as unknown as Record<string, unknown>[],
    newApprovals.length,
  );

  const subject = `AfricaRegulatory daily digest — ${new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" })}`;

  let sent = 0;
  let errors = 0;

  for (const user of freeUsers) {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { "Authorization": `Bearer ${resendKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        from: "AfricaRegulatory <hello@africaregulatory.com>",
        to: [user.email as string],
        subject,
        html,
      }),
    });
    if (res.ok) { sent++; } else { errors++; }
  }

  return Response.json({ ok: true, sent, errors, users: freeUsers.length });
}
