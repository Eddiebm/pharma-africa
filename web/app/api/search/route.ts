export const runtime = "edge";

import { neon } from "@neondatabase/serverless";
import { verifyToken } from "@/app/lib/auth";

const COUNTRIES: Record<string, string> = {
  ZA: "South Africa", NG: "Nigeria", KE: "Kenya", GH: "Ghana", RW: "Rwanda",
  TZ: "Tanzania", UG: "Uganda", ET: "Ethiopia", ZM: "Zambia", ZW: "Zimbabwe",
  MA: "Morocco", MW: "Malawi", EG: "Egypt", SN: "Senegal", CI: "Côte d'Ivoire",
  TN: "Tunisia",
};

export async function GET(req: Request) {
  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return Response.json({ error: "Internal server error" }, { status: 500 });

  const user = await verifyToken(req);
  const { searchParams } = new URL(req.url);
  const q = (searchParams.get("q") || "").trim();
  const country = searchParams.get("country") || "";
  const status = searchParams.get("status") || "";
  const expiryBefore = searchParams.get("expiry_before") || "";
  const expiryAfter = searchParams.get("expiry_after") || "";
  const page = Math.max(1, parseInt(searchParams.get("page") || "1"));
  const limit = 50;
  const offset = (page - 1) * limit;

  if (!q || q.length < 2) return Response.json({ results: [], total: 0, page, limit });

  const sql = neon(dbUrl);

  // Rate limit free users: 5 searches per day
  if (user?.plan === "free") {
    const today = new Date().toISOString().slice(0, 10);
    const [{ count }] = await sql`
      SELECT COUNT(*)::int AS count FROM search_logs
      WHERE user_id = ${user.id} AND created_at::date = ${today}::date
    `;
    if (count >= 5) {
      return Response.json({ error: "Daily search limit reached. Upgrade to Pro for unlimited searches.", limit_reached: true }, { status: 429 });
    }
  }

  const pattern = `%${q}%`;

  // Build dynamic query — parameterized
  const rows = await sql`
    SELECT r.id, r.inn, r.brand_name, r.country_code, r.registration_no,
           r.holder, r.local_agent, r.status, r.expiry_date,
           r.dosage_forms, r.source_url, r.last_verified,
           COUNT(*) OVER() AS total_count
    FROM registrations r
    WHERE (r.inn ILIKE ${pattern} OR r.brand_name ILIKE ${pattern})
      AND r.source_type != 'alert'
      AND (${country} = '' OR r.country_code = ${country})
      AND (${status} = '' OR r.status = ${status})
      AND (${expiryBefore} = '' OR r.expiry_date <= NULLIF(${expiryBefore}, '')::date)
      AND (${expiryAfter} = '' OR r.expiry_date >= NULLIF(${expiryAfter}, '')::date)
    ORDER BY CASE r.status WHEN 'active' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END,
             r.expiry_date DESC NULLS LAST
    LIMIT ${limit} OFFSET ${offset}
  `;

  const total = rows.length > 0 ? Number(rows[0].total_count) : 0;
  const results = rows.map((r: Record<string, unknown>) => ({
    ...r,
    total_count: undefined,
    country_name: COUNTRIES[r.country_code as string] || r.country_code,
  }));

  // Log search for authenticated users
  if (user) {
    await sql`
      INSERT INTO search_logs (user_id, query, country_code)
      VALUES (${user.id}, ${q}, ${country || null})
    `;
  }

  return Response.json({ results, total, page, limit });
}
