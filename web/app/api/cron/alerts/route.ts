export const runtime = "edge";

import { neon } from "@neondatabase/serverless";

const COUNTRIES: Record<string, string> = {
  ZA: "South Africa", NG: "Nigeria", KE: "Kenya", GH: "Ghana", RW: "Rwanda",
  TZ: "Tanzania", UG: "Uganda", ET: "Ethiopia", ZM: "Zambia", ZW: "Zimbabwe",
  MA: "Morocco", MW: "Malawi", EG: "Egypt", SN: "Senegal", CI: "Côte d'Ivoire", TN: "Tunisia",
};

function fmt(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

function daysUntil(d: string) {
  return Math.ceil((new Date(d).getTime() - Date.now()) / 86400000);
}

function urgencyColor(days: number): string {
  if (days <= 30) return "#dc2626";
  if (days <= 60) return "#d97706";
  return "#059669";
}

function buildEmail(
  expiring: Record<string, unknown>[],
  threshold: number,
  countryCodes: string[],
): { subject: string; html: string } {
  const countryList = [...new Set(
    expiring.map(r => COUNTRIES[r.country_code as string] || r.country_code as string)
  )].join(", ");

  const subject = `${expiring.length} registration${expiring.length !== 1 ? "s" : ""} expiring within ${threshold} days — ${countryList}`;

  const rows = expiring.map(r => {
    const days = daysUntil(r.expiry_date as string);
    return `
      <tr>
        <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;font-weight:500;color:#111827;">${r.brand_name || r.inn}</td>
        <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;color:#6b7280;font-size:12px;">${r.inn}</td>
        <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;color:#374151;">${COUNTRIES[r.country_code as string] || r.country_code}</td>
        <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;font-weight:600;color:${urgencyColor(days)};">${fmt(r.expiry_date as string)}<br><span style="font-size:11px;font-weight:400;">${days}d</span></td>
        <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;color:#6b7280;font-size:12px;">${r.holder || "—"}</td>
        <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;color:#9ca3af;font-size:11px;">${r.registration_no || "—"}</td>
      </tr>`;
  }).join("");

  const html = `<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,sans-serif;background:#f9fafb;margin:0;padding:32px 16px;">
  <div style="max-width:680px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">

    <div style="background:#1d4ed8;padding:24px 32px;display:flex;align-items:center;gap:12px;">
      <div>
        <div style="color:#fff;font-size:18px;font-weight:700;letter-spacing:-0.3px;">AfricaRegulatory</div>
        <div style="color:#93c5fd;font-size:12px;margin-top:2px;">Registration Expiry Alert</div>
      </div>
    </div>

    <div style="padding:32px;">
      <p style="font-size:16px;color:#111827;margin:0 0 6px;">
        <strong>${expiring.length} registration${expiring.length !== 1 ? "s" : ""}</strong> in your monitored markets
        ${expiring.length !== 1 ? "are" : "is"} expiring within <strong>${threshold} days</strong>.
      </p>
      <p style="font-size:13px;color:#6b7280;margin:0 0 28px;">Markets covered: ${countryList}</p>

      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:13px;min-width:560px;">
          <thead>
            <tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb;">
              <th style="padding:10px 12px;text-align:left;color:#374151;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:0.05em;">Drug</th>
              <th style="padding:10px 12px;text-align:left;color:#374151;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:0.05em;">INN</th>
              <th style="padding:10px 12px;text-align:left;color:#374151;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:0.05em;">Country</th>
              <th style="padding:10px 12px;text-align:left;color:#374151;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:0.05em;">Expires</th>
              <th style="padding:10px 12px;text-align:left;color:#374151;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:0.05em;">Holder</th>
              <th style="padding:10px 12px;text-align:left;color:#374151;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:0.05em;">Reg No</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>

      <div style="margin-top:32px;text-align:center;">
        <a href="https://africaregulatory.com/portfolio"
           style="display:inline-block;background:#1d4ed8;color:#fff;padding:13px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;">
          View full portfolio →
        </a>
      </div>

      <div style="margin-top:32px;padding-top:20px;border-top:1px solid #f3f4f6;">
        <p style="font-size:12px;color:#9ca3af;margin:0;">
          You're receiving this because you have an active AfricaRegulatory Pro subscription monitoring
          ${countryCodes.length} market${countryCodes.length !== 1 ? "s" : ""}.
          <a href="https://africaregulatory.com/alerts" style="color:#1d4ed8;text-decoration:none;">Manage alerts</a> ·
          <a href="https://africaregulatory.com" style="color:#1d4ed8;text-decoration:none;">africaregulatory.com</a>
        </p>
      </div>
    </div>
  </div>
</body>
</html>`;

  return { subject, html };
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

  const subscriptions = await sql`
    SELECT
      s.id          AS sub_id,
      s.user_id,
      s.country_codes,
      s.expiry_days_threshold,
      u.email,
      u.company_name
    FROM alert_subscriptions s
    JOIN users u ON u.id = s.user_id
    WHERE s.active = true
      AND u.plan   = 'pro'
  `;

  if (subscriptions.length === 0) {
    return Response.json({ ok: true, sent: 0, skipped: 0, reason: "No active Pro subscriptions" });
  }

  let sent = 0;
  let skipped = 0;
  let errors = 0;

  for (const sub of subscriptions) {
    const threshold = sub.expiry_days_threshold as number;
    const countryCodes = sub.country_codes as string[];

    const expiring = await sql`
      SELECT r.id, r.inn, r.brand_name, r.holder, r.expiry_date, r.registration_no, r.country_code
      FROM registrations r
      WHERE r.status      = 'active'
        AND r.source_type != 'alert'
        AND r.country_code = ANY(${countryCodes})
        AND r.expiry_date BETWEEN NOW() AND NOW() + MAKE_INTERVAL(days => ${threshold})
        AND NOT EXISTS (
          SELECT 1 FROM alert_sends s
          WHERE s.registration_id = r.id
            AND s.company_id      = ${sub.user_id}
            AND s.sent_at        >= NOW() - INTERVAL '25 days'
        )
      ORDER BY r.expiry_date ASC
      LIMIT 50
    `;

    if (expiring.length === 0) {
      skipped++;
      continue;
    }

    const { subject, html } = buildEmail(expiring, threshold, countryCodes);

    const emailRes = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${resendKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: "AfricaRegulatory <alerts@africaregulatory.com>",
        to: [sub.email as string],
        subject,
        html,
      }),
    });

    if (!emailRes.ok) {
      console.error(`Alert send failed for ${sub.email}:`, await emailRes.text());
      errors++;
      continue;
    }

    // Record sends to prevent duplicates for the next 25 days
    for (const r of expiring) {
      await sql`
        INSERT INTO alert_sends (registration_id, company_id, trigger, sent_at)
        VALUES (${r.id as string}, ${sub.user_id as string}, ${"expiry-alert"}, now())
      `;
    }

    sent++;
  }

  return Response.json({ ok: true, sent, skipped, errors });
}
